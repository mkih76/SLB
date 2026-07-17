from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token, clamp_per_page
from src.services import simulation_service

simulation_bp = Blueprint('simulation', __name__, url_prefix='/api/simulation')


@simulation_bp.route('/start', methods=['POST'])
@token_required
def start_sim(current_user):
    """开始模拟考试"""
    data = request.get_json()
    if not data or not data.get('pid'):
        return api_error("请提供试卷ID", 400)

    result = simulation_service.start_simulation(current_user['uid'], data['pid'])
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@simulation_bp.route('/submit', methods=['POST'])
@token_required
def submit_sim(current_user):
    """提交模拟考试答案"""
    data = request.get_json()
    if not data or not data.get('sim_id') or not data.get('answers'):
        return api_error("缺少必要参数", 400)

    result = simulation_service.submit_simulation(
        data['sim_id'], current_user['uid'], data['answers']
    )
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@simulation_bp.route('/<sim_id>', methods=['GET'])
@optional_token
def get_detail(current_user, sim_id):
    """获取模拟考试详情"""
    if not current_user:
        return api_error("请先登录", 401)
    result = simulation_service.get_simulation_detail(sim_id, current_user['uid'])
    if not result:
        return api_error("记录不存在", 404)
    return api_success(result)


@simulation_bp.route('/history', methods=['GET'])
@optional_token
def get_history(current_user):
    """获取模拟考试历史"""
    if not current_user:
        return api_success({'records': [], 'total': 0, 'page': 1, 'pages': 0})
    page = int(request.args.get('page', 1))
    per_page = clamp_per_page(request.args.get('limit', 20))
    result = simulation_service.get_simulation_history(
        current_user['uid'], page, per_page
    )
    return api_success(result)
