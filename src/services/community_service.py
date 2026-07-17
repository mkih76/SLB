# 社区互助系统服务
#
# 晒答案、求助帖、讨论、范文精选、评论、点赞

import json
from datetime import datetime
from src.api.utils import get_db, generate_uuid


POST_TYPE_NAMES = {
    'answer_share': '晒答案', 'question': '求助',
    'discussion': '讨论', 'tips': '备考经验'
}


def create_post(uid, post_type, content, title=None, related_sid=None, related_pid=None, related_qid=None):
    """发布帖子"""
    if post_type not in POST_TYPE_NAMES:
        return {'error': '无效的帖子类型'}

    db = get_db()
    cursor = db.execute(
        """INSERT INTO community_posts
           (uid, post_type, title, content, related_sid, related_pid, related_qid)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (uid, post_type, title, content, related_sid, related_pid, related_qid)
    )
    db.commit()
    return {'post_id': cursor.lastrowid}


def get_post_list(post_type=None, sort='latest', page=1, per_page=20):
    """获取帖子列表"""
    db = get_db()
    query = "SELECT p.*, u.nickname, u.avatar_url FROM community_posts p LEFT JOIN users u ON p.uid = u.uid WHERE p.status = 'published'"
    params = []

    if post_type:
        query += " AND p.post_type = ?"
        params.append(post_type)

    if sort == 'hot':
        query += " ORDER BY p.is_pinned DESC, p.like_count DESC, p.created_at DESC"
    elif sort == 'featured':
        query += " ORDER BY p.is_pinned DESC, p.is_featured DESC, p.created_at DESC"
    else:
        query += " ORDER BY p.is_pinned DESC, p.created_at DESC"

    total = db.execute(
        query.replace("SELECT p.*, u.nickname, u.avatar_url", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    rows = db.execute(query, params).fetchall()

    items = [format_post_brief(dict(r)) for r in rows]
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_post_detail(post_id, uid=None):
    """获取帖子详情"""
    db = get_db()
    row = db.execute(
        """SELECT p.*, u.nickname, u.avatar_url
           FROM community_posts p LEFT JOIN users u ON p.uid = u.uid
           WHERE p.id = ?""",
        (post_id,)
    ).fetchone()
    if not row:
        return None

    # 增加浏览量
    db.execute(
        "UPDATE community_posts SET view_count = view_count + 1 WHERE id = ?",
        (post_id,)
    )
    db.commit()

    post = format_post_detail(dict(row))

    # 获取评论
    post['comments'] = get_comments(post_id)

    # 检查当前用户是否点赞
    if uid:
        liked = db.execute(
            "SELECT 1 FROM community_likes WHERE uid = ? AND target_type = 'post' AND target_id = ?",
            (uid, post_id)
        ).fetchone()
        post['is_liked'] = bool(liked)

    return post


def get_comments(post_id):
    """获取帖子评论"""
    db = get_db()
    rows = db.execute(
        """SELECT c.*, u.nickname, u.avatar_url
           FROM community_comments c LEFT JOIN users u ON c.uid = u.uid
           WHERE c.post_id = ? AND c.status = 'published'
           ORDER BY c.created_at ASC""",
        (post_id,)
    ).fetchall()

    comments = []
    for r in rows:
        c = dict(r)
        comments.append({
            'comment_id': c['id'],
            'uid': c['uid'],
            'nickname': c['nickname'] or '匿名用户',
            'content': c['content'],
            'parent_comment_id': c['parent_comment_id'],
            'like_count': c['like_count'],
            'created_at': c['created_at']
        })
    return comments


def add_comment(post_id, uid, content, parent_comment_id=None):
    """添加评论"""
    db = get_db()
    cursor = db.execute(
        """INSERT INTO community_comments (post_id, uid, content, parent_comment_id)
           VALUES (?, ?, ?, ?)""",
        (post_id, uid, content, parent_comment_id)
    )
    db.execute(
        "UPDATE community_posts SET comment_count = comment_count + 1 WHERE id = ?",
        (post_id,)
    )
    db.commit()
    return {'comment_id': cursor.lastrowid}


def toggle_like(uid, target_type, target_id):
    """切换点赞"""
    if target_type not in ('post', 'comment'):
        return {'error': '无效的目标类型'}

    db = get_db()
    existing = db.execute(
        "SELECT 1 FROM community_likes WHERE uid = ? AND target_type = ? AND target_id = ?",
        (uid, target_type, target_id)
    ).fetchone()

    if existing:
        db.execute(
            "DELETE FROM community_likes WHERE uid = ? AND target_type = ? AND target_id = ?",
            (uid, target_type, target_id)
        )
        if target_type == 'post':
            db.execute(
                "UPDATE community_posts SET like_count = MAX(0, like_count - 1) WHERE id = ?",
                (target_id,)
            )
        else:
            db.execute(
                "UPDATE community_comments SET like_count = MAX(0, like_count - 1) WHERE id = ?",
                (target_id,)
            )
        liked = False
    else:
        db.execute(
            "INSERT INTO community_likes (uid, target_type, target_id) VALUES (?, ?, ?)",
            (uid, target_type, target_id)
        )
        if target_type == 'post':
            db.execute(
                "UPDATE community_posts SET like_count = like_count + 1 WHERE id = ?",
                (target_id,)
            )
        else:
            db.execute(
                "UPDATE community_comments SET like_count = like_count + 1 WHERE id = ?",
                (target_id,)
            )
        liked = True

    db.commit()
    return {'liked': liked}


def update_post(post_id, uid, content=None, title=None):
    """编辑帖子（仅作者可编辑）"""
    db = get_db()
    post = db.execute("SELECT uid FROM community_posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return {'error': '帖子不存在'}
    if post['uid'] != uid:
        return {'error': '只能编辑自己的帖子'}

    updates = []
    params = []
    if content is not None:
        updates.append("content = ?")
        params.append(content)
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if not updates:
        return {'error': '没有要更新的内容'}

    params.append(post_id)
    db.execute(f"UPDATE community_posts SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()
    return {'post_id': post_id, 'updated': True}


def delete_post(post_id, uid):
    """删除帖子（仅作者或管理员可删除）"""
    db = get_db()
    post = db.execute("SELECT uid FROM community_posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return {'error': '帖子不存在'}
    if post['uid'] != uid:
        return {'error': '只能删除自己的帖子'}

    db.execute("UPDATE community_posts SET status = 'deleted' WHERE id = ?", (post_id,))
    db.commit()
    return {'post_id': post_id, 'deleted': True}


def feature_post(post_id):
    """管理员精选/取消精选帖子"""
    db = get_db()
    post = db.execute("SELECT is_featured FROM community_posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return {'error': '帖子不存在'}
    new_val = 0 if post['is_featured'] else 1
    db.execute("UPDATE community_posts SET is_featured = ? WHERE id = ?", (new_val, post_id))
    db.commit()
    return {'post_id': post_id, 'is_featured': bool(new_val)}


def pin_post(post_id):
    """管理员置顶/取消置顶帖子"""
    db = get_db()
    post = db.execute("SELECT is_pinned FROM community_posts WHERE id = ?", (post_id,)).fetchone()
    if not post:
        return {'error': '帖子不存在'}
    new_val = 0 if post['is_pinned'] else 1
    db.execute("UPDATE community_posts SET is_pinned = ? WHERE id = ?", (new_val, post_id))
    db.commit()
    return {'post_id': post_id, 'is_pinned': bool(new_val)}


def get_user_posts(uid, page=1, per_page=20):
    """获取用户的帖子"""
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM community_posts WHERE uid = ? AND status = 'published'",
        (uid,)
    ).fetchone()[0]

    rows = db.execute(
        """SELECT p.*, u.nickname, u.avatar_url
           FROM community_posts p LEFT JOIN users u ON p.uid = u.uid
           WHERE p.uid = ? AND p.status = 'published'
           ORDER BY p.created_at DESC LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    return {
        'items': [format_post_brief(dict(r)) for r in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_featured_posts(limit=5):
    """获取精选帖子"""
    db = get_db()
    rows = db.execute(
        """SELECT p.*, u.nickname, u.avatar_url
           FROM community_posts p LEFT JOIN users u ON p.uid = u.uid
           WHERE p.status = 'published' AND p.is_featured = 1
           ORDER BY p.created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    return [format_post_brief(dict(r)) for r in rows]


def format_post_brief(row):
    """格式化帖子摘要"""
    return {
        'post_id': row['id'],
        'post_type': row['post_type'],
        'post_type_name': POST_TYPE_NAMES.get(row['post_type'], row['post_type']),
        'title': row['title'] or '',
        'content': (row['content'] or '')[:120],
        'nickname': row.get('nickname') or '匿名用户',
        'view_count': row['view_count'],
        'like_count': row['like_count'],
        'comment_count': row['comment_count'],
        'is_featured': bool(row['is_featured']),
        'related_sid': row.get('related_sid'),
        'created_at': row['created_at']
    }


def format_post_detail(row):
    """格式化帖子详情"""
    return {
        'post_id': row['id'],
        'uid': row['uid'],
        'post_type': row['post_type'],
        'post_type_name': POST_TYPE_NAMES.get(row['post_type'], row['post_type']),
        'title': row['title'] or '',
        'content': row['content'],
        'nickname': row.get('nickname') or '匿名用户',
        'avatar_url': row.get('avatar_url', ''),
        'view_count': row['view_count'],
        'like_count': row['like_count'],
        'comment_count': row['comment_count'],
        'is_featured': bool(row['is_featured']),
        'related_sid': row.get('related_sid'),
        'related_pid': row.get('related_pid'),
        'related_qid': row.get('related_qid'),
        'created_at': row['created_at'],
        'is_liked': False
    }
