"""
Day 3 单元测试：冲突检测模块
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.ccg_models import (
    Belief, BeliefRelation, Conflict,
    BeliefType, RelationType, ConflictType, ConflictStatus
)
from app.graph.cognitive_graph import CognitiveGraph
from app.engine.conflict_detector import ConflictDetector, ConflictRanker


# ── 冲突检测器测试 ────────────────────────────────────────────────


class TestConflictDetector:
    """测试冲突检测器"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.detector = ConflictDetector()
        self.graph = CognitiveGraph("test-session")
    
    def test_detect_logical_conflicts_direct(self):
        """测试检测直接逻辑矛盾"""
        # 创建两个矛盾的信念
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.8)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.7)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        # 添加矛盾关系
        relation = BeliefRelation(
            source_id=belief1.id,
            target_id=belief2.id,
            type=RelationType.CONTRADICTS
        )
        self.graph.add_relation(relation)
        
        # 检测冲突
        conflicts = self.detector.detect_logical_conflicts(self.graph)
        
        assert len(conflicts) == 1
        assert conflicts[0].type == ConflictType.LOGICAL
        assert conflicts[0].belief_a_id == belief1.id
        assert conflicts[0].belief_b_id == belief2.id
    
    def test_detect_logical_conflicts_via_implication(self):
        """测试通过蕴含关系检测逻辑矛盾"""
        # 创建信念链：A蕴含P，B蕴含¬P
        belief_a = Belief(proposition="等式性质", type=BeliefType.CONCEPT, confidence=0.8)
        belief_p = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.7)
        belief_b = Belief(proposition="移项规则", type=BeliefType.PROCEDURE, confidence=0.75)
        belief_not_p = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.6)
        
        self.graph.add_belief(belief_a)
        self.graph.add_belief(belief_p)
        self.graph.add_belief(belief_b)
        self.graph.add_belief(belief_not_p)
        
        # 添加蕴含关系
        rel1 = BeliefRelation(
            source_id=belief_a.id,
            target_id=belief_p.id,
            type=RelationType.IMPLIES
        )
        rel2 = BeliefRelation(
            source_id=belief_b.id,
            target_id=belief_not_p.id,
            type=RelationType.IMPLIES
        )
        # 添加矛盾关系
        rel3 = BeliefRelation(
            source_id=belief_p.id,
            target_id=belief_not_p.id,
            type=RelationType.CONTRADICTS
        )
        
        self.graph.add_relation(rel1)
        self.graph.add_relation(rel2)
        self.graph.add_relation(rel3)
        
        # 检测冲突
        conflicts = self.detector.detect_logical_conflicts(self.graph)
        
        # 应该检测到A和B之间的冲突
        assert len(conflicts) >= 1
    
    def test_detect_confidence_conflicts(self):
        """测试检测置信度矛盾"""
        # 创建语义矛盾的信念
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.6)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.7)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        # 检测冲突
        conflicts = self.detector.detect_confidence_conflicts(self.graph)
        
        assert len(conflicts) == 1
        assert conflicts[0].type == ConflictType.CONFIDENCE
    
    def test_detect_confidence_conflicts_low_confidence(self):
        """测试低置信度不检测为冲突"""
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.3)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.4)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        conflicts = self.detector.detect_confidence_conflicts(self.graph)
        
        assert len(conflicts) == 0
    
    def test_detect_no_conflicts(self):
        """测试无冲突情况"""
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.8)
        belief2 = Belief(proposition="y=5", type=BeliefType.CONCEPT, confidence=0.7)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        conflicts = self.detector.detect_all_conflicts(self.graph)
        
        assert len(conflicts) == 0
    
    def test_detect_conflicts_avoids_duplicates(self):
        """测试避免重复检测"""
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.8)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.7)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        relation = BeliefRelation(
            source_id=belief1.id,
            target_id=belief2.id,
            type=RelationType.CONTRADICTS
        )
        self.graph.add_relation(relation)
        
        # 第一次检测
        conflicts1 = self.detector.detect_logical_conflicts(self.graph)
        assert len(conflicts1) == 1
        
        # 第二次检测（不应重复）
        conflicts2 = self.detector.detect_logical_conflicts(self.graph)
        assert len(conflicts2) == 0  # 已存在，不再创建
    
    def test_calculate_severity(self):
        """测试计算严重度"""
        belief1 = Belief(proposition="x=3", type=BeliefType.CONCEPT, confidence=0.8)
        belief2 = Belief(proposition="x=5", type=BeliefType.CONCEPT, confidence=0.7)
        
        self.graph.add_belief(belief1)
        self.graph.add_belief(belief2)
        
        relation = BeliefRelation(
            source_id=belief1.id,
            target_id=belief2.id,
            type=RelationType.CONTRADICTS
        )
        self.graph.add_relation(relation)
        
        conflicts = self.detector.detect_logical_conflicts(self.graph)
        
        assert len(conflicts) == 1
        
        # 验证严重度计算
        expected_severity = 0.8 * 0.7 * 1.0  # confidence_a * confidence_b * clarity
        assert abs(conflicts[0].severity - expected_severity) < 0.01


# ── 冲突排序器测试 ────────────────────────────────────────────────


class TestConflictRanker:
    """测试冲突排序器"""
    
    def test_rank_conflicts_empty(self):
        """测试空冲突列表"""
        ranked = ConflictRanker.rank_conflicts([])
        assert ranked == []
    
    def test_rank_conflicts_single(self):
        """测试单个冲突"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL,
            severity=0.8,
            teaching_value=0.7
        )
        
        ranked = ConflictRanker.rank_conflicts([conflict])
        
        assert len(ranked) == 1
        assert ranked[0][0] == conflict
        assert ranked[0][1] > 0
    
    def test_rank_conflicts_multiple(self):
        """测试多个冲突排序"""
        conflict1 = Conflict(
            belief_a_id="a1",
            belief_b_id="b1",
            type=ConflictType.LOGICAL,
            severity=0.3,
            teaching_value=0.3
        )
        conflict2 = Conflict(
            belief_a_id="a2",
            belief_b_id="b2",
            type=ConflictType.LOGICAL,
            severity=0.9,
            teaching_value=0.9
        )
        
        ranked = ConflictRanker.rank_conflicts([conflict1, conflict2])
        
        assert len(ranked) == 2
        # conflict2应该排在前面（优先级更高）
        assert ranked[0][0] == conflict2
        assert ranked[1][0] == conflict1
    
    def test_rank_conflicts_max_limit(self):
        """测试最大数量限制"""
        conflicts = [
            Conflict(
                belief_a_id=f"a{i}",
                belief_b_id=f"b{i}",
                type=ConflictType.LOGICAL,
                severity=0.5,
                teaching_value=0.5
            )
            for i in range(10)
        ]
        
        ranked = ConflictRanker.rank_conflicts(conflicts, max_conflicts=3)
        
        assert len(ranked) == 3
    
    def test_rank_conflicts_novelty(self):
        """测试新颖度影响"""
        # 同类型的冲突
        conflict1 = Conflict(
            belief_a_id="a1",
            belief_b_id="b1",
            type=ConflictType.LOGICAL,
            severity=0.8,
            teaching_value=0.8
        )
        conflict2 = Conflict(
            belief_a_id="a2",
            belief_b_id="b2",
            type=ConflictType.LOGICAL,
            severity=0.8,
            teaching_value=0.8
        )
        conflict3 = Conflict(
            belief_a_id="a3",
            belief_b_id="b3",
            type=ConflictType.BOUNDARY,
            severity=0.8,
            teaching_value=0.8
        )
        
        ranked = ConflictRanker.rank_conflicts([conflict1, conflict2, conflict3])
        
        # BOUNDARY类型应该排在前面（更新颖）
        assert ranked[0][0].type == ConflictType.BOUNDARY


# ── 运行测试 ────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
