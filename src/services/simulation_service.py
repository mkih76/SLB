# 模拟考试服务
#
# 全真模拟考场：限时答题、自动提交、排名计算

import json
from datetime import datetime
from src.api.utils import get_db, generate_uuid


def start_simulation(uid, pid):
    """开始一次模拟考试

    Returns:
        dict: {sim_id, pid, started_at, time_limit, questions}
    """
    db = get_db()

    # 检查是否有未完成的模拟
    existing = db.execute(
        "SELECT id FROM simulation_records WHERE uid = ? AND pid = ? AND status = 'in_progress'",
        (uid, pid)
    ).fetchone()
    if existing:
        return {'error': '你有一次未完成的模拟考试，请先提交或等待超时', 'sim_id': existing['id']}

    # 获取试卷信息
    paper = db.execute("SELECT * FROM papers WHERE pid = ?", (pid,)).fetchone()
    if not paper:
        return {'error': '试卷不存在'}

    questions = json.loads(paper['questions']) if paper['questions'] else []
    time_limit = 150  # 默认150分钟

    now = datetime.now().isoformat()
    sim_id = generate_uuid()

    db.execute(
        """INSERT INTO simulation_records (id, uid, pid, started_at, time_spent, status)
           VALUES (?, ?, ?, ?, 0, 'in_progress')""",
        (sim_id, uid, pid, now)
    )
    db.commit()

    # 去掉答案信息，防止作弊
    safe_questions = []
    for q in questions:
        safe_questions.append({
            'qid': q.get('qid', ''),
            'type': q.get('type', ''),
            'type_name': _type_name(q.get('type', '')),
            'stem': q.get('stem', q.get('question_text', '')),
            'word_limit': q.get('word_limit', ''),
            'score': q.get('score', q.get('score_max', 0)),
            'requirement': q.get('requirement', '')
        })

    return {
        'sim_id': sim_id,
        'pid': pid,
        'paper_title': paper['title'],
        'started_at': now,
        'time_limit': time_limit,
        'questions': safe_questions,
        'material': json.loads(paper['material']) if paper['material'] else []
    }


def submit_simulation(sim_id, uid, answers):
    """提交模拟考试答案

    Args:
        sim_id: 模拟考试 ID
        uid: 用户 ID
        answers: {qid: user_answer, ...}

    Returns:
        dict: 批改结果
    """
    db = get_db()

    sim = db.execute(
        "SELECT * FROM simulation_records WHERE id = ? AND uid = ?",
        (sim_id, uid)
    ).fetchone()
    if not sim:
        return {'error': '模拟记录不存在'}
    if sim['status'] != 'in_progress':
        return {'error': '该模拟已提交'}

    # 计算用时
    started = datetime.fromisoformat(sim['started_at'])
    now = datetime.now()
    time_spent = int((now - started).total_seconds())

    # 获取试卷信息
    paper = db.execute("SELECT * FROM papers WHERE pid = ?", (sim['pid'],)).fetchone()
    if not paper:
        return {'error': '试卷不存在'}

    questions = json.loads(paper['questions']) if paper['questions'] else []
    material = json.loads(paper['material']) if paper['material'] else None

    # 逐题批改
    from src.services.grader.scorer import grade_answer
    question_scores = {}
    total_score = 0
    total_max = 0
    results = []

    for q in questions:
        qid = q.get('qid', '')
        q_max = q.get('score', q.get('score_max', 0))
        total_max += q_max

        user_ans = answers.get(qid, '').strip()
        if not user_ans:
            question_scores[qid] = 0
            results.append({'qid': qid, 'score': 0, 'max_score': q_max, 'status': 'not_answered'})
            continue

        try:
            # 构造完整的 question 字典供 grader 使用
            q_full = dict(q)
            q_full['key_points'] = q.get('key_points', [])

            grading = grade_answer(sim['pid'], qid, q_full, user_ans, material)
            raw_score = grading.get('score', 0)

            # 将 0-100 的分数换算为该题满分
            actual_score = round(raw_score * q_max / 100, 1)
            question_scores[qid] = actual_score
            total_score += actual_score

            # 同时记录到 submissions 表
            from src.services import submission_service
            sid = submission_service.create_submission(uid, sim['pid'], qid, user_ans)
            submission_service.update_submission_grading(
                sid=sid,
                score=raw_score,
                dimension_scores=grading.get('dimension_scores'),
                ai_feedback=grading.get('ai_feedback'),
                hit_points=grading.get('hit_points', []),
                missing_points=grading.get('missing_points', []),
                improving_suggestions=grading.get('improving_suggestions')
            )

            # 更新题型训练统计
            from src.services import drill_service
            drill_service.record_drill(
                uid=uid,
                question_type=q.get('type', 'guina'),
                pid=sim['pid'],
                qid=qid,
                sid=sid,
                score=raw_score,
                dimension_scores=grading.get('dimension_scores')
            )

            results.append({
                'qid': qid,
                'score': actual_score,
                'max_score': q_max,
                'raw_score': raw_score,
                'sid': sid,
                'status': 'graded'
            })

        except Exception as e:
            question_scores[qid] = 0
            results.append({'qid': qid, 'score': 0, 'max_score': q_max, 'status': 'error'})

    # 更新模拟记录
    now_str = now.isoformat()
    db.execute(
        """UPDATE simulation_records
           SET submitted_at = ?, time_spent = ?, total_score = ?,
               question_scores = ?, status = 'submitted'
           WHERE id = ?""",
        (now_str, time_spent, total_score, json.dumps(question_scores), sim_id)
    )
    db.commit()

    # 计算排名
    rank = calculate_rank(sim['pid'], total_score)

    return {
        'sim_id': sim_id,
        'total_score': round(total_score, 1),
        'total_max': total_max,
        'time_spent': time_spent,
        'question_scores': question_scores,
        'results': results,
        'rank_percentile': rank
    }


def calculate_rank(pid, user_score):
    """计算用户在同卷考生中的排名百分位"""
    db = get_db()
    scores = db.execute(
        """SELECT total_score FROM simulation_records
           WHERE pid = ? AND status = 'submitted'
           ORDER BY total_score""",
        (pid,)
    ).fetchall()

    if not scores:
        return None

    all_scores = [s['total_score'] for s in scores]
    below = sum(1 for s in all_scores if s < user_score)
    return round(below / len(all_scores) * 100, 1)


def get_simulation_history(uid, page=1, per_page=20):
    """获取模拟考试历史"""
    db = get_db()
    offset = (page - 1) * per_page

    rows = db.execute(
        """SELECT s.*, p.title as paper_title
           FROM simulation_records s
           LEFT JOIN papers p ON s.pid = p.pid
           WHERE s.uid = ?
           ORDER BY s.started_at DESC LIMIT ? OFFSET ?""",
        (uid, per_page, offset)
    ).fetchall()

    total = db.execute(
        "SELECT COUNT(*) as cnt FROM simulation_records WHERE uid = ?",
        (uid,)
    ).fetchone()['cnt']

    items = []
    for row in rows:
        items.append({
            'sim_id': row['id'],
            'pid': row['pid'],
            'paper_title': row['paper_title'],
            'total_score': row['total_score'],
            'time_spent': row['time_spent'],
            'rank_percentile': row['rank_percentile'],
            'status': row['status'],
            'started_at': row['started_at'],
            'submitted_at': row['submitted_at']
        })

    return {
        'items': items,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }


def get_simulation_detail(sim_id, uid):
    """获取单次模拟详情"""
    db = get_db()
    row = db.execute(
        """SELECT s.*, p.title as paper_title, p.questions
           FROM simulation_records s
           LEFT JOIN papers p ON s.pid = p.pid
           WHERE s.id = ? AND s.uid = ?""",
        (sim_id, uid)
    ).fetchone()

    if not row:
        return None

    question_scores = json.loads(row['question_scores']) if row['question_scores'] else {}
    questions = json.loads(row['questions']) if row['questions'] else []

    return {
        'sim_id': row['id'],
        'pid': row['pid'],
        'paper_title': row['paper_title'],
        'total_score': row['total_score'],
        'time_spent': row['time_spent'],
        'rank_percentile': row['rank_percentile'],
        'status': row['status'],
        'started_at': row['started_at'],
        'submitted_at': row['submitted_at'],
        'question_scores': question_scores,
        'questions': [{'qid': q.get('qid'), 'type': q.get('type'),
                        'stem': q.get('stem', '')[:50], 'max_score': q.get('score', 0)}
                       for q in questions]
    }


def _type_name(t):
    return {'guina': '归纳概括', 'zonghe': '综合分析', 'duice': '提出对策',
            'zhixing': '贯彻执行', 'zuowen': '大作文'}.get(t, t)
