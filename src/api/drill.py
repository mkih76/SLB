from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, get_db, clamp_per_page
from src.services import drill_service

drill_bp = Blueprint('drill', __name__, url_prefix='/api/drill')


@drill_bp.route('/types', methods=['GET'])
@token_required
def get_type_stats(current_user):
    """获取五种题型的统计数据"""
    stats = drill_service.get_user_type_stats(current_user['uid'])
    return api_success({
        'types': stats,
        'type_names': drill_service.QUESTION_TYPE_NAMES
    })


@drill_bp.route('/recommend', methods=['GET'])
@token_required
def get_recommendations(current_user):
    """获取推荐练习题"""
    qtype = request.args.get('type', 'guina')
    if qtype not in drill_service.QUESTION_TYPE_NAMES:
        return api_error("无效的题型", 400)

    limit = min(int(request.args.get('limit', 5)), 20)
    items = drill_service.get_recommended_questions(current_user['uid'], qtype, limit)
    return api_success({'items': items, 'question_type': qtype})


@drill_bp.route('/history', methods=['GET'])
@token_required
def get_history(current_user):
    """获取训练历史"""
    qtype = request.args.get('type')
    page = int(request.args.get('page', 1))
    per_page = clamp_per_page(request.args.get('limit', 20))

    result = drill_service.get_drill_history(
        current_user['uid'], qtype, page, per_page
    )
    return api_success(result)


@drill_bp.route('/progress', methods=['GET'])
@token_required
def get_progress(current_user):
    """获取某题型的进步趋势"""
    qtype = request.args.get('type', 'guina')
    if qtype not in drill_service.QUESTION_TYPE_NAMES:
        return api_error("无效的题型", 400)

    limit = min(int(request.args.get('limit', 10)), 50)
    trend = drill_service.get_drill_progress(current_user['uid'], qtype, limit)
    return api_success({
        'question_type': qtype,
        'trend': trend
    })
