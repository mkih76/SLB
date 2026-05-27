from flask import Blueprint, request

from src.api.utils import api_success, api_error, admin_required, get_db
from src.services import paper_service, phrase_service
from src.services.auth import get_user_profile, is_vip_user

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


def get_dashboard_stats():
    db = get_db()

    # User stats
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today_users = db.execute(
        "SELECT COUNT(*) FROM users WHERE date(created_at) = date('now')"
    ).fetchone()[0]

    # Submission stats
    total_submissions = db.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]
    today_submissions = db.execute(
        "SELECT COUNT(*) FROM submissions WHERE date(created_at) = date('now')"
    ).fetchone()[0]

    # Pending review
    pending_reviews = db.execute(
        "SELECT COUNT(*) FROM submissions WHERE score < 60 OR is_reviewed = 0"
    ).fetchone()[0]

    # Papers stats
    total_papers = db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]

    # Pending phrases
    pending_phrases = db.execute(
        "SELECT COUNT(*) FROM good_phrases WHERE status = 'pending'"
    ).fetchone()[0]

    return {
        'total_users': total_users,
        'today_users': today_users,
        'total_submissions': total_submissions,
        'today_submissions': today_submissions,
        'pending_reviews': pending_reviews,
        'total_papers': total_papers,
        'pending_phrases': pending_phrases
    }


@admin_bp.route('/dashboard', methods=['GET'])
@admin_required('stats.view')
def dashboard():
    return api_success(get_dashboard_stats())


@admin_bp.route('/stats', methods=['GET'])
@admin_required('stats.view')
def stats():
    return api_success(get_dashboard_stats())


# ============ User Management ============

@admin_bp.route('/users', methods=['GET'])
@admin_required('users.view')
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    role = request.args.get('role')
    status = request.args.get('status')
    search = request.args.get('search', '')

    db = get_db()
    query = "SELECT uid, username, nickname, role, vip_expire, created_at, last_login, status FROM users WHERE 1=1"
    params = []

    if role:
        query += " AND role = ?"
        params.append(role)
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (username LIKE ? OR nickname LIKE ?)"
        params.append(f'%{search}%')
        params.append(f'%{search}%')

    total = db.execute(
        "SELECT COUNT(*) FROM users WHERE " + " AND ".join(
            ["1=1"] + [f"{'role = ?' if role else '1=1'}"] +
            [f"{'status = ?' if status else '1=1'}" for _ in [1]] +
            [f"(username LIKE ? OR nickname LIKE ?)" if search else '1=1' for _ in [1]]
        ) if role or status or search else "SELECT COUNT(*) FROM users",
        params if params else []
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}"
    users = db.execute(query, params).fetchall()

    return api_success({
        'users': [dict(u) for u in users],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })


@admin_bp.route('/users/<uid>', methods=['GET'])
@admin_required('users.view')
def get_user(uid):
    user = get_user_profile(uid)
    if not user:
        return api_error("用户不存在", 404)

    # Get learning stats
    db = get_db()
    submissions_count = db.execute(
        "SELECT COUNT(*) FROM submissions WHERE uid = ?", (uid,)
    ).fetchone()[0]
    avg_score = db.execute(
        "SELECT AVG(score) FROM submissions WHERE uid = ? AND score IS NOT NULL", (uid,)
    ).fetchone()[0]

    user['submissions_count'] = submissions_count
    user['avg_score'] = round(avg_score, 1) if avg_score else None
    user['is_vip'] = is_vip_user(user)

    return api_success(user)


@admin_bp.route('/users/<uid>', methods=['PUT'])
@admin_required('users.edit')
def update_user(uid):
    data = request.get_json()
    if not data:
        return api_error("请提供更新数据", 400)

    db = get_db()
    fields = []
    values = []

    for field in ['nickname', 'role', 'vip_expire', 'status']:
        if field in data:
            fields.append(f"{field} = ?")
            values.append(data[field])

    if fields:
        values.append(uid)
        db.execute(f"UPDATE users SET {', '.join(fields)} WHERE uid = ?", values)
        db.commit()

    # Log action
    db.execute(
        "INSERT INTO admin_logs (admin_uid, action, target_type, target_id, detail) VALUES (?, 'update_user', 'user', ?, ?)",
        ('admin', uid, json.dumps(data))
    )
    db.commit()

    return api_success(message="用户已更新")


@admin_bp.route('/users/<uid>/ban', methods=['PUT'])
@admin_required('users.ban')
def ban_user(uid):
    data = request.get_json() or {}
    action = data.get('action', 'ban')

    db = get_db()
    new_status = 'banned' if action == 'ban' else 'active'
    db.execute("UPDATE users SET status = ? WHERE uid = ?", (new_status, uid))
    db.commit()

    db.execute(
        "INSERT INTO admin_logs (admin_uid, action, target_type, target_id, detail) VALUES (?, ?, 'user', ?, ?)",
        ('admin', action + '_user', uid, json.dumps({'action': action}))
    )
    db.commit()

    return api_success(message=f"用户已{'封禁' if action == 'ban' else '解封'}")


# ============ Paper Management ============

@admin_bp.route('/papers', methods=['GET'])
@admin_required('papers.view')
def list_papers():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    status = request.args.get('status')
    exam_type = request.args.get('exam_type')

    db = get_db()
    query = "SELECT * FROM papers WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)
    if exam_type:
        query += " AND exam_type = ?"
        params.append(exam_type)

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}"
    papers = db.execute(query, params).fetchall()

    return api_success({
        'papers': [dict(p) for p in papers],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })


@admin_bp.route('/papers', methods=['POST'])
@admin_required('papers.add')
def create_paper():
    data = request.get_json()
    if not data:
        return api_error("请提供试卷数据", 400)

    pid = paper_service.create_paper(data)
    return api_success({'pid': pid}, "试卷已创建")


@admin_bp.route('/papers/<pid>', methods=['PUT'])
@admin_required('papers.edit')
def update_paper(pid):
    data = request.get_json()
    if not data:
        return api_error("请提供更新数据", 400)

    paper_service.update_paper(pid, data)
    return api_success(message="试卷已更新")


@admin_bp.route('/papers/<pid>', methods=['DELETE'])
@admin_required('papers.delete')
def delete_paper(pid):
    paper_service.delete_paper(pid)
    return api_success(message="试卷已删除")


@admin_bp.route('/papers/<pid>/publish', methods=['PUT'])
@admin_required('papers.edit')
def publish_paper(pid):
    data = request.get_json()
    status = data.get('status', 'published') if data else 'published'

    paper_service.update_paper(pid, {'status': status})
    return api_success(message=f"试卷已{'发布' if status == 'published' else '下架'}")


# ============ Phrase Management ============

@admin_bp.route('/phrases', methods=['GET'])
@admin_required('phrases.view')
def list_phrases():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    status = request.args.get('status')

    db = get_db()
    query = "SELECT * FROM good_phrases WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}"
    phrases = db.execute(query, params).fetchall()

    return api_success({
        'phrases': [dict(p) for p in phrases],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })


@admin_bp.route('/phrases/<int:phrase_id>/approve', methods=['POST'])
@admin_required('phrases.approve')
def approve_phrase(phrase_id):
    phrase_service.approve_phrase(phrase_id, 'admin')
    return api_success(message="好词已审核通过")


@admin_bp.route('/phrases/<int:phrase_id>/reject', methods=['POST'])
@admin_required('phrases.approve')
def reject_phrase(phrase_id):
    phrase_service.reject_phrase(phrase_id)
    return api_success(message="好词已驳回")


# ============ Review Management ============

@admin_bp.route('/submissions/pending_review', methods=['GET'])
@admin_required('submissions.review')
def pending_reviews():
    db = get_db()
    submissions = db.execute(
        """SELECT s.*, u.nickname, p.title as paper_title
           FROM submissions s
           JOIN users u ON s.uid = u.uid
           JOIN papers p ON s.pid = p.pid
           WHERE (s.score < 60 OR s.needs_review = 1) AND s.is_reviewed = 0
           ORDER BY s.created_at DESC LIMIT 50"""
    ).fetchall()

    return api_success({
        'submissions': [dict(s) for s in submissions]
    })


@admin_bp.route('/submissions/<sid>/review', methods=['POST'])
@admin_required('submissions.review')
def review_submission(sid):
    data = request.get_json()
    if not data:
        return api_error("请提供复核结果", 400)

    db = get_db()
    db.execute(
        """UPDATE submissions SET
           score = ?, dimension_scores = ?, ai_feedback = ?,
           is_reviewed = 1, needs_review = 0
           WHERE sid = ?""",
        (
            data.get('score'),
            json.dumps(data.get('dimension_scores', {})),
            data.get('feedback'),
            sid
        )
    )
    db.commit()

    return api_success(message="复核已完成")


# ============ Logs ============

@admin_bp.route('/logs', methods=['GET'])
@admin_required('logs.view')
def get_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 50, type=int)
    action = request.args.get('action')

    db = get_db()
    query = "SELECT * FROM admin_logs WHERE 1=1"
    params = []

    if action:
        query += " AND action LIKE ?"
        params.append(f'%{action}%')

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" ORDER BY created_at DESC LIMIT {per_page} OFFSET {offset}"
    logs = db.execute(query, params).fetchall()

    return api_success({
        'logs': [dict(l) for l in logs],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    })


import json
