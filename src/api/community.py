from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required
from src.services import community_service

community_bp = Blueprint('community', __name__, url_prefix='/api/community')


@community_bp.route('/posts', methods=['GET'])
def list_posts():
    """获取帖子列表"""
    post_type = request.args.get('type')
    sort = request.args.get('sort', 'latest')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = community_service.get_post_list(post_type, sort, page, per_page)
    return api_success(result)


@community_bp.route('/posts', methods=['POST'])
@token_required
def create_post(current_user):
    """发布帖子"""
    data = request.get_json()
    if not data or not data.get('content') or not data.get('post_type'):
        return api_error("缺少必要参数", 400)

    result = community_service.create_post(
        uid=current_user['uid'],
        post_type=data['post_type'],
        content=data['content'],
        title=data.get('title'),
        related_sid=data.get('related_sid'),
        related_pid=data.get('related_pid'),
        related_qid=data.get('related_qid')
    )
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    """获取帖子详情"""
    uid = None
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        try:
            from src.api.utils import verify_token
            payload = verify_token(auth[7:])
            uid = payload.get('uid')
        except Exception:
            pass

    result = community_service.get_post_detail(post_id, uid)
    if not result:
        return api_error("帖子不存在", 404)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>/comments', methods=['POST'])
@token_required
def add_comment(current_user, post_id):
    """添加评论"""
    data = request.get_json()
    if not data or not data.get('content'):
        return api_error("评论内容不能为空", 400)

    result = community_service.add_comment(
        post_id, current_user['uid'], data['content'],
        parent_comment_id=data.get('parent_comment_id')
    )
    return api_success(result)


@community_bp.route('/<target_type>/<int:target_id>/like', methods=['POST'])
@token_required
def toggle_like(current_user, target_type, target_id):
    """切换点赞"""
    result = community_service.toggle_like(
        current_user['uid'], target_type, target_id
    )
    if 'error' in result:
        return api_error(result['error'], 400)
    return api_success(result)


@community_bp.route('/featured', methods=['GET'])
def featured_posts():
    """获取精选帖子"""
    limit = request.args.get('limit', 5, type=int)
    result = community_service.get_featured_posts(min(limit, 20))
    return api_success({'items': result})


@community_bp.route('/my', methods=['GET'])
@token_required
def my_posts(current_user):
    """获取我的帖子"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = community_service.get_user_posts(current_user['uid'], page, per_page)
    return api_success(result)
