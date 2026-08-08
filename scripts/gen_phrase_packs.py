#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/gen_phrase_packs.py

为 good_phrases 生成主题标签，并聚合成 phrase_packs 素材包。

主题关键词规则（标题/内容匹配）：
  乡村振兴 / 科技创新 / 民生福祉 / 生态文明 / 基层治理 / 文化建设
  改革开放 / 法治建设 / 青年奋斗 / 经济发展 / 党的建设 / 百年党史

用法：
  python scripts/gen_phrase_packs.py            # 打标签+生成素材包
  python scripts/gen_phrase_packs.py --dry-run  # 只统计
"""
import argparse
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'slb.db'

THEME_RULES = [
    ('乡村振兴', ['乡村', '农业', '农民', '农村', '扶贫', '脱贫攻坚', '粮食', '土地']),
    ('科技创新', ['科技', '创新', '数字', '人工智能', '技术', '互联网', '数据', '人才']),
    ('民生福祉', ['民生', '人民', '群众', '就业', '教育', '医疗', '养老', '幸福']),
    ('生态文明', ['生态', '环境', '绿色', '自然', '碳', '污染', '可持续']),
    ('基层治理', ['基层', '治理', '社区', '群众工作', '党建', '组织']),
    ('文化建设', ['文化', '文明', '精神', '传统', '历史', '文艺', '价值观']),
    ('改革开放', ['改革', '开放', '发展', '市场经济', '现代化']),
    ('法治建设', ['法治', '法律', '制度', '规则', '公平正义', '监督']),
    ('青年奋斗', ['青年', '奋斗', '理想', '担当', '青春', '梦想', '实干']),
    ('经济发展', ['经济', '产业', '企业', '市场', '增长', '创新驱动', '高质量']),
    ('党的建设', ['党', '党员', '纪律', '作风', '忠诚', '初心', '使命']),
    ('百年党史', ['党史', '革命', '红色', '征程', '复兴', '精神谱系']),
]

PACK_DESCRIPTIONS = {
    '乡村振兴': '全面推进乡村振兴的核心论述与典型表述',
    '科技创新': '科技自立自强与创新驱动发展战略金句',
    '民生福祉': '以人民为中心的发展思想经典表述',
    '生态文明': '绿水青山就是金山银山的生态理念',
    '基层治理': '基层社会治理现代化的实践要求',
    '文化建设': '坚定文化自信与精神文明建设',
    '改革开放': '全面深化改革与高水平对外开放',
    '法治建设': '全面依法治国与法治中国建设',
    '青年奋斗': '青年担当与实干奋斗精神',
    '经济发展': '高质量发展与中国式现代化',
    '党的建设': '全面从严治党与党的建设总要求',
    '百年党史': '党史学习与红色精神传承',
}


def classify_phrase(text):
    hits = []
    for theme, kws in THEME_RULES:
        for kw in kws:
            if kw in text:
                hits.append(theme)
                break
    return hits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--min-pack', type=int, default=8, help='素材包最少金句数')
    args = parser.parse_args()

    con = sqlite3.connect(DB)
    cur = con.cursor()

    # 1. 给所有无 tag 的金句打标签
    rows = cur.execute("SELECT id, phrase, tag FROM good_phrases").fetchall()
    tagged = 0
    theme_phrases = {}
    for rid, phrase, tag in rows:
        try:
            tl = json.loads(tag) if tag else []
        except Exception:
            tl = []
        if not tl:
            hits = classify_phrase(phrase)
            if hits:
                tl = hits[:2]
                if not args.dry_run:
                    cur.execute("UPDATE good_phrases SET tag = ? WHERE id = ?",
                                (json.dumps(tl, ensure_ascii=False), rid))
                tagged += 1
        for t in tl:
            theme_phrases.setdefault(t, []).append(rid)

    # 2. 生成素材包（跳过已存在同名包）
    existing = set(r[0] for r in cur.execute("SELECT name FROM phrase_packs").fetchall())
    created = 0
    for theme, ids in theme_phrases.items():
        if theme not in PACK_DESCRIPTIONS:
            continue
        if len(ids) < args.min_pack:
            continue
        name = f'{theme}素材包'
        if name in existing:
            continue
        if not args.dry_run:
            cur.execute(
                "INSERT INTO phrase_packs (name, description, theme, phrase_ids, difficulty, sort_order, status) "
                "VALUES (?, ?, ?, ?, ?, ?, 'published')",
                (name, PACK_DESCRIPTIONS[theme], theme, json.dumps(ids, ensure_ascii=False),
                 2 if len(ids) >= 15 else 1, 0)
            )
        created += 1
        existing.add(name)

    if not args.dry_run:
        con.commit()

    print(f"[{'DRY-RUN' if args.dry_run else 'DONE'}] 打标签金句: {tagged}")
    print(f"[{'DRY-RUN' if args.dry_run else 'DONE'}] 生成素材包: {created}")
    for theme, ids in sorted(theme_phrases.items(), key=lambda x: -len(x[1])):
        if theme in PACK_DESCRIPTIONS and len(ids) >= args.min_pack:
            print(f"  - {theme}: {len(ids)} 条")
    con.close()


if __name__ == '__main__':
    main()
