import json
from src.api.utils import get_db


def get_phrases(source=None, tag=None, status='approved', page=1, per_page=20):
    db = get_db()
    query = "SELECT * FROM good_phrases WHERE status = ?"
    params = [status]

    if source:
        query += " AND source = ?"
        params.append(source)
    if tag:
        query += " AND tag LIKE ?"
        params.append(f'%{tag}%')

    query += " ORDER BY heat DESC, created_at DESC"

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    phrases = db.execute(query, params).fetchall()

    return {
        'phrases': [dict(p) for p in phrases],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }


def get_phrase_by_id(phrase_id: int):
    db = get_db()
    phrase = db.execute("SELECT * FROM good_phrases WHERE id = ?", (phrase_id,)).fetchone()
    return dict(phrase) if phrase else None


def add_phrase(phrase_data: dict):
    db = get_db()
    db.execute(
        """INSERT INTO good_phrases (phrase, translation, usage, source, source_url, source_date, tag, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (
            phrase_data['phrase'],
            phrase_data.get('translation'),
            phrase_data.get('usage'),
            phrase_data['source'],
            phrase_data.get('source_url'),
            phrase_data.get('source_date'),
            json.dumps(phrase_data.get('tag', []), ensure_ascii=False)
        )
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid() as id").fetchone()['id']


def approve_phrase(phrase_id: int, admin_uid: str):
    db = get_db()
    db.execute(
        "UPDATE good_phrases SET status = 'approved', approved_by = ? WHERE id = ?",
        (admin_uid, phrase_id)
    )
    db.commit()


def reject_phrase(phrase_id: int):
    db = get_db()
    db.execute(
        "UPDATE good_phrases SET status = 'rejected' WHERE id = ?",
        (phrase_id,)
    )
    db.commit()


def favorite_phrase(uid: str, phrase_id: int, note: str = None):
    db = get_db()
    try:
        db.execute(
            "INSERT OR IGNORE INTO user_favorites (uid, phrase_id, note) VALUES (?, ?, ?)",
            (uid, phrase_id, note)
        )
        db.execute("UPDATE good_phrases SET heat = heat + 1 WHERE id = ?", (phrase_id,))
        db.commit()
        return True
    except:
        return False


def unfavorite_phrase(uid: str, phrase_id: int):
    db = get_db()
    db.execute("DELETE FROM user_favorites WHERE uid = ? AND phrase_id = ?", (uid, phrase_id))
    db.commit()


def get_user_favorites(uid: str, page=1, per_page=20):
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM user_favorites WHERE uid = ?", (uid,)
    ).fetchone()[0]

    favorites = db.execute(
        """SELECT p.*, uf.note as user_note, uf.created_at as favorited_at
           FROM user_favorites uf
           JOIN good_phrases p ON uf.phrase_id = p.id
           WHERE uf.uid = ?
           ORDER BY uf.created_at DESC
           LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    return {
        'phrases': [dict(f) for f in favorites],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }
