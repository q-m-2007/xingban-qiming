"""
统一教学管道（Unified Teaching Pipeline）
七层架构：Gate → Perception → Validation → Reasoning → Personalization → Decision → Execution → Evolution
融合13条铁律（6性能 + 7教育伦理）
"""

import time
from typing import Dict, List, Optional
from datetime import datetime

from .models import (
    PipelineContext, GateResult, PerceptionResult, ValidationResult,
    ReasoningResult, PersonalizationResult, DecisionResult,
    ExecutionResult, CognitiveProfile, StudentState
)
from .gate import GateLayer
from .perception import PerceptionLayer
from .validation import ValidationLayer
from .reasoning import ReasoningLayer
from .personalization import PersonalizationLayer
from .decision import DecisionLayer
from .execution import ExecutionLayer
from .evolution import EvolutionLayer


class UnifiedTeachingPipeline:
    """统一教学管道"""

    def __init__(self, llm_client=None, db_module=None):
        # 初始化各层
        self.gate = GateLayer()
        self.perception = PerceptionLayer()
        self.validation = ValidationLayer()
        self.reasoning = ReasoningLayer()
        self.personalization = PersonalizationLayer(db_module=db_module)
        self.decision = DecisionLayer()
        self.execution = ExecutionLayer()
        self.evolution = EvolutionLayer()

        # 学生画像存储
        self.profiles: Dict[str, CognitiveProfile] = {}

        # LLM客户端（可选）
        self.llm_client = llm_client

        # 数据库模块（可选）
        self.db = db_module

    async def process(self, student_id: str, student_input: str,
                      topic: str = "",
                      conversation_history: List[str] = None) -> Dict:
        """
        处理学生输入，返回教学决策

        Args:
            student_id: 学生ID
            student_input: 学生输入
            topic: 当前话题
            conversation_history: 对话历史

        Returns:
            包含回复和元数据的字典
        """
        start_time = time.time()

        # 创建上下文
        context = PipelineContext(
            student_id=student_id,
            student_input=student_input,
            conversation_history=conversation_history or [],
            topic=topic,
        )

        # 获取或创建画像
        context.profile = self._get_or_create_profile(student_id)

        # ═══════════════════════════════════════════
        # 第0层：守门层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.gate = self.gate.process(context)
        context.layer_times["gate"] = (time.time() - layer_start) * 1000

        # 检查是否应该回复
        if not context.gate.should_respond:
            return self._build_response(context, "")

        # ═══════════════════════════════════════════
        # 第1层：感知层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.perception = self.perception.process(context)
        context.layer_times["perception"] = (time.time() - layer_start) * 1000

        # 更新话题
        if not topic and context.perception.match.topic != "unknown":
            context.topic = context.perception.match.topic

        # ═══════════════════════════════════════════
        # 第2层：验证层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.validation = self.validation.process(context)
        context.layer_times["validation"] = (time.time() - layer_start) * 1000

        # ═══════════════════════════════════════════
        # 第3层：推理层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.reasoning = self.reasoning.process(context)
        context.layer_times["reasoning"] = (time.time() - layer_start) * 1000

        # ═══════════════════════════════════════════
        # 第4层：个性化层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.personalization = self.personalization.process(context)
        context.layer_times["personalization"] = (time.time() - layer_start) * 1000

        # 检查是否需要等待
        if context.personalization.pacing.should_wait:
            return self._build_response(context, "")

        # ═══════════════════════════════════════════
        # 第5层：决策层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.decision = self.decision.process(context)
        context.layer_times["decision"] = (time.time() - layer_start) * 1000

        # ═══════════════════════════════════════════
        # 第6层：执行层
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context.execution = self.execution.process(context)
        context.layer_times["execution"] = (time.time() - layer_start) * 1000

        # ═══════════════════════════════════════════
        # 第7层：进化层（后台异步）
        # ═══════════════════════════════════════════
        layer_start = time.time()
        context = self.evolution.process(context)
        context.layer_times["evolution"] = (time.time() - layer_start) * 1000

        # 更新画像
        if context.profile:
            self.profiles[student_id] = context.profile

        # 追问计数（per-student）
        if context.decision and context.decision.inquiry_type.value != "silence":
            self.gate.increment_question_count(student_id)
        else:
            self.gate.reset_question_count(student_id)

        # 构建响应
        total_time = (time.time() - start_time) * 1000
        return self._build_response(
            context,
            context.execution.final_response if context.execution else "",
            total_time
        )

    def _get_or_create_profile(self, student_id: str) -> CognitiveProfile:
        """获取或创建学生画像"""
        if student_id not in self.profiles:
            self.profiles[student_id] = CognitiveProfile(
                student_id=student_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        return self.profiles[student_id]

    def _build_response(self, context: PipelineContext,
                        response: str,
                        total_time: float = 0.0) -> Dict:
        """构建响应"""
        return {
            "response": response,
            "topic": context.topic,
            "state": context.reasoning.state.value if context.reasoning else "unknown",
            "emotion": context.perception.emotion if context.perception else "neutral",
            "inquiry_type": context.decision.inquiry_type.value if context.decision else "none",
            "explanation": context.execution.explanation if context.execution else "",
            "performance": {
                "total_ms": round(total_time, 1),
                "layer_times": {
                    k: round(v, 1) for k, v in context.layer_times.items()
                },
            },
            "debug": {
                "gate": {
                    "should_respond": context.gate.should_respond if context.gate else True,
                    "silence_reason": context.gate.silence_reason if context.gate else "",
                },
                "perception": {
                    "match_level": context.perception.match.level if context.perception else 0,
                    "match_confidence": context.perception.match.confidence if context.perception else 0,
                    "beliefs_count": len(context.perception.beliefs) if context.perception else 0,
                },
                "validation": {
                    "misconceptions_count": len(context.validation.misconceptions) if context.validation else 0,
                    "prerequisite_ok": context.validation.prerequisite_ok if context.validation else True,
                },
                "reasoning": {
                    "conflicts_count": len(context.reasoning.conflicts) if context.reasoning else 0,
                    "top_conflict": context.reasoning.top_conflict.description if context.reasoning and context.reasoning.top_conflict else "",
                },
                "personalization": {
                    "difficulty": round(context.personalization.difficulty_level, 2) if context.personalization else 0.5,
                    "inertia_detected": context.personalization.inertia_detected if context.personalization else False,
                },
            },
        }

    def get_student_diagnosis(self, student_id: str) -> str:
        """获取学生诊断报告"""
        profile = self._get_or_create_profile(student_id)

        lines = [f"=== Student Diagnosis Report ===\n"]
        lines.append(f"[Basic Info]")
        lines.append(f"  Student ID: {student_id}")
        lines.append(f"  Data Points: {profile.data_points}")
        lines.append(f"  Profile Confidence: {profile.confidence:.0%}\n")

        lines.append("[Cognitive Profile]")
        dimensions = [
            ("visual", "Visual"), ("verbal", "Verbal"), ("kinesthetic", "Kinesthetic"),
            ("inductive", "Inductive"), ("deductive", "Deductive"), ("analogical", "Analogical"),
            ("fast_jump", "Fast Jump"), ("rigorous", "Rigorous"), ("divergent", "Divergent"),
            ("abstract_reasoning", "Abstract"), ("challenge_drive", "Challenge"),
            ("persistence", "Persistence"), ("metacognition", "Metacog"),
            ("collaboration", "Collab"), ("creativity", "Creative"),
        ]

        for dim, label in dimensions:
            val = getattr(profile, dim, 0.5)
            filled = int(val * 20)
            bar = '#' * filled + '-' * (20 - filled)
            lines.append(f"  {label:12s} [{bar}] {val:.0%}")

        return '\n'.join(lines)
