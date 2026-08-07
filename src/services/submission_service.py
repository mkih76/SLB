import json
from datetime import datetime
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
    db = get_db()
    sub = db.execute("SELECT share_token FROM submissions WHERE sid = ?", (sid,)).fetchone()
    if not sub:
        return None
    if sub['share_token']:
        return sub['share_token']
    token = generate_uuid()[:12]
    db.execute("UPDATE submissions SET share_token = ? WHERE sid = ?", (token, sid))
    db.commit()
    return token


def get_submission_by_share_token(token: str):
    db = get_db()
    sub = db.execute(
        "SELECT s.*, p.title as paper_title FROM submissions s "
        "JOIN papers p ON s.pid = p.pid WHERE s.share_token = ?",
        (token,)
    ).fetchone()
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
