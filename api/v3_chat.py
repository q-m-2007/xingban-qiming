"""
V3 API：统一教学管道
融合13条铁律的七层架构
集成LLM和数据库
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline import UnifiedTeachingPipeline
from llm_client import LLMClient
import database
import auth

router = APIRouter(prefix="/api/v3", tags=["V3 Unified Pipeline"])

_pipeline: Optional[UnifiedTeachingPipeline] = None
_llm_client: Optional[LLMClient] = None


def get_llm() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


def get_pipeline() -> UnifiedTeachingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = UnifiedTeachingPipeline(llm_client=get_llm(), db_module=database)
    return _pipeline


class ChatMessage(BaseModel):
    message: str
    topic: str = ""
    session_id: str = ""


class ChatResponse(BaseModel):
    response: str
    topic: str
    state: str
    emotion: str
    inquiry_type: str
    explanation: str
    performance: Dict
    session_id: str


class DiagnosisResponse(BaseModel):
    student_id: str
    diagnosis: str
    stats: Dict


@router.post("/chat/message", response_model=ChatResponse)
async def v3_chat_message(msg: ChatMessage, user: dict = Depends(auth.get_current_user)):
    """
    V3统一教学管道聊天接口
    需要登录
    """
    try:
        user_id = user["user_id"]
        session_id = msg.session_id or str(uuid.uuid4())

        # 获取历史对话
        history_rows = database.get_conversation_history(user_id, session_id, limit=10)
        history = [r["content"] for r in history_rows if r["role"] == "student"]

        # 调用管道
        pipeline = get_pipeline()
        result = await pipeline.process(
            student_id=str(user_id),
            student_input=msg.message,
            topic=msg.topic,
            conversation_history=history,
        )

        # 保存学生消息
        database.save_message(
            user_id=user_id,
            session_id=session_id,
            role="student",
            content=msg.message,
            topic=result.get("topic", ""),
            state=result.get("state", ""),
            emotion=result.get("emotion", ""),
        )

        # 如果管道没有回复（沉默），用LLM生成
        response_text = result.get("response", "")
        if not response_text:
            llm = get_llm()
            try:
                system_prompt = """你是星伴·启明，一个AI数学辅导老师，专教四年级数学。
你的教学原则：
1. 不直接告诉学生答案，引导他们自己思考
2. 用提问的方式帮助学生理解
3. 语言简洁，适合小学生理解
4. 鼓励学生，不批评"""
                response_text = await llm.chat(
                    prompt=msg.message,
                    system=system_prompt,
                    temperature=0.7,
                )
            except Exception:
                response_text = "让我想想这个问题...你能再说说你的想法吗？"

        # 保存AI回复
        database.save_message(
            user_id=user_id,
            session_id=session_id,
            role="assistant",
            content=response_text,
            topic=result.get("topic", ""),
            state=result.get("state", ""),
        )

        # 保存学习记录（如果检测到答题）
        topic = result.get("topic", "")
        state = result.get("state", "")
        if topic and state in ["exploring", "partial_stuck", "deep_stuck"]:
            # 判断是否答对（简化逻辑：如果状态是exploring且没有误解，认为答对）
            is_correct = state == "exploring" and not result.get("debug", {}).get("validation", {}).get("misconceptions_count", 0)
            database.save_learning_record(
                user_id=user_id,
                topic=topic,
                question=msg.message,
                answer=response_text,
                is_correct=is_correct,
                time_spent=result.get("performance", {}).get("total_ms", 0) / 1000,
                difficulty=result.get("debug", {}).get("personalization", {}).get("difficulty", 0.5),
            )

        return ChatResponse(
            response=response_text,
            topic=result.get("topic", ""),
            state=result.get("state", ""),
            emotion=result.get("emotion", ""),
            inquiry_type=result.get("inquiry_type", ""),
            explanation=result.get("explanation", ""),
            performance=result.get("performance", {}),
            session_id=session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/chat/sessions")
async def get_sessions(user: dict = Depends(auth.get_current_user)):
    """获取会话列表"""
    sessions = database.get_user_sessions(user["user_id"])
    return {"sessions": sessions}


@router.get("/chat/history/{session_id}")
async def get_history(session_id: str, user: dict = Depends(auth.get_current_user)):
    """获取对话历史"""
    history = database.get_conversation_history(user["user_id"], session_id, limit=50)
    return {"history": history}


@router.get("/student/diagnosis", response_model=DiagnosisResponse)
async def get_diagnosis(user: dict = Depends(auth.get_current_user)):
    """获取学习诊断报告"""
    try:
        user_id = user["user_id"]
        pipeline = get_pipeline()
        diagnosis = pipeline.get_student_diagnosis(str(user_id))
        stats = database.get_learning_stats(user_id)

        return DiagnosisResponse(
            student_id=str(user_id),
            diagnosis=diagnosis,
            stats=stats,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "version": "3.0.0",
        "algorithm": "Unified Teaching Pipeline",
        "domain": "xingban.xinxunai.com.cn",
    }
