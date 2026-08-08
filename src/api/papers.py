from flask import Blueprint, request
import json

from src.services import paper_service
from src.services.grader.scorer import grade_answer
from src.api.utils import api_success, api_error, clamp_per_page

import time
import threading

# 演示接口限流：每 IP 每分钟最多 5 次调用（防匿名刷 LLM 成本）
_demo_rate = {}
_demo_total = {}  # 每 IP 总调用计数（不随窗口清理，防慢速绕过）
_demo_rate_lock = threading.Lock()
DEMO_RATE_LIMIT = 5  # 每分钟次数
DEMO_RATE_WINDOW = 60  # 秒
DEMO_TOTAL_LIMIT = 20  # 每 IP 总次数上限（防换 IP 绕过分钟限流）

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
    """免登录试用批改接口（限流：每 IP 每分钟 5 次）"""
    ip = request.remote_addr or 'unknown'
    global _demo_rate
    global _demo_total
    now = time.time()
    with _demo_rate_lock:
        # 总次数限制（独立持久计数，不随窗口清理——防慢速绕过）
        total = _demo_total.get(ip, 0)
        if total >= DEMO_TOTAL_LIMIT:
            return api_error("演示次数已用完，请登录后使用完整批改", 429)
        # 分钟窗口限流
        _demo_rate = {k: v for k, v in _demo_rate.items() if v[0] > now - DEMO_RATE_WINDOW}
        rec = _demo_rate.get(ip, (0, 0))
        if rec[1] >= DEMO_RATE_LIMIT:
            return api_error("演示次数已用完，请登录后使用完整批改", 429)
        _demo_rate[ip] = (now, rec[1] + 1)
        _demo_total[ip] = total + 1

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
