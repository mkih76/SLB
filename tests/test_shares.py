"""批改结果分享功能测试"""
import json
from datetime import datetime, timedelta
import pytest

from src.api.utils import get_db


def _register(client, username, password='testpass123'):
    resp = client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'nickname': username,
    })
    assert resp.status_code in (200, 201), resp.get_data(as_text=True)
    return resp.get_json()


def _insert_paper_and_submission(app, uid, sid='test_sub1'):
    """向测试库插入一张试卷和一条提交记录（uid 需先在 users 表存在以通过外键约束）"""
    with app.app_context():
        db = get_db()
        db.execute(
            """INSERT OR IGNORE INTO users (uid, username, password_hash, nickname, role, status)
               VALUES (?, ?, ?, ?, 'user', 'active')""",
            (uid, 'user_' + uid[:8], 'x', '测试用户')
        )
        db.execute(
            """INSERT OR IGNORE INTO papers (pid, source, exam_type, year, title, material, questions, answer_keys)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            ('test_p1', 'test', '国考', 2026, '测试卷',
             json.dumps(['材料一']), json.dumps([{'qid': 'q1', 'stem': '题目'}]),
             json.dumps({'q1': '答案'}))
        )
        db.execute(
            """INSERT OR REPLACE INTO submissions
               (sid, uid, pid, qid, user_answer, score, dimension_scores, ai_feedback,
                hit_points, missing_points, improving_suggestions, graded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (sid, uid, 'test_p1', 'q1', '我的答案', 82.5,
             json.dumps({'踩点命中': 30, '逻辑结构': 22}),
             'AI反馈', json.dumps(['要点A']), json.dumps(['要点B']),
             '改进建议', '2026-01-01T10:00:00')
        )
        db.commit()


class TestShareResult:
    """分享链接：生成、公开读取、隐私保护、越权校验"""

    def test_create_share_generates_token(self, app, client):
        """本人可为自己的提交生成分享 token"""
        data = _register(client, 'share_owner')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)

        resp = client.post('/api/submissions/test_sub1/share',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        body = resp.get_json()
        assert body['data']['share_token']
        assert body['data']['share_url'] == f"/share/{body['data']['share_token']}"

    def test_share_is_idempotent(self, app, client):
        """同一提交重复生成返回同一 token"""
        data = _register(client, 'share_owner2')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)

        r1 = client.post('/api/submissions/test_sub1/share',
                         headers={'Authorization': f'Bearer {token}'}).get_json()
        r2 = client.post('/api/submissions/test_sub1/share',
                         headers={'Authorization': f'Bearer {token}'}).get_json()
        assert r1['data']['share_token'] == r2['data']['share_token']

    def test_share_requires_auth(self, app, client):
        """未登录不能创建分享"""
        _insert_paper_and_submission(app, 'u_any')
        resp = client.post('/api/submissions/test_sub1/share')
        assert resp.status_code in (401, 403)

    def test_cannot_share_others_submission(self, app, client):
        """不能为别人的提交生成分享（404）"""
        _insert_paper_and_submission(app, 'u_owner')
        data = _register(client, 'share_intruder')
        token = data['data']['token']

        resp = client.post('/api/submissions/test_sub1/share',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 404

    def test_get_shared_submission_public(self, app, client):
        """公开读取分享内容，且不含 user_answer（隐私保护）"""
        data = _register(client, 'share_owner3')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)

        st = client.post('/api/submissions/test_sub1/share',
                         headers={'Authorization': f'Bearer {token}'}).get_json()
        share_token = st['data']['share_token']

        # 不携带任何鉴权头
        resp = client.get(f'/api/submissions/share/{share_token}')
        assert resp.status_code == 200
        body = resp.get_json()['data']
        assert body['score'] == 82.5
        assert body['paper_title'] == '测试卷'
        assert body['dimension_scores'] == {'踩点命中': 30, '逻辑结构': 22}
        assert 'user_answer' not in body
        assert '我的答案' not in json.dumps(body)

    def test_invalid_share_token_404(self, client):
        """无效分享 token 返回 404"""
        resp = client.get('/api/submissions/share/nonexistent')
        assert resp.status_code == 404
    def test_share_blocked_after_free_trial_used(self, app, client):
        """免费试用已用完的非 VIP 用户不能生成分享（403）"""
        data = _register(client, 'share_freeused')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)
        # 模拟免费试用已用完
        with app.app_context():
            db = get_db()
            db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (uid,))
            db.commit()

        resp = client.post('/api/submissions/test_sub1/share',
                           headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403

    def test_revoke_share_removes_access(self, app, client):
        """撤销分享后，原链接返回 404"""
        data = _register(client, 'share_revoke')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)

        st = client.post('/api/submissions/test_sub1/share',
                         headers={'Authorization': f'Bearer {token}'}).get_json()
        share_token = st['data']['share_token']
        # 撤销前可访问
        assert client.get(f'/api/submissions/share/{share_token}').status_code == 200

        resp = client.delete('/api/submissions/test_sub1/share',
                             headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        # 撤销后 404
        assert client.get(f'/api/submissions/share/{share_token}').status_code == 404

    def test_expired_share_token_404(self, app, client):
        """已过期的分享链接返回 404"""
        data = _register(client, 'share_expired')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)
        # 直接把 share_expires_at 设为过去时间
        with app.app_context():
            db = get_db()
            db.execute(
                "UPDATE submissions SET share_token = 'expiredtoken', share_expires_at = ? WHERE sid = 'test_sub1'",
                ((datetime.now() - timedelta(days=1)).isoformat(),)
            )
            db.commit()

        resp = client.get('/api/submissions/share/expiredtoken')
        assert resp.status_code == 404
    def test_revoke_others_share_404(self, app, client):
        """不能撤销别人的分享（404）"""
        _insert_paper_and_submission(app, 'u_owner2')
        data = _register(client, 'share_intruder2')
        token = data['data']['token']
        # 先由 owner 生成分享
        owner_data = _register(client, 'share_owner2b')
        owner_uid = owner_data['data']['uid']
        owner_token = owner_data['data']['token']
        _insert_paper_and_submission(app, owner_uid, sid='test_sub2')
        # 用 intruder 撤销 owner 的提交
        resp = client.delete('/api/submissions/test_sub2/share',
                             headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 404

    def test_regenerate_after_expiry(self, app, client):
        """过期后重新生成分享得到新 token，且新 token 可用"""
        data = _register(client, 'share_regen')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper_and_submission(app, uid)
        # 先置为过期 token
        with app.app_context():
            db = get_db()
            db.execute(
                "UPDATE submissions SET share_token = 'oldtoken', share_expires_at = ? WHERE sid = 'test_sub1'",
                ((datetime.now() - timedelta(days=1)).isoformat(),)
            )
            db.commit()
        # 重新生成
        st = client.post('/api/submissions/test_sub1/share',
                         headers={'Authorization': f'Bearer {token}'}).get_json()
        new_token = st['data']['share_token']
        assert new_token != 'oldtoken'
        # 新 token 可访问，旧 token 404
        assert client.get(f'/api/submissions/share/{new_token}').status_code == 200
        assert client.get('/api/submissions/share/oldtoken').status_code == 404
