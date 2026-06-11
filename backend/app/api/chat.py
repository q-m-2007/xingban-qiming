"""
CCG对话API
RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, Optional

from ..models.ccg_models import (
    ChatRequest, ChatResponse, GraphResponse,
    HealthResponse, ErrorResponse
)
from ..engine.conversation_manager_v2 import ConversationManagerV2
from ..storage.sqlite_store import SQLiteStore


# 创建路由器
router = APIRouter(prefix="/api", tags=["chat"])

# 全局对话管理器实例
_manager: Optional[ConversationManagerV2] = None


def get_manager() -> ConversationManagerV2:
    """获取对话管理器单例"""
    global _manager
    if _manager is None:
        _manager = ConversationManagerV2()
    return _manager


# ── 对话接口 ────────────────────────────────────────────────


@router.post("/chat/message", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    """
    发送学生消息
    
    接收学生的输入，返回AI的追问响应
    """
    try:
        manager = get_manager()
        response = await manager.process_message(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/graph", response_model=GraphResponse)
async def get_session_graph(session_id: str):
    """
    获取会话的认知图谱
    
    返回指定会话的信念、关系和冲突
    """
    try:
        manager = get_manager()
        graph = manager.get_session_graph(session_id)
        
        if not graph:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return GraphResponse(
            session_id=session_id,
            beliefs=[b.to_dict() for b in graph.beliefs.values()],
            relations=[r.to_dict() for r in graph.relations.values()],
            conflicts=[c.to_dict() for c in graph.conflicts.values()],
            statistics=graph.get_statistics()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/statistics")
async def get_session_statistics(session_id: str):
    """
    获取会话统计信息
    
    返回指定会话的统计数据
    """
    try:
        manager = get_manager()
        stats = manager.get_session_statistics(session_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 图谱接口 ────────────────────────────────────────────────


@router.get("/graph/{session_id}/beliefs")
async def get_beliefs(session_id: str, belief_type: Optional[str] = None):
    """
    获取信念列表
    
    可按类型过滤
    """
    try:
        manager = get_manager()
        graph = manager.get_session_graph(session_id)
        
        if not graph:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        beliefs = list(graph.beliefs.values())
        
        if belief_type:
            from ..models.ccg_models import BeliefType
            try:
                bt = BeliefType(belief_type)
                beliefs = [b for b in beliefs if b.type == bt]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的信念类型: {belief_type}")
        
        return {
            "session_id": session_id,
            "beliefs": [b.to_dict() for b in beliefs],
            "total": len(beliefs)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph/{session_id}/conflicts")
async def get_conflicts(session_id: str, status: Optional[str] = None):
    """
    获取冲突列表
    
    可按状态过滤
    """
    try:
        manager = get_manager()
        graph = manager.get_session_graph(session_id)
        
        if not graph:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        conflicts = list(graph.conflicts.values())
        
        if status:
            from ..models.ccg_models import ConflictStatus
            try:
                cs = ConflictStatus(status)
                conflicts = [c for c in conflicts if c.status == cs]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的冲突状态: {status}")
        
        return {
            "session_id": session_id,
            "conflicts": [c.to_dict() for c in conflicts],
            "total": len(conflicts)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 健康检查 ────────────────────────────────────────────────


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    健康检查
    
    返回服务状态
    """
    return HealthResponse(
        status="ok",
        service="星伴·启明 CCG追问引擎",
        version="1.0.0",
        algorithm="CCG (Cognitive Conflict Graph)",
        active_sessions=len(get_manager().active_sessions)
    )


# ── 会话管理 ────────────────────────────────────────────────


@router.get("/sessions")
async def list_sessions(limit: int = 100):
    """
    列出所有会话
    """
    try:
        store = SQLiteStore()
        sessions = store.list_sessions(limit)
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话
    """
    try:
        store = SQLiteStore()
        success = store.delete_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return {"message": "会话已删除", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
