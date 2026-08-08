#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migrate_qtypes.py

统一题型代码体系：中文题型名 → 英文代码（guina/zonghe/duice/zhixing/zuowen）。

背景：服务层（drill/diagnosis/scorer/prompts）全部使用英文代码，但数据库里
题目的 type 是中文（导入真题/seed 数据），导致按题型聚合的推荐/统计/历史/进度
全部静默失效。本脚本把所有存量中文 type 迁移为英文代码。

覆盖范围：
  1. papers.questions JSON 中的每个题目 type
  2. user_question_type_stats.question_type（提交时写入的中文）
  3. question_type_drills.question_type（训练记录）
  4. diagnostic_reports 表（score_guina 等列不受影响，但 report 里存的 type_scores key 若为中文一并转换）

用法：
  python scripts/migrate_qtypes.py          # 执行迁移（打印变更统计）
  python scripts/migrate_qtypes.py --dry-run  # 只统计不写入
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'slb.db'

# 中文 → 英文题型映射（覆盖数据库实测的全部取值）
QTYPE_MAP = {
    '归纳概括': 'guina',
    '综合分析': 'zonghe',
    '提出对策': 'duice',
    '对策建议': 'duice',
    '贯彻执行': 'zhixing',
    '大作文': 'zuowen',
    '文章写作': 'zuowen',
}
DEFAULT_QTYPE = 'guina'


def normalize_type(t):
    """任意题型值 → 英文代码；未知值返回 None"""
    if not t:
        return None
    t = str(t).strip()
    if t in QTYPE_MAP:
        return QTYPE_MAP[t]
    # 已是英文代码
    if t in ('guina', 'zonghe', 'duice', 'zhixing', 'zuowen'):
        return t
    return None


def migrate_papers(cur, dry_run=False):
    """迁移 papers.questions 中的题目 type"""
    rows = cur.execute("SELECT pid, questions FROM papers").fetchall()
    changed_papers = 0
    changed_questions = 0
    unknown = {}
    for pid, qjson in rows:
        if not qjson:
            continue
        try:
            qs = json.loads(qjson)
        except Exception:
            continue
        new_qs = []
        is_changed = False
        for q in qs:
            if not isinstance(q, dict):
                new_qs.append(q)
                continue
            nt = normalize_type(q.get('type'))
            if nt and q.get('type') != nt:
                q['type'] = nt
                is_changed = True
                changed_questions += 1
            elif q.get('type') and not nt:
                unknown[str(q.get('type'))] = unknown.get(str(q.get('type')), 0) + 1
            new_qs.append(q)
        if is_changed:
            changed_papers += 1
            if not dry_run:
                cur.execute("UPDATE papers SET questions = ? WHERE pid = ?",
                            (json.dumps(new_qs, ensure_ascii=False), pid))
    return changed_papers, changed_questions, unknown


def migrate_column(cur, table, col, dry_run=False):
    """迁移某表某列的 question_type 值（若列为空/不存在则跳过）"""
    cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        return 0
    rows = cur.execute(f"SELECT rowid, {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''").fetchall()
    changed = 0
    for rowid, val in rows:
        nt = normalize_type(val)
        if nt and str(val).strip() != nt:
            changed += 1
            if not dry_run:
                cur.execute(f"UPDATE {table} SET {col} = ? WHERE rowid = ?", (nt, rowid))
    return changed


def migrate_diag_reports(cur, dry_run=False):
    """迁移 diagnostic_reports.report 中 type_scores 的中文 key"""
    cols = [r[1] for r in cur.execute("PRAGMA table_info(diagnostic_reports)").fetchall()]
    if 'report' not in cols:
        return 0
    rows = cur.execute("SELECT id, report FROM diagnostic_reports WHERE report IS NOT NULL").fetchall()
    changed = 0
    for rid, report in rows:
        try:
            data = json.loads(report)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        moved = False
        ts = data.get('type_scores')
        if isinstance(ts, dict):
            new_ts = {}
            for k, v in ts.items():
                nt = normalize_type(k)
                new_ts[nt if nt else k] = v
                if nt and k != nt:
                    moved = True
            if moved:
                data['type_scores'] = new_ts
        if moved:
            changed += 1
            if not dry_run:
                cur.execute("UPDATE diagnostic_reports SET report = ? WHERE id = ?",
                            (json.dumps(data, ensure_ascii=False), rid))
    return changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    con = sqlite3.connect(DB)
    cur = con.cursor()

    p_changed, q_changed, unknown = migrate_papers(cur, args.dry_run)
    s_changed = migrate_column(cur, 'user_question_type_stats', 'question_type', args.dry_run)
    d_changed = migrate_column(cur, 'question_type_drills', 'question_type', args.dry_run)
    r_changed = migrate_diag_reports(cur, args.dry_run)

    if not args.dry_run:
        con.commit()

    print(f"[{'DRY-RUN' if args.dry_run else 'MIGRATED'}] papers 变更: {p_changed} 套 / {q_changed} 题")
    print(f"[{'DRY-RUN' if args.dry_run else 'MIGRATED'}] user_question_type_stats 变更: {s_changed} 行")
    print(f"[{'DRY-RUN' if args.dry_run else 'MIGRATED'}] question_type_drills 变更: {d_changed} 行")
    print(f"[{'DRY-RUN' if args.dry_run else 'MIGRATED'}] diagnostic_reports 变更: {r_changed} 行")
    if unknown:
        print("无法识别的题型（保持原样）:", unknown)
    con.close()


if __name__ == '__main__':
    main()
