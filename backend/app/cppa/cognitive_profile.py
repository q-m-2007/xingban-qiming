"""
CPPA 认知画像引擎
15维认知画像 + 贝叶斯实时更新 + 集体知识冷启动 + 遗忘感知
"""
import math
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


# ──────────────────────────────────────────
# 画像维度定义
# ──────────────────────────────────────────

DIMENSION_GROUPS = {
    'information_style': ['visual', 'verbal', 'kinesthetic'],
    'reasoning_style': ['inductive', 'deductive', 'analogical'],
    'strategy_style': ['forward', 'backward', 'trial'],
    'cognitive_traits': ['fast_jump', 'rigorous', 'divergent'],
    'meta_traits': ['abstract_reasoning', 'challenge_drive', 'attention_span'],
}

ALL_DIMENSIONS = [d for group in DIMENSION_GROUPS.values() for d in group]

DIMENSION_DESCRIPTIONS = {
    'visual': '视觉型：喜欢画图、看图、空间想象',
    'verbal': '语言型：喜欢分析文字、列式、用语言描述思路',
    'kinesthetic': '动手型：喜欢试数、代入、实验验证',
    'inductive': '归纳型：从具体例子总结规律',
    'deductive': '演绎型：从公式定理出发推导',
    'analogical': '类比型：用已知问题套新问题',
    'forward': '正向推导：从条件推向结论',
    'backward': '逆向推导：从结论反推条件',
    'trial': '试探法：先猜一个答案，再验证',
    'fast_jump': '跳跃思维：思路快，容易跳步',
    'rigorous': '严谨思维：步骤完整，速度慢',
    'divergent': '发散思维：能想到多种方法',
    'abstract_reasoning': '抽象推理能力：理解和运用抽象概念的能力',
    'challenge_drive': '挑战驱动：喜欢难题还是偏好安全',
    'attention_span': '注意力持久度：能持续专注多长时间',
}


@dataclass
class CognitiveProfile:
    """学生认知画像：15维连续向量"""

    student_id: str

    # 信息获取偏好
    visual: float = 0.33
    verbal: float = 0.33
    kinesthetic: float = 0.33

    # 推理方式偏好
    inductive: float = 0.33
    deductive: float = 0.33
    analogical: float = 0.33

    # 解题策略偏好
    forward: float = 0.33
    backward: float = 0.33
    trial: float = 0.33

    # 认知特征
    fast_jump: float = 0.33
    rigorous: float = 0.33
    divergent: float = 0.33

    # 元认知特征
    abstract_reasoning: float = 0.5
    challenge_drive: float = 0.5
    attention_span: float = 0.5

    # 元数据
    data_points: int = 0
    confidence: float = 0.0
    last_updated: str = ''

    def to_dict(self) -> dict:
        return {d: getattr(self, d) for d in ALL_DIMENSIONS}

    @classmethod
    def from_dict(cls, data: dict) -> 'CognitiveProfile':
        profile = cls(student_id=data.get('student_id', ''))
        for d in ALL_DIMENSIONS:
            if d in data:
                setattr(profile, d, data[d])
        profile.data_points = data.get('data_points', 0)
        profile.confidence = data.get('confidence', 0.0)
        profile.last_updated = data.get('last_updated', '')
        return profile

    def get_group(self, group_name: str) -> Dict[str, float]:
        dims = DIMENSION_GROUPS.get(group_name, [])
        return {d: getattr(self, d) for d in dims}

    def get_dominant(self, group_name: str) -> str:
        group = self.get_group(group_name)
        return max(group, key=group.get)

    def get_style_label(self) -> str:
        info = self.get_dominant('information_style')
        reason = self.get_dominant('reasoning_style')
        strat = self.get_dominant('strategy_style')
        info_labels = {'visual': '视觉型', 'verbal': '语言型', 'kinesthetic': '动手型'}
        reason_labels = {'inductive': '归纳型', 'deductive': '演绎型', 'analogical': '类比型'}
        strat_labels = {'forward': '正向推导', 'backward': '逆向推导', 'trial': '试探法'}
        return f"{info_labels[info]}-{reason_labels[reason]}-{strat_labels[strat]}"


# ──────────────────────────────────────────
# 优化3：遗忘感知画像
# ──────────────────────────────────────────

@dataclass
class MethodMastery:
    """方法掌握度（含遗忘）"""
    method_id: str
    mastery: float = 0.5           # 当前掌握度 [0, 1]
    last_practice: str = ''        # 最后练习时间
    practice_count: int = 0        # 练习次数
    success_count: int = 0         # 成功次数
    half_life: float = 7200.0      # 遗忘半衰期（秒），默认2小时
    baseline: float = 0.1          # 基线掌握度（不会完全遗忘到0）

    def apply_forgetting(self) -> float:
        """应用Ebbinghaus遗忘曲线，返回当前实际掌握度"""
        if not self.last_practice:
            return self.baseline
        last = datetime.fromisoformat(self.last_practice)
        elapsed = (datetime.now() - last).total_seconds()
        decay = math.exp(-elapsed / self.half_life)
        return self.baseline + (self.mastery - self.baseline) * decay

    def reinforce(self, success: bool, learning_rate: float = 0.3):
        """练习后强化掌握度"""
        current = self.apply_forgetting()
        if success:
            self.mastery = current + learning_rate * (1.0 - current)
        else:
            self.mastery = current - learning_rate * current * 0.5
        self.mastery = max(0.05, min(0.95, self.mastery))
        self.last_practice = datetime.now().isoformat()
        self.practice_count += 1
        if success:
            self.success_count += 1


@dataclass
class ForgettingAwareProfile:
    """遗忘感知画像：在基础画像上增加方法掌握度追踪"""
    base_profile: CognitiveProfile
    method_masteries: Dict[str, MethodMastery] = field(default_factory=dict)
    engagement_history: List[Dict] = field(default_factory=list)  # 优化7

    def get_effective_mastery(self, method_id: str) -> float:
        """获取某方法的当前有效掌握度（考虑遗忘）"""
        if method_id not in self.method_masteries:
            return 0.3  # 未知方法的默认掌握度
        return self.method_masteries[method_id].apply_forgetting()

    def practice_method(self, method_id: str, success: bool):
        """记录一次方法练习"""
        if method_id not in self.method_masteries:
            self.method_masteries[method_id] = MethodMastery(method_id=method_id)
        self.method_masteries[method_id].reinforce(success)

    def get_methods_needing_review(self, threshold: float = 0.3) -> List[str]:
        """获取需要复习的方法（掌握度低于阈值）"""
        need_review = []
        for mid, mm in self.method_masteries.items():
            effective = mm.apply_forgetting()
            if effective < threshold and mm.practice_count > 0:
                need_review.append(mid)
        return need_review

    def add_engagement(self, signal: Dict):
        """添加投入度信号"""
        self.engagement_history.append({
            **signal,
            'timestamp': datetime.now().isoformat(),
        })
        # 只保留最近50条
        if len(self.engagement_history) > 50:
            self.engagement_history = self.engagement_history[-50:]

    def get_avg_engagement(self, window: int = 10) -> Dict[str, float]:
        """获取最近N次的平均投入度"""
        recent = self.engagement_history[-window:]
        if not recent:
            return {'bored': 0.0, 'challenged': 0.0, 'curious': 0.0, 'frustrated': 0.0}
        result = {}
        for key in ['bored', 'challenged', 'curious', 'frustrated']:
            values = [s.get(key, 0) for s in recent]
            result[key] = np.mean(values)
        return result


# ──────────────────────────────────────────
# 贝叶斯画像更新器
# ──────────────────────────────────────────

class ProfileUpdater:
    """贝叶斯画像更新器"""

    def __init__(self, learning_rate: float = 0.3, min_data: int = 5):
        self.learning_rate = learning_rate
        self.min_data = min_data

    def update(self, profile: CognitiveProfile, evidence: Dict[str, float]) -> CognitiveProfile:
        for dimension, observed in evidence.items():
            if dimension not in ALL_DIMENSIONS:
                continue
            prior = getattr(profile, dimension)
            likelihood = observed
            posterior = (likelihood * prior) / (
                likelihood * prior + (1 - likelihood + 1e-10) * (1 - prior + 1e-10)
            )
            alpha = self.learning_rate
            new_value = prior * (1 - alpha) + posterior * alpha
            new_value = max(0.05, min(0.95, new_value))
            setattr(profile, dimension, new_value)

        self._normalize_group(profile, 'information_style')
        self._normalize_group(profile, 'reasoning_style')
        self._normalize_group(profile, 'strategy_style')

        profile.data_points += 1
        profile.confidence = min(1.0, profile.data_points / 30.0)
        profile.last_updated = datetime.now().isoformat()
        return profile

    def _normalize_group(self, profile: CognitiveProfile, group_name: str):
        dims = DIMENSION_GROUPS[group_name]
        values = [getattr(profile, d) for d in dims]
        total = sum(values)
        if total > 0:
            for d in dims:
                setattr(profile, d, getattr(profile, d) / total)

    def bulk_update(self, profile: CognitiveProfile,
                    evidences: List[Dict[str, float]]) -> CognitiveProfile:
        for evidence in evidences:
            profile = self.update(profile, evidence)
        return profile


# ──────────────────────────────────────────
# 冷启动：集体知识初始化
# ──────────────────────────────────────────

class ColdStartInitializer:
    """从集体知识初始化新学生画像"""

    def __init__(self):
        self.collective_profiles: List[CognitiveProfile] = []

    def add_historical_profile(self, profile: CognitiveProfile):
        if profile.data_points >= 10:
            self.collective_profiles.append(profile)

    def initialize(self, student_id: str,
                   student_features: Optional[Dict] = None) -> CognitiveProfile:
        if not self.collective_profiles:
            return CognitiveProfile(student_id=student_id)
        if student_features is None:
            student_features = {}
        similarities = []
        for hp in self.collective_profiles:
            sim = self._compute_similarity(student_features, hp)
            similarities.append((hp, sim))
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_k = similarities[:min(5, len(similarities))]
        profile = CognitiveProfile(student_id=student_id)
        total_weight = sum(s for _, s in top_k)
        if total_weight > 0:
            for d in ALL_DIMENSIONS:
                weighted_sum = sum(getattr(hp, d) * sim for hp, sim in top_k)
                setattr(profile, d, weighted_sum / total_weight)
        profile.confidence = 0.2
        return profile

    def _compute_similarity(self, features: Dict, profile: CognitiveProfile) -> float:
        if not features:
            return 1.0 / max(len(self.collective_profiles), 1)
        similarity = 0.0
        count = 0
        for key, value in features.items():
            if hasattr(profile, key):
                profile_value = getattr(profile, key)
                similarity += 1.0 - abs(value - profile_value)
                count += 1
        return similarity / max(count, 1)


# ──────────────────────────────────────────
# 解题历史记录
# ──────────────────────────────────────────

@dataclass
class MethodAttempt:
    """一次解法尝试记录"""
    student_id: str
    problem_id: str
    problem_type: str
    method_used: str
    success: bool
    time_spent: float
    steps_count: int
    verification_level: int
    error_type: Optional[str]
    timestamp: str = ''

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MethodHistory:
    """学生解法使用历史"""

    def __init__(self):
        self.attempts: List[MethodAttempt] = []

    def add_attempt(self, attempt: MethodAttempt):
        self.attempts.append(attempt)

    def get_method_distribution(self, limit: int = 20) -> Dict[str, float]:
        recent = self.attempts[-limit:]
        if not recent:
            return {}
        counts = {}
        for a in recent:
            counts[a.method_used] = counts.get(a.method_used, 0) + 1
        total = len(recent)
        return {m: c / total for m, c in counts.items()}

    def get_method_success_rate(self, method: str) -> float:
        attempts = [a for a in self.attempts if a.method_used == method]
        if not attempts:
            return 0.5
        return sum(1 for a in attempts if a.success) / len(attempts)

    def get_avg_efficiency(self, method: str) -> float:
        attempts = [a for a in self.attempts if a.method_used == method and a.success]
        if not attempts:
            return 0.5
        efficiencies = []
        for a in attempts:
            eff = (a.verification_level / 3.0) / max(a.time_spent / 60.0, 0.1)
            efficiencies.append(min(1.0, eff))
        return np.mean(efficiencies)

    def get_last_practice_time(self, method: str) -> Optional[datetime]:
        """获取某方法最后练习时间"""
        attempts = [a for a in self.attempts if a.method_used == method]
        if not attempts:
            return None
        return datetime.fromisoformat(attempts[-1].timestamp)
