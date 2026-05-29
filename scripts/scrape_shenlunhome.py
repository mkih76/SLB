#!/usr/bin/env python3
"""
shenlunhome.com 申论真题批量抓取器
- 自动发现所有板块（国考/各省）
- 遍历每个板块的帖子列表
- 提取正文（材料+题目），GBK→UTF-8
- 输出到 data/shenlun_zhenti/ 目录
"""

import os
import re
import sys
import json
import time
import hashlib
import requests
from datetime import datetime
from html.parser import HTMLParser

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
BASE_URL = "http://shenlunhome.com"
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

# Rate limit: polite delay between requests
DELAY = 0.8

def fetch(path, params=None, retries=3):
    """Fetch a page with GBK decoding and retry."""
    url = f"{BASE_URL}/{path}"
    for attempt in range(retries):
        try:
            resp = SESSION.get(url, params=params, timeout=20)
            resp.encoding = "utf-8"
            if resp.status_code == 200:
                return resp.text
            print(f"  [WARN] HTTP {resp.status_code} for {path}")
        except Exception as e:
            print(f"  [ERR] {e} (attempt {attempt+1}/{retries})")
        time.sleep(DELAY * 2)
    return None


def discover_boards():
    """Discover all forum board IDs from the main forum page."""
    print("[1/4] 发现板块...")
    html = fetch("forum.php", {"mobile": "2"})
    if not html:
        print("  无法访问首页，使用已知板块列表")
        return get_known_boards()

    # Find board links: forumdisplay&fid=XX
    fids = re.findall(r'fid=(\d+)', html)
    fids = list(set(fids))
    print(f"  发现 {len(fids)} 个板块ID: {sorted(fids)}")

    boards = []
    for fid in sorted(fids):
        # Fetch the board page to get its name
        time.sleep(DELAY)
        page = fetch("forum.php", {"mod": "forumdisplay", "fid": fid, "mobile": "2"})
        if not page:
            continue
        # Extract board name from <div class="header_center">XXX</div>
        m = re.search(r'<div class="header_center">(.*?)</div>', page)
        if m:
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        else:
            name = f"板块{fid}"
        # Count threads
        tids = re.findall(r'tid=(\d+)', page)
        tids = list(set(tids))
        boards.append({"fid": fid, "name": name, "sample_tids": tids[:3], "thread_sample_count": len(tids)})
        print(f"  fid={fid} name={name} 样本帖子数={len(tids)}")

    return boards


def get_known_boards():
    """Fallback: known board structure from search results."""
    return [
        {"fid": "59", "name": "国考", "sample_tids": [], "thread_sample_count": 0},
        {"fid": "60", "name": "各省省考", "sample_tids": [], "thread_sample_count": 0},
        {"fid": "61", "name": "国考", "sample_tids": [], "thread_sample_count": 0},
    ]


def get_thread_list(fid, max_pages=20):
    """Get all thread IDs from a board, paginating through all pages."""
    all_tids = []
    for page_num in range(1, max_pages + 1):
        params = {"mod": "forumdisplay", "fid": fid, "page": str(page_num), "mobile": "2"}
        html = fetch("forum.php", params)
        if not html:
            break

        tids = re.findall(r'tid=(\d+)', html)
        tids = list(set(tids))
        if not tids:
            break

        new_tids = [t for t in tids if t not in all_tids]
        if not new_tids:
            break

        all_tids.extend(new_tids)
        print(f"    板块fid={fid} 第{page_num}页: +{len(new_tids)}帖子 (累计{len(all_tids)})")
        time.sleep(DELAY)

    return all_tids


def extract_content(html):
    """Extract title and post content from a thread page."""
    # Title from <title>
    title_m = re.search(r'<title>(.*?)\s*-\s*', html)
    title = title_m.group(1).strip() if title_m else "未知"

    # Content from <div class="contentmake mtw message">
    content_m = re.search(r'<div class="contentmake mtw message">(.*?)</div>\s*<div', html, re.DOTALL)
    if not content_m:
        # Try alternative
        content_m = re.search(r'class="contentmake[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
    if not content_m:
        return title, ""

    raw = content_m.group(1)

    # Clean HTML to plain text
    # Replace <br> and <div> with newlines
    text = re.sub(r'<br\s*/?\s*>', '\n', raw)
    text = re.sub(r'<div[^>]*>', '\n', text)
    text = re.sub(r'</div>', '', text)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace('&#39;', "'")
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.strip()

    return title, text


def classify_exam(title):
    """Classify exam type, year, province from title."""
    year_m = re.search(r'(20\d{2})', title)
    year = int(year_m.group(1)) if year_m else 0

    province = "国考"
    if "国考" in title or "国家公务员" in title:
        province = "国考"
    else:
        # Try to extract province
        provinces = ["北京", "天津", "上海", "重庆", "河北", "山西", "辽宁", "吉林",
                     "黑龙江", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
                     "湖北", "湖南", "广东", "海南", "四川", "贵州", "云南", "陕西",
                     "甘肃", "青海", "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
                     "联考"]
        for p in provinces:
            if p in title:
                province = p
                break

    exam_type = "国考" if province == "国考" else "省考"

    return {
        "year": year,
        "province": province,
        "exam_type": exam_type,
    }


def save_paper(tid, title, content, board_name, out_dir):
    """Save a paper as markdown file."""
    info = classify_exam(title)

    # Build filename
    prov = info["province"]
    year = info["year"]
    safe_title = re.sub(r'[^\w\u4e00-\u9fff（）]', '_', title)[:60]
    filename = f"{prov}_{year}_{safe_title}.md"
    filepath = os.path.join(out_dir, filename)

    md = f"""---
source: shenlunhome.com
tid: {tid}
board: {board_name}
province: {prov}
year: {year}
exam_type: {info['exam_type']}
title: {title}
crawled_at: {datetime.now().isoformat()[:19]}
---

# {title}

{content}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md)
    return filepath


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data", "shenlun_zhenti")
    os.makedirs(out_dir, exist_ok=True)

    # Step 1: Discover boards
    boards = discover_boards()
    print(f"\n[2/4] 共发现 {len(boards)} 个板块\n")

    # Step 2: Get all thread IDs per board
    board_threads = {}
    for board in boards:
        fid = board["fid"]
        name = board["name"]
        print(f"[3/4] 获取板块 '{name}' (fid={fid}) 的帖子列表...")
        tids = get_thread_list(fid, max_pages=30)
        board_threads[fid] = {"name": name, "tids": tids}
        print(f"  → 共 {len(tids)} 个帖子\n")
        time.sleep(DELAY)

    # Deduplicate tids across boards
    all_tids = {}
    for fid, info in board_threads.items():
        for tid in info["tids"]:
            if tid not in all_tids:
                all_tids[tid] = info["name"]

    print(f"[3/4] 去重后共 {len(all_tids)} 个唯一帖子\n")

    # Load existing manifest for resume
    manifest_path = os.path.join(out_dir, "_manifest.json")
    existing_tids = set()
    manifest = []
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            existing = json.load(f)
            existing_tids = {str(m["tid"]) for m in existing}
            manifest = existing
        print(f"  已有 {len(existing_tids)} 个已抓取帖子，将跳过")

    # Step 3: Fetch each thread
    success = len(manifest)
    failed = 0

    for i, (tid, board_name) in enumerate(all_tids.items(), 1):
        if tid in existing_tids:
            continue
        print(f"[4/4] ({i}/{len(all_tids)}) 抓取 tid={tid}...")
        time.sleep(DELAY)

        html = fetch("forum.php", {"mod": "viewthread", "tid": tid, "mobile": "2"})
        if not html:
            print(f"  ✗ 失败")
            failed += 1
            continue

        title, content = extract_content(html)
        if not content or len(content) < 100:
            print(f"  ✗ 内容太短({len(content)}字符), 跳过")
            failed += 1
            continue

        filepath = save_paper(tid, title, content, board_name, out_dir)
        info = classify_exam(title)
        manifest.append({
            "tid": tid,
            "title": title,
            "file": os.path.basename(filepath),
            "province": info["province"],
            "year": info["year"],
            "exam_type": info["exam_type"],
            "chars": len(content),
        })
        print(f"  ✓ {info['province']} {info['year']}年 ({len(content)}字)")
        success += 1

    # Save manifest
    manifest_path = os.path.join(out_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"抓取完成!")
    print(f"  成功: {success}")
    print(f"  失败: {failed}")
    print(f"  输出: {out_dir}")
    print(f"  清单: {manifest_path}")


if __name__ == "__main__":
    main()
