"""
粉笔网盘公开资料抓取器（无需登录）

发现过程：
  粉笔网盘 (www.fenbi.com/fpr/doc-user-v2/dir/xxx) 是 SPA 页面，
  通过 Playwright 拦截网络请求发现其底层 API：
    - 目录列表: https://webapi.fenbi.com/doc/api/publs/{dir_id}
    - 文件下载: https://nodestatic.fbstatic.cn/pan/downloads/{cospath}

  这两个端点完全公开，不需要任何认证。

用法：
    from src.crawler.fenbi_public import FenbiPublicScraper
    scraper = FenbiPublicScraper(output_dir="./data/fenbi_shenlun")
    scraper.download_dir(28695, "2024国考申论密卷")
"""

import json
import logging
import os
import subprocess
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ============ 常量 ============

API_BASE = "https://webapi.fenbi.com/doc/api/publs/{did}?secret=***&av=100&kav=100&hav=100&app=web"
DOWNLOAD_BASE = "https://nodestatic.fbstatic.cn/pan/downloads"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 申论相关目录 ID（通过枚举+筛选发现）
SHENLUN_DIRS = [
    (28695, "2024国考申论密卷"),
    (28704, "2024浙江省考申论密卷"),
    (40326, "2025国考申论解析"),
    (40328, "2025省考申论解析"),
    (22202, "历年国考真题"),
    (35591, "三色笔记"),
    (25001, "申论基础"),
    (25030, "申论资料包"),
    (32741, "2025申论热点范文"),
    (32267, "申论高分必背素材"),
    (32266, "申论名言1000句"),
    (28690, "申论金词金句"),
    (36828, "粉笔辅导员资料"),
]

# 过滤关键词
KEYWORDS = ['申论', '真题', '范文', '国考', '省考', '联考', '三色笔记', '行测']


class FenbiPublicScraper:
    """粉笔网盘公开资料抓取器"""

    def __init__(self, output_dir: str = "./data/fenbi_shenlun"):
        self.output_dir = output_dir
        self._curl_available = None

    def _check_curl(self) -> bool:
        if self._curl_available is None:
            try:
                subprocess.run(["curl", "--version"], capture_output=True, timeout=5)
                self._curl_available = True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._curl_available = False
        return self._curl_available

    def fetch_dir(self, dir_id: int) -> Optional[dict]:
        """获取目录内容（公开API，无需登录）"""
        url = API_BASE.format(did=dir_id)
        try:
            result = subprocess.run(
                ["curl", "-s", "--connect-timeout", "10", url, "-H", f"User-Agent: {UA}"],
                capture_output=True, timeout=20
            )
            data = json.loads(result.stdout)
            return data.get('data') if data.get('code') == 1 else None
        except Exception as e:
            logger.warning(f"获取目录 {dir_id} 失败: {e}")
            return None

    def collect_files(self, dir_id: int, path: str = "", depth: int = 0, max_depth: int = 3) -> list:
        """递归收集目录下所有文件"""
        if depth > max_depth:
            return []

        data = self.fetch_dir(dir_id)
        if not data:
            return []

        files = []
        for f in data.get('files', []):
            files.append({
                'name': f['name'],
                'cospath': f['cospath'],
                'size': int(f['size']),
                'path': path,
                'dir_id': dir_id,
            })

        for sub in data.get('dirs', []):
            sub_path = f"{path}/{sub['name']}" if path else sub['name']
            files.extend(self.collect_files(sub['id'], sub_path, depth + 1, max_depth))

        return files

    def filter_shenlun(self, files: list) -> list:
        """过滤出申论相关文件"""
        return [
            f for f in files
            if any(kw in f['name'] or kw in f['path'] for kw in KEYWORDS)
        ]

    def download_file(self, cospath: str, save_path: str) -> int:
        """下载单个文件，返回文件大小(bytes)"""
        url = f"{DOWNLOAD_BASE}/{cospath}?time={int(time.time() * 1000)}"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        result = subprocess.run(
            ["curl", "-sL", "-o", save_path, "-w", "%{http_code}", url,
             "-H", f"User-Agent: {UA}", "-H", "Referer: https://www.fenbi.com/",
             "--connect-timeout", "15", "--max-time", "120"],
            capture_output=True, timeout=130
        )

        status = result.stdout.decode().strip()
        if status == '200' and os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
            return os.path.getsize(save_path)

        if os.path.exists(save_path):
            os.remove(save_path)
        raise Exception(f"下载失败: HTTP {status}")

    def download_dir(self, dir_id: int, label: str = "", filter_kw: bool = True) -> dict:
        """
        下载整个目录

        Args:
            dir_id: 粉笔网盘目录 ID
            label: 本地子目录名
            filter_kw: 是否只下载申论相关文件

        Returns:
            {"total": N, "downloaded": N, "failed": N, "skipped": N, "size_mb": float}
        """
        if not self._check_curl():
            raise RuntimeError("需要 curl 命令")

        logger.info(f"收集目录 {dir_id} ({label})...")
        files = self.collect_files(dir_id, label)

        if filter_kw and label not in ['历年国考真题', '三色笔记']:
            files = self.filter_shenlun(files)

        # 去重
        seen = set()
        unique = []
        for f in files:
            if f['cospath'] not in seen:
                seen.add(f['cospath'])
                unique.append(f)

        stats = {"total": len(unique), "downloaded": 0, "failed": 0, "skipped": 0, "size_mb": 0.0}

        for f in unique:
            safe_name = f['name'].replace('/', '_').replace('\\', '_')
            save_path = os.path.join(self.output_dir, f['path'], safe_name)

            if os.path.exists(save_path):
                stats["skipped"] += 1
                continue

            try:
                size = self.download_file(f['cospath'], save_path)
                stats["downloaded"] += 1
                stats["size_mb"] += size / 1024 / 1024
                logger.info(f"  ✅ {safe_name} ({size / 1024 / 1024:.1f}MB)")
                time.sleep(0.2)  # 礼貌间隔
            except Exception as e:
                stats["failed"] += 1
                logger.warning(f"  ❌ {safe_name}: {e}")

        return stats

    def download_all(self) -> dict:
        """下载所有预设的申论目录"""
        total_stats = {"dirs": 0, "downloaded": 0, "failed": 0, "skipped": 0, "size_mb": 0.0}

        for dir_id, label in SHENLUN_DIRS:
            logger.info(f"\n=== {label} (id={dir_id}) ===")
            stats = self.download_dir(dir_id, label)
            total_stats["dirs"] += 1
            total_stats["downloaded"] += stats["downloaded"]
            total_stats["failed"] += stats["failed"]
            total_stats["skipped"] += stats["skipped"]
            total_stats["size_mb"] += stats["size_mb"]

        return total_stats

    def scan_range(self, start: int, end: int) -> list:
        """
        扫描目录 ID 范围，发现新的公开分享目录

        Returns:
            [{"id": N, "name": str, "files": N, "dirs": N}, ...]
        """
        found = []
        for did in range(start, end + 1):
            data = self.fetch_dir(did)
            if data:
                fc = len(data.get('files', []))
                dc = len(data.get('dirs', []))
                if fc > 0 or dc > 0:
                    found.append({
                        "id": did,
                        "name": data.get('name', ''),
                        "files": fc,
                        "dirs": dc,
                    })
                    logger.info(f"  发现目录 {did}: {data.get('name', '')} ({fc}文件, {dc}子目录)")
            time.sleep(0.1)
        return found


# ============ CLI 入口 ============

if __name__ == '__main__':
    import sys

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    scraper = FenbiPublicScraper()

    if len(sys.argv) > 1 and sys.argv[1] == 'scan':
        start = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
        end = int(sys.argv[3]) if len(sys.argv) > 3 else 20050
        print(f"扫描目录 {start}-{end}...")
        found = scraper.scan_range(start, end)
        print(f"\n找到 {len(found)} 个目录")
    else:
        stats = scraper.download_all()
        print(f"\n🏁 完成: {stats['downloaded']} 下载, {stats['skipped']} 跳过, {stats['failed']} 失败")
        print(f"📊 总大小: {stats['size_mb']:.1f}MB")
