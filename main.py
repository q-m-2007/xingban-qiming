"""
星伴·启明 AI教学引擎
FastAPI主应用

集成算法：
- V3: 统一教学管道：融合13条铁律的七层架构
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

from api.v3_chat import router as v3_chat_router
from api.auth import router as auth_router

app = FastAPI(
    title="星伴·启明",
    description="AI智能数学辅导 - 四年级数学",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(auth_router)
app.include_router(v3_chat_router)

# 静态文件
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# 页面路由
@app.get("/", response_class=HTMLResponse)
async def index():
    """首页"""
    return FileResponse(str(static_dir / "index.html"))


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """登录页"""
    return FileResponse(str(static_dir / "login.html"))


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """对话页"""
    return FileResponse(str(static_dir / "chat.html"))


@app.get("/diagnosis", response_class=HTMLResponse)
async def diagnosis_page():
    """诊断页"""
    return FileResponse(str(static_dir / "diagnosis.html"))


@app.get("/api/info")
async def api_info():
    """API信息"""
    return {
        "name": "星伴·启明",
        "version": "1.0.0",
        "domain": "xingban.xinxunai.com.cn",
        "endpoints": {
            "chat": "/api/v3/chat/message",
            "login": "/api/auth/login",
            "register": "/api/auth/register",
            "diagnosis": "/api/v3/student/diagnosis",
        },
    }
