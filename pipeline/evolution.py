"""
第7层：进化层（Evolution Layer）
职责：画像更新 + 误解演化 + 知识库扩展 + 策略优化 + 老化检测 + 过拟合防护
铁律：P4自进化 + E6老化检测 + E4防过拟合 + E3不优化短期
"""

import math
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .models import (
    CognitiveProfile, Misconception, MisconceptionState,
    PipelineContext, ExecutionResult, StudentState
)

logger = logging.getLogger(__name__)


class ProfileUpdater:
    """贝叶斯画像更新器（P4自进化）"""

    def update(self, profile: CognitiveProfile,
               context: PipelineContext) -> CognitiveProfile:
        """贝叶斯更新学生画像"""
        if not context.perception or not context.reasoning:
            return profile

        # 贝叶斯更新公式：posterior = (likelihood × prior) / normalizer
        state = context.reasoning.state
        emotion = context.perception.emotion

        # 更新相关维度
        if state == StudentState.EXPLORING:
            profile = self._update_dimension(profile, "persistence", 0.1)
            profile = self._update_dimension(profile, "challenge_drive", 0.05)
        elif state == StudentState.FRUSTRATED:
            profile = self._update_dimension(profile, "persistence", -0.1)
        elif state == StudentState.CONCEPT_ERROR:
            profile = self._update_dimension(profile, "metacognition", -0.05)

        if emotion == "curious":
            profile = self._update_dimension(profile, "challenge_drive", 0.05)
            profile = self._update_dimension(profile, "creativity", 0.05)
        elif emotion == "frustrated":
            profile = self._update_dimension(profile, "challenge_drive", -0.05)

        # 更新数据点数
        profile.data_points += 1
        profile.confidence = min(1.0, 0.3 + profile.data_points * 0.02)
        profile.updated_at = datetime.now()

        return profile

    def _update_dimension(self, profile: CognitiveProfile,
                          dimension: str, delta: float) -> CognitiveProfile:
        """贝叶斯更新单个维度"""
        prior = getattr(profile, dimension, 0.5)

        # 贝叶斯更新
        likelihood = 0.7 if delta > 0 else 0.3
        posterior = (likelihood * prior) / (
            likelihood * prior + (1 - likelihood) * (1 - prior)
        )

        # 应用增量
        new_value = posterior + delta
        new_value = min(1.0, max(0.0, new_value))

        setattr(profile, dimension, new_value)
        return profile


class MisconceptionEvolver:
    """误解演化状态机（P4自进化）"""

    # 状态转移规则
    TRANSITIONS = {
        MisconceptionState.ACTIVE: {
            "evidence_decreased": MisconceptionState.FADING,
            "correct_response": MisconceptionState.FADING,
        },
        MisconceptionState.FADING: {
            "no_evidence": MisconceptionState.RESOLVED,
            "error_recurred": MisconceptionState.RECURRING,
        },
        MisconceptionState.RESOLVED: {
            "error_recurred": MisconceptionState.RECURRING,
        },
        MisconceptionState.RECURRING: {
            "correct_response": MisconceptionState.FADING,
        },
    }

    def evolve(self, misconceptions: List[Misconception],
               context: PipelineContext) -> List[Misconception]:
        """演化误解状态"""
        evolved = []
        for mis in misconceptions:
            new_state = self._determine_next_state(mis, context)
            if new_state != mis.state:
                mis.state = new_state
                mis.last_seen = datetime.now()
            evolved.append(mis)
        return evolved

    def _determine_next_state(self, mis: Misconception,
                              context: PipelineContext) -> MisconceptionState:
        """确定下一个状态"""
        state = context.reasoning.state if context.reasoning else StudentState.EXPLORING

        if mis.state == MisconceptionState.ACTIVE:
            if state == StudentState.EXPLORING:
                return MisconceptionState.FADING
        elif mis.state == MisconceptionState.FADING:
            if state == StudentState.CONCEPT_ERROR:
                return MisconceptionState.RECURRING
            # 检查是否长时间没有证据
            if mis.last_seen:
                days_since = (datetime.now() - mis.last_seen).days
                if days_since > 7:
                    return MisconceptionState.RESOLVED
        elif mis.state == MisconceptionState.RESOLVED:
            if state == StudentState.CONCEPT_ERROR:
                return MisconceptionState.RECURRING

        return mis.state


class KnowledgeBaseExpander:
    """知识库扩展器（P6可扩展）"""

    def __init__(self):
        self.expansion_log: List[Dict] = []

    def check_and_expand(self, context: PipelineContext) -> Optional[Dict]:
        """检查是否需要扩展知识库"""
        if not context.perception:
            return None

        match = context.perception.match

        # 匹配置信度低，可能需要新知识
        if match.confidence < 0.5 and match.level == 3:
            expansion = {
                "type": "new_topic",
                "topic": match.topic,
                "question_type": match.question_type,
                "student_input": context.student_input,
                "timestamp": datetime.now().isoformat(),
            }
            self.expansion_log.append(expansion)
            return expansion

        return None


class StrategyOptimizer:
    """策略优化器（P4自进化）"""

    def __init__(self):
        self.strategy_stats: Dict[str, Dict] = {}

    def record(self, strategy: str, success: bool):
        """记录策略效果"""
        if strategy not in self.strategy_stats:
            self.strategy_stats[strategy] = {
                "total": 0, "success": 0, "rate": 0.0
            }

        stats = self.strategy_stats[strategy]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        stats["rate"] = stats["success"] / stats["total"]

    def get_best_strategy(self, strategies: List[str]) -> str:
        """获取最佳策略"""
        best = None
        best_rate = -1

        for s in strategies:
            if s in self.strategy_stats:
                rate = self.strategy_stats[s]["rate"]
                if rate > best_rate:
                    best_rate = rate
                    best = s

        return best or strategies[0] if strategies else ""


class KnowledgeAgingDetector:
    """知识库老化检测器（E6前置检测）"""

    # 知识保质期（天）
    KNOWLEDGE_SHELF_LIFE = {
        "core_math": 365,       # 核心数学概念：1年
        "formula": 180,         # 公式：6个月
        "method": 90,           # 解题方法：3个月
        "pattern": 60,          # 题型模式：2个月
    }

    def detect_aging(self, knowledge_entries: List[Dict]) -> List[Dict]:
        """检测老化的知识"""
        aging = []
        now = datetime.now()

        for entry in knowledge_entries:
            created = entry.get("created_at")
            if not created:
                continue

            if isinstance(created, str):
                created = datetime.fromisoformat(created)

            age_days = (now - created).days
            category = entry.get("category", "method")
            shelf_life = self.KNOWLEDGE_SHELF_LIFE.get(category, 90)

            if age_days > shelf_life * 0.8:
                aging.append({
                    "entry": entry,
                    "age_days": age_days,
                    "shelf_life": shelf_life,
                    "urgency": age_days / shelf_life,
                })

        return sorted(aging, key=lambda x: x["urgency"], reverse=True)


class OverfittingGuard:
    """过拟合防护器（E4防过拟合）"""

    # E4关键：3次独立证据才确认
    MIN_EVIDENCE_COUNT = 3

    # 过拟合检测阈值
    OVERFITTING_THRESHOLDS = {
        "max_same_response": 3,      # 同一回复最多出现3次
        "max_same_strategy": 5,      # 同一策略最多连续5次
        "min_diversity": 0.3,        # 最低多样性
    }

    def check_overfitting(self, history: List[Dict]) -> Dict:
        """检查是否过拟合"""
        if len(history) < 5:
            return {"overfitting": False, "reason": "数据不足"}

        # 检查回复重复
        recent_responses = [h.get("response", "") for h in history[-10:]]
        for resp in set(recent_responses):
            if recent_responses.count(resp) > self.OVERFITTING_THRESHOLDS["max_same_response"]:
                return {
                    "overfitting": True,
                    "reason": f"回复重复{recent_responses.count(resp)}次",
                    "suggestion": "增加回复多样性",
                }

        # 检查策略重复
        recent_strategies = [h.get("strategy", "") for h in history[-10:]]
        consecutive = 1
        for i in range(1, len(recent_strategies)):
            if recent_strategies[i] == recent_strategies[i-1]:
                consecutive += 1
            else:
                consecutive = 1
            if consecutive > self.OVERFITTING_THRESHOLDS["max_same_strategy"]:
                return {
                    "overfitting": True,
                    "reason": f"策略连续重复{consecutive}次",
                    "suggestion": "切换教学策略",
                }

        # 检查多样性
        unique_responses = len(set(recent_responses))
        diversity = unique_responses / len(recent_responses)
        if diversity < self.OVERFITTING_THRESHOLDS["min_diversity"]:
            return {
                "overfitting": True,
                "reason": f"多样性过低：{diversity:.0%}",
                "suggestion": "增加回复变化",
            }

        return {"overfitting": False, "reason": "正常"}


class EvolutionLayer:
    """进化层主类"""

    def __init__(self, db_module=None):
        self.profile_updater = ProfileUpdater()
        self.misconception_evolver = MisconceptionEvolver()
        self.knowledge_expander = KnowledgeBaseExpander()
        self.strategy_optimizer = StrategyOptimizer()
        self.aging_detector = KnowledgeAgingDetector()
        self.overfitting_guard = OverfittingGuard()
        self.db = db_module

    def process(self, context: PipelineContext) -> PipelineContext:
        """处理进化层逻辑（后台异步）"""
        # 1. 贝叶斯更新画像
        if context.profile:
            context.profile = self.profile_updater.update(
                context.profile, context
            )

            # 保存画像到数据库
            if self.db:
                try:
                    self.db.save_user_profile(int(context.student_id), {
                        'visual': context.profile.visual,
                        'verbal': context.profile.verbal,
                        'kinesthetic': context.profile.kinesthetic,
                        'inductive': context.profile.inductive,
                        'deductive': context.profile.deductive,
                        'analogical': context.profile.analogical,
                        'fast_jump': context.profile.fast_jump,
                        'rigorous': context.profile.rigorous,
                        'divergent': context.profile.divergent,
                        'abstract_reasoning': context.profile.abstract_reasoning,
                        'challenge_drive': context.profile.challenge_drive,
                        'persistence': context.profile.persistence,
                        'metacognition': context.profile.metacognition,
                        'collaboration': context.profile.collaboration,
                        'creativity': context.profile.creativity,
                        'confidence': context.profile.confidence,
                        'data_points': context.profile.data_points,
                    })
                except Exception as e:
                    logger.warning(f"保存画像失败: {e}")

        # 2. 演化误解状态
        if context.validation and context.validation.misconceptions:
            context.validation.misconceptions = self.misconception_evolver.evolve(
                context.validation.misconceptions, context
            )

        # 3. 检查知识库扩展
        expansion = self.knowledge_expander.check_and_expand(context)
        if expansion:
            logger.info(f"知识库扩展建议: {expansion}")

        # 4. 检查过拟合
        history = self._get_history(context.student_id)
        overfitting = self.overfitting_guard.check_overfitting(history)
        if overfitting["overfitting"]:
            logger.warning(f"过拟合警告: {overfitting['reason']}")

        return context

    def _get_history(self, student_id: str) -> List[Dict]:
        """获取学生历史记录"""
        if self.db:
            try:
                return self.db.get_recent_performance(int(student_id), limit=20)
            except Exception:
                pass
        return []
