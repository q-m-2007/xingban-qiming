#!/bin/bash
# 星伴·启明 Python版部署脚本

set -e

echo "=== 星伴·启明 部署脚本 ==="

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "安装Docker Compose..."
    pip install docker-compose
fi

# 设置环境变量
if [ -f .env ]; then
    source .env
fi

if [ -z "$LLM_API_KEY" ]; then
    echo "请设置 LLM_API_KEY 环境变量"
    exit 1
fi

# 构建并启动
echo "构建Docker镜像..."
docker-compose build

echo "启动服务..."
docker-compose up -d

echo "=== 部署完成 ==="
echo "API地址: https://qiming.xinxunai.com.cn"
echo "健康检查: https://qiming.xinxunai.com.cn/api/v3/health"
