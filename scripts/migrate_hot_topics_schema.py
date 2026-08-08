#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/migrate_hot_topics_schema.py

为 hot_topics 表补充 source_url / original_text 列（schema 与 topic_service/topic_scraper 对齐）。

用法：
  python scripts/migrate_hot_topics_schema.py
"""
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / 'data' / 'slb.db'


def main():
    con = sqlite3.connect(DB)
    cur = con.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(hot_topics)").fetchall()]
    added = []
    if 'source_url' not in cols:
        cur.execute("ALTER TABLE hot_topics ADD COLUMN source_url TEXT")
        added.append('source_url')
    if 'original_text' not in cols:
        cur.execute("ALTER TABLE hot_topics ADD COLUMN original_text TEXT")
        added.append('original_text')
    con.commit()
    print("已添加列:", added if added else "无（已存在）")
    con.close()


if __name__ == '__main__':
    main()
