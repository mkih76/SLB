from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required, optional_token, clamp_per_page
from src.services import phrase_service

phrases_bp = Blueprint('phrases', __name__, url_prefix='/api/phrases')


@phrases_bp.route('', methods=['GET'])
def list_phrases():
    source = request.args.get('source')
    tag = request.args.get('tag')
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))

    result = phrase_service.get_phrases(
        source=source, tag=tag, page=page, per_page=per_page
    )
    return api_success(result)


@phrases_bp.route('/<int:phrase_id>', methods=['GET'])
def get_phrase(phrase_id):
    phrase = phrase_service.get_phrase_by_id(phrase_id)
    if not phrase:
        return api_error("好词不存在", 404)
    return api_success(phrase)


@phrases_bp.route('/<int:phrase_id>/favorite', methods=['POST'])
@token_required
def favorite_phrase(current_user, phrase_id):
    note = request.get_json().get('note') if request.get_json() else None
    success = phrase_service.favorite_phrase(current_user['uid'], phrase_id, note)
    if success:
        return api_success(message="已收藏")
    return api_error("收藏失败", 400)


@phrases_bp.route('/<int:phrase_id>/favorite', methods=['DELETE'])
@token_required
def unfavorite_phrase(current_user, phrase_id):
    phrase_service.unfavorite_phrase(current_user['uid'], phrase_id)
    return api_success(message="已取消收藏")


@phrases_bp.route('/favorites', methods=['GET'])
@optional_token
def get_favorites(current_user):
    if not current_user:
        return api_success({'phrases': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))

    result = phrase_service.get_user_favorites(
        current_user['uid'], page, per_page
    )
    return api_success(result)


# ============================================================
# 板块三：素材智能应用
# ============================================================

@phrases_bp.route('/study/stats', methods=['GET'])
@optional_token
def get_study_stats(current_user):
    """获取素材学习统计"""
    if not current_user:
        return api_success({'total_learned': 0, 'mastered': 0, 'learning': 0, 'new': 0})
    result = phrase_service.get_study_stats(current_user['uid'])
    return api_success(result)


@phrases_bp.route('/study/cards', methods=['GET'])
@optional_token
def get_study_cards(current_user):
    """获取今日待复习素材卡片"""
    if not current_user:
        return api_success({'cards': []})
    limit = request.args.get('limit', 5, type=int)
    result = phrase_service.get_study_cards(current_user['uid'], limit=min(limit, 20))
    return api_success({'cards': result})


@phrases_bp.route('/study/record', methods=['POST'])
@token_required
def record_study(current_user):
    """记录学习反馈"""
    data = request.get_json()
    if not data or not data.get('phrase_id') or data.get('mastery_level') is None:
        return api_error("缺少必要参数", 400)

    result = phrase_service.record_study(
        current_user['uid'], data['phrase_id'], data['mastery_level']
    )
    return api_success(result)


@phrases_bp.route('/study/history', methods=['GET'])
@optional_token
def get_study_history(current_user):
    """获取学习历史"""
    if not current_user:
        return api_success({'records': [], 'total': 0, 'page': 1, 'pages': 0})
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))
    result = phrase_service.get_study_history(current_user['uid'], page, per_page)
    return api_success(result)


@phrases_bp.route('/packs', methods=['GET'])
def list_packs():
    """获取素材包列表"""
    page = request.args.get('page', 1, type=int)
    per_page = clamp_per_page(request.args.get('limit', 20, type=int))
    result = phrase_service.get_phrase_packs(page, per_page)
    return api_success(result)


@phrases_bp.route('/packs/<int:pack_id>', methods=['GET'])
def get_pack(pack_id):
    """获取素材包详情"""
    result = phrase_service.get_phrase_pack_detail(pack_id)
    if not result:
        return api_error("素材包不存在", 404)
    return api_success(result)


@phrases_bp.route('/generate', methods=['POST'])
@token_required
def generate_paragraph(current_user):
    """AI 造段"""
    data = request.get_json()
    if not data or not data.get('point'):
        return api_error("请提供论点", 400)

    point = data['point']
    theme = data.get('theme', '通用')
    phrase_ids = data.get('phrase_ids')

    result = phrase_service.generate_paragraph(point, theme, phrase_ids)
    return api_success(result)
