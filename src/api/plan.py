from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token
from src.services import plan_service

plan_bp = Blueprint('plan', __name__, url_prefix='/api/plan')


@plan_bp.route('/active', methods=['GET'])
@optional_token
def get_active(current_user):
    """获取当前活跃的备考计划"""
    if not current_user:
        return api_success(None)
    result = plan_service.get_active_plan(current_user['uid'])
    if not result:
        return api_success(None, message="暂无备考计划")
    return api_success(result)


@plan_bp.route('/create', methods=['POST'])
@token_required
def create_plan(current_user):
    """创建备考计划"""
    data = request.get_json()
    if not data or not data.get('exam_date') or not data.get('exam_type'):
        return api_error("请提供考试日期和考试类型", 400)

    result = plan_service.create_study_plan(
        uid=current_user['uid'],
        plan_name=data.get('plan_name', '我的备考计划'),
        exam_date=data['exam_date'],
        exam_type=data['exam_type'],
        daily_minutes=data.get('daily_minutes', 120)
    )
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@plan_bp.route('/today', methods=['GET'])
@optional_token
def get_today(current_user):
    """获取今日任务"""
    if not current_user:
        return api_success([])
    result = plan_service.get_today_tasks(current_user['uid'])
    return api_success(result)


@plan_bp.route('/task/<int:task_id>/complete', methods=['POST'])
@token_required
def complete_task(current_user, task_id):
    """完成任务"""
    data = request.get_json() or {}
    result = plan_service.complete_task(
        current_user['uid'], task_id, score=data.get('score')
    )
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@plan_bp.route('/task/<int:task_id>/skip', methods=['POST'])
@token_required
def skip_task(current_user, task_id):
    """跳过任务"""
    result = plan_service.skip_task(current_user['uid'], task_id)
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@plan_bp.route('/<int:plan_id>/pause', methods=['POST'])
@token_required
def pause_plan(current_user, plan_id):
    """暂停计划"""
    result = plan_service.pause_plan(current_user['uid'], plan_id)
    return api_success(result)


@plan_bp.route('/<int:plan_id>/resume', methods=['POST'])
@token_required
def resume_plan(current_user, plan_id):
    """恢复计划"""
    result = plan_service.resume_plan(current_user['uid'], plan_id)
    return api_success(result)


@plan_bp.route('/history', methods=['GET'])
@optional_token
def get_history(current_user):
    """获取计划历史"""
    if not current_user:
        return api_success({'plans': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = plan_service.get_plan_history(current_user['uid'], page, per_page)
    return api_success(result)


@plan_bp.route('/week-progress', methods=['GET'])
@optional_token
def get_week_progress(current_user):
    """获取本周进度"""
    if not current_user:
        return api_success(None)
    result = plan_service.get_week_progress(current_user['uid'])
    return api_success(result)
