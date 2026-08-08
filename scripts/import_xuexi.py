#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/import_xuexi.py

把 data/xuexi_articles/*.md（302 篇学习强国文章）导入 hot_topics 表，
并提炼金句写入 good_phrases 表。

文件格式：
  文件名: YYYY-MM-DD-标题.md
  内容:   # 标题
          > 来源：学习强国　|　日期：YYYY-MM-DD　|　[原文链接](https://...)
          ---
          正文...

分类规则（关键词 → category）：
  jingji  经济/发展/高质量/改革/开放/市场/产业/企业
  keji    科技/创新/数字/人工智能/技术/网络/信息
  shengtai 生态/环境/绿色/碳/污染/自然
  minsheng 民生/就业/教育/医疗/养老/住房/社保/扶贫/乡村振兴
  zhili   治理/法治/基层/制度/治理体系/监督
  wenhua  文化/文明/精神/传统/历史/文艺
  shehui  社会/社区/公共/安全
  默认 xuexi（学习强国）

用法：
  python scripts/import_xuexi.py            # 导入全部
  python scripts/import_xuexi.py --dry-run  # 只解析不写入
"""
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'data' / 'xuexi_articles'
DB = ROOT / 'data' / 'slb.db'

CATEGORY_RULES = [
    ('jingji', ['经济', '高质量', '改革', '开放', '市场', '产业', '企业', '金融', '贸易', '就业']),
    ('keji', ['科技', '创新', '数字', '人工智能', '技术', '网络', '信息', '数据', '机器人', '智能']),
    ('shengtai', ['生态', '环境', '绿色', '碳', '污染', '自然', '气候']),
    ('minsheng', ['民生', '教育', '医疗', '养老', '住房', '社保', '扶贫', '乡村振兴', '农民', '健康']),
    ('zhili', ['治理', '法治', '基层', '制度', '治理体系', '监督', '反腐', '法治政府', '民法典']),
    ('wenhua', ['文化', '文明', '精神', '传统', '历史', '文艺', '文物', '党史']),
    ('shehui', ['社会', '社区', '公共', '安全', '应急', '志愿']),
]

CATEGORY_DEFAULT = 'xuexi'


def classify(title, content):
    text = title + ' ' + content[:800]
    for cat, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in text:
                return cat
    return CATEGORY_DEFAULT


def parse_article(path):
    """解析单篇 md，返回 dict 或 None"""
    raw = path.read_bytes()
    for enc in ('utf-8', 'utf-8-sig', 'gb18030'):
        try:
            text = raw.decode(enc)
            break
        except (UnicodeDecodeError, LookupError):
            text = raw.decode('utf-8', errors='replace')
    lines = text.splitlines()
    title = ''
    source_url = ''
    date_str = ''
    content_lines = []
    in_body = False
    for line in lines:
        s = line.strip()
        if not title and s.startswith('#'):
            title = s.lstrip('#').strip()
            continue
        if not in_body and s.startswith('>'):
            # 来源行：> 来源：学习强国　|　日期：2020-01-05　|　[原文链接](url)
            m = re.search(r'日期[:：]\s*(\d{4}-\d{2}-\d{2})', s)
            if m:
                date_str = m.group(1)
            m = re.search(r'\[原文链接\]\(([^)]+)\)', s)
            if m:
                source_url = m.group(1)
            continue
        if s == '---':
            in_body = True
            continue
        if in_body:
            content_lines.append(line)
    if not title:
        # 从文件名取标题
        title = path.stem.split('-', 2)[-1] if '-' in path.stem else path.stem
    if not date_str:
        m = re.match(r'(\d{4}-\d{2}-\d{2})', path.name)
        if m:
            date_str = m.group(1)
    body = '\n'.join(content_lines).strip()
    if not body:
        return None
    return {
        'title': title,
        'source_url': source_url,
        'date': date_str,
        'body': body,
    }


def extract_golden_phrases(art, limit_per_art=5):
    """从正文提炼金句（习近平讲话/名言/排比句），返回 (金句, 出处) 列表"""
    phrases = []
    body = art['body']
    # 1. 引号内的短句（含习近平讲话）
    for m in re.finditer(r'[“"]([^“”"]{8,80})[”"]', body):
        p = m.group(1).strip()
        if p and len(p) >= 8 and '按' not in p[:3]:
            phrases.append(p)
    # 2. 每日金句文件整篇
    if '金句' in art['title']:
        for line in body.splitlines():
            s = line.strip().strip('·').strip()
            if 10 <= len(s) <= 90 and not s.startswith(('http', '#', '>', '—')):
                phrases.append(s)
    # 去重去短
    seen = set()
    out = []
    for p in phrases:
        if p not in seen and len(p) >= 10:
            seen.add(p)
            out.append(p)
        if len(out) >= limit_per_art:
            break
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--limit', type=int, default=0, help='只处理前 N 篇（调试用）')
    args = parser.parse_args()

    files = sorted(SRC.glob('*.md'))
    if args.limit:
        files = files[:args.limit]

    con = sqlite3.connect(DB)
    cur = con.cursor()
    existing = set(r[0] for r in cur.execute("SELECT title FROM hot_topics").fetchall())
    existing_phr = set(r[0] for r in cur.execute("SELECT phrase FROM good_phrases").fetchall())

    inserted = 0
    skipped = 0
    phrases_added = 0
    cat_count = {}
    for f in files:
        art = parse_article(f)
        if not art:
            skipped += 1
            continue
        if art['title'] in existing:
            skipped += 1
            continue
        cat = classify(art['title'], art['body'])
        cat_count[cat] = cat_count.get(cat, 0) + 1
        summary = re.sub(r'\s+', '', art['body'])[:200]
        if not args.dry_run:
            cur.execute(
                "INSERT INTO hot_topics (title, summary, category, keywords, source_url, original_text, week_label, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'published')",
                (art['title'], summary, cat, '[]', art['source_url'] or '', art['body'],
                 f"{art['date'][:4]}-W{max(1, int(art['date'][5:7])//2+1)}" if art['date'] else None)
            )
            # 金句提炼
            for p in extract_golden_phrases(art):
                if p not in existing_phr:
                    cur.execute(
                        "INSERT INTO good_phrases (phrase, source, source_url, source_date, tag) VALUES (?, '学习强国', ?, ?, '[]')",
                        (p, art['source_url'] or '', art['date'] or None)
                    )
                    existing_phr.add(p)
                    phrases_added += 1
        else:
            phrases_added += len(extract_golden_phrases(art))
        inserted += 1
        existing.add(art['title'])

    if not args.dry_run:
        con.commit()
    print(f"[{'DRY-RUN' if args.dry_run else 'IMPORTED'}] 文件 {len(files)}，新导入 {inserted}，跳过 {skipped}")
    print(f"[{'DRY-RUN' if args.dry_run else 'IMPORTED'}] 分类分布: {cat_count}")
    print(f"[{'DRY-RUN' if args.dry_run else 'IMPORTED'}] 提炼金句: {phrases_added}")
    con.close()


if __name__ == '__main__':
    main()
