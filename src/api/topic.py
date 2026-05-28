from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token, admin_required, get_db
from src.services import topic_service
from src.services.topic_scraper import run_scrape, run_scrape_xuexi

topic_bp = Blueprint('topic', __name__, url_prefix='/api/topics')


@topic_bp.route('', methods=['GET'])
def list_topics():
    """获取热点专题列表"""
    category = request.args.get('category')
    week_label = request.args.get('week')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = topic_service.get_topic_list(category, week_label, page, per_page)
    return api_success(result)


@topic_bp.route('/latest', methods=['GET'])
def latest_topics():
    """获取最新热点"""
    limit = request.args.get('limit', 5, type=int)
    result = topic_service.get_latest_topics(min(limit, 20))
    return api_success({'items': result})


@topic_bp.route('/week', methods=['GET'])
def week_topics():
    """获取本周热点"""
    week_label = request.args.get('week')
    result = topic_service.get_week_topics(week_label)
    return api_success(result)


@topic_bp.route('/<int:topic_id>', methods=['GET'])
def get_topic(topic_id):
    """获取热点详情（支持未登录浏览）"""
    import jwt
    from src.config import JWT_SECRET, JWT_ALGORITHM
    uid = None
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        try:
            data = jwt.decode(auth[7:], JWT_SECRET, algorithms=[JWT_ALGORITHM])
            uid = data.get('sub')
        except Exception:
            pass
    result = topic_service.get_topic_detail(topic_id, uid)
    if not result:
        return api_error("专题不存在", 404)
    return api_success(result)


@topic_bp.route('/<int:topic_id>/read', methods=['POST'])
@token_required
def mark_read(current_user, topic_id):
    """标记已读"""
    result = topic_service.mark_topic_read(current_user['uid'], topic_id)
    return api_success(result)


@topic_bp.route('/<int:topic_id>/bookmark', methods=['POST'])
@token_required
def toggle_bookmark(current_user, topic_id):
    """切换收藏"""
    result = topic_service.toggle_bookmark(current_user['uid'], topic_id)
    return api_success(result)


@topic_bp.route('/<int:topic_id>/notes', methods=['POST'])
@token_required
def save_notes(current_user, topic_id):
    """保存笔记"""
    data = request.get_json()
    notes = data.get('notes', '') if data else ''
    result = topic_service.save_notes(current_user['uid'], topic_id, notes)
    return api_success(result)


@topic_bp.route('/bookmarks', methods=['GET'])
@optional_token
def get_bookmarks(current_user):
    """获取收藏列表"""
    if not current_user:
        return api_success({'items': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)
    result = topic_service.get_user_bookmarks(current_user['uid'], page, per_page)
    return api_success(result)


@topic_bp.route('/stats', methods=['GET'])
@optional_token
def get_stats(current_user):
    """获取学习统计"""
    if not current_user:
        return api_success({'total_read': 0, 'total_bookmarked': 0})
    result = topic_service.get_user_learning_stats(current_user['uid'])
    return api_success(result)


@topic_bp.route('', methods=['POST'])
@admin_required()
def add_topic(current_user):
    """添加热点专题（管理员）"""
    data = request.get_json()
    if not data or not data.get('title') or not data.get('summary') or not data.get('category'):
        return api_error("缺少必要参数", 400)
    topic_id = topic_service.add_topic(data)
    return api_success({'topic_id': topic_id})


@topic_bp.route('/scrape', methods=['POST'])
@admin_required()
def scrape_topics(current_user):
    """自动抓取热点（管理员）"""
    db = get_db()
    result = run_scrape(db)
    return api_success(result)


@topic_bp.route('/scrape-xuexi', methods=['POST'])
@admin_required()
def scrape_xuexi(current_user):
    """抓取学习强国文章（管理员）"""
    db = get_db()
    result = run_scrape_xuexi(db)
    return api_success(result)
