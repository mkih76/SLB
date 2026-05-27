from src.api.utils import get_db


def record_weak_point(uid: str, missing_key: str, topic_tag: str = None, pid: str = None, qid: str = None):
    db = get_db()
    existing = db.execute(
        "SELECT * FROM weak_points WHERE uid = ? AND missing_key = ?",
        (uid, missing_key)
    ).fetchone()

    if existing:
        db.execute(
            "UPDATE weak_points SET times_missed = times_missed + 1 WHERE uid = ? AND missing_key = ?",
            (uid, missing_key)
        )
    else:
        db.execute(
            """INSERT INTO weak_points (uid, missing_key, topic_tag, pid, qid)
               VALUES (?, ?, ?, ?, ?)""",
            (uid, missing_key, topic_tag, pid, qid)
        )
    db.commit()


def get_user_weak_points(uid: str, topic_tag: str = None):
    db = get_db()
    query = "SELECT * FROM weak_points WHERE uid = ?"
    params = [uid]

    if topic_tag:
        query += " AND topic_tag = ?"
        params.append(topic_tag)

    query += " ORDER BY times_missed DESC"
    points = db.execute(query, params).fetchall()
    return [dict(p) for p in points]


def get_weak_point_stats(uid: str):
    db = get_db()
    stats = db.execute(
        """SELECT topic_tag, COUNT(*) as count, SUM(times_missed) as total_missed
           FROM weak_points WHERE uid = ? AND topic_tag IS NOT NULL
           GROUP BY topic_tag""",
        (uid,)
    ).fetchall()
    return [dict(s) for s in stats]


def mark_reviewed(weak_id: int):
    db = get_db()
    from datetime import datetime
    db.execute(
        "UPDATE weak_points SET review_count = review_count + 1, last_reviewed = ? WHERE id = ?",
        (datetime.now().isoformat(), weak_id)
    )
    db.commit()
