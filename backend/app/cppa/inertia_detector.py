"""
CPPA 惯性思维检测引擎
检测学生的方法惯性，设计突破策略
"""
import math
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Optional

from .cognitive_profile import MethodHistory, MethodAttempt


@dataclass
class InertiaReport:
    """惯性思维报告"""
    student_id: str
    dominant_method: str           # 惯用方法
    dominant_ratio: float          # 惯用方法占比
    concentration: float           # 方法集中度
    efficiency_gap: float          # 与其他方法的效率差距
    strength: float                # 惯性强度 [0, 1]
    all_methods_ratio: Dict[str, float]  # 所有方法的使用比例
    suggested_alternative: str     # 建议的替代方法
    breakthrough_strategy: Dict    # 突破策略


class InertiaDetector:
    """惯性思维检测器"""

    def __init__(self, min_attempts: int = 8,
                 strength_threshold: float = 0.5):
        self.min_attempts = min_attempts
        self.strength_threshold = strength_threshold

    def detect(self, student_id: str,
               history: MethodHistory) -> Optional[InertiaReport]:
        """
        检测学生的惯性思维

        返回：InertiaReport 或 None（无显著惯性）
        """
        attempts = history.attempts
        if len(attempts) < self.min_attempts:
            return None

        # ── Step 1: 计算方法分布 ──
        distribution = history.get_method_distribution(limit=30)
        if len(distribution) < 2:
            return None  # 只用过一种方法，数据不足以判断

        # ── Step 2: 找到主导方法 ──
        dominant_method = max(distribution, key=distribution.get)
        dominant_ratio = distribution[dominant_method]

        # ── Step 3: 计算方法集中度（基于熵） ──
        concentration = self._compute_concentration(distribution)

        # ── Step 4: 评估主导方法的效率 ──
        efficiency_gap = self._compute_efficiency_gap(
            dominant_method, distribution, history
        )

        # ── Step 5: 计算惯性强度 ──
        strength = self._compute_strength(
            concentration, dominant_ratio, efficiency_gap, len(attempts)
        )

        # ── Step 6: 判断是否构成惯性 ──
        if strength < self.strength_threshold:
            return None

        # ── Step 7: 生成报告 ──
        alternative = self._suggest_alternative(
            dominant_method, distribution, history
        )
        strategy = self._design_strategy(
            dominant_method, alternative, efficiency_gap, strength
        )

        return InertiaReport(
            student_id=student_id,
            dominant_method=dominant_method,
            dominant_ratio=dominant_ratio,
            concentration=concentration,
            efficiency_gap=efficiency_gap,
            strength=strength,
            all_methods_ratio=distribution,
            suggested_alternative=alternative,
            breakthrough_strategy=strategy,
        )

    def _compute_concentration(self, distribution: Dict[str, float]) -> float:
        """
        计算方法集中度（基于信息熵）

        集中度 = 1 - 熵/最大熵
        所有方法均匀使用 → 熵最大 → 集中度=0
        只用一种方法 → 熵=0 → 集中度=1
        """
        n = len(distribution)
        if n <= 1:
            return 1.0

        entropy = 0.0
        for p in distribution.values():
            if p > 0:
                entropy -= p * math.log2(p)

        max_entropy = math.log2(n)
        concentration = 1.0 - (entropy / max(max_entropy, 0.01))

        return max(0, min(1, concentration))

    def _compute_efficiency_gap(self, dominant: str,
                                distribution: Dict[str, float],
                                history: MethodHistory) -> float:
        """
        计算主导方法与其他方法的效率差距

        正值 = 主导方法比其他方法低效（惯性导致低效）
        负值 = 主导方法比其他方法高效（惯性合理）
        """
        dominant_eff = history.get_avg_efficiency(dominant)

        other_effs = []
        for method in distribution:
            if method != dominant:
                eff = history.get_avg_efficiency(method)
                other_effs.append(eff)

        if not other_effs:
            return 0.0

        avg_other_eff = np.mean(other_effs)
        return avg_other_eff - dominant_eff

    def _compute_strength(self, concentration: float, dominant_ratio: float,
                          efficiency_gap: float, total_attempts: int) -> float:
        """
        计算惯性强度

        公式：strength = w1×集中度 + w2×主导占比 + w3×低效程度 + w4×持续时间
        """
        # 低效程度（只计算正值，即主导方法确实低效的情况）
        inefficiency = max(0, efficiency_gap)

        # 持续时间（归一化）
        duration = min(1.0, total_attempts / 50.0)

        strength = (
            concentration * 0.3 +
            dominant_ratio * 0.3 +
            inefficiency * 0.25 +
            duration * 0.15
        )

        return max(0, min(1, strength))

    def _suggest_alternative(self, dominant: str,
                             distribution: Dict[str, float],
                             history: MethodHistory) -> str:
        """建议替代方法"""
        alternatives = [m for m in distribution if m != dominant]

        if alternatives:
            # 选择成功率最高的替代方法
            best = max(alternatives,
                       key=lambda m: history.get_method_success_rate(m))
            return best

        # 没有使用过其他方法，返回None
        return 'unknown'

    def _design_strategy(self, dominant: str, alternative: str,
                         efficiency_gap: float,
                         strength: float) -> Dict:
        """设计惯性突破策略"""

        if efficiency_gap > 0.2:
            # 主导方法明显低效 → 效率冲击策略
            return {
                'type': 'efficiency_shock',
                'name': '效率冲击',
                'description': f'用一道{alternative}比{dominant}快得多的题，让学生体验差距',
                'steps': [
                    f'1. 让学生用{dominant}做题',
                    f'2. 做完后展示{alternative}的方法',
                    '3. 对比两种方法的效率',
                    '4. 引导学生思考"什么时候该用什么方法"',
                ],
                'intensity': 'high' if strength > 0.7 else 'medium',
            }
        elif strength > 0.7:
            # 强惯性但效率相近 → 渐进拓展策略
            return {
                'type': 'gradual_expansion',
                'name': '渐进拓展',
                'description': f'逐步引导学生体验{alternative}',
                'steps': [
                    f'1. 先用{dominant}做2道题（建立信心）',
                    f'2. 第3道题引导体验{alternative}',
                    f'3. 让学生自己比较两种方法的优劣',
                    f'4. 后续练习中交替使用两种方法',
                ],
                'intensity': 'medium',
            }
        else:
            # 轻度惯性 → 方法意识提升
            return {
                'type': 'awareness_boost',
                'name': '方法意识',
                'description': '让学生意识到"还有其他方法"',
                'steps': [
                    '1. 做完题后问"还有别的方法吗？"',
                    f'2. 展示{alternative}的思路',
                    '3. 讨论不同方法的适用场景',
                ],
                'intensity': 'low',
            }


# ──────────────────────────────────────────
# 惯性势垒计算
# ──────────────────────────────────────────

def compute_inertia_barrier(profile_dict: dict,
                            old_method_cognitive_req: dict,
                            new_method_cognitive_req: dict) -> float:
    """
    计算惯性势垒（从旧方法切换到新方法的认知成本）

    势垒越高，切换越难
    """
    # 旧方法的认知成本（熟练后低）
    old_cost = 0.0
    for dim, req in old_method_cognitive_req.items():
        ability = profile_dict.get(dim, 0.5)
        old_cost += req * (1 - ability)
    old_cost *= 0.3  # 熟练系数

    # 新方法的认知成本（不熟练所以高）
    new_cost = 0.0
    for dim, req in new_method_cognitive_req.items():
        ability = profile_dict.get(dim, 0.5)
        new_cost += req * (1 - ability)
    new_cost *= 1.5  # 不熟练系数

    # 切换成本（方法差异度）
    all_dims = set(old_method_cognitive_req.keys()) | set(new_method_cognitive_req.keys())
    distance = 0.0
    for dim in all_dims:
        old_val = old_method_cognitive_req.get(dim, 0)
        new_val = new_method_cognitive_req.get(dim, 0)
        distance += abs(old_val - new_val)
    switch_cost = distance / max(len(all_dims), 1) * 0.5

    barrier = max(0, (new_cost - old_cost) + switch_cost)
    return barrier
