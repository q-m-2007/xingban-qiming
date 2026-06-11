#!/bin/bash
# 星伴·启明 CCG追问引擎 启动脚本

set -e

echo "🚀 启动星伴·启明 CCG追问引擎..."
echo ""

# 检查Python环境
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "📥 安装依赖..."
pip install -q networkx pydantic fastapi uvicorn httpx pytest

# 创建数据目录
echo "📁 创建数据目录..."
mkdir -p data

# 运行测试
echo "🧪 运行单元测试..."
python -m pytest tests/ -v --tb=short

if [ $? -ne 0 ]; then
    echo "❌ 测试失败，请修复后重试"
    exit 1
fi

echo ""
echo "✅ 所有测试通过！"
echo ""

# 启动服务
echo "🌟 启动服务..."
echo "📖 API文档: http://localhost:8000/docs"
echo "🌐 前端界面: http://localhost:8000"
echo "❤️  健康检查: http://localhost:8000/api/health"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
