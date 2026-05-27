from flask import Blueprint, request

from src.api.utils import api_success, api_error, token_required
from src.services import phrase_service

phrases_bp = Blueprint('phrases', __name__, url_prefix='/api/phrases')


@phrases_bp.route('', methods=['GET'])
def list_phrases():
    source = request.args.get('source')
    tag = request.args.get('tag')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)

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
@token_required
def get_favorites(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 20, type=int)

    result = phrase_service.get_user_favorites(
        current_user['uid'], page, per_page
    )
    return api_success(result)
