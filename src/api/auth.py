from flask import Blueprint, request

from src.services.auth import register_user, login_user, logout_user, get_user_profile, is_vip_user
from src.api.utils import api_success, api_error, token_required

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
