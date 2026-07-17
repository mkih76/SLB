# 备考计划引擎
#
# 根据考试日期、当前水平、可用时间，自动生成个性化每日任务

import json
from datetime import datetime, date, timedelta
from src.api.utils import get_db

EXAM_TYPE_NAMES = {
    'guokao': '国考', 'shengkao': '省考', 'xuandiao': '选调'
}

LEVEL_NAMES = {
    'beginner': '入门', 'intermediate': '中级', 'advanced': '高级'
}

TASK_TYPE_NAMES = {
    'drill': '题型练习', 'phrase_read': '素材学习',
    'simulation': '全真模拟', 'review': '复习回顾', 'essay_write': '大作文练习'
}


def assess_user_level(uid):
    """基于历史数据评估用户当前水平"""
    db = get_db()
    row = db.execute(
        "SELECT AVG(score) as avg_score, COUNT(*) as cnt FROM submissions WHERE uid = ? AND score IS NOT NULL",
        (uid,)
    ).fetchone()

    if not row or row['cnt'] < 3:
        return 'beginner'
    avg = row['avg_score'] or 0
    if avg >= 75:
        return 'advanced'
    elif avg >= 55:
        return 'intermediate'
    return 'beginner'


def create_study_plan(uid, plan_name, exam_date, exam_type, daily_minutes=120):
    """创建备考计划"""
    db = get_db()

    # 检查是否有活跃计划
    existing = db.execute(
        "SELECT id FROM study_plans WHERE uid = ? AND status = 'active'",
        (uid,)
    ).fetchone()
    if existing:
        return {'error': '你已有一个活跃的备考计划，请先完成或暂停'}

    try:
        exam_dt = datetime.strptime(exam_date, '%Y-%m-%d').date()
    except ValueError:
        return {'error': '日期格式不正确，请使用 YYYY-MM-DD'}

    days_remaining = (exam_dt - date.today()).days
    if days_remaining <= 0:
        return {'error': '考试日期已过，请选择未来日期'}

    current_level = assess_user_level(uid)
    daily_minutes = max(30, min(480, int(daily_minutes)))

    # 生成阶段计划
    if days_remaining > 60:
        phases = [
            {"name": "基础夯实", "days": int(days_remaining * 0.4),
             "focus": "分题型专项训练",
             "ratio": {"drill": 0.5, "phrase_read": 0.3, "essay_write": 0.2}},
            {"name": "强化提升", "days": int(days_remaining * 0.35),
             "focus": "全真模拟+薄弱项突破",
             "ratio": {"simulation": 0.4, "drill": 0.3, "phrase_read": 0.2, "review": 0.1}},
            {"name": "冲刺模考", "days": int(days_remaining * 0.25),
             "focus": "全真模考+素材巩固",
             "ratio": {"simulation": 0.5, "phrase_read": 0.3, "review": 0.2}}
        ]
    elif days_remaining > 20:
        phases = [
            {"name": "重点突破", "days": int(days_remaining * 0.5),
             "focus": "薄弱题型+高频素材",
             "ratio": {"drill": 0.5, "phrase_read": 0.3, "simulation": 0.2}},
            {"name": "模考冲刺", "days": int(days_remaining * 0.5),
             "focus": "全真模考+查漏补缺",
             "ratio": {"simulation": 0.6, "review": 0.2, "phrase_read": 0.2}}
        ]
    else:
        phases = [
            {"name": "考前冲刺", "days": days_remaining,
             "focus": "全真模考+素材速记",
             "ratio": {"simulation": 0.5, "phrase_read": 0.3, "review": 0.2}}
        ]

    # 调整天数总和
    total_phase_days = sum(p['days'] for p in phases)
    if total_phase_days < days_remaining:
        phases[-1]['days'] += days_remaining - total_phase_days

    now = datetime.now().isoformat()
    cursor = db.execute(
        """INSERT INTO study_plans
           (uid, plan_name, exam_date, exam_type, daily_minutes, current_level,
            phases, daily_tasks_tmpl, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)""",
        (uid, plan_name, exam_date, exam_type, daily_minutes, current_level,
         json.dumps(phases, ensure_ascii=False), json.dumps({}, ensure_ascii=False),
         now, now)
    )
    plan_id = cursor.lastrowid
    db.commit()

    # 生成前7天的每日任务
    _generate_daily_tasks(db, uid, plan_id, phases, daily_minutes, days=7)

    return get_plan_detail(uid, plan_id)


def _generate_daily_tasks(db, uid, plan_id, phases, daily_minutes, days=7):
    """生成每日任务"""
    weaknesses = _get_user_weaknesses(uid)
    task_date = date.today()

    for i in range(days):
        # 确定当前阶段
        phase = _get_phase_for_day(phases, i)
        if not phase:
            break

        ratio = phase.get('ratio', {})
        tasks_for_day = []

        # 题型练习
        drill_min = int(daily_minutes * ratio.get('drill', 0))
        if drill_min > 0:
            target_type = weaknesses[0] if weaknesses else 'guina'
            type_names = {'guina': '归纳概括', 'zonghe': '综合分析', 'duice': '提出对策',
                          'zhixing': '贯彻执行', 'zuowen': '大作文'}
            tasks_for_day.append({
                'task_type': 'drill',
                'task_detail': json.dumps({
                    'title': f'练习{type_names.get(target_type, target_type)}题 2道',
                    'target_type': target_type,
                    'estimated_minutes': drill_min
                }, ensure_ascii=False),
                'estimated_minutes': drill_min
            })

        # 素材学习
        phrase_min = int(daily_minutes * ratio.get('phrase_read', 0))
        if phrase_min > 0:
            tasks_for_day.append({
                'task_type': 'phrase_read',
                'task_detail': json.dumps({
                    'title': '学习/复习素材 10条',
                    'estimated_minutes': phrase_min
                }, ensure_ascii=False),
                'estimated_minutes': phrase_min
            })

        # 模拟考试
        sim_min = int(daily_minutes * ratio.get('simulation', 0))
        if sim_min > 0:
            tasks_for_day.append({
                'task_type': 'simulation',
                'task_detail': json.dumps({
                    'title': '全真模拟考试 1套',
                    'estimated_minutes': sim_min
                }, ensure_ascii=False),
                'estimated_minutes': sim_min
            })

        # 大作文练习
        essay_min = int(daily_minutes * ratio.get('essay_write', 0))
        if essay_min > 0:
            tasks_for_day.append({
                'task_type': 'essay_write',
                'task_detail': json.dumps({
                    'title': '大作文提纲或全文练习 1篇',
                    'estimated_minutes': essay_min
                }, ensure_ascii=False),
                'estimated_minutes': essay_min
            })

        # 复习回顾
        review_min = int(daily_minutes * ratio.get('review', 0))
        if review_min > 0:
            tasks_for_day.append({
                'task_type': 'review',
                'task_detail': json.dumps({
                    'title': '复习错题和薄弱知识点',
                    'estimated_minutes': review_min
                }, ensure_ascii=False),
                'estimated_minutes': review_min
            })

        for task in tasks_for_day:
            db.execute(
                """INSERT INTO daily_tasks (uid, plan_id, task_date, task_type, task_detail, status)
                   VALUES (?, ?, ?, ?, ?, 'pending')""",
                (uid, plan_id, task_date, task['task_type'], task['task_detail'])
            )

        task_date += timedelta(days=1)

    db.commit()


def _get_phase_for_day(phases, day_idx):
    """根据天数索引获取当前阶段"""
    cumulative = 0
    for phase in phases:
        cumulative += phase['days']
        if day_idx < cumulative:
            return phase
    return phases[-1] if phases else None


def _get_user_weaknesses(uid):
    """获取用户薄弱题型"""
    db = get_db()
    rows = db.execute(
        """SELECT question_type, avg_score FROM user_question_type_stats
           WHERE uid = ? ORDER BY avg_score ASC""",
        (uid,)
    ).fetchall()
    return [r['question_type'] for r in rows] if rows else ['guina', 'zonghe']


def get_active_plan(uid):
    """获取用户活跃的备考计划"""
    db = get_db()
    plan = db.execute(
        "SELECT * FROM study_plans WHERE uid = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
        (uid,)
    ).fetchone()
    if not plan:
        return None
    return _format_plan(dict(plan))


def get_plan_detail(uid, plan_id):
    """获取计划详情"""
    db = get_db()
    plan = db.execute(
        "SELECT * FROM study_plans WHERE id = ? AND uid = ?",
        (plan_id, uid)
    ).fetchone()
    if not plan:
        return None
    return _format_plan(dict(plan))


def _format_plan(plan):
    """格式化计划数据"""
    phases = json.loads(plan['phases']) if plan.get('phases') else []
    exam_date = plan.get('exam_date', '')
    days_remaining = 0
    if exam_date:
        try:
            days_remaining = (datetime.strptime(exam_date, '%Y-%m-%d').date() - date.today()).days
        except ValueError:
            pass

    return {
        'plan_id': plan['id'],
        'plan_name': plan['plan_name'],
        'exam_date': exam_date,
        'exam_type': plan['exam_type'],
        'exam_type_name': EXAM_TYPE_NAMES.get(plan['exam_type'], plan['exam_type']),
        'daily_minutes': plan['daily_minutes'],
        'current_level': plan['current_level'],
        'level_name': LEVEL_NAMES.get(plan['current_level'], plan['current_level']),
        'phases': phases,
        'status': plan['status'],
        'progress_pct': plan['progress_pct'],
        'streak_days': plan['streak_days'],
        'longest_streak': plan['longest_streak'],
        'days_remaining': max(0, days_remaining),
        'created_at': plan['created_at']
    }


def get_today_tasks(uid):
    """获取今日任务"""
    db = get_db()
    today = date.today().isoformat()

    # 确保今天有任务，如果没有则补充
    plan = db.execute(
        "SELECT * FROM study_plans WHERE uid = ? AND status = 'active'",
        (uid,)
    ).fetchone()

    if plan:
        existing = db.execute(
            "SELECT COUNT(*) as cnt FROM daily_tasks WHERE uid = ? AND plan_id = ? AND task_date = ?",
            (uid, plan['id'], today)
        ).fetchone()['cnt']

        if existing == 0:
            phases = json.loads(plan['phases'])
            _generate_daily_tasks(db, uid, plan['id'], phases, plan['daily_minutes'], days=1)

    rows = db.execute(
        """SELECT * FROM daily_tasks
           WHERE uid = ? AND task_date = ?
           ORDER BY id ASC""",
        (uid, today)
    ).fetchall()

    tasks = []
    for r in rows:
        detail = json.loads(r['task_detail']) if r['task_detail'] else {}
        tasks.append({
            'task_id': r['id'],
            'task_type': r['task_type'],
            'task_type_name': TASK_TYPE_NAMES.get(r['task_type'], r['task_type']),
            'title': detail.get('title', ''),
            'target_type': detail.get('target_type', ''),
            'estimated_minutes': detail.get('estimated_minutes', 0),
            'status': r['status'],
            'score': r['score'],
            'completed_at': r['completed_at']
        })

    # 统计完成情况
    completed = sum(1 for t in tasks if t['status'] == 'completed')

    return {
        'date': today,
        'tasks': tasks,
        'total': len(tasks),
        'completed': completed
    }


def complete_task(uid, task_id, score=None):
    """完成一个任务"""
    db = get_db()

    task = db.execute(
        "SELECT * FROM daily_tasks WHERE id = ? AND uid = ?",
        (task_id, uid)
    ).fetchone()
    if not task:
        return {'error': '任务不存在'}
    if task['status'] == 'completed':
        return {'error': '任务已完成'}

    now = datetime.now().isoformat()
    db.execute(
        "UPDATE daily_tasks SET status = 'completed', completed_at = ?, score = ? WHERE id = ?",
        (now, score, task_id)
    )
    db.commit()

    # 更新计划进度
    _update_plan_progress(db, uid, task['plan_id'])

    # 更新连续打卡
    _update_streak(db, uid, task['plan_id'])

    return {'task_id': task_id, 'status': 'completed'}


def skip_task(uid, task_id):
    """跳过一个任务"""
    db = get_db()
    task = db.execute(
        "SELECT * FROM daily_tasks WHERE id = ? AND uid = ?",
        (task_id, uid)
    ).fetchone()
    if not task:
        return {'error': '任务不存在'}

    db.execute(
        "UPDATE daily_tasks SET status = 'skipped' WHERE id = ?", (task_id,)
    )
    db.commit()
    return {'task_id': task_id, 'status': 'skipped'}


def _update_plan_progress(db, uid, plan_id):
    """更新计划完成进度"""
    total = db.execute(
        "SELECT COUNT(*) as cnt FROM daily_tasks WHERE plan_id = ?", (plan_id,)
    ).fetchone()['cnt']

    if total == 0:
        return

    completed = db.execute(
        "SELECT COUNT(*) as cnt FROM daily_tasks WHERE plan_id = ? AND status = 'completed'",
        (plan_id,)
    ).fetchone()['cnt']

    pct = round(completed / total * 100, 1)
    db.execute(
        "UPDATE study_plans SET progress_pct = ?, updated_at = datetime('now') WHERE id = ?",
        (pct, plan_id)
    )
    db.commit()


def _update_streak(db, uid, plan_id):
    """更新连续打卡天数"""
    today = date.today()

    # 检查今天是否所有任务都完成了
    today_pending = db.execute(
        """SELECT COUNT(*) as cnt FROM daily_tasks
           WHERE plan_id = ? AND task_date = ? AND status = 'pending'""",
        (plan_id, today.isoformat())
    ).fetchone()['cnt']

    if today_pending > 0:
        return  # 今天还有未完成任务

    # 计算连续天数
    streak = 0
    check_date = today
    while True:
        day_tasks = db.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
               FROM daily_tasks WHERE plan_id = ? AND task_date = ?""",
            (plan_id, check_date.isoformat())
        ).fetchone()

        if not day_tasks or day_tasks['total'] == 0:
            break
        if day_tasks['completed'] == 0:
            break

        streak += 1
        check_date -= timedelta(days=1)

    # 更新最长连续天数
    plan = db.execute(
        "SELECT longest_streak FROM study_plans WHERE id = ?", (plan_id,)
    ).fetchone()
    longest = max(streak, plan['longest_streak'] if plan else 0)

    db.execute(
        "UPDATE study_plans SET streak_days = ?, longest_streak = ?, updated_at = datetime('now') WHERE id = ?",
        (streak, longest, plan_id)
    )
    db.commit()


def get_week_progress(uid):
    """获取本周7天的任务完成状态"""
    db = get_db()
    today = date.today()
    # 计算本周一
    monday = today - timedelta(days=today.weekday())
    days = []
    for i in range(7):
        d = monday + timedelta(days=i)
        d_str = d.isoformat()
        row = db.execute(
            """SELECT COUNT(*) as total,
                      SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
               FROM daily_tasks WHERE uid = ? AND task_date = ?""",
            (uid, d_str)
        ).fetchone()
        if d > today:
            status = 'future'
        elif not row or row['total'] == 0:
            status = 'no_task'
        elif row['completed'] == row['total']:
            status = 'done'
        elif row['completed'] > 0:
            status = 'partial'
        else:
            status = 'missed'
        days.append({
            'date': d_str,
            'weekday': ['一', '二', '三', '四', '五', '六', '日'][i],
            'total': row['total'] if row else 0,
            'completed': row['completed'] if row else 0,
            'status': status,
            'is_today': d == today
        })
    return days


def pause_plan(uid, plan_id):
    """暂停计划"""
    db = get_db()
    db.execute(
        "UPDATE study_plans SET status = 'paused', updated_at = datetime('now') WHERE id = ? AND uid = ?",
        (plan_id, uid)
    )
    db.commit()
    return {'plan_id': plan_id, 'status': 'paused'}


def resume_plan(uid, plan_id):
    """恢复计划"""
    db = get_db()
    db.execute(
        "UPDATE study_plans SET status = 'active', updated_at = datetime('now') WHERE id = ? AND uid = ?",
        (plan_id, uid)
    )
    db.commit()
    return {'plan_id': plan_id, 'status': 'active'}


def get_plan_history(uid, page=1, per_page=20):
    """获取计划历史"""
    db = get_db()
    offset = (page - 1) * per_page

    total = db.execute(
        "SELECT COUNT(*) FROM study_plans WHERE uid = ?", (uid,)
    ).fetchone()[0]

    rows = db.execute(
        """SELECT * FROM study_plans WHERE uid = ?
           ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    items = [_format_plan(dict(r)) for r in rows]
    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }
