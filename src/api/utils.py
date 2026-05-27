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
    """Initialize database with schema"""
    db = sqlite3.connect(Config.DATABASE_PATH)
    with open('data/schema.sql', 'r', encoding='utf-8') as f:
        db.executescript(f.read())
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


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return api_error("Token required", 401)
        token = auth_header.replace('Bearer ', '')
        try:
            data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            db = get_db()
            user = db.execute(
                "SELECT * FROM users WHERE uid = ? AND status = 'active'",
                (data['sub'],)
            ).fetchone()
            if not user:
                return api_error("User not found", 401)
            kwargs['current_user'] = dict(user)
        except jwt.ExpiredSignatureError:
            return api_error("Token expired", 401)
        except jwt.InvalidTokenError:
            return api_error("Invalid token", 401)
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


