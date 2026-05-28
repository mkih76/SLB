#!/bin/bash
# SLB 数据库自动备份脚本
# 用法: bash scripts/backup_db.sh
# 建议通过 crontab 每日执行: 0 3 * * * cd /path/to/SLB && bash scripts/backup_db.sh

set -e

BACKUP_DIR="data/backups"
DB_PATH="data/slb.db"
MAX_BACKUPS=7  # 保留最近7天的备份

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/slb_${TIMESTAMP}.db"

# 使用 sqlite3 的 .backup 命令（安全备份，不会锁定数据库）
if command -v sqlite3 &> /dev/null; then
    sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"
else
    # 如果没有 sqlite3 命令，使用 cp（需要确保数据库未被写入）
    cp "$DB_PATH" "$BACKUP_FILE"
fi

# 压缩备份
gzip "$BACKUP_FILE"

echo "[$(date)] Backup created: ${BACKUP_FILE}.gz"

# 清理旧备份，只保留最近 MAX_BACKUPS 个
cd "$BACKUP_DIR"
ls -t slb_*.db.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm -f

echo "[$(date)] Cleanup done. Kept latest $MAX_BACKUPS backups."
