#!/bin/bash
# SLB 一键部署脚本
# 用法: bash deploy.sh

set -e

echo "=========================================="
echo "  SLB (申论帮) 一键部署"
echo "=========================================="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "[!] Docker 未安装，正在安装..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    echo "[+] Docker 安装完成"
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "[!] docker-compose 未安装，正在安装..."
    apt-get update && apt-get install -y docker-compose-plugin
    echo "[+] docker-compose 安装完成"
fi

# Generate .env if not exists
if [ ! -f .env ]; then
    echo "[*] 生成生产环境配置..."
    SECRET_KEY=$(openssl rand -hex 32)
    JWT_SECRET=$(openssl rand -hex 32)

    cat > .env << EOF
SECRET_KEY=${SECRET_KEY}
JWT_SECRET=${JWT_SECRET}

DATABASE_PATH=data/slb.db

LLM_API_KEY=your-api-key-here
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

FLASK_DEBUG=false
FLASK_ENV=production
ENV=production
PORT=8790
EOF
    echo "[+] .env 已生成，请编辑 .env 填入 LLM_API_KEY"
    echo "    命令: nano .env"
    echo ""
    read -p "填入 API Key 后按回车继续..." _
fi

# Create data directory
mkdir -p data

# Build and start
echo "[*] 构建 Docker 镜像..."
docker compose build

echo "[*] 启动服务..."
docker compose up -d

# Wait for health check
echo "[*] 等待服务启动..."
sleep 5

for i in {1..10}; do
    if curl -sf http://localhost:8790/health > /dev/null 2>&1; then
        echo "[+] 服务启动成功！"
        echo ""
        echo "=========================================="
        echo "  访问地址: http://$(hostname -I | awk '{print $1}'):8790"
        echo "  管理后台: http://$(hostname -I | awk '{print $1}'):8790/admin"
        echo "  默认管理员: admin / admin123456"
        echo "  请登录后立即修改默认密码！"
        echo "=========================================="
        exit 0
    fi
    echo "    等待中... ($i/10)"
    sleep 3
done

echo "[!] 服务启动超时，请检查日志:"
echo "    docker compose logs -f"
exit 1
