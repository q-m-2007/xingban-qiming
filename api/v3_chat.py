"""
V3 API：统一教学管道
融合13条铁律的七层架构
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline import UnifiedTeachingPipeline
from llm_client import LLMClient

router = APIRouter(prefix="/api/v3", tags=["V3 Unified Pipeline"])

# 全局管道实例
_pipeline: Optional[UnifiedTeachingPipeline] = None


def get_pipeline() -> UnifiedTeachingPipeline:
    """获取或创建管道实例"""
    global _pipeline
    if _pipeline is None:
        llm_client = LLMClient()
        _pipeline = UnifiedTeachingPipeline(llm_client=llm_client)
    return _pipeline


class ChatMessage(BaseModel):
    student_id: str
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


class DiagnosisResponse(BaseModel):
    student_id: str
    diagnosis: str


@router.post("/chat/message", response_model=ChatResponse)
async def v3_chat_message(msg: ChatMessage):
    """
    V3统一教学管道聊天接口

    融合13条铁律：
    - P1快速响应：三级匹配（哈希→规则→LLM）
    - P2逻辑准：知识图谱推导
    - P3定位准：三重定位
    - P4自进化：三层进化机制
    - P5存储优：分层存储+增量更新
    - P6可扩展：自动扩展知识库
    - E1不替思考：ThinkingBoundary检查
    - E2服从节奏：PacingController
    - E3不优化短期：独立解决率权重0.4
    - E4防过拟合：3次证据才确认
    - E5沉默权：5种沉默条件
    - E6老化检测：知识库保质期
    - E7可解释性：每个决策有报告
    """
    try:
        pipeline = get_pipeline()
        result = await pipeline.process(
            student_id=msg.student_id,
            student_input=msg.message,
            topic=msg.topic,
            conversation_history=[],
        )

        return ChatResponse(
            response=result["response"],
            topic=result["topic"],
            state=result["state"],
            emotion=result["emotion"],
            inquiry_type=result["inquiry_type"],
            explanation=result["explanation"],
            performance=result["performance"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/student/{student_id}/diagnosis", response_model=DiagnosisResponse)
async def get_student_diagnosis(student_id: str):
    """获取学生诊断报告"""
    try:
        pipeline = get_pipeline()
        diagnosis = pipeline.get_student_diagnosis(student_id)

        return DiagnosisResponse(
            student_id=student_id,
            diagnosis=diagnosis,
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
        "principles": {
            "performance": ["P1快速响应", "P2逻辑准", "P3定位准", "P4自进化", "P5存储优", "P6可扩展"],
            "ethics": ["E1不替思考", "E2服从节奏", "E3不优化短期", "E4防过拟合", "E5沉默权", "E6老化检测", "E7可解释性"],
        },
    }
