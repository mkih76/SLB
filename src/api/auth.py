from flask import Blueprint, request
from datetime import date, datetime, timedelta

from src.services.auth import register_user, login_user, logout_user, get_user_profile, is_vip_user
from src.api.utils import api_success, api_error, token_required, get_db

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return api_error("请提供用户名和密码", 400)

    username = data.get('username', '').strip()
    password = data.get('password', '')
    nickname = data.get('nickname', '').strip()

    if not username or not password:
        return api_error("用户名和密码不能为空", 400)

    if len(username) < 3 or len(username) > 30:
        return api_error("用户名长度需在3-30个字符之间", 400)

    if len(password) < 6 or len(password) > 100:
        return api_error("密码长度需在6-100个字符之间", 400)

    if nickname and len(nickname) > 50:
        return api_error("昵称不能超过50个字符", 400)

    result, err = register_user(username, password, nickname)
    if err:
        return api_error(err, 400)

    return api_success(result)


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return api_error("请提供用户名和密码", 400)

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return api_error("用户名和密码不能为空", 400)

    result, err = login_user(username, password)
    if err:
        return api_error(err, 401)

    return api_success(result)


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    logout_user(current_user['uid'], token=token)
    return api_success(message="已退出登录")


@auth_bp.route('/me', methods=['GET'])
@token_required
def me(current_user):
    profile = get_user_profile(current_user['uid'])
    if not profile:
        return api_error("用户不存在", 404)

    profile['is_vip'] = is_vip_user(profile)
    return api_success(profile)


@auth_bp.route('/password', methods=['PUT'])
@token_required
def change_password(current_user):
    """修改密码：校验旧密码后更新"""
    from src.services.auth import hash_password, verify_password
    data = request.get_json()
    if not data:
        return api_error("请提供当前密码和新密码", 400)

    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not old_password or not new_password:
        return api_error("当前密码和新密码不能为空", 400)

    if len(new_password) < 6 or len(new_password) > 100:
        return api_error("新密码长度需在6-100个字符之间", 400)

    if new_password == old_password:
        return api_error("新密码不能与当前密码相同", 400)

    db = get_db()
    row = db.execute(
        "SELECT password_hash FROM users WHERE uid = ?",
        (current_user['uid'],)
    ).fetchone()
    if not row:
        return api_error("用户不存在", 404)

    if not verify_password(old_password, row['password_hash']):
        return api_error("当前密码不正确", 403)

    db.execute(
        "UPDATE users SET password_hash = ? WHERE uid = ?",
        (hash_password(new_password), current_user['uid'])
    )
    db.commit()
    return api_success(message="密码修改成功")


# ============================================================
# 每日签到系统
# ============================================================

SIGN_IN_REWARDS = {
    1: 5, 2: 5, 3: 10, 4: 10, 5: 15, 6: 15, 7: 30  # 连续7天大奖
}


@auth_bp.route('/signin', methods=['POST'])
@token_required
def sign_in(current_user):
    """每日签到"""
    uid = current_user['uid']
    today = date.today().isoformat()
    db = get_db()

    # Check if already signed in today
    existing = db.execute(
        "SELECT id FROM sign_in_records WHERE uid = ? AND sign_date = ?",
        (uid, today)
    ).fetchone()
    if existing:
        return api_error("今日已签到，请明天再来", 400)

    # Calculate streak
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last_sign = db.execute(
        "SELECT sign_date, streak_days FROM sign_in_records WHERE uid = ? ORDER BY sign_date DESC LIMIT 1",
        (uid,)
    ).fetchone()

    streak = 1
    if last_sign:
        last_date = last_sign['sign_date']
        if last_date == yesterday:
            streak = min(last_sign['streak_days'] + 1, 7)
        elif last_date == today:
            return api_error("今日已签到", 400)

    # Calculate reward
    reward = SIGN_IN_REWARDS.get(streak, 5)

    # Insert sign-in record
    db.execute(
        "INSERT INTO sign_in_records (uid, sign_date, streak_days, reward_points) VALUES (?, ?, ?, ?)",
        (uid, today, streak, reward)
    )

    # Update user points
    db.execute(
        """INSERT INTO user_points (uid, total_points, updated_at) VALUES (?, ?, datetime('now'))
           ON CONFLICT(uid) DO UPDATE SET total_points = total_points + ?, updated_at = datetime('now')""",
        (uid, reward, reward)
    )

    # Record learning activity
    db.execute(
        "INSERT INTO learning_records (uid, action, target_id, created_at) VALUES (?, 'sign_in', ?, datetime('now'))",
        (uid, today)
    )

    db.commit()

    return api_success({
        'streak_days': streak,
        'reward_points': reward,
        'message': f'签到成功！连续签到{streak}天，获得{reward}积分'
    })


@auth_bp.route('/signin/status', methods=['GET'])
@token_required
def sign_in_status(current_user):
    """获取签到状态"""
    uid = current_user['uid']
    today = date.today().isoformat()
    db = get_db()

    # Today's sign-in
    today_sign = db.execute(
        "SELECT id FROM sign_in_records WHERE uid = ? AND sign_date = ?",
        (uid, today)
    ).fetchone()

    # Current streak
    last_sign = db.execute(
        "SELECT streak_days FROM sign_in_records WHERE uid = ? ORDER BY sign_date DESC LIMIT 1",
        (uid,)
    ).fetchone()

    # Total points
    points = db.execute(
        "SELECT total_points, used_points FROM user_points WHERE uid = ?",
        (uid,)
    ).fetchone()

    # This month's sign-in count
    month_count = db.execute(
        "SELECT COUNT(*) FROM sign_in_records WHERE uid = ? AND sign_date >= date('now', 'start of month')",
        (uid,)
    ).fetchone()[0]

    return api_success({
        'signed_today': today_sign is not None,
        'current_streak': last_sign['streak_days'] if last_sign else 0,
        'total_points': points['total_points'] if points else 0,
        'used_points': points['used_points'] if points else 0,
        'month_sign_ins': month_count
    })
