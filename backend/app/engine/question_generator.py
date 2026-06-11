"""
CCG追问生成器
根据冲突生成追问
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.ccg_models import (
    Belief, Conflict, ConflictType, QuestionType
)
from ..graph.cognitive_graph import CognitiveGraph
from ..engine.llm_client import generate_structured


# ── Prompt模板 ────────────────────────────────────────────────


QUESTION_GENERATION_PROMPT = """你是一个正在辅导学弟学妹数学的大学生，性格温和但思维敏锐。你不会直接告诉答案，而是通过聊天帮他们自己想明白。

## 学生的情况
- 学生刚说了什么："{student_input}"
- 他内心的一个矛盾：{belief_a_proposition}（他自己对这个想法的信心：{belief_a_confidence}）
- 但实际应该是：{belief_b_proposition}
- 这个矛盾属于：{conflict_description}

## 学生状态
- 情绪：{emotional_state}
- 已经聊了{round_count}轮

## 你要做的事
用一句自然的话引导他注意到自己的矛盾。

说话风格：
- 像朋友聊天，不要像老师讲课
- 可以用"诶""那""可是""你想想"这样的口语词
- 可以表达好奇、惊讶、疑惑，像真人一样有情绪
- 不超过25个字
- 不要说"你确定吗"这种废话
- 不要先夸再转折（"不错，但是..."）
- 不要直接给答案
- 不要说"让我们一起来看看"这种AI味十足的话
- 如果学生之前犯了错但现在改对了，可以真诚地表达"诶对了！"这种认可

好的追问例子：
- "那如果系数变成100呢，你还试吗？"
- "诶，那x=2和x=3有什么共同点？"
- "你怎么知道试完了？"
- "因式分解你熟吗？"
- "那要是三次方程呢？"

请返回JSON格式。"""


QUESTION_SCHEMA = {
    "question": "string - 追问内容（口语化，不超过25字）",
    "question_type": "string - 追问类型",
    "reasoning": "string - 为什么这么说",
    "expected_effect": "string - 预期学生会怎么想"
}


# ── 追问类型决策器 ────────────────────────────────────────────────


class QuestionTypeDecider:
    """
    追问类型决策器
    根据冲突类型和学生状态选择追问类型
    """
    
    # 冲突类型到追问类型的映射
    CONFLICT_TO_QUESTION_TYPE = {
        ConflictType.LOGICAL: [
            QuestionType.GUIDE_DISCOVERY,
            QuestionType.COUNTEREXAMPLE
        ],
        ConflictType.BOUNDARY: [
            QuestionType.BOUNDARY_EXPLORE,
            QuestionType.GUIDE_DISCOVERY
        ],
        ConflictType.CONFIDENCE: [
            QuestionType.GUIDE_DISCOVERY,
            QuestionType.PATH_COMPARE
        ],
        ConflictType.PATH_DEPENDENCY: [
            QuestionType.PATH_COMPARE,
            QuestionType.DECOMPOSE
        ]
    }
    
    @staticmethod
    def decide(
        conflict: Conflict,
        emotional_state: str = "neutral",
        cognitive_load: float = 0.5,
        round_count: int = 0
    ) -> QuestionType:
        """
        决策追问类型
        
        Args:
            conflict: 冲突
            emotional_state: 情绪状态
            cognitive_load: 认知负荷
            round_count: 已追问轮次
            
        Returns:
            追问类型
        """
        # 获取候选追问类型
        candidates = QuestionTypeDecider.CONFLICT_TO_QUESTION_TYPE.get(
            conflict.type,
            [QuestionType.GUIDE_DISCOVERY]
        )
        
        # 根据学生状态调整
        if emotional_state in ["frustrated", "angry"]:
            # 高挫败状态，使用更温和的类型
            return QuestionType.DECOMPOSE
        
        if cognitive_load > 0.8:
            # 高认知负荷，使用拆解引导
            return QuestionType.DECOMPOSE
        
        if round_count > 3:
            # 已追问多轮，使用更直接的类型
            return QuestionType.COUNTEREXAMPLE
        
        # 默认返回第一个候选
        return candidates[0]


# ── 追问生成器 ────────────────────────────────────────────────


class QuestionGenerator:
    """
    追问生成器
    根据冲突生成追问
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.decider = QuestionTypeDecider()
    
    async def generate_question(
        self,
        conflict: Conflict,
        graph: CognitiveGraph,
        student_input: str = "",
        emotional_state: str = "neutral",
        cognitive_load: float = 0.5,
        round_count: int = 0,
        question_context: str = ""
    ) -> Dict[str, Any]:
        """
        生成追问
        
        Args:
            conflict: 冲突
            graph: 认知图谱
            student_input: 学生最新输入
            emotional_state: 情绪状态
            cognitive_load: 认知负荷
            round_count: 已追问轮次
            question_context: 题目上下文
            
        Returns:
            追问信息
        """
        # 获取冲突的信念
        belief_a = graph.get_belief(conflict.belief_a_id)
        belief_b = graph.get_belief(conflict.belief_b_id)
        
        if not belief_a or not belief_b:
            return self._fallback_question(conflict)
        
        # 决策追问类型
        question_type = self.decider.decide(
            conflict, emotional_state, cognitive_load, round_count
        )
        
        # 构建冲突描述
        conflict_description = self._build_conflict_description(
            conflict, belief_a, belief_b
        )
        
        # 构建prompt
        prompt = QUESTION_GENERATION_PROMPT.format(
            student_input=student_input or "（学生刚开口）",
            conflict_type=conflict.type.value,
            belief_a_proposition=belief_a.proposition,
            belief_a_confidence=belief_a.confidence,
            belief_b_proposition=belief_b.proposition,
            belief_b_confidence=belief_b.confidence,
            conflict_description=conflict_description,
            emotional_state=emotional_state,
            cognitive_load=cognitive_load,
            round_count=round_count,
            question_type=question_type.value
        )
        
        try:
            # 调用LLM生成
            result = await generate_structured(prompt, QUESTION_SCHEMA)
            
            # 验证和清理
            question = result.get("question", "").strip()
            if not question:
                return self._fallback_question(conflict, question_type)
            
            # 检查约束条件
            if not self._check_constraints(question):
                return self._fallback_question(conflict, question_type)
            
            return {
                "question": question,
                "question_type": question_type.value,
                "reasoning": result.get("reasoning", ""),
                "expected_effect": result.get("expected_effect", ""),
                "conflict_id": conflict.id,
                "conflict_type": conflict.type.value
            }
            
        except Exception as e:
            print(f"追问生成失败: {e}")
            return self._fallback_question(conflict, question_type)
    
    def _build_conflict_description(
        self,
        conflict: Conflict,
        belief_a: Belief,
        belief_b: Belief
    ) -> str:
        """构建冲突描述 - 口语化"""
        if conflict.type == ConflictType.LOGICAL:
            return f"他觉得'{belief_a.proposition}'，但其实应该是'{belief_b.proposition}'，这两个想法矛盾"
        elif conflict.type == ConflictType.BOUNDARY:
            return f"他把'{belief_a.proposition}'套用到了不太合适的场景"
        elif conflict.type == ConflictType.CONFIDENCE:
            return f"他对'{belief_a.proposition}'挺有信心，但实际上'{belief_b.proposition}'"
        elif conflict.type == ConflictType.PATH_DEPENDENCY:
            return f"他从不同角度得出了'{belief_a.proposition}'和'{belief_b.proposition}'，但推理前提不太对"
        else:
            return f"他的想法'{belief_a.proposition}'和实际情况'{belief_b.proposition}'有出入"
    
    def _check_constraints(self, question: str) -> bool:
        """检查追问约束条件"""
        # 长度检查
        if len(question) > 30:
            return False
        
        # 不评判
        judgment_words = ["错", "不对", "不应该", "不能这样"]
        for word in judgment_words:
            if word in question:
                return False
        
        # 不直接给答案
        answer_words = ["答案是", "应该等于", "正确的是"]
        for word in answer_words:
            if word in question:
                return False
        
        return True
    
    def _fallback_question(
        self,
        conflict: Conflict,
        question_type: Optional[QuestionType] = None
    ) -> Dict[str, Any]:
        """降级追问（规则引擎）- 自然口语化"""
        default_questions = {
            ConflictType.LOGICAL: "诶，这两个想法不会打架吗？",
            ConflictType.BOUNDARY: "这条件一直成立吗？",
            ConflictType.CONFIDENCE: "你再想想？",
            ConflictType.PATH_DEPENDENCY: "你这个前提哪来的？"
        }
        
        question = default_questions.get(conflict.type, "那你觉得呢？")
        
        return {
            "question": question,
            "question_type": (question_type or QuestionType.GUIDE_DISCOVERY).value,
            "reasoning": "降级追问",
            "expected_effect": "引导学生思考",
            "conflict_id": conflict.id,
            "conflict_type": conflict.type.value
        }


# ── 约束条件检查器 ────────────────────────────────────────────────


class ConstraintChecker:
    """
    约束条件检查器
    验证追问是否符合约束
    """
    
    @staticmethod
    def check(question: str) -> Dict[str, Any]:
        """
        检查追问约束
        
        Args:
            question: 追问内容
            
        Returns:
            检查结果
        """
        issues = []
        
        # 长度检查
        if len(question) > 20:
            issues.append(f"长度超过20字（当前{len(question)}字）")
        
        # 不评判
        judgment_words = ["错", "不对", "不应该", "不能这样"]
        for word in judgment_words:
            if word in question:
                issues.append(f"包含评判词汇：{word}")
        
        # 不直接给答案
        answer_words = ["答案是", "应该等于", "正确的是"]
        for word in answer_words:
            if word in question:
                issues.append(f"包含答案词汇：{word}")
        
        # 不先肯定再否定
        if "但是" in question or "不过" in question:
            if any(word in question for word in ["对", "好", "不错"]):
                issues.append("可能包含先肯定再否定的结构")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "length": len(question)
        }
