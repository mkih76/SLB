from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token
from src.services import diagnosis_service

diagnosis_bp = Blueprint('diagnosis', __name__, url_prefix='/api/diagnosis')


@diagnosis_bp.route('/latest', methods=['GET'])
@optional_token
def get_latest(current_user):
    """获取最新诊断报告"""
    if not current_user:
        return api_success(None)
    report = diagnosis_service.get_latest_report(current_user['uid'])
    if not report:
        return api_error("暂无诊断报告，请先完成一次练习", 404)
    return api_success(report)


@diagnosis_bp.route('/<int:report_id>', methods=['GET'])
@optional_token
def get_report(current_user, report_id):
    """获取指定诊断报告"""
    if not current_user:
        return api_error("请先登录", 401)
    report = diagnosis_service.get_report_by_id(current_user['uid'], report_id)
    if not report:
        return api_error("报告不存在", 404)
    return api_success(report)


@diagnosis_bp.route('/trend', methods=['GET'])
@optional_token
def get_trend(current_user):
    """获取得分趋势"""
    if not current_user:
        return api_success({'trend': []})
    limit = min(int(request.args.get('limit', 10)), 50)
    qtype = request.args.get('type')

    if qtype:
        trend = diagnosis_service.get_type_score_trend(current_user['uid'], qtype, limit)
    else:
        trend = diagnosis_service.get_score_trend(current_user['uid'], limit)

    return api_success({'trend': trend, 'question_type': qtype})


@diagnosis_bp.route('/generate', methods=['POST'])
@token_required
def generate_report(current_user):
    """手动生成诊断报告"""
    sid = request.json.get('sid') if request.is_json else None
    report = diagnosis_service.generate_diagnostic_report(current_user['uid'], sid)
    if not report:
        return api_error("数据不足，无法生成报告", 400)
    return api_success(report)


@diagnosis_bp.route('/weekly', methods=['GET'])
@optional_token
def get_weekly(current_user):
    """获取最新周报"""
    if not current_user:
        return api_success(None)
    report = diagnosis_service.generate_weekly_report(current_user['uid'])
    if not report:
        return api_error("本周练习数据不足（至少需要2次练习），暂无法生成周报", 404)
    return api_success(report)


@diagnosis_bp.route('/weekly/generate', methods=['POST'])
@token_required
def generate_weekly(current_user):
    """手动生成周报"""
    report = diagnosis_service.generate_weekly_report(current_user['uid'])
    if not report:
        return api_error("本周练习数据不足（至少需要2次练习），暂无法生成周报", 400)
    return api_success(report)
