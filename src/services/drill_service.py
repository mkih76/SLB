# 题型训练服务
#
# 五种题型（归纳概括/综合分析/提出对策/贯彻执行/大作文）
# 的训练统计、推荐、历史和进步趋势

import json
from datetime import datetime
from src.api.utils import get_db, generate_uuid

# 题型代码与中文名映射
QUESTION_TYPE_NAMES = {
    'guina': '归纳概括',
    'zonghe': '综合分析',
    'duice': '提出对策',
    'zhixing': '贯彻执行',
    'zuowen': '大作文'
}

# 段位升级规则
LEVEL_THRESHOLDS = [
    ('diamond', 50, 90),
    ('platinum', 30, 85),
    ('gold', 15, 75),
    ('silver', 5, 60),
    ('bronze', 0, 0)
]

LEVEL_NAMES = {
    'bronze': '青铜',
    'silver': '白银',
    'gold': '黄金',
    'platinum': '铂金',
    'diamond': '钻石'
}


def _calculate_level(avg_score, total_attempts):
    """根据均分和练习次数计算段位"""
    for level, min_attempts, min_score in LEVEL_THRESHOLDS:
        if total_attempts >= min_attempts and avg_score >= min_score:
            return level
    return 'bronze'


def get_user_type_stats(uid):
    """获取用户五种题型的统计数据

    Returns:
        dict: {question_type: {total_attempts, avg_score, best_score, level, ...}}
    """
    db = get_db()
    rows = db.execute(
        "SELECT * FROM user_question_type_stats WHERE uid = ?",
        (uid,)
    ).fetchall()

    stats = {}
    for row in rows:
        stats[row['question_type']] = {
            'total_attempts': row['total_attempts'],
            'avg_score': round(row['avg_score'], 1),
            'best_score': round(row['best_score'], 1),
            'level': row['level'],
            'level_name': LEVEL_NAMES.get(row['level'], '青铜'),
            'dimension_breakdown': json.loads(row['dimension_breakdown']) if row['dimension_breakdown'] else {},
            'last_attempt_at': row['last_attempt_at']
        }

    # 补充未练习过的题型
    for qtype in QUESTION_TYPE_NAMES:
        if qtype not in stats:
            stats[qtype] = {
                'total_attempts': 0,
                'avg_score': 0,
                'best_score': 0,
                'level': 'bronze',
                'level_name': '青铜',
                'dimension_breakdown': {},
                'last_attempt_at': None
            }

    return stats


def record_drill(uid, question_type, pid, qid, sid, score, dimension_scores=None, time_spent=None):
    """记录一次题型训练

    同时更新 user_question_type_stats 汇总表
    """
    db = get_db()

    # 计算踩点率
    hit_rate = 0.0
    if dimension_scores:
        point_cov = dimension_scores.get('point_coverage', dimension_scores.get('踩点命中', 0))
        max_cov = 70 if 'point_coverage' in dimension_scores else 40
        hit_rate = point_cov / max_cov if max_cov > 0 else 0

    # 插入训练记录
    db.execute(
        """INSERT INTO question_type_drills
           (uid, question_type, pid, qid, sid, score, dimension_scores, key_point_hit_rate, time_spent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (uid, question_type, pid, qid, sid, score,
         json.dumps(dimension_scores) if dimension_scores else None,
         hit_rate, time_spent)
    )

    # 更新汇总统计
    existing = db.execute(
        "SELECT * FROM user_question_type_stats WHERE uid = ? AND question_type = ?",
        (uid, question_type)
    ).fetchone()

    now = datetime.now().isoformat()

    if existing:
        new_attempts = existing['total_attempts'] + 1
        new_total = existing['total_score'] + score
        new_avg = new_total / new_attempts
        new_best = max(existing['best_score'], score)
        new_level = _calculate_level(new_avg, new_attempts)

        db.execute(
            """UPDATE user_question_type_stats
               SET total_attempts = ?, total_score = ?, avg_score = ?,
                   best_score = ?, level = ?, last_attempt_at = ?,
                   dimension_breakdown = ?, updated_at = ?
               WHERE uid = ? AND question_type = ?""",
            (new_attempts, new_total, round(new_avg, 2), new_best,
             new_level, now,
             json.dumps(dimension_scores) if dimension_scores else existing['dimension_breakdown'],
             now, uid, question_type)
        )
    else:
        new_level = _calculate_level(score, 1)
        db.execute(
            """INSERT INTO user_question_type_stats
               (uid, question_type, total_attempts, total_score, avg_score,
                best_score, last_attempt_at, dimension_breakdown, level)
               VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)""",
            (uid, question_type, score, score, score, now,
             json.dumps(dimension_scores) if dimension_scores else '{}',
             new_level)
        )

    db.commit()


def get_drill_history(uid, question_type=None, page=1, per_page=20):
    """获取训练历史"""
    db = get_db()
    offset = (page - 1) * per_page

    if question_type:
        rows = db.execute(
            """SELECT d.*, p.title as paper_title
               FROM question_type_drills d
               LEFT JOIN papers p ON d.pid = p.pid
               WHERE d.uid = ? AND d.question_type = ?
               ORDER BY d.created_at DESC LIMIT ? OFFSET ?""",
            (uid, question_type, per_page, offset)
        ).fetchall()
        total = db.execute(
            "SELECT COUNT(*) as cnt FROM question_type_drills WHERE uid = ? AND question_type = ?",
            (uid, question_type)
        ).fetchone()['cnt']
    else:
        rows = db.execute(
            """SELECT d.*, p.title as paper_title
               FROM question_type_drills d
               LEFT JOIN papers p ON d.pid = p.pid
               WHERE d.uid = ?
               ORDER BY d.created_at DESC LIMIT ? OFFSET ?""",
            (uid, per_page, offset)
        ).fetchall()
        total = db.execute(
            "SELECT COUNT(*) as cnt FROM question_type_drills WHERE uid = ?",
            (uid,)
        ).fetchone()['cnt']

    items = []
    for row in rows:
        items.append({
            'id': row['id'],
            'question_type': row['question_type'],
            'question_type_name': QUESTION_TYPE_NAMES.get(row['question_type'], ''),
            'pid': row['pid'],
            'qid': row['qid'],
            'sid': row['sid'],
            'score': row['score'],
            'dimension_scores': json.loads(row['dimension_scores']) if row['dimension_scores'] else None,
            'key_point_hit_rate': row['key_point_hit_rate'],
            'time_spent': row['time_spent'],
            'paper_title': row['paper_title'],
            'created_at': row['created_at']
        })

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_drill_progress(uid, question_type, limit=10):
    """获取某题型的进步趋势数据

    Returns:
        list: [{score, created_at}, ...] 按时间正序
    """
    db = get_db()
    rows = db.execute(
        """SELECT score, created_at FROM question_type_drills
           WHERE uid = ? AND question_type = ?
           ORDER BY created_at DESC LIMIT ?""",
        (uid, question_type, limit)
    ).fetchall()

    # 反转为时间正序
    return [{'score': row['score'], 'created_at': row['created_at']} for row in reversed(rows)]


def get_recommended_questions(uid, question_type, limit=5):
    """推荐练习题

    优先推荐用户未做过的、难度适中的题目
    """
    db = get_db()

    # 获取用户已做过的题目
    done = db.execute(
        "SELECT DISTINCT pid, qid FROM question_type_drills WHERE uid = ? AND question_type = ?",
        (uid, question_type)
    ).fetchall()
    done_set = set((r['pid'], r['qid']) for r in done)

    # 获取所有该题型的题目
    papers = db.execute(
        "SELECT pid, title, questions, difficulty FROM papers WHERE status = 'published'"
    ).fetchall()

    candidates = []
    for paper in papers:
        questions = json.loads(paper['questions']) if paper['questions'] else []
        for q in questions:
            if q.get('type') == question_type:
                if (paper['pid'], q.get('qid', '')) not in done_set:
                    candidates.append({
                        'pid': paper['pid'],
                        'qid': q.get('qid', ''),
                        'paper_title': paper['title'],
                        'question_text': q.get('stem', q.get('question_text', '')),
                        'difficulty': paper['difficulty'],
                        'word_limit': q.get('word_limit', '')
                    })

    # 按难度排序，优先推荐中等难度
    candidates.sort(key=lambda x: abs(x['difficulty'] - 3))
    return candidates[:limit]
