"""
V1 API：CCG追问引擎（兼容保留）
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/api/chat", tags=["V1 Chat"])


class ChatMessage(BaseModel):
    student_id: str
    message: str
    topic: str = "general"
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    topic: str
    state: str


@router.post("/message", response_model=ChatResponse)
async def chat_message(msg: ChatMessage):
    """V1聊天接口（兼容保留）"""
    return ChatResponse(
        response="请使用V3接口 /api/v3/chat/message",
        topic=msg.topic,
        state="redirect",
    )
