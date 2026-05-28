import json
from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, get_db, clamp_per_page
from src.services import drill_service, submission_service
from src.services.grader.scorer import grade_answer
from src.services import paper_service

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


@drill_bp.route('/submit', methods=['POST'])
@token_required
def submit_drill(current_user):
    """提交题型训练答案并批改"""
    data = request.get_json()
    if not data or not data.get('pid') or not data.get('qid') or not data.get('user_answer'):
        return api_error("缺少必要参数（pid, qid, user_answer）", 400)

    pid = data['pid']
    qid = data['qid']
    user_answer = data['user_answer'].strip()

    if not user_answer:
        return api_error("答案不能为空", 400)

    # 获取题目信息
    question = paper_service.get_question_by_qid(pid, qid)
    if not question:
        return api_error("题目不存在", 404)

    question_type = question.get('type', 'guina')

    # 创建提交记录
    sid = submission_service.create_submission(
        current_user['uid'], pid, qid, user_answer
    )

    # 获取试卷材料
    paper = paper_service.get_paper_by_pid(pid)
    material = json.loads(paper['material']) if paper and paper['material'] else None

    # 批改
    try:
        grading = grade_answer(pid, qid, question, user_answer, material)

        # 更新提交记录
        submission_service.update_submission_grading(
            sid=sid,
            score=grading['score'],
            dimension_scores=grading['dimension_scores'],
            ai_feedback=grading['ai_feedback'],
            hit_points=grading.get('hit_points', []),
            missing_points=grading.get('missing_points', []),
            improving_suggestions=grading.get('improving_suggestions')
        )

        # 记录题型训练统计
        drill_service.record_drill(
            uid=current_user['uid'],
            question_type=question_type,
            pid=pid,
            qid=qid,
            sid=sid,
            score=grading['score'],
            dimension_scores=grading['dimension_scores']
        )

        # 记录薄弱点
        from src.services import weak_point_service
        for missing in grading.get('missing_points', []):
            weak_point_service.record_weak_point(
                current_user['uid'], missing,
                topic_tag=question_type
            )

        # 自动生成诊断报告
        from src.services import diagnosis_service
        diagnosis_service.generate_diagnostic_report(current_user['uid'], sid)

        return api_success({
            'sid': sid,
            'score': grading['score'],
            'dimension_scores': grading['dimension_scores'],
            'hit_points': grading.get('hit_points', []),
            'missing_points': grading.get('missing_points', []),
            'ai_feedback': grading['ai_feedback'],
            'improving_suggestions': grading.get('improving_suggestions'),
            'question_type': question_type
        })

    except Exception as e:
        return api_error(f"批改失败: {str(e)}", 500)
