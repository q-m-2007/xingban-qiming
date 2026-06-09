"""
星伴·启明 AI教学引擎
FastAPI主应用

集成算法：
- V1: CCG（认知冲突图谱）：追问引擎
- V2: CPTE+CPPA：个性化教学引擎
- V3: 统一教学管道：融合13条铁律的七层架构
"""

import os
import sys
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent / "env_file"
if env_path.exists():
    load_dotenv(env_path, override=True)
else:
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path, override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.chat import router as chat_router
from api.v2_chat import router as v2_chat_router
from api.v3_chat import router as v3_chat_router


# 创建FastAPI应用
app = FastAPI(
    title="星伴·启明 AI教学引擎",
    description="基于统一教学管道的个性化AI教学系统（融合13条铁律）",
    version="3.0.0",
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
app.include_router(chat_router)      # V1: CCG追问引擎（兼容）
app.include_router(v2_chat_router)   # V2: CPTE+CPPA集成引擎（兼容）
app.include_router(v3_chat_router)   # V3: 统一教学管道（推荐）


# 根路由
@app.get("/")
async def root():
    """根路由"""
    return {
        "service": "星伴·启明 AI教学引擎",
        "version": "3.0.0",
        "algorithms": {
            "V1": "CCG (Cognitive Conflict Graph) - 追问引擎（兼容）",
            "V2": "CPTE + CPPA - 个性化教学引擎（兼容）",
            "V3": "统一教学管道 - 融合13条铁律的七层架构（推荐）",
        },
        "principles": {
            "performance": [
                "P1快速响应：三级匹配（哈希→规则→LLM）",
                "P2逻辑准：知识图谱推导",
                "P3定位准：三重定位",
                "P4自进化：三层进化机制",
                "P5存储优：分层存储+增量更新",
                "P6可扩展：自动扩展知识库",
            ],
            "ethics": [
                "E1不替思考：ThinkingBoundary检查",
                "E2服从节奏：PacingController",
                "E3不优化短期：独立解决率权重0.4",
                "E4防过拟合：3次证据才确认",
                "E5沉默权：5种沉默条件",
                "E6老化检测：知识库保质期",
                "E7可解释性：每个决策有报告",
            ],
        },
        "docs": "/docs",
        "endpoints": {
            "v3_chat": "/api/v3/chat/message",
            "v3_diagnosis": "/api/v3/student/{student_id}/diagnosis",
            "v3_health": "/api/v3/health",
            "v1_chat": "/api/chat/message（兼容）",
            "v2_chat": "/api/v2/chat/message（兼容）",
        },
    }
