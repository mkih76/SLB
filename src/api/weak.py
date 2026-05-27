from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required
from src.services import weak_point_service

weak_bp = Blueprint('weak', __name__, url_prefix='/api/weak')


@weak_bp.route('', methods=['GET'])
@token_required
def get_weak_points(current_user):
    """获取用户薄弱点列表"""
    topic_tag = request.args.get('topic_tag')
    points = weak_point_service.get_user_weak_points(
        current_user['uid'], topic_tag=topic_tag
    )
    return api_success({'weak_points': points})


@weak_bp.route('/stats', methods=['GET'])
@token_required
def get_weak_stats(current_user):
    """获取用户薄弱点统计"""
    stats = weak_point_service.get_weak_point_stats(current_user['uid'])
    return api_success({'topic_distribution': stats})
