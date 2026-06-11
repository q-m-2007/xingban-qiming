"""
Day 5 单元测试：对话管理 + API
"""

import pytest
import sys
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.ccg_models import (
    ChatRequest, ChatResponse, BeliefType
)
from app.engine.conversation_manager import ConversationManager, ConversationState
from app.storage.sqlite_store import SQLiteStore


# ── 对话管理器测试 ────────────────────────────────────────────────


class TestConversationManager:
    """测试对话管理器"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.db_path = "/tmp/test_conversation.db"
        self.store = SQLiteStore(self.db_path)
        self.manager = ConversationManager(self.store)
    
    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_get_or_create_session_new(self):
        """测试创建新会话"""
        graph = self.manager._get_or_create_session("test-session-1")
        
        assert graph is not None
        assert graph.session_id == "test-session-1"
        assert "test-session-1" in self.manager.active_sessions
    
    def test_get_or_create_session_existing(self):
        """测试获取已有会话"""
        # 创建会话
        graph1 = self.manager._get_or_create_session("test-session-2")
        
        # 再次获取
        graph2 = self.manager._get_or_create_session("test-session-2")
        
        assert graph1 is graph2
    
    def test_estimate_student_readiness(self):
        """测试估算学生就绪度"""
        from app.graph.cognitive_graph import CognitiveGraph
        
        graph = CognitiveGraph("test")
        
        # 无冲突
        readiness = self.manager._estimate_student_readiness(graph)
        assert readiness == 1.0
    
    def test_estimate_emotional_state_neutral(self):
        """测试估算情绪状态：中性"""
        state = self.manager._estimate_emotional_state("x等于3")
        assert state == "neutral"
    
    def test_estimate_emotional_state_frustrated(self):
        """测试估算情绪状态：挫败"""
        state = self.manager._estimate_emotional_state("这道题太难了，我不会")
        assert state == "frustrated"
    
    def test_estimate_emotional_state_positive(self):
        """测试估算情绪状态：积极"""
        state = self.manager._estimate_emotional_state("我明白了")
        assert state == "positive"
    
    def test_estimate_cognitive_load(self):
        """测试估算认知负荷"""
        from app.graph.cognitive_graph import CognitiveGraph
        from app.models.ccg_models import Belief
        
        graph = CognitiveGraph("test")
        
        # 空图谱
        load = self.manager._estimate_cognitive_load(graph)
        assert load == 0.0
        
        # 添加信念
        for i in range(5):
            belief = Belief(proposition=f"信念{i}", type=BeliefType.CONCEPT)
            graph.add_belief(belief)
        
        load = self.manager._estimate_cognitive_load(graph)
        assert 0 < load <= 1.0
    
    def test_calculate_thinking_time(self):
        """测试计算思考时间"""
        from app.graph.cognitive_graph import CognitiveGraph
        
        graph = CognitiveGraph("test")
        
        # 低负荷
        time = self.manager._calculate_thinking_time(graph)
        assert time == 10
    
    def test_get_conversation_state(self):
        """测试获取对话状态"""
        from app.graph.cognitive_graph import CognitiveGraph
        
        graph = CognitiveGraph("test")
        
        state = self.manager._get_conversation_state(graph)
        assert state == ConversationState.ACTIVE
    
    def test_generate_general_response(self):
        """测试生成一般性回复"""
        response = self.manager._generate_general_response("测试输入")
        
        assert isinstance(response, str)
        assert len(response) > 0


# ── API测试 ────────────────────────────────────────────────


class TestAPI:
    """测试API接口"""
    
    def setup_method(self):
        """每个测试前初始化"""
        from fastapi.testclient import TestClient
        from app.main import app
        
        self.client = TestClient(app)
    
    def test_root(self):
        """测试根路由"""
        response = self.client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "CCG" in data["service"]
    
    def test_health_check(self):
        """测试健康检查"""
        response = self.client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "CCG" in data["algorithm"]
    
    def test_list_sessions(self):
        """测试列出会话"""
        response = self.client.get("/api/sessions")
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
    
    def test_send_message(self):
        """测试发送消息"""
        request_data = {
            "student_input": "x等于3",
            "context": {
                "grade": "high_school",
                "subject": "math"
            }
        }
        
        response = self.client.post("/api/chat/message", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "ai_response" in data
        assert "beliefs_extracted" in data
    
    def test_get_session_graph(self):
        """测试获取会话图谱"""
        # 先创建会话
        request_data = {
            "student_input": "x等于3",
            "context": {
                "grade": "high_school",
                "subject": "math"
            }
        }
        response = self.client.post("/api/chat/message", json=request_data)
        session_id = response.json()["session_id"]
        
        # 获取图谱
        response = self.client.get(f"/api/chat/{session_id}/graph")
        
        assert response.status_code == 200
        data = response.json()
        assert "beliefs" in data
        assert "relations" in data
        assert "conflicts" in data
    
    def test_get_session_statistics(self):
        """测试获取会话统计"""
        # 先创建会话
        request_data = {
            "student_input": "x等于3",
            "context": {
                "grade": "high_school",
                "subject": "math"
            }
        }
        response = self.client.post("/api/chat/message", json=request_data)
        session_id = response.json()["session_id"]
        
        # 获取统计
        response = self.client.get(f"/api/chat/{session_id}/statistics")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_beliefs" in data
    
    def test_get_beliefs(self):
        """测试获取信念列表"""
        # 先创建会话
        request_data = {
            "student_input": "x等于3",
            "context": {
                "grade": "high_school",
                "subject": "math"
            }
        }
        response = self.client.post("/api/chat/message", json=request_data)
        session_id = response.json()["session_id"]
        
        # 获取信念
        response = self.client.get(f"/api/graph/{session_id}/beliefs")
        
        assert response.status_code == 200
        data = response.json()
        assert "beliefs" in data
        assert "total" in data
    
    def test_get_conflicts(self):
        """测试获取冲突列表"""
        # 先创建会话
        request_data = {
            "student_input": "x等于3",
            "context": {
                "grade": "high_school",
                "subject": "math"
            }
        }
        response = self.client.post("/api/chat/message", json=request_data)
        session_id = response.json()["session_id"]
        
        # 获取冲突
        response = self.client.get(f"/api/graph/{session_id}/conflicts")
        
        assert response.status_code == 200
        data = response.json()
        assert "conflicts" in data
        assert "total" in data


# ── 运行测试 ────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
