# 时政热点专题服务
#
# 系统性的热点积累，AI 押题分析

import json
from datetime import datetime, timedelta
from src.api.utils import get_db

CATEGORY_NAMES = {
    'shiping': '时评', 'lilun': '理论', 'dangjian': '党建',
    'xuexi': '学习强国',
    'jingji': '经济', 'shehui': '社会', 'wenhua': '文化',
    'shengtai': '生态', 'minsheng': '民生', 'zhili': '治理',
    'keji': '科技'
}


def get_topic_list(category=None, week_label=None, page=1, per_page=20):
    """获取热点专题列表"""
    db = get_db()
    query = "SELECT * FROM hot_topics WHERE status = 'published'"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)
    if week_label:
        query += " AND week_label = ?"
        params.append(week_label)

    query += " ORDER BY created_at DESC"

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    rows = db.execute(query, params).fetchall()

    items = []
    for r in rows:
        items.append(_format_topic_brief(dict(r)))

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_topic_detail(topic_id, uid=None):
    """获取热点专题详情"""
    db = get_db()
    row = db.execute("SELECT * FROM hot_topics WHERE id = ?", (topic_id,)).fetchone()
    if not row:
        return None

    topic = _format_topic_detail(dict(row))

    # 获取用户学习状态
    if uid:
        learning = db.execute(
            "SELECT * FROM user_topic_learning WHERE uid = ? AND topic_id = ?",
            (uid, topic_id)
        ).fetchone()
        if learning:
            topic['user_state'] = {
                'is_read': bool(learning['is_read']),
                'is_bookmarked': bool(learning['is_bookmarked']),
                'notes': learning['notes'] or ''
            }
        else:
            topic['user_state'] = {'is_read': False, 'is_bookmarked': False, 'notes': ''}

    return topic


def get_latest_topics(limit=5):
    """获取最新热点"""
    db = get_db()
    rows = db.execute(
        """SELECT * FROM hot_topics WHERE status = 'published'
           ORDER BY created_at DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    return [_format_topic_brief(dict(r)) for r in rows]


def get_week_topics(week_label=None):
    """获取本周热点"""
    db = get_db()
    if not week_label:
        # 获取最新一周
        latest = db.execute(
            "SELECT week_label FROM hot_topics WHERE status = 'published' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        week_label = latest['week_label'] if latest else ''

    rows = db.execute(
        """SELECT * FROM hot_topics WHERE week_label = ? AND status = 'published'
           ORDER BY id ASC""",
        (week_label,)
    ).fetchall()

    return {
        'week_label': week_label,
        'topics': [_format_topic_brief(dict(r)) for r in rows]
    }


def mark_topic_read(uid, topic_id):
    """标记热点为已读"""
    db = get_db()
    _upsert_learning(db, uid, topic_id, is_read=1)
    return {'topic_id': topic_id, 'is_read': True}


def toggle_bookmark(uid, topic_id):
    """切换收藏状态"""
    db = get_db()
    existing = db.execute(
        "SELECT is_bookmarked FROM user_topic_learning WHERE uid = ? AND topic_id = ?",
        (uid, topic_id)
    ).fetchone()

    new_state = 0 if (existing and existing['is_bookmarked']) else 1
    _upsert_learning(db, uid, topic_id, is_bookmarked=new_state)
    return {'topic_id': topic_id, 'is_bookmarked': bool(new_state)}


def save_notes(uid, topic_id, notes):
    """保存用户笔记"""
    db = get_db()
    _upsert_learning(db, uid, topic_id, notes=notes)
    return {'topic_id': topic_id, 'notes': notes}


def get_user_bookmarks(uid, page=1, per_page=20):
    """获取用户收藏的热点"""
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        """SELECT COUNT(*) FROM user_topic_learning
           WHERE uid = ? AND is_bookmarked = 1""",
        (uid,)
    ).fetchone()[0]

    rows = db.execute(
        """SELECT t.*, utl.notes as user_notes
           FROM user_topic_learning utl
           JOIN hot_topics t ON utl.topic_id = t.id
           WHERE utl.uid = ? AND utl.is_bookmarked = 1
           ORDER BY utl.created_at DESC LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    return {
        'items': [_format_topic_brief(dict(r)) for r in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_user_learning_stats(uid):
    """获取用户热点学习统计"""
    db = get_db()
    total_topics = db.execute(
        "SELECT COUNT(*) FROM hot_topics WHERE status = 'published'"
    ).fetchone()[0]

    read_count = db.execute(
        "SELECT COUNT(*) FROM user_topic_learning WHERE uid = ? AND is_read = 1",
        (uid,)
    ).fetchone()[0]

    bookmark_count = db.execute(
        "SELECT COUNT(*) FROM user_topic_learning WHERE uid = ? AND is_bookmarked = 1",
        (uid,)
    ).fetchone()[0]

    # 各类别已读数
    category_stats = {}
    for cat_key, cat_name in CATEGORY_NAMES.items():
        cnt = db.execute(
            """SELECT COUNT(*) FROM user_topic_learning utl
               JOIN hot_topics t ON utl.topic_id = t.id
               WHERE utl.uid = ? AND utl.is_read = 1 AND t.category = ?""",
            (uid, cat_key)
        ).fetchone()[0]
        category_stats[cat_name] = cnt

    return {
        'total_topics': total_topics,
        'read_count': read_count,
        'bookmark_count': bookmark_count,
        'unread_count': max(0, total_topics - read_count),
        'category_stats': category_stats
    }


def add_topic(data):
    """添加热点专题（管理员）"""
    db = get_db()
    cursor = db.execute(
        """INSERT INTO hot_topics
           (title, summary, category, keywords, multi_views, related_phrases,
            related_papers, exam_prediction, exam_history, week_label, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published')""",
        (
            data['title'],
            data['summary'],
            data['category'],
            json.dumps(data.get('keywords', []), ensure_ascii=False),
            json.dumps(data.get('multi_views', []), ensure_ascii=False),
            json.dumps(data.get('related_phrases', []), ensure_ascii=False),
            json.dumps(data.get('related_papers', []), ensure_ascii=False),
            json.dumps(data.get('exam_prediction', {}), ensure_ascii=False),
            json.dumps(data.get('exam_history', []), ensure_ascii=False),
            data.get('week_label', '')
        )
    )
    db.commit()
    return cursor.lastrowid


def _upsert_learning(db, uid, topic_id, is_read=None, is_bookmarked=None, notes=None):
    """更新或插入学习记录"""
    existing = db.execute(
        "SELECT id FROM user_topic_learning WHERE uid = ? AND topic_id = ?",
        (uid, topic_id)
    ).fetchone()

    if existing:
        updates = []
        params = []
        if is_read is not None:
            updates.append("is_read = ?")
            params.append(is_read)
        if is_bookmarked is not None:
            updates.append("is_bookmarked = ?")
            params.append(is_bookmarked)
        if notes is not None:
            updates.append("notes = ?")
            params.append(notes)
        if updates:
            params.extend([uid, topic_id])
            db.execute(
                f"UPDATE user_topic_learning SET {', '.join(updates)} WHERE uid = ? AND topic_id = ?",
                params
            )
    else:
        db.execute(
            """INSERT INTO user_topic_learning (uid, topic_id, is_read, is_bookmarked, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (uid, topic_id, is_read or 0, is_bookmarked or 0, notes or '')
        )
    db.commit()


def _format_topic_brief(row):
    """格式化热点摘要"""
    keywords = json.loads(row.get('keywords', '[]')) if isinstance(row.get('keywords'), str) else row.get('keywords', [])
    exam_prediction = json.loads(row.get('exam_prediction', '{}')) if isinstance(row.get('exam_prediction'), str) else row.get('exam_prediction', {})
    exam_history = json.loads(row.get('exam_history', '[]')) if isinstance(row.get('exam_history'), str) else row.get('exam_history', [])

    return {
        'topic_id': row['id'],
        'title': row['title'],
        'summary': (row['summary'] or '')[:100],
        'category': row['category'],
        'category_name': CATEGORY_NAMES.get(row['category'], row['category']),
        'keywords': keywords,
        'probability': exam_prediction.get('probability', ''),
        'related_count': len(exam_history),
        'week_label': row.get('week_label', ''),
        'created_at': row.get('created_at', '')
    }


def _format_topic_detail(row):
    """格式化热点详情"""
    return {
        'topic_id': row['id'],
        'title': row['title'],
        'summary': row['summary'],
        'category': row['category'],
        'category_name': CATEGORY_NAMES.get(row['category'], row['category']),
        'keywords': json.loads(row.get('keywords', '[]')) if isinstance(row.get('keywords'), str) else row.get('keywords', []),
        'multi_views': json.loads(row.get('multi_views', '[]')) if isinstance(row.get('multi_views'), str) else row.get('multi_views', []),
        'related_phrases': json.loads(row.get('related_phrases', '[]')) if isinstance(row.get('related_phrases'), str) else row.get('related_phrases', []),
        'related_papers': json.loads(row.get('related_papers', '[]')) if isinstance(row.get('related_papers'), str) else row.get('related_papers', []),
        'exam_prediction': json.loads(row.get('exam_prediction', '{}')) if isinstance(row.get('exam_prediction'), str) else row.get('exam_prediction', {}),
        'exam_history': json.loads(row.get('exam_history', '[]')) if isinstance(row.get('exam_history'), str) else row.get('exam_history', []),
        'week_label': row.get('week_label', ''),
        'source_url': row.get('source_url', ''),
        'original_text': row.get('original_text', ''),
        'created_at': row.get('created_at', '')
    }
