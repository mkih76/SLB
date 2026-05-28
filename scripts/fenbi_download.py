#!/usr/bin/env python3
"""
粉笔申论资料一键下载脚本

用法:
    # 下载全部公开申论资料（无需登录）
    python scripts/fenbi_download.py

    # 下载题库真题（需要账号）
    python scripts/fenbi_download.py --phone 13800138000 --password xxx
"""
import argparse
import logging
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.crawler.fenbi_public import FenbiPublicScraper
from src.crawler.fenbi_tiku import FenbiTikuScraper

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='粉笔申论资料下载器')
    parser.add_argument('--phone', help='粉笔手机号（不提供则只下载公开资料）')
    parser.add_argument('--password', help='粉笔密码')
    parser.add_argument('--output', default='./data', help='输出目录 (默认 ./data)')
    parser.add_argument('--type', default='shenlun', choices=['shenlun', 'xingce'],
                        help='题库下载类型 (默认 shenlun)')
    parser.add_argument('--provinces', help='题库省份筛选，逗号分隔')
    parser.add_argument('--scan', nargs=2, type=int, metavar=('START', 'END'),
                        help='扫描目录 ID 范围')
    args = parser.parse_args()

    # 1. 公开资料
    logger.info("=" * 50)
    logger.info("📥 下载粉笔网盘公开资料")
    logger.info("=" * 50)

    public = FenbiPublicScraper(output_dir=os.path.join(args.output, 'fenbi_shenlun'))

    if args.scan:
        found = public.scan_range(args.scan[0], args.scan[1])
        logger.info(f"\n发现 {len(found)} 个公开目录")
        for d in found:
            logger.info(f"  {d['id']}: {d['name']} ({d['files']}文件)")
        return

    stats = public.download_all()
    logger.info(f"\n📊 公开资料: {stats['downloaded']} 下载, {stats['skipped']} 跳过, {stats['failed']} 失败, {stats['size_mb']:.1f}MB")

    # 2. 题库真题（可选）
    if args.phone and args.password:
        logger.info("\n" + "=" * 50)
        logger.info("📥 下载粉笔题库真题（需登录）")
        logger.info("=" * 50)

        tiku = FenbiTikuScraper(
            phone=args.phone,
            password=args.password,
            output_dir=os.path.join(args.output, 'fenbi_zhenti')
        )

        if tiku.login():
            provinces = args.provinces.split(',') if args.provinces else None
            tiku_stats = tiku.download_papers(args.type, provinces)
            logger.info(f"\n📊 题库真题: {tiku_stats['downloaded']} 下载, {tiku_stats['skipped']} 跳过, {tiku_stats['failed']} 失败")
        else:
            logger.error("登录失败，跳过题库下载")

    logger.info("\n🏁 全部完成!")


if __name__ == '__main__':
    main()
