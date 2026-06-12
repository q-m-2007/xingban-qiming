"""
星伴·启明 AI教学引擎
FastAPI主应用
"""

import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path, override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from api.v3_chat import router as v3_chat_router
from api.auth import router as auth_router
import database

app = FastAPI(
    title="星伴·启明",
    description="AI智能数学辅导 - 四年级数学",
    version="1.0.0",
)

# CORS配置 - 限制来源
ALLOWED_ORIGINS = [
    "https://xingban.xinxunai.com.cn",
    "http://xingban.xinxunai.com.cn",
    "http://124.220.62.96",
    "http://localhost:8000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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


# 启动事件
@app.on_event("startup")
async def startup():
    logger.info("星伴·启明 启动中...")
    database.init_db()
    logger.info("数据库初始化完成")


# 页面路由
@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(str(static_dir / "index.html"))


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    return FileResponse(str(static_dir / "login.html"))


@app.get("/register", response_class=HTMLResponse)
async def register_page():
    return FileResponse(str(static_dir / "register.html"))


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    return FileResponse(str(static_dir / "chat.html"))


@app.get("/diagnosis", response_class=HTMLResponse)
async def diagnosis_page():
    return FileResponse(str(static_dir / "diagnosis.html"))


@app.get("/api/info")
async def api_info():
    return {
        "name": "星伴·启明",
        "version": "1.0.0",
        "domain": "xingban.xinxunai.com.cn",
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"}
    )
