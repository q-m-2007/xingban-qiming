"""
优化2: 遗忘曲线模型

基于 Ebbinghaus 遗忘曲线，每个信念的置信度随时间衰减。
不同类型的信念有不同的衰减速度。

公式：confidence(t) = confidence_0 * exp(-t / tau) + baseline

tau 越小 → 忘得越快
baseline → 永远不会完全忘掉（肌肉记忆/深层理解）
"""

import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field


# 不同信念类型的半衰期（秒）
DEFAULT_HALF_LIVES = {
    "concept":      7200,    # 概念性信念：2 小时
    "procedure":    10800,   # 程序性信念：3 小时（更持久）
    "heuristic":    3600,    # 启发式信念：1 小时（容易忘）
    "presupposition": 14400, # 前提性信念：4 小时（最深层，最难忘）
}

# 基线置信度（永远不会衰减到 0）
BASELINE_CONFIDENCE = 0.05

# 激活次数的强化效应
ACTIVATION_BOOST = 0.02  # 每次激活增加 2% 的抗遗忘能力
MAX_ACTIVATION_BOOST = 0.3  # 最多增加 30%


@dataclass
class ForgettableBelief:
    """带遗忘模型的信念"""
    id: str
    proposition: str
    belief_type: str
    initial_confidence: float
    created_at: datetime
    last_activated: datetime
    activation_count: int = 1
    emotional_tag: str = "neutral"

    # 遗忘参数
    half_life: float = 7200.0  # 默认 2 小时
    baseline: float = BASELINE_CONFIDENCE

    # 缓存
    _cached_confidence: Optional[float] = None
    _cache_time: Optional[datetime] = None

    @property
    def effective_half_life(self) -> float:
        """考虑激活次数后的有效半衰期

        激活越多 → 记得越牢 → 半衰期越长
        """
        boost = min(MAX_ACTIVATION_BOOST, self.activation_count * ACTIVATION_BOOST)
        return self.half_life * (1 + boost)

    @property
    def tau(self) -> float:
        """衰减时间常数 τ = t_half / ln(2)"""
        return self.effective_half_life / np.log(2)

    def current_confidence(self, now: Optional[datetime] = None) -> float:
        """计算当前置信度（考虑遗忘衰减）

        C(t) = (C_0 - baseline) * exp(-t/tau) + baseline
        """
        now = now or datetime.now()
        elapsed = (now - self.last_activated).total_seconds()

        # 衰减
        decayed = (self.initial_confidence - self.baseline) * np.exp(-elapsed / self.tau)

        # 情感修正
        emotion_multiplier = {
            "neutral": 1.0,
            "attached": 1.3,   # 有情感依附的记忆更持久
            "insecure": 0.8,   # 不自信的记忆更容易忘
        }
        multiplier = emotion_multiplier.get(self.emotional_tag, 1.0)

        confidence = decayed * multiplier + self.baseline
        return float(np.clip(confidence, 0, 1))

    def activate(self, now: Optional[datetime] = None):
        """激活信念（重新回忆，重置衰减）"""
        now = now or datetime.now()
        self.initial_confidence = self.current_confidence(now)
        self.last_activated = now
        self.activation_count += 1
        self._cached_confidence = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposition": self.proposition,
            "belief_type": self.belief_type,
            "initial_confidence": self.initial_confidence,
            "current_confidence": self.current_confidence(),
            "created_at": self.created_at.isoformat(),
            "last_activated": self.last_activated.isoformat(),
            "activation_count": self.activation_count,
            "emotional_tag": self.emotional_tag,
            "half_life": self.half_life,
            "effective_half_life": self.effective_half_life,
        }


class ForgettingModel:
    """遗忘模型管理器

    管理一组带遗忘的信念，提供衰减计算、
    复习建议等功能。
    """

    def __init__(self, half_lives: Optional[Dict[str, float]] = None):
        self.half_lives = half_lives or DEFAULT_HALF_LIVES
        self.beliefs: Dict[str, ForgettableBelief] = {}

    def add_belief(
        self,
        belief_id: str,
        proposition: str,
        belief_type: str,
        confidence: float,
        emotional_tag: str = "neutral",
        now: Optional[datetime] = None
    ) -> ForgettableBelief:
        """添加带遗忘的信念"""
        now = now or datetime.now()
        half_life = self.half_lives.get(belief_type, 7200)

        belief = ForgettableBelief(
            id=belief_id,
            proposition=proposition,
            belief_type=belief_type,
            initial_confidence=confidence,
            created_at=now,
            last_activated=now,
            activation_count=1,
            emotional_tag=emotional_tag,
            half_life=half_life,
        )
        self.beliefs[belief_id] = belief
        return belief

    def get_current_confidences(self, now: Optional[datetime] = None) -> Dict[str, float]:
        """获取所有信念的当前置信度"""
        now = now or datetime.now()
        return {
            bid: b.current_confidence(now)
            for bid, b in self.beliefs.items()
        }

    def get_forgotten_beliefs(self, threshold: float = 0.15, now: Optional[datetime] = None) -> List[ForgettableBelief]:
        """获取即将被遗忘的信念（置信度低于阈值）"""
        now = now or datetime.now()
        return [
            b for b in self.beliefs.values()
            if b.current_confidence(now) < threshold
        ]

    def get_review_candidates(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """获取需要复习的信念（遗忘曲线的"复习窗口"）"""
        now = now or datetime.now()
        candidates = []

        for belief in self.beliefs.values():
            current = belief.current_confidence(now)
            # 复习窗口：置信度掉到初始值的 60% 以下
            if current < belief.initial_confidence * 0.6:
                candidates.append({
                    "belief": belief,
                    "current_confidence": current,
                    "drop_rate": 1 - current / belief.initial_confidence,
                    "priority": (1 - current) * belief.activation_count,
                })

        candidates.sort(key=lambda x: x["priority"], reverse=True)
        return candidates

    def apply_decay_to_vector(
        self,
        belief_vector: np.ndarray,
        belief_types: List[str],
        elapsed_times: List[float],
        activation_counts: List[int]
    ) -> np.ndarray:
        """将遗忘衰减应用到信念向量的各维度

        Args:
            belief_vector: 原始信念向量
            belief_types: 每个维度对应的信念类型
            elapsed_times: 每个维度距上次激活的时间（秒）
            activation_counts: 每个维度的激活次数

        Returns:
            衰减后的信念向量
        """
        decayed = np.zeros_like(belief_vector)

        for i in range(len(belief_vector)):
            btype = belief_types[i] if i < len(belief_types) else "concept"
            elapsed = elapsed_times[i] if i < len(elapsed_times) else 0
            count = activation_counts[i] if i < len(activation_counts) else 1

            half_life = self.half_lives.get(btype, 7200)
            boost = min(MAX_ACTIVATION_BOOST, count * ACTIVATION_BOOST)
            effective_tau = half_life * (1 + boost) / np.log(2)

            decay_factor = np.exp(-elapsed / effective_tau)
            decayed[i] = belief_vector[i] * decay_factor + BASELINE_CONFIDENCE * np.sign(belief_vector[i])

        return np.clip(decayed, -1, 1)

    def predict_forgetting_curve(
        self,
        belief_id: str,
        duration_hours: float = 24,
        n_points: int = 100
    ) -> Dict[str, Any]:
        """预测某个信念的遗忘曲线（用于可视化）"""
        belief = self.beliefs.get(belief_id)
        if not belief:
            return {"error": "belief_not_found"}

        times = np.linspace(0, duration_hours * 3600, n_points)
        confidences = [
            belief.current_confidence(belief.last_activated + timedelta(seconds=t))
            for t in times
        ]

        return {
            "belief_id": belief_id,
            "times_hours": (times / 3600).tolist(),
            "confidences": confidences,
            "half_life_hours": belief.effective_half_life / 3600,
            "baseline": belief.baseline,
        }

    def summary(self) -> Dict[str, Any]:
        """总结"""
        now = datetime.now()
        confidences = self.get_current_confidences(now)
        forgotten = self.get_forgotten_beliefs(now=now)

        return {
            "total_beliefs": len(self.beliefs),
            "mean_confidence": float(np.mean(list(confidences.values()))) if confidences else 0,
            "forgotten_count": len(forgotten),
            "review_candidates": len(self.get_review_candidates(now)),
        }
