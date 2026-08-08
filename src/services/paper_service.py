import json
from datetime import datetime
from src.api.utils import get_db, generate_uuid


def get_papers(exam_type=None, year=None, province=None, status='published', page=1, per_page=20):
    db = get_db()
    query = "SELECT * FROM papers WHERE status = ?"
    params = [status]

    if exam_type:
        query += " AND exam_type = ?"
        params.append(exam_type)
    if year:
        query += " AND year = ?"
        params.append(year)
    if province:
        query += " AND province = ?"
        params.append(province)

    query += " ORDER BY created_at DESC"

    # Count total
    count_query = query.replace("SELECT *", "SELECT COUNT(*)")
    total = db.execute(count_query, params).fetchone()[0]

    # Paginate
    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    papers = db.execute(query, params).fetchall()

    return {
        'papers': [dict(p) for p in papers],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }


def get_paper_by_pid(pid: str):
    db = get_db()
    paper = db.execute("SELECT * FROM papers WHERE pid = ?", (pid,)).fetchone()
    return dict(paper) if paper else None


def get_question_by_qid(pid: str, qid: str):
    paper = get_paper_by_pid(pid)
    if not paper:
        return None

    questions = json.loads(paper['questions'])
    for q in questions:
        if q.get('qid') == qid:
            return {
                'qid': q.get('qid'),
                'type': q.get('type'),
                'stem': q.get('stem'),
                'score_max': q.get('score_max'),
                'word_limit': q.get('word_limit'),
                'key_points': q.get('key_points') or [],
                'material': json.loads(paper['material']) if paper['material'] else []
            }
    return None


def create_paper(paper_data: dict):
    db = get_db()
    pid = paper_data.get('pid') or f"custom_{generate_uuid()[:8]}"

    db.execute(
        """INSERT INTO papers (pid, source, exam_type, year, season, province, title,
           material, questions, answer_keys, difficulty, tag, source_url, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            pid,
            paper_data.get('source', '自建'),
            paper_data['exam_type'],
            paper_data['year'],
            paper_data.get('season'),
            paper_data.get('province'),
            paper_data['title'],
            json.dumps(paper_data.get('material', []), ensure_ascii=False),
            json.dumps(paper_data.get('questions', []), ensure_ascii=False),
            json.dumps(paper_data.get('answer_keys', {}), ensure_ascii=False),
            paper_data.get('difficulty', 3),
            json.dumps(paper_data.get('tag', []), ensure_ascii=False),
            paper_data.get('source_url'),
            paper_data.get('status', 'draft')
        )
    )
    db.commit()
    return pid


def update_paper(pid: str, paper_data: dict):
    db = get_db()
    fields = []
    values = []

    for key in ['source', 'exam_type', 'year', 'season', 'province', 'title',
                'material', 'questions', 'answer_keys', 'difficulty', 'tag',
                'source_url', 'status']:
        if key in paper_data:
            fields.append(f"{key} = ?")
            value = paper_data[key]
            if key in ('material', 'questions', 'answer_keys', 'tag'):
                value = json.dumps(value, ensure_ascii=False)
            values.append(value)

    if fields:
        values.append(pid)
        db.execute(f"UPDATE papers SET {', '.join(fields)} WHERE pid = ?", values)
        db.commit()
    return pid


def delete_paper(pid: str):
    db = get_db()
    db.execute("DELETE FROM papers WHERE pid = ?", (pid,))
    db.commit()


def increment_paper_heat(pid: str):
    db = get_db()
    db.execute("UPDATE papers SET heat = heat + 1 WHERE pid = ?", (pid,))
    db.commit()
