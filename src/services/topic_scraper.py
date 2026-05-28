# 时政热点自动抓取服务
#
# 从学习强国合作源抓取时评、理论、党建三个板块的原文
# 数据源：人民网评论、求是网、人民网理论、人民网党建

import json
import logging
import re
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}
TIMEOUT = 20


def get_week_label():
    now = datetime.now()
    return f'{now.year}-W{now.isocalendar()[1]:02d}'


def deduplicate(items):
    seen = {}
    for item in items:
        title = item['title']
        if title not in seen or (item.get('original_text') and not seen[title].get('original_text')):
            seen[title] = item
    return list(seen.values())


# ============================================================
# 正文抓取
# ============================================================

def fetch_article_text(url):
    """抓取文章正文"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or 'utf-8'
        html = resp.text

        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        content = ''
        # 主要方式：从 p 标签提取段落（最可靠）
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL | re.IGNORECASE)
        paragraphs = [p for p in paragraphs if len(re.sub(r'<[^>]+>', '', p).strip()) > 15]
        if paragraphs:
            content = '\n'.join(paragraphs[:30])

        content = re.sub(r'<br\s*/?>', '\n', content)
        content = re.sub(r'<p[^>]*>', '\n', content)
        content = re.sub(r'</p>', '', content)
        content = re.sub(r'<[^>]+>', '', content)
        for entity, char in [('&nbsp;', ' '), ('&ldquo;', '\u201c'), ('&rdquo;', '\u201d'),
                              ('&lsquo;', '\u2018'), ('&rsquo;', '\u2019'), ('&mdash;', '\u2014'),
                              ('&hellip;', '\u2026'), ('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>')]:
            content = content.replace(entity, char)
        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        return content[:8000] if content else ''
    except Exception as e:
        logger.warning(f'抓取正文失败 {url}: {e}')
        return ''


def _extract_people_links(html, base_url=''):
    """通用人民网链接提取（匹配 /n1/YYYY/MMDD/cXXXXX-XXXXXXX.html 格式，支持相对和绝对URL）"""
    # 匹配相对路径和绝对URL
    pat_relative = r'href="(/n1/20\d{2}/\d{4}/c\d+-\d+\.html?)"'
    pat_absolute = r'href="((?:https?://)?[^"]*?/n1/20\d{2}/\d{4}/c\d+-\d+\.html?)"'

    all_hrefs = set()
    for m in re.finditer(pat_relative, html):
        all_hrefs.add(('relative', m.group(1)))
    for m in re.finditer(pat_absolute, html):
        all_hrefs.add(('absolute', m.group(1)))

    results = []
    seen = set()
    for kind, href in all_hrefs:
        # 找 title 属性
        esc_href = re.escape(href)
        title_match = re.search(r'href="' + esc_href + r'"[^>]*title="([^"]{4,100})"', html)
        if not title_match:
            title_match = re.search(r'href="' + esc_href + r'">([^<]{4,100})</a>', html)
        if not title_match:
            continue
        title = title_match.group(1).strip()
        if not title or title in seen or len(title) < 4:
            continue
        seen.add(title)
        if kind == 'relative':
            full_url = base_url + href
        else:
            full_url = href
        results.append((full_url, title))
    return results


# ============================================================
# 时评：人民网评论
# ============================================================

def fetch_shiping(limit=15):
    """抓取人民网评论（时评）"""
    url = 'http://opinion.people.com.cn/'
    results = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        links = _extract_people_links(resp.text, 'http://opinion.people.com.cn')
        for href, title in links:
            results.append({'title': title, 'source': '人民网评论', 'source_url': href, 'category': 'shiping'})
            if len(results) >= limit:
                break
        logger.info(f'人民网评论抓取到 {len(results)} 条')
    except Exception as e:
        logger.error(f'人民网评论抓取失败: {e}')
    return results


# ============================================================
# 理论：求是网 + 人民网理论
# ============================================================

def fetch_lilun(limit=15):
    """抓取理论文章"""
    results = []
    seen = set()

    # 求是网
    try:
        resp = requests.get('http://www.qstheory.cn/', headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        # 求是网链接格式多样，用 title 属性匹配
        links = re.findall(r'href="(http://www\.qstheory\.cn/[^"]*\.htm)"[^>]*title="([^"]{4,100})"', resp.text)
        if not links:
            links = re.findall(r'href="(http://www\.qstheory\.cn/[^"]*\.htm)"[^>]*>([^<]{4,100})</a>', resp.text)
        for href, title in links:
            title = title.strip()
            if not title or title in seen or len(title) < 4:
                continue
            seen.add(title)
            results.append({'title': title, 'source': '求是网', 'source_url': href, 'category': 'lilun'})
            if len(results) >= limit // 2:
                break
        logger.info(f'求是网抓取到 {len(results)} 条')
    except Exception as e:
        logger.error(f'求是网抓取失败: {e}')

    # 人民网理论
    remaining = limit - len(results)
    if remaining > 0:
        try:
            resp = requests.get('http://theory.people.com.cn/', headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            links = _extract_people_links(resp.text, 'http://theory.people.com.cn')
            for href, title in links:
                if title in seen:
                    continue
                seen.add(title)
                results.append({'title': title, 'source': '人民网理论', 'source_url': href, 'category': 'lilun'})
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f'人民网理论抓取失败: {e}')

    logger.info(f'理论文章共抓取 {len(results)} 条')
    return results[:limit]


# ============================================================
# 党建：人民网党建
# ============================================================

def fetch_dangjian(limit=15):
    """抓取人民网党建"""
    urls = [
        'http://cpc.people.com.cn/',
        'http://cpc.people.com.cn/GB/64093/64094/index.html',
        'http://cpc.people.com.cn/GB/64093/64378/index.html',
    ]
    results = []
    seen = set()
    for page_url in urls:
        try:
            resp = requests.get(page_url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            links = _extract_people_links(resp.text, 'http://cpc.people.com.cn')
            for href, title in links:
                if title in seen:
                    continue
                seen.add(title)
                results.append({'title': title, 'source': '人民网党建', 'source_url': href, 'category': 'dangjian'})
                if len(results) >= limit:
                    break
        except Exception as e:
            logger.error(f'人民网党建抓取失败 {page_url}: {e}')
    logger.info(f'党建文章抓取到 {len(results)} 条')
    return results[:limit]


# ============================================================
# 主流程
# ============================================================

def fetch_all(limit_per_source=10):
    """抓取三个板块"""
    all_items = []
    all_items.extend(fetch_shiping(limit_per_source))
    all_items.extend(fetch_lilun(limit_per_source))
    all_items.extend(fetch_dangjian(limit_per_source))
    deduped = deduplicate(all_items)
    logger.info(f'去重后共 {len(deduped)} 条')
    return deduped


def save_topics(items, db):
    """抓取正文并入库"""
    week_label = get_week_label()
    saved = 0
    skipped = 0

    for item in items:
        title = item['title']
        existing = db.execute("SELECT id FROM hot_topics WHERE title = ?", (title,)).fetchone()
        if existing:
            skipped += 1
            continue

        source_url = item.get('source_url', '')
        logger.info(f'抓取正文: {title[:30]}...')
        original_text = fetch_article_text(source_url) if source_url else ''

        summary = original_text[:200] if original_text else f"来源：{item.get('source', '')}"
        category = item.get('category', 'shiping')
        keywords = [item.get('source', '')]

        db.execute(
            """INSERT INTO hot_topics
               (title, summary, category, keywords, multi_views, related_phrases,
                related_papers, exam_prediction, exam_history, week_label, status,
                source_url, original_text)
               VALUES (?, ?, ?, ?, '[]', '[]', '[]', '{}', '[]', ?, 'published', ?, ?)""",
            (title, summary, category, json.dumps(keywords, ensure_ascii=False),
             week_label, source_url, original_text)
        )
        saved += 1

    db.commit()
    logger.info(f'入库完成：新增 {saved} 条，跳过 {skipped} 条')
    return {'saved': saved, 'skipped': skipped, 'total': len(items)}


def fetch_xuexi_articles(limit=10, cookies_file=None):
    """从学习强国抓取习近平重要文章。

    优先用 cookies + Playwright 从列表页发现文章；
    若 cookies 缺失/过期（列表页 0 篇），自动 fallback 到搜索引擎发现文章 URL。
    文章详情页是公开的，抓正文不需要 cookies。
    """
    import asyncio
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning('playwright 未安装，跳过学习强国抓取')
        return []

    if cookies_file is None:
        import os
        # 按优先级查找 cookies 文件
        candidates = [
            os.path.expanduser('~/.hermes/xuexi_cookies.json'),
            r"D:\新建文件夹\下载\www.xuexi.cn.cookies.json",
        ]
        for c in candidates:
            if os.path.exists(c):
                cookies_file = c
                break

    PAGE_URL = "https://www.xuexi.cn/6db80fbc0859e5c06b81fd5d6d618749/9a3668c13f6e303932b5e0e100fc248b.html"
    from datetime import datetime, timedelta
    CUTOFF = datetime.now() - timedelta(days=180)

    # ---- 正文抓取（不需要 cookies） ----
    async def _fetch_article_content(page, art):
        """打开文章详情页，提取标题和正文"""
        import re as _re
        url = art['url']
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        title = await page.evaluate("""() => {
            var el = document.querySelector('[class*=title]')
                     || document.querySelector('.article-title')
                     || document.querySelector('h1');
            return el ? el.innerText.trim() : '';
        }""")

        body = await page.evaluate("""() => {
            var ps = document.querySelectorAll('p');
            var parts = [];
            for (var i = 0; i < ps.length; i++) {
                var t = ps[i].innerText.trim();
                if (t.length > 5) parts.push(t);
            }
            if (parts.length > 3) return parts.join('\\n\\n');
            return document.body.innerText;
        }""")

        title = _re.sub(r'\s*20\d{2}[-/]\d{2}[-/]\d{2}\s*', '', title).strip()
        markers = ['服务电话：12361', '中央宣传部宣传舆情研究中心版权所有',
                    'Copyright', '互联网新闻信息服务许可证', 'ICP备案']
        for marker in markers:
            idx = body.find(marker)
            if idx > 0:
                body = body[:idx]
        body = body.strip()

        if title and len(body) > 200:
            return {
                'title': title,
                'source': '学习强国',
                'source_url': url,
                'category': 'xuexi',
                'original_text': body,
                'date': art.get('date', ''),
            }
        return None

    # ---- 方式 A：cookies + 列表页发现 ----
    async def _discover_via_cookies(context, page):
        import re as _re
        import json as _json

        if not cookies_file:
            logger.info('cookies 文件未配置，跳过列表页发现')
            return []

        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = _json.load(f)
        except Exception as e:
            logger.warning(f'读取 cookies 失败: {e}')
            return []

        pw_cookies = [{'name': c['name'], 'value': c['value'],
                        'domain': c['domain'], 'path': c['path']} for c in cookies]
        await context.add_cookies(pw_cookies)

        await page.goto(PAGE_URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        cells = await page.query_selector_all('.grid-cell')
        if not cells:
            logger.info('列表页无 grid-cell（cookies 可能过期）')
            return []

        article_cells = []
        for i, cell in enumerate(cells):
            text = await cell.inner_text()
            date_match = _re.search(r'20\d{2}[-年/]\d{2}[-月/]\d{2}', text)
            if date_match:
                date_str = date_match.group(0).replace('年', '-').replace('月', '-').replace('/', '-')
                try:
                    art_date = datetime.strptime(date_str, '%Y-%m-%d')
                    if art_date < CUTOFF:
                        continue
                except:
                    continue
                article_cells.append((i, date_str))

        article_urls = []
        seen_ids = set()
        for cell_idx, date_str in article_cells:
            cells = await page.query_selector_all('.grid-cell')
            if cell_idx >= len(cells):
                continue
            try:
                async with context.expect_page(timeout=8000) as new_page_info:
                    await cells[cell_idx].click()
                new_page = await new_page_info.value
                await new_page.wait_for_load_state('domcontentloaded', timeout=10000)
                id_match = _re.search(r'id=(\d+)', new_page.url)
                if id_match:
                    art_id = id_match.group(1)
                    if art_id not in seen_ids:
                        seen_ids.add(art_id)
                        article_urls.append({'id': art_id, 'date': date_str, 'url': new_page.url})
                await new_page.close()
                await page.wait_for_timeout(500)
            except:
                if 'lgpage/detail' in page.url:
                    await page.go_back()
                    await page.wait_for_timeout(1000)

        logger.info(f'列表页发现 {len(article_urls)} 篇文章')
        return article_urls

    # ---- 方式 B：从 URL 缓存文件发现（不需要 cookies） ----
    async def _discover_via_cache(limit_count):
        """从 URL 缓存文件读取待抓取的文章 URL。

        缓存文件由 Hermes cron 定期写入（搜索引擎发现），
        也支持手动写入。格式: 每行一个 URL 或 JSON 数组。
        """
        import json as _json
        import os as _os
        import re as _re

        cache_file = _os.path.expanduser('~/.hermes/xuexi_urls.json')
        if not _os.path.exists(cache_file):
            logger.info(f'URL 缓存文件不存在: {cache_file}')
            return []

        try:
            with open(cache_file, 'r') as f:
                data = _json.load(f)
            # 支持两种格式: [{"id":..., "url":...}] 或 ["url1", "url2"]
            article_urls = []
            seen_ids = set()
            for item in data[:limit_count * 2]:
                if isinstance(item, str):
                    url = item
                    id_match = _re.search(r'id=(\d+)', url)
                    art_id = id_match.group(1) if id_match else url
                else:
                    url = item.get('url', '')
                    art_id = item.get('id', '')
                if art_id not in seen_ids:
                    seen_ids.add(art_id)
                    article_urls.append({'id': str(art_id), 'date': item.get('date', '') if isinstance(item, dict) else '', 'url': url})
            logger.info(f'从缓存文件读取 {len(article_urls)} 篇文章 URL')
            return article_urls[:limit_count]
        except Exception as e:
            logger.warning(f'读取 URL 缓存失败: {e}')
            return []

    # ---- 主流程 ----
    async def _scrape():
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # 优先 cookies 方式
            article_urls = await _discover_via_cookies(context, page)

            # fallback: 搜索引擎
            if not article_urls:
                logger.info('cookies 方式无结果，切换搜索引擎发现')
                article_urls = await _discover_via_cache(limit)

            if not article_urls:
                logger.warning('两种方式均未发现文章')
                await browser.close()
                return []

            # 抓取正文（不需要 cookies）
            results = []
            for art in article_urls[:limit]:
                try:
                    result = await _fetch_article_content(page, art)
                    if result:
                        results.append(result)
                        logger.info(f'✅ {result["title"][:40]} ({len(result["original_text"])}字)')
                except Exception as e:
                    logger.warning(f'抓取文章失败 {art["id"]}: {e}')

            await browser.close()
            return results

    try:
        return asyncio.run(_scrape())
    except Exception as e:
        logger.error(f'学习强国抓取失败: {e}')
        return []


def save_xuexi_topics(items, db):
    """学习强国文章入库"""
    saved = 0
    skipped = 0
    for item in items:
        title = item['title']
        existing = db.execute("SELECT id FROM hot_topics WHERE title = ?", (title,)).fetchone()
        if existing:
            skipped += 1
            continue
        summary = item['original_text'][:200] if item['original_text'] else ''
        db.execute(
            """INSERT INTO hot_topics
               (title, summary, category, keywords, multi_views, related_phrases,
                related_papers, exam_prediction, exam_history, week_label, status,
                source_url, original_text)
               VALUES (?, ?, 'xuexi', '[]', '[]', '[]', '[]', '{}', '[]', ?, 'published', ?, ?)""",
            (title, summary, item.get('date', '')[:7], item['source_url'], item['original_text'])
        )
        saved += 1
    db.commit()
    logger.info(f'学习强国入库完成：新增 {saved} 条，跳过 {skipped} 条')
    return {'saved': saved, 'skipped': skipped, 'total': len(items)}


def run_scrape(db):
    """执行一次完整的抓取+入库流程"""
    items = fetch_all(limit_per_source=10)
    if not items:
        return {'saved': 0, 'skipped': 0, 'total': 0, 'error': '所有数据源抓取失败'}
    return save_topics(items, db)


def run_scrape_xuexi(db):
    """执行学习强国抓取+入库"""
    items = fetch_xuexi_articles(limit=10)
    if not items:
        return {'saved': 0, 'skipped': 0, 'total': 0, 'error': '学习强国抓取失败或无新内容'}
    return save_xuexi_topics(items, db)
