"""
星伴·启明 AI教学引擎
FastAPI主应用

集成算法：
- CCG（认知冲突图谱）：V1追问引擎
- CPTE（认知相变引擎）：相变检测、能量景观
- CPPA（认知画像引擎）：学生画像、教学策略
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router
from .api.v2_chat import router as v2_chat_router


# 创建FastAPI应用
app = FastAPI(
    title="星伴·启明 AI教学引擎",
    description="基于CPTE+CPPA双算法的个性化AI教学系统",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat_router)      # V1: CCG追问引擎
app.include_router(v2_chat_router)   # V2: CPTE+CPPA集成引擎


# 根路由
@app.get("/")
async def root():
    """根路由"""
    return {
        "service": "星伴·启明 AI教学引擎",
        "version": "2.0.0",
        "algorithms": {
            "V1": "CCG (Cognitive Conflict Graph) - 追问引擎",
            "V2": "CPTE + CPPA - 个性化教学引擎"
        },
        "docs": "/docs",
        "endpoints": {
            "v1_chat": "/api/chat/message",
            "v2_chat": "/api/v2/chat/message",
            "v2_diagnosis": "/api/v2/chat/{session_id}/diagnosis",
            "v2_method_recommend": "/api/v2/method/recommend",
            "v2_learning_path": "/api/v2/chat/{session_id}/path",
            "v2_generate_methods": "/api/v2/method/generate?topic=..."
        }
    }
