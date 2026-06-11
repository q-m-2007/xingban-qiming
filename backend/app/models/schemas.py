"""
星伴·启明 — Pydantic 数据模型
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── 请求模型 ────────────────────────────────────────────────


class QuestionRequest(BaseModel):
    """提交题目"""
    question: str = Field(..., description="题目文本")
    session_id: Optional[str] = Field(None, description="会话ID（首次提问留空，服务端自动生成）")


class AnswerRequest(BaseModel):
    """提交学生回答"""
    session_id: str = Field(..., description="会话ID")
    answer: str = Field(..., description="学生的回答文本")


# ── 响应模型 ────────────────────────────────────────────────


class FollowUpResponse(BaseModel):
    """追问响应"""
    session_id: str
    state: str
    action: str
    feedback: str
    hints: list[str] = []
    final: bool = False


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    service: str = "星伴·启明 AI 追问引擎"
    version: str = "0.1.0"
    knowledge_points_count: int = 0
    active_sessions: int = 0


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
