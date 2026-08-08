from flask import Blueprint, request
import json
import logging

logger = logging.getLogger(__name__)

from src.api.utils import api_success, api_error, token_required, optional_token, get_db, clamp_per_page
from src.services import submission_service, paper_service, weak_point_service, drill_service, diagnosis_service
from src.services.grader.scorer import grade_answer
from src.services.auth import is_vip_user

submissions_bp = Blueprint('submissions', __name__, url_prefix='/api/submissions')


@submissions_bp.route('', methods=['POST'])
@token_required
def create_submission(current_user):
    data = request.get_json()
    if not data:
        return api_error("请提供答案", 400)

    pid = data.get('pid')
    qid = data.get('qid')
    user_answer = data.get('user_answer', '').strip()

    if not pid or not qid or not user_answer:
        return api_error("缺少必要参数", 400)

    # Get question info
    question = paper_service.get_question_by_qid(pid, qid)
    if not question:
        return api_error("题目不存在", 404)

    # Create submission record

    # 付费墙：非 VIP 且免费试用已用完的用户在调用 LLM 前拦截（不消耗成本）
    if not is_vip_user(current_user) and current_user.get('free_trial_used', 0):
        return api_error("免费试用已结束，开通VIP查看详细批改结果", 403)
    sid = submission_service.create_submission(
        current_user['uid'], pid, qid, user_answer
    )

    # Get paper material
    paper = paper_service.get_paper_by_pid(pid)
    material = json.loads(paper['material']) if paper and paper['material'] else None

    # Grade the answer
    try:
        grading_result = grade_answer(pid, qid, question, user_answer, material)

        # Mark free trial as used for non-VIP users
        if current_user.get('role') not in ('admin', 'super_admin', 'vip'):
            if not current_user.get('free_trial_used'):
                db = get_db()
                db.execute("UPDATE users SET free_trial_used = 1 WHERE uid = ?", (current_user['uid'],))
                db.commit()

        # Update submission with grading result
        submission_service.update_submission_grading(
            sid=sid,
            score=grading_result['score'],
            dimension_scores=grading_result['dimension_scores'],
            ai_feedback=grading_result['ai_feedback'],
            hit_points=grading_result.get('hit_points', []),
            missing_points=grading_result.get('missing_points', []),
            improving_suggestions=json.dumps(grading_result.get('improving_suggestions'), ensure_ascii=False) if grading_result.get('improving_suggestions') else None
        )

        # Record learning
        submission_service.record_learning(
            current_user['uid'], 'submit', sid, grading_result['score']
        )

        # Record weak points
        for missing in grading_result.get('missing_points', []):
            weak_point_service.record_weak_point(
                current_user['uid'], missing.get('point', '') if isinstance(missing, dict) else missing,
                topic_tag=question.get('type')
            )

        # Record drill stats for question type
        question_type = question.get('type', 'guina')
        drill_service.record_drill(
            uid=current_user['uid'],
            question_type=question_type,
            pid=pid, qid=qid, sid=sid,
            score=grading_result['score'],
            dimension_scores=grading_result['dimension_scores']
        )

        # Auto-generate diagnostic report
        try:
            diagnosis_service.generate_diagnostic_report(current_user['uid'], sid)
        except Exception:
            pass  # don't fail the submission if diagnosis fails

        return api_success({
            'sid': sid,
            'status': 'completed',
            'score': grading_result['score'],
            'dimension_scores': grading_result['dimension_scores']
        })

    except Exception as e:
        # LLM 批改失败：尝试本地规则降级（scorer 内部已降级，此处兜底）
        from src.services.grader.scorer import grade_answer_local
        try:
            grading_result = grade_answer_local(pid, qid, question, user_answer, material)
            submission_service.update_submission_grading(
                sid=sid,
                score=grading_result['score'],
                dimension_scores=grading_result['dimension_scores'],
                ai_feedback=grading_result['ai_feedback'],
                hit_points=grading_result.get('hit_points', []),
                missing_points=grading_result.get('missing_points', []),
                improving_suggestions=json.dumps(grading_result.get('improving_suggestions'), ensure_ascii=False) if grading_result.get('improving_suggestions') else None
            )
            return api_success({
                'sid': sid,
                'status': 'completed',
                'score': grading_result['score'],
                'dimension_scores': grading_result['dimension_scores']
            })
        except Exception as e2:
            logger.error(f"降级批改也失败 (sid={sid}): {e2}")
            return api_success({
                'sid': sid,
                'status': 'grading',
                'message': '批改中，请稍后查询结果'
            })


@submissions_bp.route('/<sid>', methods=['GET'])
@optional_token
def get_submission(current_user, sid):
    if not current_user:
        return api_error("请先登录查看详细批改结果", 401)
    submission = submission_service.get_submission(sid)
    if not submission:
        return api_error("提交记录不存在", 404)

    # Check ownership
    if submission['uid'] != current_user['uid']:
        return api_error("无权查看此提交", 403)

    # Check if user is VIP for detailed feedback
    is_vip = is_vip_user(current_user)

    result = {
        'sid': submission['sid'],
        'pid': submission['pid'],
        'paper_title': submission['paper_title'],
        'qid': submission['qid'],
        'user_answer': submission['user_answer'],
        'score': submission['score'],
        'graded_at': submission['graded_at'],
        'created_at': submission['created_at'],
        'is_vip': is_vip
    }

    # Full details for VIP or free trial not yet used
    free_trial_used = current_user.get('free_trial_used', 0)
    if is_vip or not free_trial_used:
        result['dimension_scores'] = json.loads(submission['dimension_scores']) if submission['dimension_scores'] else None
        result['ai_feedback'] = submission['ai_feedback']
        result['hit_points'] = json.loads(submission['hit_points']) if submission['hit_points'] else []
        result['missing_points'] = json.loads(submission['missing_points']) if submission['missing_points'] else []
        result['improving_suggestions'] = submission['improving_suggestions']
    else:
        result['upgrade_required'] = True
        result['upgrade_message'] = '免费试用已结束，开通VIP查看详细批改结果'

    return api_success(result)


@submissions_bp.route('/<sid>/share', methods=['POST'])
@token_required
def create_share(current_user, sid):
    submission = submission_service.get_submission(sid)
    if not submission or submission['uid'] != current_user['uid']:
        return api_error("提交记录不存在", 404)
    # 付费墙：仅 VIP 或未用免费试用者可以生成分享（与 get_submission 完整可见性一致）
    is_vip = is_vip_user(current_user)
    free_trial_used = current_user.get('free_trial_used', 0)
    if not is_vip and free_trial_used:
        return api_error("免费试用已结束，开通VIP可分享批改结果", 403)
    token = submission_service.generate_share_token(sid)
    return api_success({'share_token': token, 'share_url': f'/share/{token}'})


@submissions_bp.route('/<sid>/share', methods=['DELETE'])
@token_required
def revoke_share(current_user, sid):
    submission = submission_service.get_submission(sid)
    if not submission or submission['uid'] != current_user['uid']:
        return api_error("提交记录不存在", 404)
    submission_service.revoke_share_token(sid)
    return api_success({'revoked': True})


@submissions_bp.route('/share/<token>', methods=['GET'])
def get_shared_submission(token):
    submission = submission_service.get_submission_by_share_token(token)
    if not submission:
        return api_error("分享链接无效或已过期", 404)

    # Public data only - hide user answer for privacy
    result = {
        'sid': submission['sid'],
        'paper_title': submission['paper_title'],
        'score': submission['score'],
        'graded_at': submission['graded_at'],
        'dimension_scores': json.loads(submission['dimension_scores']) if submission['dimension_scores'] else None,
        'hit_points': json.loads(submission['hit_points']) if submission['hit_points'] else [],
        'missing_points': json.loads(submission['missing_points']) if submission['missing_points'] else [],
        'ai_feedback': submission['ai_feedback'],
        'improving_suggestions': submission['improving_suggestions'],
    }
    return api_success(result)



@submissions_bp.route('/history', methods=['GET'])
@optional_token
def get_history(current_user):
    if not current_user:
        return api_success({'submissions': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))

    # 付费墙：非 VIP 且免费试用已用完的用户看不到历史中的详细反馈
    is_vip = is_vip_user(current_user)
    free_trial_used = current_user.get('free_trial_used', 0)
    full_detail = is_vip or not free_trial_used

    result = submission_service.get_user_submissions(
        current_user['uid'], page, per_page, full_detail=full_detail
    )
    return api_success(result)


@submissions_bp.route('/<sid>/feedback', methods=['POST'])
@token_required
def submit_feedback(current_user, sid):
    data = request.get_json()
    if not data or not data.get('text'):
        return api_error("请输入反馈内容", 400)

    db = get_db()
    submission = submission_service.get_submission(sid)
    if not submission or submission['uid'] != current_user['uid']:
        return api_error("提交记录不存在", 404)

    # Log feedback
    db.execute(
        """INSERT INTO admin_logs (admin_uid, action, target_type, target_id, detail)
           VALUES ('system', 'user_feedback', 'submission', ?, ?)""",
        (sid, json.dumps({'uid': current_user['uid'], 'content': data['text']}))
    )
    db.commit()

    return api_success(message="感谢反馈，我们会尽快核实")
