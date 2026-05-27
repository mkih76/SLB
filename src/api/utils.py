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


def paginate(query, page=1, per_page=20):
    offset = (page - 1) * per_page
    items = query.limit(per_page).offset(offset).all()
    total = query.count()
    return {
        'items': [dict(i) for i in items],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page,
        'per_page': per_page
    }