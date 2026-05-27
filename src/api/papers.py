from flask import Blueprint, request

from src.services import paper_service
from src.api.utils import api_success, api_error

papers_bp = Blueprint('papers', __name__, url_prefix='/api/papers')


@papers_bp.route('', methods=['GET'])
def list_papers():
    exam_type = request.args.get('exam_type')
    year = request.args.get('year', type=int)
    province = request.args.get('province')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)

    result = paper_service.get_papers(
        exam_type=exam_type,
        year=year,
        province=province,
        page=page,
        per_page=per_page
    )
    return api_success(result)


@papers_bp.route('/<pid>', methods=['GET'])
def get_paper(pid):
    paper = paper_service.get_paper_by_pid(pid)
    if not paper:
        return api_error("试卷不存在", 404)
    return api_success(paper)


@papers_bp.route('/<pid>/question/<qid>', methods=['GET'])
def get_question(pid, qid):
    question = paper_service.get_question_by_qid(pid, qid)
    if not question:
        return api_error("题目不存在", 404)
    return api_success(question)
