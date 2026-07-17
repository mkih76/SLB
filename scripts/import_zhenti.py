#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/import_zhenti.py

把 data/shenlun_zhenti/*.md (393 套真题) 导入 papers 表。

数据约束（按实测文件发现的三种格式）：
  格式 A（联考多见）：每题独立，标"题目一："、"题目二：" ...
  格式 B（上海/北京多见）：开头"作答要求"块，中文数字"一、" "二、" 分题
  格式 C：阿拉伯数字"1. xxx" "2. xxx"（混合）

所有格式共有的特征：
  - 头部 YAML frontmatter
  - "材料1" / "材料2" 段落（可能带冒号）
  - 题目末尾常含"要求：...字..." 元数据
  - 大作文段

本脚本把所有题目 key_points 留空（占位），后续用 LLM 补 answer_keys。

用法：
  python scripts/import_zhenti.py                # 导入全部到 data/slb.db
  python scripts/import_zhenti.py --dry-run      # 只解析不入库
  python scripts/import_zhenti.py --limit 5      # 只跑前 5 份
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SRC = ROOT / 'data' / 'shenlun_zhenti'
DEFAULT_DB = ROOT / 'data' / 'slb.db'

# ============================================================
# 题型关键词（按出现顺序判定优先级）
# ============================================================
QUESTION_TYPE_KEYWORDS = [
    ('归纳概括', ['归纳概括', '概括', '总结', '简述', '简要说']),
    ('综合分析', ['综合分析', '分析', '谈谈理解', '谈谈看法', '阐释', '评析', '论述']),
    ('提出对策', ['提出对策', '对策', '建议', '措施', '怎么办']),
    ('贯彻执行', ['贯彻', '执行', '写一份', '拟写', '撰写', '讲话稿', '倡议书', '发言提纲',
                  '汇报材料', '工作总结', '公开信', '调查报告', '建议书', '倡议']),
    ('大作文', ['自选角度', '自拟题目', '写一篇文章', '写一篇议论文', '文章', '作文']),
]

CHINESE_NUM = '一二三四五六七八九十'

# ============================================================
# 模式匹配
# ============================================================
# 格式 A：题目一：xxx / 题目 1：xxx / 第一题：xxx / 问题一：
RE_Q_A = re.compile(
    rf'^\s*(?:题目|问题|第)\s*[{CHINESE_NUM}\d]+\s*题?\s*[:：.、]?\s*(.*?)$',
    re.MULTILINE
)
# 格式 B：作答要求 / 题目及要求（可能是单独一行，也可能内联到下一段）
RE_ZUOYAO_LINE = re.compile(r'^\s*(?:作答要求|题目及要求)\s*$', re.MULTILINE)
# 内联形式：作答要求一、  /  作答要求第一题：  /  作答要求（一）  /  题目及要求一、
RE_ZUOYAO_INLINE = re.compile(
    rf'(?:作答要求|题目及要求)\s*(?=一、|二、|三、|第一题|第二题|第三题|第四题|第五题|[（(]一[）)])',
    re.MULTILINE
)

def _find_zuoyao(body: str):
    """找到作答要求块的起点（用作答要求开始位置），返回字符 offset"""
    m = RE_ZUOYAO_LINE.search(body)
    if m:
        return m.start()
    m = RE_ZUOYAO_INLINE.search(body)
    if m:
        return m.start()
    return -1
RE_Q_B_CN = re.compile(
    rf'^\s*[(（]?([{CHINESE_NUM}]+)[)）、.]\s*(.*?)(?=\s*(?:要求\s*[：:]|第\s*[一二三四五六七八九十]\s*题|第\s*\d+\s*题|$))',
    re.DOTALL | re.MULTILINE
)
# 格式 C：作答要求块里的"第一题：xxx" / "第1题：xxx"
# 关键：边界可以是 "\n\s*要求" 也可以是下一题前 (无换行紧贴)
RE_Q_B_DI = re.compile(
    rf'第\s*([{CHINESE_NUM}\d]+)\s*题\s*[:：]?\s*(.*?)(?=\s*(?:要求\s*[：:]|第\s*[二三四五六七八九十]\s*题|第\s*\d+\s*题|$))',
    re.DOTALL | re.MULTILINE
)
# 阿拉伯数字：1. xxx  2. xxx
RE_Q_B_NUM = re.compile(
    r'^\s*(\d+)\s*[.、]\s+([^\n]+?)(?=\n\s*(?:要求|\d+[.、]|$))',
    re.MULTILINE
)
# 材料段
RE_MATERIAL = re.compile(
    rf'^\s*材料\s*[{CHINESE_NUM}\d]+\s*[:：]?\s*$',
    re.MULTILINE
)
# 大作文段
RE_DZW = re.compile(r'^\s*大作文\s*$', re.MULTILINE)

# 字数/分值提取
RE_WORDLIMIT = re.compile(
    r'字数[（(]?不?(?:少于|超过|多于|低于|高于)?[）)]?\s*(\d+)\s*[-—~至]?\s*(\d+)?\s*字'
)
RE_WORDLIMIT2 = re.compile(r'字数\s*(\d+)\s*[-—~至]\s*(\d+)\s*字')
RE_SCORE = re.compile(r'[（(](\d+)\s*分[）)]')

CN_NUM_MAP = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
              '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析开头 YAML frontmatter"""
    text = text.lstrip('\ufeff')
    if not (text.startswith('---\n') or text.startswith('---\r\n')):
        return {}, text
    end = text.find('\n---', 4)
    if end < 0:
        return {}, text
    fm_block = text[4:end]
    body = text[end + 4:].lstrip('\r\n')
    meta = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or ':' not in line:
            continue
        k, _, v = line.partition(':')
        meta[k.strip()] = v.strip()
    return meta, body


def split_materials(body: str) -> list[str]:
    """按"材料N"切分"""
    matches = list(RE_MATERIAL.finditer(body))
    if not matches:
        return [body.strip()]
    parts = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end].strip()
        if chunk:
            parts.append(chunk)
    return parts


def _extract_score_and_wordlimit(text: str) -> tuple[int, str]:
    """从 text 中提取分值和字数限制。返回 (score, word_limit_str)"""
    score = 0
    word_limit = ''
    m = RE_SCORE.search(text)
    if m:
        score = int(m.group(1))
    m = RE_WORDLIMIT2.search(text)
    if m:
        word_limit = f"{m.group(1)}-{m.group(2)}字"
    else:
        m = RE_WORDLIMIT.search(text)
        if m:
            if m.group(2):
                word_limit = f"{m.group(1)}-{m.group(2)}字"
            else:
                word_limit = f"{m.group(1)}字"
    return score, word_limit


def guess_type(stem: str) -> str:
    """根据提干关键词猜测题型"""
    text = stem[:200]
    for type_name, kws in QUESTION_TYPE_KEYWORDS:
        for kw in kws:
            if kw in text:
                return type_name
    return '综合分析'


def extract_questions_format_a(body: str) -> list[dict]:
    """格式 A：每题独立"题目N：xxx"（"要求："单独一行跟随）"""
    questions = []
    matches = list(RE_Q_A.finditer(body))
    for i, m in enumerate(matches):
        qid_text = m.group(0).strip()
        # 解析 qid 编号
        qn_match = re.search(r'([一二三四五六七八九十]|\d+)', qid_text)
        if not qn_match:
            continue
        qn_raw = qn_match.group(1)
        if qn_raw.isdigit():
            qid = f"q{qn_raw}"
        else:
            qid = f"q{CN_NUM_MAP.get(qn_raw, i + 1)}"
        # 提干：group(1) 已包含到行尾的全部内容（含"要求：..."）
        # 用 group(1) 截到"要求"前作为 stem
        full_stem = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else ''
        # 大作文特殊处理
        if '大作文' in qid_text or '大作文' in full_stem[:10]:
            type_guess = '大作文'
        else:
            type_guess = guess_type(full_stem)
        score, word_limit = _extract_score_and_wordlimit(full_stem + ' ' + qid_text)
        if '大作文' in type_guess:
            score = score or 40
        # 截 stem 到"要求："前
        req_split = re.search(r'要求\s*[：:]', full_stem)
        if req_split:
            stem = full_stem[:req_split.start()].strip()
            req_text = full_stem[req_split.start():]
        else:
            stem = full_stem
            req_text = ''
        questions.append({
            'qid': qid,
            'type': type_guess,
            'stem': stem[:500],
            'score_max': score or 25,
            'word_limit': word_limit,
            'key_points': [],
        })
    return questions


def extract_questions_format_b(body: str) -> list[dict]:
    """格式 B/C：作答要求块用中文数字 / 阿拉伯数字 / 第N题分题"""
    start = _find_zuoyao(body)
    if start < 0:
        return []
    block = body[start:]
    questions = []

    # 先尝试 CN（一、xxx）
    cn_matches = list(RE_Q_B_CN.finditer(block))
    if len(cn_matches) >= 2:
        for i, cm in enumerate(cn_matches):
            cn = cm.group(1)
            qid = f"q{CN_NUM_MAP.get(cn, i + 1)}"
            section = cm.group(2).strip()
            stem = section
            req_split = re.search(r'要求\s*[：:]', section)
            if req_split:
                stem = section[:req_split.start()].strip()
                req_text = section[req_split.start():]
            else:
                next_start = cn_matches[i + 1].start() if i + 1 < len(cn_matches) else len(block)
                full = block[cm.end():next_start]
                req_split = re.search(r'要求\s*[：:]', full)
                if req_split:
                    req_text = full[req_split.start():]
                else:
                    req_text = ''
            type_guess = '大作文' if '大作文' in stem[:10] or '自拟题目' in stem else guess_type(stem)
            score, word_limit = _extract_score_and_wordlimit(req_text)
            if type_guess == '大作文':
                score = score or 40
            questions.append({
                'qid': qid,
                'type': type_guess,
                'stem': stem[:500],
                'score_max': score or 25,
                'word_limit': word_limit,
                'key_points': [],
            })
        if questions:
            return questions

    # 再尝试 DI（第一题：xxx）
    di_matches = list(RE_Q_B_DI.finditer(block))
    if len(di_matches) >= 2:
        for i, dm in enumerate(di_matches):
            qn = dm.group(1)
            if qn.isdigit():
                qid = f"q{qn}"
            else:
                qid = f"q{CN_NUM_MAP.get(qn, i + 1)}"
            section = dm.group(2).strip()
            stem = section  # 默认值：全部 section（即使无"要求"边界也保留）
            req_split = re.search(r'要求\s*[：:]', section)
            if req_split:
                stem = section[:req_split.start()].strip()
                req_text = section[req_split.start():]
            else:
                next_start = di_matches[i + 1].start() if i + 1 < len(di_matches) else len(block)
                full = block[dm.end():next_start]
                req_split = re.search(r'要求\s*[：:]', full)
                if req_split:
                    req_text = full[req_split.start():]
                else:
                    req_text = ''
            # 加分值（在题号后括号里，如"(20分)"）
            head_text = block[dm.start():dm.end()]
            score_head, _ = _extract_score_and_wordlimit(head_text)
            score_body, word_limit = _extract_score_and_wordlimit(req_text)
            score = score_head or score_body
            type_guess = '大作文' if '大作文' in stem[:10] or '自拟题目' in stem else guess_type(stem)
            if type_guess == '大作文':
                score = score or 40
            questions.append({
                'qid': qid,
                'type': type_guess,
                'stem': stem[:500],
                'score_max': score or 25,
                'word_limit': word_limit,
                'key_points': [],
            })
        return questions

    return questions


def extract_questions(body: str) -> list[dict]:
    """主入口：按格式 A→B 顺序尝试，取最多的"""
    a_qs = extract_questions_format_a(body)
    b_qs = extract_questions_format_b(body)
    # 选多的；都不足时回退到"作答要求"块整体作为单题
    if len(a_qs) >= len(b_qs) and a_qs:
        return a_qs
    if b_qs:
        return b_qs
    # 兜底：找"作答要求"段作为一题
    start = _find_zuoyao(body)
    if start >= 0:
        return [{
            'qid': 'q1',
            'type': '综合分析',
            'stem': body[start:start + 500].strip(),
            'score_max': 30,
            'word_limit': '',
            'key_points': [],
        }]
    return []


def safe_pid(meta: dict, filename: str) -> str:
    """稳定 pid：优先 manifest 的 tid"""
    tid = meta.get('tid')
    if tid:
        return f"zh_{str(tid).zfill(4)}"
    base = Path(filename).stem
    base = re.sub(r'[^\w\u4e00-\u9fff]+', '_', base)[:60]
    return f"zh_{base}"


def parse_one(filepath: Path) -> Optional[dict]:
    try:
        text = filepath.read_text(encoding='utf-8')
    except Exception as e:
        print(f'[FAIL] read {filepath.name}: {e}', file=sys.stderr)
        return None

    meta, body = parse_frontmatter(text)
    if not meta:
        fn = filepath.stem
        m = re.match(r'(.+?)_(\d{4})', fn)
        if m:
            meta = {
                'province': m.group(1),
                'year': m.group(2),
                'exam_type': '国考' if m.group(1) == '国考' else '省考',
                'title': fn,
            }

    materials = split_materials(body)
    questions = extract_questions(body)
    if not materials or not questions:
        return None

    return {
        'pid': safe_pid(meta, filepath.name),
        'source': 'shenlunhome',
        'exam_type': meta.get('exam_type') or '省考',
        'year': int(meta.get('year', 0) or 0) or 2020,
        'season': None,
        'province': meta.get('province') or None,
        'title': meta.get('title') or filepath.stem,
        'material': json.dumps(materials, ensure_ascii=False),
        'questions': json.dumps(questions, ensure_ascii=False),
        'answer_keys': '{}',
        'difficulty': 3,
        'heat': 0,
        'tag': '[]',
        'source_url': f"https://www.shenlunhome.com/tid/{meta.get('tid','')}.html" if meta.get('tid') else None,
        'status': 'published',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=str(DEFAULT_SRC))
    ap.add_argument('--db', default=str(DEFAULT_DB))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f'[FAIL] source dir not found: {src}', file=sys.stderr)
        sys.exit(1)

    md_files = sorted(src.glob('*.md'))
    # 跳过 < 1500 字节的残缺文件或参考文章
    md_files = [f for f in md_files if f.stat().st_size >= 1500]
    if args.limit:
        md_files = md_files[:args.limit]
    print(f'[*] Found {len(md_files)} .md files (>=1500 bytes) in {src}')

    parsed, skipped = [], 0
    for f in md_files:
        rec = parse_one(f)
        if rec:
            parsed.append(rec)
        else:
            skipped += 1

    print(f'[*] Parsed {len(parsed)} papers, skipped {skipped}')

    if args.dry_run:
        if parsed:
            print('\n--- 3 samples ---')
            for s in parsed[:3]:
                qs = json.loads(s['questions'])
                ms = json.loads(s['material'])
                print(f"\n  pid={s['pid']}")
                print(f"  title={s['title'][:60]}")
                print(f"  year={s['year']} province={s['province']} exam_type={s['exam_type']}")
                print(f"  materials: {len(ms)} sections")
                print(f"  questions: {len(qs)}")
                for q in qs[:3]:
                    print(f"    [{q['qid']}] {q['type']} ({q['score_max']}分, {q['word_limit']}): {q['stem'][:60]}")
        return

    db = sqlite3.connect(args.db)
    db.execute('PRAGMA foreign_keys = ON')
    inserted = 0
    for rec in parsed:
        try:
            cur = db.execute(
                """INSERT INTO papers (pid, source, exam_type, year, season, province, title,
                    material, questions, answer_keys, difficulty, heat, tag, source_url, status)
                   VALUES (:pid,:source,:exam_type,:year,:season,:province,:title,
                    :material,:questions,:answer_keys,:difficulty,:heat,:tag,:source_url,:status)
                   ON CONFLICT(pid) DO UPDATE SET
                    title=excluded.title, material=excluded.material, questions=excluded.questions,
                    answer_keys=excluded.answer_keys""",
                rec
            )
            inserted += 1
        except sqlite3.Error as e:
            print(f'[FAIL] insert {rec["pid"]}: {e}', file=sys.stderr)
    db.commit()
    total = db.execute('SELECT COUNT(*) FROM papers').fetchone()[0]
    db.close()
    print(f'[+] Inserted/updated {inserted} papers. Total in DB: {total}')


if __name__ == '__main__':
    main()