import sqlite3
import uuid
from datetime import datetime
from functools import wraps
from typing import Optional

import jwt
from flask import g, request, jsonify

from src.config import Config, JWT_ALGORITHM, JWT_SECRET


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(Config.DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize database with schema and seed data"""
    import os
    db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else '.', exist_ok=True)
    db = sqlite3.connect(db_path)

    # Use absolute path relative to project root (works in Docker and local)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    schema_path = os.path.join(project_root, 'data', 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()

    # Load seed data if tables are empty
    count = db.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
    if count == 0:
        seed_files = [
            'data/seed_papers.sql',
            'data/seed_phrases.sql',
        ]
        for sf in seed_files:
            sf_path = os.path.join(project_root, sf)
            if os.path.exists(sf_path):
                with open(sf_path, 'r', encoding='utf-8') as f:
                    try:
                        db.executescript(f.read())
                    except Exception as e:
                        print(f"Warning: failed to load {sf}: {e}")
        db.commit()

    # Load topics seed if hot_topics is empty
    count = db.execute("SELECT COUNT(*) FROM hot_topics").fetchone()[0]
    if count == 0:
        topics_path = os.path.join(project_root, 'data', 'seed_topics.sql')
        if os.path.exists(topics_path):
            with open(topics_path, 'r', encoding='utf-8') as f:
                try:
                    db.executescript(f.read())
                except Exception as e:
                    print(f"Warning: failed to load seed_topics.sql: {e}")
            db.commit()

    db.close()


def generate_uuid():
    return str(uuid.uuid4())


def generate_sid():
    return 'sid_' + generate_uuid()


def api_success(data=None, message="ok"):
    return jsonify({"data": data, "message": message}), 200


def api_error(message, code=400):
    return jsonify({"error": message, "code": code}), code


def clamp_per_page(per_page: int, max_val: int = 100) -> int:
    """限制每页数量，防止恶意请求过大值"""
    return max(1, min(per_page, max_val))


def _extract_user_from_token():
    """从请求中提取用户信息，返回 (user_dict, error_response)"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None, None  # 没有 token，不算错误
    token = auth_header.replace('Bearer ', '')
    try:
        data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        jti = data.get('jti')
        if jti:
            blacklisted = get_db().execute(
                "SELECT 1 FROM token_blacklist WHERE jti = ?", (jti,)
            ).fetchone()
            if blacklisted:
                return None, api_error("Token已失效，请重新登录", 401)
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE uid = ? AND status = 'active'",
            (data['sub'],)
        ).fetchone()
        if not user:
            return None, api_error("User not found", 401)
        return dict(user), None
    except jwt.ExpiredSignatureError:
        return None, api_error("Token expired", 401)
    except jwt.InvalidTokenError:
        return None, api_error("Invalid token", 401)


def token_required(f):
    """强制要求登录的装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = _extract_user_from_token()
        if err:
            return err
        if not user:
            return api_error("Token required", 401)
        kwargs['current_user'] = user
        return f(*args, **kwargs)
    return decorated


def optional_token(f):
    """可选登录装饰器：有 token 则解析用户，没有则 current_user=None"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user, err = _extract_user_from_token()
        if err:
            return err
        kwargs['current_user'] = user  # None 或 user dict
        return f(*args, **kwargs)
    return decorated


ROLE_PERMISSIONS = {
    'super_admin': ['*'],
    'admin': [
        'users.view', 'users.edit', 'users.ban',
        'papers.view', 'papers.add', 'papers.edit', 'papers.delete',
        'phrases.view', 'phrases.approve',
        'submissions.view', 'submissions.review',
        'stats.view', 'logs.view'
    ],
    'reviewer': [
        'submissions.view', 'submissions.review',
        'phrases.view', 'phrases.approve'
    ],
    'operator': [
        'papers.view', 'papers.add', 'papers.edit', 'papers.delete',
        'phrases.view', 'phrases.add'
    ]
}


def has_permission(role: str, permission: str) -> bool:
    """Check if a role has a specific permission"""
    if not permission:
        return True
    perms = ROLE_PERMISSIONS.get(role, [])
    if '*' in perms:
        return True
    # Check wildcard match (e.g., 'papers.*' matches 'papers.view')
    resource = permission.split('.')[0] if '.' in permission else ''
    if f'{resource}.*' in perms:
        return True
    return permission in perms


def admin_required(permission=None):
    """Admin permission decorator"""
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            current_user = kwargs.get('current_user')
            role = current_user.get('role', 'user')
            if role not in ('super_admin', 'admin', 'reviewer', 'operator'):
                return api_error("Admin access required", 403)
            if not has_permission(role, permission):
                return api_error("Permission denied", 403)
            return f(*args, **kwargs)
        return decorated
    return decorator


def get_user_by_id(uid: str) -> Optional[dict]:
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE uid = ?", (uid,)).fetchone()
    return dict(user) if user else None


def get_user_by_username(username: str) -> Optional[dict]:
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(user) if user else None


