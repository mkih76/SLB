import sqlite3

import bcrypt
import jwt
from datetime import datetime, timedelta

from src.config import Config, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS
from src.api.utils import get_db, generate_uuid


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def create_token(uid: str) -> str:
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    jti = generate_uuid()
    payload = {
        'sub': uid,
        'jti': jti,
        'exp': expire,
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def register_user(username: str, password: str, nickname: str = None):
    db = get_db()

    uid = generate_uuid()
    password_hash = hash_password(password)
    nickname = nickname or username

    try:
        db.execute(
            """INSERT INTO users (uid, username, password_hash, nickname, role, status)
               VALUES (?, ?, ?, ?, 'user', 'active')""",
            (uid, username, password_hash, nickname)
        )
        db.commit()
    except sqlite3.IntegrityError:
        return None, "用户名已存在"

    token = create_token(uid)
    return {
        'uid': uid,
        'username': username,
        'nickname': nickname,
        'role': 'user',
        'token': token
    }, None


def login_user(username: str, password: str):
    db = get_db()

    user = db.execute("SELECT * FROM users WHERE username = ? AND status = 'active'", (username,)).fetchone()
    if not user:
        return None, "用户名或密码错误"

    if not verify_password(password, user['password_hash']):
        return None, "用户名或密码错误"

    # Update last login
    db.execute("UPDATE users SET last_login = ? WHERE uid = ?", (datetime.now().isoformat(), user['uid']))
    db.commit()

    token = create_token(user['uid'])
    return {
        'uid': user['uid'],
        'username': user['username'],
        'nickname': user['nickname'],
        'role': user['role'],
        'vip_expire': user['vip_expire'],
        'token': token
    }, None


def logout_user(uid: str, token: str = None):
    """登出用户，将token加入黑名单"""
    db = get_db()
    db.execute("DELETE FROM sessions WHERE uid = ?", (uid,))
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            jti = payload.get('jti')
            exp = datetime.fromtimestamp(payload['exp'])
            if jti:
                db.execute(
                    "INSERT OR IGNORE INTO token_blacklist (jti, uid, expires_at) VALUES (?, ?, ?)",
                    (jti, uid, exp.isoformat())
                )
        except jwt.InvalidTokenError:
            pass
    db.commit()
    return True


def is_token_blacklisted(jti: str) -> bool:
    """检查token是否在黑名单中"""
    if not jti:
        return False
    db = get_db()
    row = db.execute("SELECT 1 FROM token_blacklist WHERE jti = ?", (jti,)).fetchone()
    return row is not None


def get_user_profile(uid: str):
    db = get_db()
    user = db.execute(
        "SELECT uid, username, nickname, role, vip_expire, created_at, last_login, settings FROM users WHERE uid = ?",
        (uid,)
    ).fetchone()
    return dict(user) if user else None


def is_vip_user(user: dict) -> bool:
    if user.get('role') in ('admin', 'super_admin', 'vip'):
        return True
    vip_expire = user.get('vip_expire')
    if not vip_expire:
        return False
    return datetime.fromisoformat(vip_expire) > datetime.now()