#!/usr/bin/env python3
"""
SLB 自动化内容更新脚本
定时执行：爬取新素材、更新热点专题
用法: python scripts/auto_update.py [--task all|phrases|topics|backup]
"""

import sys
import os
import subprocess
import logging
import argparse
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_phrases_crawl():
    """执行好词好句爬取"""
    logger.info("Starting phrases crawl...")
    try:
        result = subprocess.run(
            [sys.executable, os.path.join(PROJECT_ROOT, 'scripts', 'crawl_phrases.py'), '--count', '15'],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            logger.info(f"Phrases crawl completed: {result.stdout.strip()}")
        else:
            logger.error(f"Phrases crawl failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("Phrases crawl timed out")
    except Exception as e:
        logger.error(f"Phrases crawl error: {e}")


def run_topics_update():
    """更新热点专题（从 topic_scraper 导入）"""
    logger.info("Starting topics update...")
    try:
        from src.api.utils import get_db
        from src.services.topic_scraper import run_scrape, run_scrape_xuexi
        db = get_db()
        shiping_result = run_scrape(db)
        shiping_count = shiping_result.get('saved', 0) if isinstance(shiping_result, dict) else shiping_result
        logger.info(f"Topics update completed: {shiping_count} shiping topics")
        try:
            xuexi_result = run_scrape_xuexi(db)
            xuexi_count = xuexi_result.get('saved', 0) if isinstance(xuexi_result, dict) else xuexi_result
            logger.info(f"Xuexi topics update completed: {xuexi_count} new xuexi topics")
        except Exception as e:
            logger.warning(f"Xuexi scrape skipped: {e}")
    except ImportError as e:
        logger.warning(f"topic_scraper not available, skipping: {e}")
    except Exception as e:
        logger.error(f"Topics update error: {e}")


def run_backup():
    """执行数据库备份"""
    logger.info("Starting database backup...")
    try:
        backup_script = os.path.join(PROJECT_ROOT, 'scripts', 'backup_db.sh')
        result = subprocess.run(
            ['bash', backup_script],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            logger.info(f"Backup completed: {result.stdout.strip()}")
        else:
            logger.error(f"Backup failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Backup error: {e}")


def run_cleanup():
    """清理过期数据"""
    logger.info("Starting cleanup...")
    try:
        import sqlite3
        from src.config import Config

        db = sqlite3.connect(Config.DATABASE_PATH)

        # 清理90天前的管理员日志
        db.execute("DELETE FROM admin_logs WHERE created_at < datetime('now', '-90 days')")
        # 清理过期的 token 黑名单
        db.execute("DELETE FROM token_blacklist WHERE expires_at < datetime('now')")
        # 清理过期的会话
        db.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")

        deleted = db.total_changes
        db.commit()
        db.close()
        logger.info(f"Cleanup completed: removed {deleted} expired records")
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


def main():
    parser = argparse.ArgumentParser(description='SLB 自动化内容更新')
    parser.add_argument('--task', choices=['all', 'phrases', 'topics', 'backup', 'cleanup'],
                       default='all', help='执行任务')
    args = parser.parse_args()

    logger.info(f"=== SLB Auto Update [{args.task}] started at {datetime.now()} ===")

    if args.task in ('all', 'phrases'):
        run_phrases_crawl()

    if args.task in ('all', 'topics'):
        run_topics_update()

    if args.task in ('all', 'backup'):
        run_backup()

    if args.task in ('all', 'cleanup'):
        run_cleanup()

    logger.info(f"=== Auto Update completed at {datetime.now()} ===")


if __name__ == '__main__':
    main()
