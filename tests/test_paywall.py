"""付费墙门控测试：drill 提交 + demo 限流"""
import json
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


def _insert_paper(app, pid='test_p1'):
    """插入一张含题目和要点答案的试卷"""
    with app.app_context():
        db = get_db()
        db.execute(
            """INSERT OR IGNORE INTO papers (pid, source, exam_type, year, title, material, questions, answer_keys)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (pid, 'test', '国考', 2026, '测试卷',
             json.dumps(['材料一']),
             json.dumps([{'qid': 'q1', 'type': 'guina', 'stem': '概括要点',
                          'score_max': 10, 'word_limit': '200字',
                          'key_points': [{'point': '要点A', 'score': 5, 'alias': ['A']}],
                          'model_answer': '标准答案', 'scoring_rule': '按点给分'}]),
             json.dumps({'q1': '标准答案'}))
        )
        db.commit()


@pytest.fixture
def mock_grader(monkeypatch):
    """mock 掉 LLM 批改，返回固定结果（避免真实调用消耗 API）"""
    from src.api import drill as drill_api, papers as papers_api

    def fake_grade(pid, qid, question, user_answer, material=None):
        return {
            'score': 82.5,
            'dimension_scores': {'踩点命中': 30, '逻辑结构': 22},
            'ai_feedback': '整体良好，继续加油',
            'hit_points': ['要点A'],
            'missing_points': ['要点B'],
            'improving_suggestions': '补充要点B'
        }
    monkeypatch.setattr(drill_api, 'grade_answer', fake_grade)
    monkeypatch.setattr(papers_api, 'grade_answer', fake_grade)


@pytest.fixture
def reset_rate():
    """每个 demo 测试前重置限流计数，避免测试间串扰"""
    from src.api.papers import _demo_rate, _demo_total
    _demo_rate.clear()
    _demo_total.clear()


class TestDrillPaywall:
    """drill/submit 的付费墙门控"""

    def test_drill_free_trial_allowed(self, app, client, mock_grader):
        """免费试用未用完的用户可获得完整批改反馈"""
        data = _register(client, 'drill_free')
        token = data['data']['token']
        _insert_paper(app)
        resp = client.post('/api/drill/submit', json={
            'pid': 'test_p1', 'qid': 'q1', 'user_answer': '我的答案'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        body = resp.get_json()['data']
        assert 'dimension_scores' in body or 'ai_feedback' in body

    def test_drill_blocked_after_trial(self, app, client, mock_grader):
        """免费试用用完的非 VIP 用户在调用 LLM 前被拦截（upgrade_required）"""
        data = _register(client, 'drill_used')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper(app)
        with app.app_context():
            db = get_db()
            db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (uid,))
            db.commit()
        resp = client.post('/api/drill/submit', json={
            'pid': 'test_p1', 'qid': 'q1', 'user_answer': '我的答案'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        body = resp.get_json()['data']
        assert body['upgrade_required'] is True
        # 详细反馈被隐藏
        assert 'ai_feedback' not in body
        assert 'dimension_scores' not in body


class TestDemoRateLimit:
    """demo/grade 的 IP 限流"""

    def test_demo_allowed_within_limit(self, app, client, mock_grader, reset_rate):
        """5 次内正常返回"""
        _insert_paper(app)
        ok = 0
        for _ in range(5):
            resp = client.post('/api/papers/demo/grade', json={
                'pid': 'test_p1', 'qid': 'q1', 'user_answer': '测试答案'
            })
            if resp.status_code == 200:
                ok += 1
        assert ok == 5  # 5 次内全部成功

    def test_demo_rate_limited(self, app, client, mock_grader, reset_rate):
        """超过 5 次返回 429"""
        _insert_paper(app)
        last = None
        for _ in range(8):
            last = client.post('/api/papers/demo/grade', json={
                'pid': 'test_p1', 'qid': 'q1', 'user_answer': '测试答案'
            })
        assert last.status_code == 429  # 第 6 次起应被限流



class TestHistoryPaywall:
    """GET /api/submissions/history 的付费墙门控"""

    def _create_graded_submission(self, app, client, token, uid):
        """创建一条带完整反馈的提交记录（直接写库，避免走 LLM）"""
        with app.app_context():
            db = get_db()
            db.execute(
                """INSERT OR IGNORE INTO papers (pid, source, exam_type, year, title, material, questions, answer_keys)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                ('hist_p1', 'test', '国考', 2026, '历史卷',
                 json.dumps(['材料']), json.dumps([{'qid': 'q1'}]), json.dumps({'q1': '答案'}))
            )
            db.execute(
                """INSERT OR REPLACE INTO submissions
                   (sid, uid, pid, qid, user_answer, score, dimension_scores, ai_feedback,
                    hit_points, missing_points, improving_suggestions, graded_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                ('hist_sub1', uid, 'hist_p1', 'q1', '我的答案', 80.0,
                 json.dumps({'踩点命中': 30}), 'AI反馈内容', json.dumps(['要点A']),
                 json.dumps(['要点B']), '改进建议', '2026-01-01T00:00:00')
            )
            db.commit()

    def test_history_full_detail_for_free_trial(self, app, client, mock_grader):
        """免费试用未用完的用户在历史中能看到完整反馈"""
        data = _register(client, 'hist_free')
        uid = data['data']['uid']
        token = data['data']['token']
        self._create_graded_submission(app, client, token, uid)
        resp = client.get('/api/submissions/history',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        subs = resp.get_json()['data']['submissions']
        assert len(subs) >= 1
        assert 'ai_feedback' in subs[0]

    def test_history_strips_feedback_after_trial(self, app, client, mock_grader):
        """免费试用用完的非 VIP 用户在历史中看不到详细反馈"""
        data = _register(client, 'hist_used')
        uid = data['data']['uid']
        token = data['data']['token']
        self._create_graded_submission(app, client, token, uid)
        with app.app_context():
            db = get_db()
            db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (uid,))
            db.commit()
        resp = client.get('/api/submissions/history',
                          headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200
        subs = resp.get_json()['data']['submissions']
        assert len(subs) >= 1
        assert 'ai_feedback' not in subs[0]
        assert 'dimension_scores' not in subs[0]



class TestSubmissionPaywall:
    """POST /api/submissions 主提交端点的付费墙"""

    def test_submission_blocked_after_trial(self, app, client, mock_grader):
        """免费试用用完的非 VIP 用户提交被 403 拦截（不调 LLM）"""
        data = _register(client, 'sub_used')
        uid = data['data']['uid']
        token = data['data']['token']
        _insert_paper(app)
        with app.app_context():
            db = get_db()
            db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (uid,))
            db.commit()
        resp = client.post('/api/submissions', json={
            'pid': 'test_p1', 'qid': 'q1', 'user_answer': '我的答案'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403

    def test_submission_allowed_for_free_trial(self, app, client, mock_grader):
        """免费试用未用完的用户可正常提交"""
        data = _register(client, 'sub_free')
        token = data['data']['token']
        _insert_paper(app)
        resp = client.post('/api/submissions', json={
            'pid': 'test_p1', 'qid': 'q1', 'user_answer': '我的答案'
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 200



class TestSimulationPaywall:
    """POST /api/simulation/submit 的付费墙"""

    def test_simulation_blocked_after_trial(self, app, client, mock_grader):
        """免费试用用完的非 VIP 用户提交模拟考被 403 拦截"""
        data = _register(client, 'sim_used')
        uid = data['data']['uid']
        token = data['data']['token']
        with app.app_context():
            db = get_db()
            db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (uid,))
            db.commit()
        resp = client.post('/api/simulation/submit', json={
            'sim_id': 'sim_x', 'answers': {'q1': '答案'}
        }, headers={'Authorization': f'Bearer {token}'})
        assert resp.status_code == 403