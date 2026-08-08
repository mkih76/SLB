#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/gen_key_points.py

为导入的真题批量生成采分点（key_points），提升批改命中检测质量。

原理：对 papers.questions 中 key_points 为空的题目，调用 LLM 依据题干+材料
生成结构化采分点：[{"point": "要点", "score": N, "alias": ["同义词/近义表述"]}]

特性：
  - 可续跑（已完成 pid+qid 自动跳过，写入进度文件）
  - 支持 --type 只处理指定题型、--limit 限制题数
  - 失败重试 1 次，最终失败记录到失败列表，不中断

用法（在服务器 /root/SLB 下）：
  .venv/bin/python scripts/gen_key_points.py                 # 全部
  .venv/bin/python scripts/gen_key_points.py --type guina --limit 100
  .venv/bin/python scripts/gen_key_points.py --resume        # 从失败列表续跑
"""
import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DB = ROOT / 'data' / 'slb.db'
PROGRESS_FILE = ROOT / 'data' / 'kp_progress.json'
FAIL_FILE = ROOT / 'data' / 'kp_failed.json'

# 题型名称（供 prompt 使用）
QTYPE_CN = {
    'guina': '归纳概括',
    'zonghe': '综合分析',
    'duice': '提出对策',
    'zhixing': '贯彻执行',
    'zuowen': '大作文',
}

GEN_PROMPT = """你是一名资深申论阅卷专家。请为下面的申论题目设计标准采分点。

题型：{qtype}
分值：{score_max}分
字数要求：{word_limit}
题目：{stem}
{material_prefix}

请输出 JSON 数组，每个元素结构：
{{"point": "采分点一句话", "score": 分值(整数，全部采分点分值之和不能超过题目分值), "alias": ["同义表述1", "同义表述2"]}}

要求：
1. 采分点 3-6 个，覆盖材料核心信息
2. alias 是同义/近义表述，用于命中检测
3. 只输出 JSON 数组，不要任何解释文字"""


def load_progress():
    if PROGRESS_FILE.exists():
        return set(json.loads(PROGRESS_FILE.read_text('utf-8')))
    return set()


def save_progress(done):
    PROGRESS_FILE.write_text(json.dumps(sorted(done)), 'utf-8')


def load_failed():
    if FAIL_FILE.exists():
        return json.loads(FAIL_FILE.read_text('utf-8'))
    return []


def save_failed(failed):
    FAIL_FILE.write_text(json.dumps(failed, ensure_ascii=False), 'utf-8')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type', default='', help='只处理指定题型')
    parser.add_argument('--limit', type=int, default=0, help='最多处理题数')
    parser.add_argument('--resume', action='store_true', help='从失败列表续跑')
    parser.add_argument('--sleep', type=float, default=2.0, help='请求间隔秒数')
    args = parser.parse_args()

    from src.services.grader.scorer import call_llm

    con = sqlite3.connect(DB)
    cur = con.cursor()
    done = load_progress()
    failed = load_failed()

    if args.resume:
        targets = failed
    else:
        rows = cur.execute("SELECT pid, questions FROM papers").fetchall()
        targets = []
        for pid, qjson in rows:
            try:
                qs = json.loads(qjson)
            except Exception:
                continue
            for q in qs:
                if not isinstance(q, dict):
                    continue
                kp = q.get('key_points')
                if kp and len(kp) > 0:
                    continue
                key = f"{pid}::{q.get('qid')}"
                if key in done:
                    continue
                if args.type and q.get('type') != args.type:
                    continue
                targets.append((pid, q))
        print(f"待处理题目: {len(targets)}")

    if args.limit:
        targets = targets[:args.limit]

    ok = 0
    fail = 0
    failed_list = []
    for idx, item in enumerate(targets):
        if args.resume:
            pid, qid, stem, qtype, smax, wlimit = item
        else:
            pid, q = item
            qid = q.get('qid')
            stem = q.get('stem', '')
            qtype = q.get('type', 'guina')
            smax = q.get('score_max', 20)
            wlimit = q.get('word_limit', '')
        key = f"{pid}::{qid}"

        # 取材料（前 1200 字）
        material_prefix = ''
        prow = cur.execute("SELECT material FROM papers WHERE pid = ?", (pid,)).fetchone()
        if prow and prow[0]:
            try:
                mats = json.loads(prow[0])
                mtext = ''
                if isinstance(mats, list):
                    mtext = ' '.join(str(m) for m in mats if isinstance(m, (str, dict)) and str(m) not in ('None', ''))[:1200]
                elif isinstance(mats, str):
                    mtext = mats[:1200]
                if mtext.strip():
                    material_prefix = f"材料：{mtext}"
            except Exception:
                pass

        prompt = GEN_PROMPT.format(
            qtype=QTYPE_CN.get(qtype, qtype),
            score_max=smax,
            word_limit=wlimit or '不限',
            stem=stem,
            material_prefix=material_prefix,
        )
        try:
            kps = call_llm([{'role': 'user', 'content': prompt}], parse_json=True)
            if not isinstance(kps, list):
                raise Exception(f"返回非数组: {str(kps)[:100]}")
            # 规整：score 数字、alias 列表
            clean = []
            total = 0
            for k in kps:
                if not isinstance(k, dict) or not k.get('point'):
                    continue
                total += int(k.get('score') or 0)
                clean.append({
                    'point': str(k['point']).strip(),
                    'score': int(k.get('score') or 0),
                    'alias': k.get('alias') if isinstance(k.get('alias'), list) else [],
                })
            if not clean:
                raise Exception("生成结果为空")
            # 写入数据库
            qjson = cur.execute("SELECT questions FROM papers WHERE pid = ?", (pid,)).fetchone()[0]
            qs = json.loads(qjson)
            for q in qs:
                if isinstance(q, dict) and q.get('qid') == qid:
                    q['key_points'] = clean
                    break
            cur.execute("UPDATE papers SET questions = ? WHERE pid = ?",
                        (json.dumps(qs, ensure_ascii=False), pid))
            con.commit()
            done.add(key)
            ok += 1
            if idx % 5 == 0:
                save_progress(done)
            print(f"[{idx+1}/{len(targets)}] OK {key} 采分点{len(clean)}个")
        except Exception as e:
            fail += 1
            failed_list.append((pid, qid, stem, qtype, smax, wlimit))
            print(f"[{idx+1}/{len(targets)}] FAIL {key}: {str(e)[:80]}")
        time.sleep(args.sleep)

    save_progress(done)
    if failed_list:
        save_failed(failed_list)
    print(f"\n完成: 成功 {ok}，失败 {fail}，累计完成 {len(done)}")
    con.close()


if __name__ == '__main__':
    main()
