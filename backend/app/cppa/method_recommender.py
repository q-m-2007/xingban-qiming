"""
CPPA 解法推荐引擎
根据学生画像 + 解法认知需求 → 推荐最适合的解法
"""
import math
import numpy as np
from typing import Dict, List, Optional, Tuple

from .cognitive_profile import CognitiveProfile, MethodHistory, ALL_DIMENSIONS
from .method_bank import MethodBank, Method


class MethodRecommender:
    """解法推荐引擎"""

    def __init__(self, method_bank: MethodBank):
        self.bank = method_bank

    def recommend(self, topic: str, profile: CognitiveProfile,
                  mode: str = 'comfort',
                  history: Optional[MethodHistory] = None) -> List[Tuple[Method, float]]:
        """
        推荐解法

        mode:
          'comfort'  — 推荐学生最擅长的方法（建立信心）
          'expand'   — 推荐学生不熟悉但适合的方法（拓展能力）
          'challenge' — 推荐有难度的方法（挑战自我）

        返回：[(解法, 匹配分数)] 按分数降序排列
        """
        methods = self.bank.get_methods(topic)
        if not methods:
            return []

        scored = []
        for method in methods:
            score = self._compute_score(method, profile, mode, history)
            scored.append((method, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def recommend_best(self, topic: str, profile: CognitiveProfile,
                       mode: str = 'comfort',
                       history: Optional[MethodHistory] = None) -> Optional[Method]:
        """推荐最佳解法"""
        results = self.recommend(topic, profile, mode, history)
        return results[0][0] if results else None

    def _compute_score(self, method: Method, profile: CognitiveProfile,
                       mode: str, history: Optional[MethodHistory]) -> float:
        """计算解法匹配分数"""

        # ── 基础匹配分：画像与解法认知需求的匹配度 ──
        base_score = self._compute_cognitive_match(method, profile)

        # ── 模式调整 ──
        if mode == 'comfort':
            # 舒适区：偏好匹配度 + 历史成功率
            preference_bonus = self._get_preference_bonus(method, profile, history)
            return base_score * 0.5 + preference_bonus * 0.5

        elif mode == 'expand':
            # 拓展区：成长潜力越大分越高
            growth = self._compute_growth_potential(method, profile)
            return base_score * 0.3 + growth * 0.7

        elif mode == 'challenge':
            # 挑战区：难度适配
            difficulty_fit = self._compute_difficulty_fit(method, profile)
            return base_score * 0.3 + difficulty_fit * 0.7

        return base_score

    def _compute_cognitive_match(self, method: Method,
                                 profile: CognitiveProfile) -> float:
        """
        计算解法认知需求与学生画像的匹配度

        核心思想：
        - 解法需要的能力，学生强 → 匹配
        - 解法不需要的能力，学生弱 → 也行（不影响）
        - 解法需要的能力，学生弱 → 不匹配
        """
        score = 0.0
        total_weight = 0.0

        for dimension, required in method.cognitive_requirements.items():
            if not hasattr(profile, dimension):
                continue

            student_ability = getattr(profile, dimension)
            weight = required  # 需求越高，权重越大

            if required < 0.2:
                # 解法不太需要这个维度，中性
                match = 0.5
            else:
                # 解法需要这个维度，看学生能力
                # 用sigmoid映射，让中等能力也有不错的分数
                match = self._sigmoid(student_ability, center=0.5, steepness=5)

            score += match * weight
            total_weight += weight

        return score / max(total_weight, 0.01)

    def _get_preference_bonus(self, method: Method,
                              profile: CognitiveProfile,
                              history: Optional[MethodHistory]) -> float:
        """学生对某种方法的历史偏好加分"""
        if history is None:
            return 0.3  # 无历史，中性

        success_rate = history.get_method_success_rate(method.id)
        return success_rate

    def _compute_growth_potential(self, method: Method,
                                  profile: CognitiveProfile) -> float:
        """
        计算方法对学生能力成长的潜力

        思路：学生在这个方法涉及的维度上越弱，成长潜力越大
        """
        potential = 0.0
        count = 0
        for dimension, required in method.cognitive_requirements.items():
            if required > 0.3 and hasattr(profile, dimension):
                student_ability = getattr(profile, dimension)
                potential += (1.0 - student_ability)
                count += 1
        return potential / max(count, 1)

    def _compute_difficulty_fit(self, method: Method,
                                profile: CognitiveProfile) -> float:
        """
        计算难度适配度

        思路：难度略高于学生当前水平最好（最近发展区）
        """
        student_level = profile.abstract_reasoning
        ideal_difficulty = student_level + 0.1  # 略高于当前水平
        gap = abs(method.difficulty - ideal_difficulty)
        return max(0, 1.0 - gap * 2)

    def _sigmoid(self, x: float, center: float = 0.5,
                 steepness: float = 5) -> float:
        """Sigmoid映射函数"""
        return 1.0 / (1.0 + math.exp(-steepness * (x - center)))

    def get_method_comparison(self, topic: str,
                              profile: CognitiveProfile) -> str:
        """
        生成方法对比报告（可读文本）
        """
        methods = self.bank.get_methods(topic)
        if not methods:
            return "暂无可用解法"

        lines = [f"【{topic}】解法对比分析\n"]
        lines.append(f"学生风格：{profile.get_style_label()}\n")

        for method in methods:
            match_score = self._compute_cognitive_match(method, profile)
            growth = self._compute_growth_potential(method, profile)

            lines.append(f"━━━ {method.name} ━━━")
            lines.append(f"  难度：{'★' * int(method.difficulty * 5)}")
            lines.append(f"  匹配度：{match_score:.0%}")
            lines.append(f"  成长潜力：{growth:.0%}")
            lines.append(f"  适用场景：{method.when_to_use}")

            # 匹配/不匹配的维度
            strengths = []
            weaknesses = []
            for dim, req in method.cognitive_requirements.items():
                if req > 0.3 and hasattr(profile, dim):
                    ability = getattr(profile, dim)
                    if ability > 0.6:
                        strengths.append(dim)
                    elif ability < 0.3:
                        weaknesses.append(dim)

            if strengths:
                lines.append(f"  ✅ 优势维度：{', '.join(strengths)}")
            if weaknesses:
                lines.append(f"  ⚠️ 薄弱维度：{', '.join(weaknesses)}")
            lines.append("")

        return '\n'.join(lines)
