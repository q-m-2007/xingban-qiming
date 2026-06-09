"""
V2 API：CPTE+CPPA集成引擎（兼容保留）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/v2", tags=["V2 Chat"])


class V2ChatMessage(BaseModel):
    student_id: str
    message: str
    topic: str = "general"
    session_id: str = ""


class V2ChatResponse(BaseModel):
    response: str
    topic: str
    state: str
    strategy: str


@router.post("/chat/message", response_model=V2ChatResponse)
async def v2_chat_message(msg: V2ChatMessage):
    """V2聊天接口（兼容保留）"""
    return V2ChatResponse(
        response="请使用V3接口 /api/v3/chat/message",
        topic=msg.topic,
        state="redirect",
        strategy="redirect",
    )
