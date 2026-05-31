from flask import Blueprint, request
import json

from src.services import paper_service
from src.services.grader.scorer import grade_answer
from src.api.utils import api_success, api_error, clamp_per_page

papers_bp = Blueprint('papers', __name__, url_prefix='/api/papers')


@papers_bp.route('', methods=['GET'])
def list_papers():
    exam_type = request.args.get('exam_type')
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))

    result = paper_service.get_papers(
        exam_type=exam_type,
        year=year,
        province=province,
        page=page,
        per_page=per_page
    )
    # Remove answer_keys from list response to prevent cheating
    if isinstance(result, dict) and 'papers' in result:
        for paper in result['papers']:
            paper.pop('answer_keys', None)
    return api_success(result)


@papers_bp.route('/<pid>', methods=['GET'])
def get_paper(pid):
    paper = paper_service.get_paper_by_pid(pid)
    if not paper:
        return api_error("试卷不存在", 404)
    # Remove answer_keys from public response to prevent cheating
    paper.pop('answer_keys', None)
    return api_success(paper)


@papers_bp.route('/<pid>/question/<qid>', methods=['GET'])
def get_question(pid, qid):
    question = paper_service.get_question_by_qid(pid, qid)
    if not question:
        return api_error("题目不存在", 404)
    return api_success(question)


@papers_bp.route('/demo/grade', methods=['POST'])
def demo_grade():
    """免登录试用批改接口"""
    data = request.get_json()
    if not data:
        return api_error("请提供答案", 400)

    pid = data.get('pid')
    qid = data.get('qid')
    user_answer = data.get('user_answer', '').strip()

    if not pid or not qid or not user_answer:
        return api_error("缺少必要参数", 400)

    question = paper_service.get_question_by_qid(pid, qid)
    if not question:
        return api_error("题目不存在", 404)

    paper = paper_service.get_paper_by_pid(pid)
    material = json.loads(paper['material']) if paper and paper['material'] else None

    try:
        grading_result = grade_answer(pid, qid, question, user_answer, material)
        return api_success({
            'score': grading_result['score'],
            'dimension_scores': grading_result.get('dimension_scores'),
            'ai_feedback': grading_result.get('ai_feedback'),
            'hit_points': grading_result.get('hit_points', []),
            'missing_points': grading_result.get('missing_points', []),
            'improving_suggestions': grading_result.get('improving_suggestions')
        })
    except Exception as e:
        return api_error("批改失败，请稍后重试", 500)
