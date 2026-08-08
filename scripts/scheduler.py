#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/scheduler.py

轻量定时调度器：每 N 小时执行一次 auto_update.py --task all。
适用于无 cron/systemd 的容器环境，通过 nohup 常驻。

用法：
  nohup .venv/bin/python scripts/scheduler.py > /root/slb-scheduler.log 2>&1 &
"""
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTERVAL_HOURS = 6  # 每 6 小时更新一次
LOG = Path('/root/slb-scheduler.log')


def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG.open('a') as f:
        f.write(line + '\n')


def run_update():
    log("开始自动更新...")
    try:
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'auto_update.py'), '--task', 'all'],
            capture_output=True, text=True, timeout=1800
        )
        log(f"更新完成 returncode={result.returncode}")
        if result.stdout:
            for line in result.stdout.strip().splitlines()[-5:]:
                log(f"  {line}")
        if result.returncode != 0 and result.stderr:
            log(f"  STDERR: {result.stderr.strip()[-300:]}")
    except subprocess.TimeoutExpired:
        log("更新超时（1800s）")
    except Exception as e:
        log(f"更新异常: {e}")


def main():
    log(f"调度器启动，每 {INTERVAL_HOURS} 小时执行一次自动更新")
    # 启动后立即执行一次，然后按间隔循环
    while True:
        try:
            run_update()
        except Exception as e:
            log(f"调度器异常: {e}")
        time.sleep(INTERVAL_HOURS * 3600)


if __name__ == '__main__':
    main()
