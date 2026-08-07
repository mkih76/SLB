import json
from datetime import datetime, timedelta
from src.api.utils import get_db, generate_uuid


def create_submission(uid: str, pid: str, qid: str, user_answer: str):
    db = get_db()
    sid = 'sub_' + generate_uuid()

    db.execute(
        """INSERT INTO submissions (sid, uid, pid, qid, user_answer, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sid, uid, pid, qid, user_answer, datetime.now().isoformat())
    )
    db.commit()
    return sid




def generate_share_token(sid: str) -> str:
    """生成分享 token，过期时间为 30 天。已存在的有效 token 直接复用。"""
    db = get_db()
    sub = db.execute("SELECT share_token, share_expires_at FROM submissions WHERE sid = ?", (sid,)).fetchone()
    if not sub:
        return None
    # 已有未过期的 token 直接返回
    if sub['share_token'] and sub['share_expires_at']:
        expires = datetime.fromisoformat(sub['share_expires_at'])
        if expires > datetime.now():
            return sub['share_token']
    token = generate_uuid()[:12]
    expires_at = (datetime.now() + timedelta(days=30)).isoformat()
    db.execute(
        "UPDATE submissions SET share_token = ?, share_expires_at = ? WHERE sid = ?",
        (token, expires_at, sid)
    )
    db.commit()
    return token


def revoke_share_token(sid: str) -> bool:
    """撤销分享链接（清空 token 与过期时间）"""
    db = get_db()
    cur = db.execute(
        "UPDATE submissions SET share_token = NULL, share_expires_at = NULL WHERE sid = ?",
        (sid,)
    )
    db.commit()
    return cur.rowcount > 0


def get_submission_by_share_token(token: str):
    """按 token 查分享；已过期的视为无效"""
    db = get_db()
    sub = db.execute(
        "SELECT s.*, p.title as paper_title FROM submissions s "
        "JOIN papers p ON s.pid = p.pid WHERE s.share_token = ?",
        (token,)
    ).fetchone()
    if not sub:
        return None
    if sub['share_expires_at']:
        expires = datetime.fromisoformat(sub['share_expires_at'])
        if expires <= datetime.now():
            return None
    return dict(sub) if sub else None

def get_submission(sid: str):
    db = get_db()
    sub = db.execute(
        "SELECT s.*, p.title as paper_title FROM submissions s "
        "JOIN papers p ON s.pid = p.pid WHERE s.sid = ?",
        (sid,)
    ).fetchone()
    return dict(sub) if sub else None


def update_submission_grading(sid: str, score: float, dimension_scores: dict,
                              ai_feedback: str, hit_points: list, missing_points: list,
                              improving_suggestions: str = None):
    db = get_db()
    db.execute(
        """UPDATE submissions SET
           score = ?, dimension_scores = ?, ai_feedback = ?,
           hit_points = ?, missing_points = ?, improving_suggestions = ?,
           graded_at = ?, is_reviewed = 0, needs_review = ?
           WHERE sid = ?""",
        (
            score,
            json.dumps(dimension_scores, ensure_ascii=False),
            ai_feedback,
            json.dumps(hit_points, ensure_ascii=False),
            json.dumps(missing_points, ensure_ascii=False),
            improving_suggestions,
            datetime.now().isoformat(),
            1 if score is not None and score < 60 else 0,
            sid
        )
    )
    db.commit()


def get_user_submissions(uid: str, page=1, per_page=20):
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM submissions WHERE uid = ?", (uid,)
    ).fetchone()[0]

    subs = db.execute(
        """SELECT s.*, p.title as paper_title
           FROM submissions s
           JOIN papers p ON s.pid = p.pid
           WHERE s.uid = ?
           ORDER BY s.created_at DESC
           LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    return {
        'submissions': [dict(s) for s in subs],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }


def record_learning(uid: str, action: str, target_id: str, score: float = None):
    db = get_db()
    db.execute(
        """INSERT INTO learning_records (uid, action, target_id, score)
           VALUES (?, ?, ?, ?)""",
        (uid, action, target_id, score)
    )
    db.commit()
