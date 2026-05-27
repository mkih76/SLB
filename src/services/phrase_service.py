import json
from datetime import datetime, timedelta
from src.api.utils import get_db


def get_phrases(source=None, tag=None, status='approved', page=1, per_page=20):
    db = get_db()
    query = "SELECT * FROM good_phrases WHERE status = ?"
    params = [status]

    if source:
        query += " AND source = ?"
        params.append(source)
    if tag:
        query += " AND tag LIKE ?"
        params.append(f'%{tag}%')

    query += " ORDER BY heat DESC, created_at DESC"

    total = db.execute(
        query.replace("SELECT *", "SELECT COUNT(*)"), params
    ).fetchone()[0]

    offset = (page - 1) * per_page
    query += f" LIMIT {per_page} OFFSET {offset}"
    phrases = db.execute(query, params).fetchall()

    return {
        'phrases': [dict(p) for p in phrases],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }


def get_phrase_by_id(phrase_id: int):
    db = get_db()
    phrase = db.execute("SELECT * FROM good_phrases WHERE id = ?", (phrase_id,)).fetchone()
    return dict(phrase) if phrase else None


def add_phrase(phrase_data: dict):
    db = get_db()
    db.execute(
        """INSERT INTO good_phrases (phrase, translation, usage, source, source_url, source_date, tag, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')""",
        (
            phrase_data['phrase'],
            phrase_data.get('translation'),
            phrase_data.get('usage'),
            phrase_data['source'],
            phrase_data.get('source_url'),
            phrase_data.get('source_date'),
            json.dumps(phrase_data.get('tag', []), ensure_ascii=False)
        )
    )
    db.commit()
    return db.execute("SELECT last_insert_rowid() as id").fetchone()['id']


def approve_phrase(phrase_id: int, admin_uid: str):
    db = get_db()
    db.execute(
        "UPDATE good_phrases SET status = 'approved', approved_by = ? WHERE id = ?",
        (admin_uid, phrase_id)
    )
    db.commit()


def reject_phrase(phrase_id: int):
    db = get_db()
    db.execute(
        "UPDATE good_phrases SET status = 'rejected' WHERE id = ?",
        (phrase_id,)
    )
    db.commit()


def favorite_phrase(uid: str, phrase_id: int, note: str = None):
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT OR IGNORE INTO user_favorites (uid, phrase_id, note) VALUES (?, ?, ?)",
            (uid, phrase_id, note)
        )
        if cursor.rowcount > 0:
            db.execute("UPDATE good_phrases SET heat = heat + 1 WHERE id = ?", (phrase_id,))
        db.commit()
        return True
    except Exception:
        return False


def unfavorite_phrase(uid: str, phrase_id: int):
    db = get_db()
    db.execute("DELETE FROM user_favorites WHERE uid = ? AND phrase_id = ?", (uid, phrase_id))
    db.commit()


def get_user_favorites(uid: str, page=1, per_page=20):
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM user_favorites WHERE uid = ?", (uid,)
    ).fetchone()[0]

    favorites = db.execute(
        """SELECT p.*, uf.note as user_note, uf.created_at as favorited_at
           FROM user_favorites uf
           JOIN good_phrases p ON uf.phrase_id = p.id
           WHERE uf.uid = ?
           ORDER BY uf.created_at DESC
           LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    return {
        'phrases': [dict(f) for f in favorites],
        'total': total,
        'page': page,
        'pages': (total + per_page - 1) // per_page
    }


# ============================================================
# 板块三：素材智能应用系统
# ============================================================

CATEGORY_NAMES = {
    'jingji': '经济', 'shehui': '社会', 'wenhua': '文化',
    'shengtai': '生态', 'minsheng': '民生', 'zhili': '治理',
    'keji': '科技', 'other': '其他'
}

MASTERY_LABELS = {0: '新学', 1: '认识', 2: '熟悉', 3: '掌握'}


def _calculate_next_review(mastery_level, review_count):
    """根据掌握程度计算下次复习时间（简化版 SM-2）"""
    intervals = {0: 1, 1: 3, 2: 7, 3: 30}
    days = intervals.get(mastery_level, 1)
    return (datetime.now() + timedelta(days=days)).isoformat()


def get_study_stats(uid):
    """获取用户素材学习统计"""
    db = get_db()

    total_phrases = db.execute(
        "SELECT COUNT(*) FROM good_phrases WHERE status = 'approved'"
    ).fetchone()[0]

    learning = db.execute(
        "SELECT COUNT(*) FROM user_phrase_learning WHERE uid = ?", (uid,)
    ).fetchone()[0]

    mastered = db.execute(
        "SELECT COUNT(*) FROM user_phrase_learning WHERE uid = ? AND mastery_level >= 3", (uid,)
    ).fetchone()[0]

    due_today = db.execute(
        "SELECT COUNT(*) FROM user_phrase_learning WHERE uid = ? AND next_review_at <= datetime('now')",
        (uid,)
    ).fetchone()[0]

    # 各掌握度分布
    distribution = {}
    for level in range(4):
        cnt = db.execute(
            "SELECT COUNT(*) FROM user_phrase_learning WHERE uid = ? AND mastery_level = ?",
            (uid, level)
        ).fetchone()[0]
        distribution[MASTERY_LABELS[level]] = cnt

    return {
        'total_phrases': total_phrases,
        'learning': learning,
        'mastered': mastered,
        'due_today': due_today,
        'distribution': distribution
    }


def get_study_cards(uid, limit=5):
    """获取今日待复习的素材卡片"""
    db = get_db()

    # 优先取到期需要复习的
    due = db.execute(
        """SELECT pl.*, p.phrase, p.translation, p.usage, p.source, p.source_date, p.tag
           FROM user_phrase_learning pl
           JOIN good_phrases p ON pl.phrase_id = p.id
           WHERE pl.uid = ? AND pl.next_review_at <= datetime('now')
           ORDER BY pl.next_review_at ASC LIMIT ?""",
        (uid, limit)
    ).fetchall()

    if len(due) >= limit:
        return [_format_study_card(dict(c)) for c in due]

    # 不够则补充新素材
    remaining = limit - len(due)
    learned_ids = db.execute(
        "SELECT phrase_id FROM user_phrase_learning WHERE uid = ?", (uid,)
    ).fetchall()
    learned_id_set = {r['phrase_id'] for r in learned_ids}

    new_phrases = db.execute(
        "SELECT * FROM good_phrases WHERE status = 'approved' ORDER BY heat DESC, RANDOM() LIMIT 50"
    ).fetchall()

    new_cards = []
    for p in new_phrases:
        if p['id'] not in learned_id_set:
            new_cards.append(dict(p))
        if len(new_cards) >= remaining:
            break

    result = [_format_study_card(dict(c)) for c in due]
    for nc in new_cards:
        result.append({
            'phrase_id': nc['id'],
            'phrase': nc['phrase'],
            'translation': nc.get('translation', ''),
            'usage': nc.get('usage', ''),
            'source': nc.get('source', ''),
            'source_date': nc.get('source_date', ''),
            'tag': nc.get('tag', '[]'),
            'mastery_level': 0,
            'mastery_label': '新学',
            'is_new': True
        })

    return result


def _format_study_card(row):
    return {
        'phrase_id': row.get('phrase_id'),
        'phrase': row.get('phrase', ''),
        'translation': row.get('translation', ''),
        'usage': row.get('usage', ''),
        'source': row.get('source', ''),
        'source_date': row.get('source_date', ''),
        'tag': row.get('tag', '[]'),
        'mastery_level': row.get('mastery_level', 0),
        'mastery_label': MASTERY_LABELS.get(row.get('mastery_level', 0), '新学'),
        'review_count': row.get('review_count', 0),
        'applied_count': row.get('applied_count', 0),
        'is_new': False
    }


def record_study(uid, phrase_id, mastery_level):
    """记录用户对素材的学习反馈（不认识/认识/熟悉/掌握）"""
    db = get_db()
    mastery_level = max(0, min(3, int(mastery_level)))
    next_review = _calculate_next_review(mastery_level, 0)

    existing = db.execute(
        "SELECT id FROM user_phrase_learning WHERE uid = ? AND phrase_id = ?",
        (uid, phrase_id)
    ).fetchone()

    if existing:
        db.execute(
            """UPDATE user_phrase_learning
               SET mastery_level = ?, next_review_at = ?,
                   review_count = review_count + 1, last_reviewed_at = datetime('now')
               WHERE uid = ? AND phrase_id = ?""",
            (mastery_level, next_review, uid, phrase_id)
        )
    else:
        db.execute(
            """INSERT INTO user_phrase_learning
               (uid, phrase_id, mastery_level, next_review_at, review_count, last_reviewed_at)
               VALUES (?, ?, ?, ?, 1, datetime('now'))""",
            (uid, phrase_id, mastery_level, next_review)
        )
    db.commit()
    return {'mastery_level': mastery_level, 'next_review_at': next_review}


def mark_applied(uid, phrase_id):
    """标记素材在作答中被使用过"""
    db = get_db()
    db.execute(
        """UPDATE user_phrase_learning SET applied_count = applied_count + 1
           WHERE uid = ? AND phrase_id = ?""",
        (uid, phrase_id)
    )
    db.commit()


def get_phrase_packs(page=1, per_page=20):
    """获取素材包列表"""
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM phrase_packs WHERE status = 'published'"
    ).fetchone()[0]

    packs = db.execute(
        """SELECT * FROM phrase_packs WHERE status = 'published'
           ORDER BY sort_order ASC, created_at DESC LIMIT ? OFFSET ?""",
        (per_page, offset)
    ).fetchall()

    items = []
    for p in packs:
        pack = dict(p)
        phrase_ids = json.loads(pack.get('phrase_ids', '[]'))
        pack['phrase_count'] = len(phrase_ids)
        items.append(pack)

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_phrase_pack_detail(pack_id):
    """获取素材包详情（含素材列表）"""
    db = get_db()
    pack = db.execute("SELECT * FROM phrase_packs WHERE id = ?", (pack_id,)).fetchone()
    if not pack:
        return None

    pack = dict(pack)
    phrase_ids = json.loads(pack.get('phrase_ids', '[]'))

    phrases = []
    if phrase_ids:
        placeholders = ','.join('?' * len(phrase_ids))
        rows = db.execute(
            f"SELECT * FROM good_phrases WHERE id IN ({placeholders}) AND status = 'approved'",
            phrase_ids
        ).fetchall()
        phrases = [dict(r) for r in rows]

    pack['phrases'] = phrases
    pack['phrase_count'] = len(phrases)
    return pack


def get_study_history(uid, page=1, per_page=20):
    """获取用户素材学习历史"""
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM user_phrase_learning WHERE uid = ?", (uid,)
    ).fetchone()[0]

    rows = db.execute(
        """SELECT pl.*, p.phrase, p.source
           FROM user_phrase_learning pl
           JOIN good_phrases p ON pl.phrase_id = p.id
           WHERE pl.uid = ?
           ORDER BY pl.last_reviewed_at DESC LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    items = []
    for r in rows:
        items.append({
            'phrase_id': r['phrase_id'],
            'phrase': r['phrase'],
            'source': r['source'],
            'mastery_level': r['mastery_level'],
            'mastery_label': MASTERY_LABELS.get(r['mastery_level'], '新学'),
            'review_count': r['review_count'],
            'applied_count': r['applied_count'],
            'last_reviewed_at': r['last_reviewed_at']
        })

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def generate_paragraph(point, theme, phrase_ids=None):
    """AI 造段：围绕论点生成示范段落"""
    from src.services.grader.scorer import call_llm

    db = get_db()

    # 获取素材池
    phrases_pool = []
    if phrase_ids:
        placeholders = ','.join('?' * len(phrase_ids))
        rows = db.execute(
            f"SELECT phrase, usage FROM good_phrases WHERE id IN ({placeholders}) AND status = 'approved'",
            phrase_ids
        ).fetchall()
        phrases_pool = [{'phrase': r['phrase'], 'usage': r['usage']} for r in rows]
    else:
        # 按主题自动匹配
        rows = db.execute(
            """SELECT phrase, usage FROM good_phrases
               WHERE status = 'approved' AND (tag LIKE ? OR usage LIKE ?)
               ORDER BY heat DESC LIMIT 10""",
            (f'%{theme}%', f'%{theme}%')
        ).fetchall()
        phrases_pool = [{'phrase': r['phrase'], 'usage': r['usage']} for r in rows]

    phrases_text = json.dumps(phrases_pool, ensure_ascii=False) if phrases_pool else '（无可用素材，请自由发挥）'

    prompt = f"""你是申论写作专家。请围绕以下论点，写一个150字左右的申论段落。

论点：{point}
主题：{theme}

请优先使用以下素材（金句）：
{phrases_text}

要求：
1. 段落结构：论点句 → 分析/论据 → 回扣论点
2. 至少嵌入2条素材，且嵌入自然不生硬
3. 语言风格符合申论规范，避免口语化
4. 直接输出段落内容，不要加标题或解释"""

    result = call_llm(prompt)

    # 提取使用的素材ID
    used_phrases = []
    for sp in phrases_pool:
        if sp['phrase'] in result:
            used_phrases.append(sp['phrase'])

    return {
        'paragraph': result,
        'theme': theme,
        'point': point,
        'used_phrases': used_phrases,
        'phrases_pool_count': len(phrases_pool)
    }
