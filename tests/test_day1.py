"""
Day 1 单元测试：数据模型 + 图结构 + 持久化
"""

import pytest
import sys
import os
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.ccg_models import (
    Belief, BeliefRelation, Conflict,
    BeliefType, RelationType, ConflictType, ConflictStatus
)
from app.graph.cognitive_graph import CognitiveGraph
from app.storage.sqlite_store import SQLiteStore


# ── 数据模型测试 ────────────────────────────────────────────────


class TestBelief:
    """测试信念模型"""
    
    def test_create_belief(self):
        """测试创建信念"""
        belief = Belief(
            proposition="x应该等于3",
            type=BeliefType.CONCEPT,
            confidence=0.8,
            source="student_input"
        )
        
        assert belief.proposition == "x应该等于3"
        assert belief.type == BeliefType.CONCEPT
        assert belief.confidence == 0.8
        assert belief.id is not None
        assert belief.activation_count == 1
    
    def test_activate_belief(self):
        """测试激活信念"""
        belief = Belief(
            proposition="移项需要变号",
            type=BeliefType.PROCEDURE
        )
        
        initial_count = belief.activation_count
        belief.activate()
        
        assert belief.activation_count == initial_count + 1
    
    def test_update_confidence(self):
        """测试更新置信度"""
        belief = Belief(
            proposition="等式两边同加减",
            type=BeliefType.CONCEPT,
            confidence=0.5
        )
        
        belief.update_confidence(0.8)
        assert belief.confidence == 0.8
        
        belief.update_confidence(1.5)  # 超出范围
        assert belief.confidence == 1.0
        
        belief.update_confidence(-0.5)  # 超出范围
        assert belief.confidence == 0.0
    
    def test_to_dict(self):
        """测试序列化"""
        belief = Belief(
            proposition="测试命题",
            type=BeliefType.HEURISTIC
        )
        
        data = belief.to_dict()
        
        assert data["proposition"] == "测试命题"
        assert data["type"] == "heuristic"
        assert "id" in data
        assert "timestamp" in data


class TestConflict:
    """测试冲突模型"""
    
    def test_create_conflict(self):
        """测试创建冲突"""
        conflict = Conflict(
            belief_a_id="belief-1",
            belief_b_id="belief-2",
            type=ConflictType.LOGICAL,
            severity=0.8,
            teaching_value=0.7
        )
        
        assert conflict.belief_a_id == "belief-1"
        assert conflict.type == ConflictType.LOGICAL
        assert conflict.status == ConflictStatus.ACTIVE
    
    def test_update_status(self):
        """测试更新状态"""
        conflict = Conflict(
            belief_a_id="belief-1",
            belief_b_id="belief-2",
            type=ConflictType.BOUNDARY
        )
        
        conflict.update_status(
            ConflictStatus.EXPOSED,
            action="追问暴露",
            result="学生正在思考"
        )
        
        assert conflict.status == ConflictStatus.EXPOSED
        assert len(conflict.history) == 1
        assert conflict.history[0]["action"] == "追问暴露"
    
    def test_calculate_priority(self):
        """测试计算优先级"""
        conflict = Conflict(
            belief_a_id="belief-1",
            belief_b_id="belief-2",
            type=ConflictType.LOGICAL,
            severity=0.8,
            teaching_value=0.7
        )
        
        priority = conflict.calculate_priority(
            student_readiness=1.0,
            novelty=1.0
        )
        
        assert priority == 0.8 * 0.7 * 1.0 * 1.0


# ── 认知图谱测试 ────────────────────────────────────────────────


class TestCognitiveGraph:
    """测试认知图谱"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.graph = CognitiveGraph("test-session-001")
    
    def test_add_belief(self):
        """测试添加信念"""
        belief = Belief(
            proposition="x=3",
            type=BeliefType.CONCEPT,
            confidence=0.8
        )
        
        belief_id = self.graph.add_belief(belief)
        
        assert belief_id in self.graph.beliefs
        assert self.graph.graph.has_node(belief_id)
        assert len(self.graph.beliefs) == 1
    
    def test_get_belief(self):
        """测试获取信念"""
        belief = Belief(
            proposition="移项变号",
            type=BeliefType.PROCEDURE
        )
        
        belief_id = self.graph.add_belief(belief)
        retrieved = self.graph.get_belief(belief_id)
        
        assert retrieved is not None
        assert retrieved.proposition == "移项变号"
    
    def test_update_belief(self):
        """测试更新信念"""
        belief = Belief(
            proposition="初始命题",
            type=BeliefType.CONCEPT,
            confidence=0.5
        )
        
        belief_id = self.graph.add_belief(belief)
        
        success = self.graph.update_belief(belief_id, {
            "confidence": 0.9,
            "proposition": "更新后的命题"
        })
        
        assert success is True
        
        updated = self.graph.get_belief(belief_id)
        assert updated.confidence == 0.9
        assert updated.proposition == "更新后的命题"
    
    def test_remove_belief(self):
        """测试删除信念"""
        belief = Belief(
            proposition="要删除的信念",
            type=BeliefType.CONCEPT
        )
        
        belief_id = self.graph.add_belief(belief)
        assert len(self.graph.beliefs) == 1
        
        success = self.graph.remove_belief(belief_id)
        
        assert success is True
        assert len(self.graph.beliefs) == 0
        assert not self.graph.graph.has_node(belief_id)
    
    def test_add_relation(self):
        """测试添加关系"""
        belief1 = Belief(proposition="等式性质", type=BeliefType.CONCEPT)
        belief2 = Belief(proposition="移项变号", type=BeliefType.PROCEDURE)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        relation = BeliefRelation(
            source_id=belief1.id,
            target_id=belief2.id,
            type=RelationType.IMPLIES,
            strength=0.9
        )
        
        relation_id = self.graph.add_relation(relation)
        
        assert relation_id in self.graph.relations
        assert self.graph.graph.has_edge(belief1.id, belief2.id)
    
    def test_add_relation_invalid_nodes(self):
        """测试添加关系时节点不存在"""
        relation = BeliefRelation(
            source_id="non-existent-1",
            target_id="non-existent-2",
            type=RelationType.CONTRADICTS
        )
        
        with pytest.raises(ValueError):
            self.graph.add_relation(relation)
    
    def test_find_similar_belief(self):
        """测试查找相似信念"""
        belief = Belief(
            proposition="x等于3",
            type=BeliefType.CONCEPT
        )
        
        self.graph.add_belief(belief)
        
        # 精确匹配
        found = self.graph.find_similar_belief("x等于3")
        assert found is not None
        assert found.id == belief.id
        
        # 不匹配
        not_found = self.graph.find_similar_belief("y等于5")
        assert not_found is None
    
    def test_get_contradicting_beliefs(self):
        """测试获取矛盾信念"""
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        relation = BeliefRelation(
            source_id=belief1.id,
            target_id=belief2.id,
            type=RelationType.CONTRADICTS
        )
        self.graph.add_relation(relation)
        
        contradicting = self.graph.get_contradicting_beliefs(belief1.id)
        
        assert len(contradicting) == 1
        assert contradicting[0].id == belief2.id
    
    def test_add_conflict(self):
        """测试添加冲突"""
        belief1 = Belief(proposition="A", type=BeliefType.CONCEPT)
        belief2 = Belief(proposition="B", type=BeliefType.CONCEPT)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        conflict = Conflict(
            belief_a_id=belief1.id,
            belief_b_id=belief2.id,
            type=ConflictType.LOGICAL,
            severity=0.8
        )
        
        conflict_id = self.graph.add_conflict(conflict)
        
        assert conflict_id in self.graph.conflicts
        assert len(self.graph.get_active_conflicts()) == 1
    
    def test_get_highest_priority_conflict(self):
        """测试获取最高优先级冲突"""
        belief1 = Belief(proposition="A", type=BeliefType.CONCEPT)
        belief2 = Belief(proposition="B", type=BeliefType.CONCEPT)
        belief3 = Belief(proposition="C", type=BeliefType.CONCEPT)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        self.graph.add_belief(belief3)
        
        # 低优先级冲突
        conflict1 = Conflict(
            belief_a_id=belief1.id,
            belief_b_id=belief2.id,
            type=ConflictType.LOGICAL,
            severity=0.3,
            teaching_value=0.3
        )
        self.graph.add_conflict(conflict1)
        
        # 高优先级冲突
        conflict2 = Conflict(
            belief_a_id=belief2.id,
            belief_b_id=belief3.id,
            type=ConflictType.LOGICAL,
            severity=0.9,
            teaching_value=0.9
        )
        self.graph.add_conflict(conflict2)
        
        highest = self.graph.get_highest_priority_conflict()
        
        assert highest is not None
        assert highest.id == conflict2.id
    
    def test_get_statistics(self):
        """测试获取统计信息"""
        belief1 = Belief(proposition="A", type=BeliefType.CONCEPT, confidence=0.8)
        belief2 = Belief(proposition="B", type=BeliefType.PROCEDURE, confidence=0.6)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        stats = self.graph.get_statistics()
        
        assert stats["total_beliefs"] == 2
        assert stats["total_relations"] == 0
        assert stats["belief_types"]["concept"] == 1
        assert stats["belief_types"]["procedure"] == 1
        assert stats["avg_confidence"] == 0.7
    
    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        belief = Belief(proposition="测试", type=BeliefType.CONCEPT)
        self.graph.add_belief(belief)
        
        # 序列化
        data = self.graph.to_dict()
        
        # 反序列化
        restored = CognitiveGraph.from_dict(data)
        
        assert restored.session_id == self.graph.session_id
        assert len(restored.beliefs) == 1
        assert restored.beliefs[belief.id].proposition == "测试"


# ── 持久化测试 ────────────────────────────────────────────────


class TestSQLiteStore:
    """测试SQLite持久化"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.db_path = "/tmp/test_ccg.db"
        self.store = SQLiteStore(self.db_path)
        
        # 清理旧数据
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.store = SQLiteStore(self.db_path)
    
    def teardown_method(self):
        """每个测试后清理"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_save_and_load_session(self):
        """测试保存和加载会话"""
        graph = CognitiveGraph("test-session-001")
        
        belief = Belief(proposition="x=3", type=BeliefType.CONCEPT)
        graph.add_belief(belief)
        
        # 保存
        success = self.store.save_session(graph)
        assert success is True
        
        # 加载
        loaded = self.store.load_session("test-session-001")
        
        assert loaded is not None
        assert loaded.session_id == "test-session-001"
        assert len(loaded.beliefs) == 1
        assert loaded.beliefs[belief.id].proposition == "x=3"
    
    def test_load_nonexistent_session(self):
        """测试加载不存在的会话"""
        loaded = self.store.load_session("non-existent")
        assert loaded is None
    
    def test_delete_session(self):
        """测试删除会话"""
        graph = CognitiveGraph("test-session-002")
        self.store.save_session(graph)
        
        success = self.store.delete_session("test-session-002")
        assert success is True
        
        loaded = self.store.load_session("test-session-002")
        assert loaded is None
    
    def test_list_sessions(self):
        """测试列出会话"""
        # 创建多个会话
        for i in range(3):
            graph = CognitiveGraph(f"session-{i}")
            self.store.save_session(graph)
        
        sessions = self.store.list_sessions()
        
        assert len(sessions) == 3
        assert all("session_id" in s for s in sessions)
    
    def test_save_with_conflicts(self):
        """测试保存包含冲突的图谱"""
        graph = CognitiveGraph("test-session-003")
        
        belief1 = Belief(proposition="A", type=BeliefType.CONCEPT)
        belief2 = Belief(proposition="B", type=BeliefType.CONCEPT)
        
        graph.add_belief(belief1)
        graph.add_belief(belief2)
        
        conflict = Conflict(
            belief_a_id=belief1.id,
            belief_b_id=belief2.id,
            type=ConflictType.LOGICAL,
            severity=0.8
        )
        graph.add_conflict(conflict)
        
        # 保存
        self.store.save_session(graph)
        
        # 加载
        loaded = self.store.load_session("test-session-003")
        
        assert len(loaded.conflicts) == 1
        conflict_id = list(loaded.conflicts.keys())[0]
        assert loaded.conflicts[conflict_id].severity == 0.8


# ── 运行测试 ────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
