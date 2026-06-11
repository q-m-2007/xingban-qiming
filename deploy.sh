#!/bin/bash
# 星伴·启明 部署脚本

set -e

echo "=== 星伴·启明 部署脚本 ==="

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "安装Docker..."
    curl -fsSL https://get.docker.com | sh
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
sudo docker compose build

echo "启动服务..."
sudo docker compose up -d

# 配置Nginx
echo "配置Nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/xingban
sudo ln -sf /etc/nginx/sites-available/xingban /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

echo "=== 部署完成 ==="
echo "网站地址: https://xingban.xinxunai.com.cn"
echo "健康检查: https://xingban.xinxunai.com.cn/api/v3/health"
