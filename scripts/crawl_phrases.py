#!/usr/bin/env python3
"""
好词好句自动爬取脚本
从人民日报、求是网等来源抓取申论素材
用法: python scripts/crawl_phrases.py [--count 10]
"""

import sys
import os
import json
import sqlite3
import logging
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def crawl_people_daily_phrases(count=10):
    """从人民日报评论版抓取好词好句"""
    import requests
    from bs4 import BeautifulSoup

    phrases = []
    urls = [
        'http://opinion.people.com.cn/GB/8213/49154/index.html',
        'http://opinion.people.com.cn/GB/8213/49155/index.html',
    ]

    for url in urls:
        try:
            resp = requests.get(url, timeout=15, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.encoding = 'gb2312'
            soup = BeautifulSoup(resp.text, 'lxml')

            links = soup.select('a[href*="people.com.cn"]')[:count]
            for link in links:
                try:
                    article_url = link['href']
                    if not article_url.startswith('http'):
                        article_url = 'http://opinion.people.com.cn' + article_url

                    art_resp = requests.get(article_url, timeout=15, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    art_resp.encoding = 'gb2312'
                    art_soup = BeautifulSoup(art_resp.text, 'lxml')

                    # 提取正文中的精华句子
                    content_div = art_soup.select_one('.rm_text_con, .text_con, #rwb_zw')
                    if content_div:
                        paragraphs = content_div.find_all('p')
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            # 筛选含有申论常用表达的句子
                            keywords = ['坚持', '推动', '促进', '实现', '构建', '完善',
                                       '深化', '统筹', '着力', '全面', '人民', '发展']
                            if len(text) > 30 and len(text) < 200 and any(kw in text for kw in keywords):
                                phrases.append({
                                    'phrase': text,
                                    'source': '人民日报',
                                    'source_url': article_url,
                                    'source_date': datetime.now().strftime('%Y-%m-%d'),
                                    'tag': json.dumps(['人民日报', '时评'], ensure_ascii=False)
                                })
                except Exception as e:
                    logger.debug(f"Failed to crawl article: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Failed to crawl {url}: {e}")
            continue

    return phrases[:count]


def crawl_xinhua_phrases(count=10):
    """从新华网评抓取好词好句"""
    import requests
    from bs4 import BeautifulSoup

    phrases = []
    try:
        url = 'http://www.xinhuanet.com/comments/'
        resp = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'lxml')

        links = soup.select('a[href*="xinhuanet.com"]')[:count * 2]
        for link in links:
            try:
                href = link.get('href', '')
                if not href or 'comments' not in href:
                    continue
                if not href.startswith('http'):
                    continue

                art_resp = requests.get(href, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                art_resp.encoding = 'utf-8'
                art_soup = BeautifulSoup(art_resp.text, 'lxml')

                content_div = art_soup.select_one('#detail, .article, .content')
                if content_div:
                    paragraphs = content_div.find_all('p')
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        keywords = ['治理', '改革', '创新', '民生', '法治', '生态',
                                   '高质量', '现代化', '人民', '发展', '安全']
                        if len(text) > 30 and len(text) < 200 and any(kw in text for kw in keywords):
                            phrases.append({
                                'phrase': text,
                                'source': '新华网',
                                'source_url': href,
                                'source_date': datetime.now().strftime('%Y-%m-%d'),
                                'tag': json.dumps(['新华网', '时评'], ensure_ascii=False)
                            })
            except Exception as e:
                logger.debug(f"Failed to crawl article: {e}")
                continue

    except Exception as e:
        logger.warning(f"Failed to crawl xinhua: {e}")

    return phrases[:count]


def save_phrases(phrases):
    """保存好词好句到数据库"""
    if not phrases:
        logger.info("No phrases to save")
        return 0

    db = sqlite3.connect(Config.DATABASE_PATH)
    db.row_factory = sqlite3.Row

    saved = 0
    for p in phrases:
        # 检查是否已存在
        existing = db.execute(
            "SELECT id FROM good_phrases WHERE phrase = ?", (p['phrase'],)
        ).fetchone()
        if existing:
            continue

        db.execute(
            """INSERT INTO good_phrases (phrase, source, source_url, source_date, tag, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', datetime('now'))""",
            (p['phrase'], p['source'], p.get('source_url', ''),
             p.get('source_date', ''), p.get('tag', '[]'))
        )
        saved += 1

    db.commit()
    db.close()
    return saved


def main():
    parser = argparse.ArgumentParser(description='好词好句自动爬取')
    parser.add_argument('--count', type=int, default=10, help='每源抓取数量')
    parser.add_argument('--source', choices=['all', 'people', 'xinhua'], default='all', help='来源')
    args = parser.parse_args()

    all_phrases = []

    if args.source in ('all', 'people'):
        logger.info("Crawling People's Daily...")
        all_phrases.extend(crawl_people_daily_phrases(args.count))

    if args.source in ('all', 'xinhua'):
        logger.info("Crawling Xinhua...")
        all_phrases.extend(crawl_xinhua_phrases(args.count))

    # 去重
    seen = set()
    unique_phrases = []
    for p in all_phrases:
        if p['phrase'] not in seen:
            seen.add(p['phrase'])
            unique_phrases.append(p)

    saved = save_phrases(unique_phrases)
    logger.info(f"Crawled {len(unique_phrases)} phrases, saved {saved} new ones")


if __name__ == '__main__':
    main()
