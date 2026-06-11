"""
Day 4 单元测试：追问生成模块
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.ccg_models import (
    Belief, Conflict, ConflictType, QuestionType, BeliefType
)
from app.graph.cognitive_graph import CognitiveGraph
from app.engine.question_generator import (
    QuestionTypeDecider, QuestionGenerator, ConstraintChecker
)


# ── 追问类型决策器测试 ────────────────────────────────────────────────


class TestQuestionTypeDecider:
    """测试追问类型决策器"""
    
    def test_decide_logical_conflict(self):
        """测试逻辑冲突的追问类型"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL
        )
        
        question_type = QuestionTypeDecider.decide(conflict)
        
        assert question_type in [QuestionType.GUIDE_DISCOVERY, QuestionType.COUNTEREXAMPLE]
    
    def test_decide_boundary_conflict(self):
        """测试边界冲突的追问类型"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.BOUNDARY
        )
        
        question_type = QuestionTypeDecider.decide(conflict)
        
        assert question_type in [QuestionType.BOUNDARY_EXPLORE, QuestionType.GUIDE_DISCOVERY]
    
    def test_decide_frustrated_state(self):
        """测试高挫败状态的追问类型"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL
        )
        
        question_type = QuestionTypeDecider.decide(
            conflict,
            emotional_state="frustrated"
        )
        
        assert question_type == QuestionType.DECOMPOSE
    
    def test_decide_high_cognitive_load(self):
        """测试高认知负荷的追问类型"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL
        )
        
        question_type = QuestionTypeDecider.decide(
            conflict,
            cognitive_load=0.9
        )
        
        assert question_type == QuestionType.DECOMPOSE
    
    def test_decide_many_rounds(self):
        """测试多轮追问后的追问类型"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL
        )
        
        question_type = QuestionTypeDecider.decide(
            conflict,
            round_count=5
        )
        
        assert question_type == QuestionType.COUNTEREXAMPLE


# ── 约束条件检查器测试 ────────────────────────────────────────────────


class TestConstraintChecker:
    """测试约束条件检查器"""
    
    def test_check_valid_question(self):
        """测试有效追问"""
        question = "这两个想法矛盾吗？"
        result = ConstraintChecker.check(question)
        
        assert result["valid"] is True
        assert len(result["issues"]) == 0
    
    def test_check_too_long(self):
        """测试过长的追问"""
        question = "这是一个非常非常非常非常非常非常非常长的追问"
        result = ConstraintChecker.check(question)
        
        assert result["valid"] is False
        assert any("长度" in issue for issue in result["issues"])
    
    def test_check_judgment_word(self):
        """测试包含评判词汇"""
        question = "你错了，再想想"
        result = ConstraintChecker.check(question)
        
        assert result["valid"] is False
        assert any("评判" in issue for issue in result["issues"])
    
    def test_check_answer_word(self):
        """测试包含答案词汇"""
        question = "答案是3，对吗？"
        result = ConstraintChecker.check(question)
        
        assert result["valid"] is False
        assert any("答案" in issue for issue in result["issues"])
    
    def test_check_affirm_then_negate(self):
        """测试先肯定再否定"""
        question = "对，但是你再想想"
        result = ConstraintChecker.check(question)
        
        assert result["valid"] is False
        assert any("肯定" in issue for issue in result["issues"])


# ── 追问生成器测试 ────────────────────────────────────────────────


class TestQuestionGenerator:
    """测试追问生成器"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.generator = QuestionGenerator()
        self.graph = CognitiveGraph("test-session")
    
    def test_fallback_question_logical(self):
        """测试降级追问：逻辑冲突"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.LOGICAL
        )
        
        result = self.generator._fallback_question(conflict)
        
        assert "矛盾" in result["question"]
        assert result["conflict_type"] == "logical"
    
    def test_fallback_question_boundary(self):
        """测试降级追问：边界冲突"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.BOUNDARY
        )
        
        result = self.generator._fallback_question(conflict)
        
        assert "条件" in result["question"]
    
    def test_fallback_question_confidence(self):
        """测试降级追问：置信度冲突"""
        conflict = Conflict(
            belief_a_id="a",
            belief_b_id="b",
            type=ConflictType.CONFIDENCE
        )
        
        result = self.generator._fallback_question(conflict)
        
        assert "确定" in result["question"]
    
    def test_build_conflict_description_logical(self):
        """测试构建逻辑冲突描述"""
        belief_a = Belief(proposition="x=3", type=BeliefType.CONCEPT)
        belief_b = Belief(proposition="x=5", type=BeliefType.CONCEPT)
        
        conflict = Conflict(
            belief_a_id=belief_a.id,
            belief_b_id=belief_b.id,
            type=ConflictType.LOGICAL
        )
        
        description = self.generator._build_conflict_description(
            conflict, belief_a, belief_b
        )
        
        assert "x=3" in description
        assert "x=5" in description
        assert "矛盾" in description
    
    def test_check_constraints_valid(self):
        """测试约束检查：有效"""
        question = "你再想想？"
        result = self.generator._check_constraints(question)
        
        assert result is True
    
    def test_check_constraints_too_long(self):
        """测试约束检查：过长"""
        question = "这是一个非常非常非常非常非常非常非常非常非常非常非常长的追问"
        result = self.generator._check_constraints(question)
        
        assert result is False
    
    def test_check_constraints_judgment(self):
        """测试约束检查：评判"""
        question = "你错了"
        result = self.generator._check_constraints(question)
        
        assert result is False


# ── 运行测试 ────────────────────────────────────────────────


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
