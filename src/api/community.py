from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token
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
            import jwt
            from src.config import JWT_SECRET, JWT_ALGORITHM
            data = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            uid = data.get('sub')
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
@optional_token
def my_posts(current_user):
    """获取我的帖子"""
    if not current_user:
        return api_success({'posts': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = community_service.get_user_posts(current_user['uid'], page, per_page)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>', methods=['PUT'])
@token_required
def edit_post(current_user, post_id):
    """编辑自己的帖子"""
    data = request.get_json()
    if not data:
        return api_error("请提供更新内容", 400)
    result = community_service.update_post(
        post_id, current_user['uid'],
        content=data.get('content'),
        title=data.get('title')
    )
    if 'error' in result:
        return api_error(result['error'], 403)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@token_required
def delete_post(current_user, post_id):
    """删除自己的帖子"""
    result = community_service.delete_post(post_id, current_user['uid'])
    if 'error' in result:
        return api_error(result['error'], 403)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>/feature', methods=['POST'])
@token_required
def feature_post(current_user, post_id):
    """管理员精选帖子"""
    if current_user.get('role') not in ('admin', 'super_admin'):
        return api_error("无权限", 403)
    result = community_service.feature_post(post_id)
    if 'error' in result:
        return api_error(result['error'], 404)
    return api_success(result)


@community_bp.route('/posts/<int:post_id>/pin', methods=['POST'])
@token_required
def pin_post(current_user, post_id):
    """管理员置顶帖子"""
    if current_user.get('role') not in ('admin', 'super_admin'):
        return api_error("无权限", 403)
    result = community_service.pin_post(post_id)
    if 'error' in result:
        return api_error(result['error'], 404)
    return api_success(result)
