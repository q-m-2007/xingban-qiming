"""
CPTE 认知相变引擎 — 自优化引擎

三轮自优化机制：
  第1轮：参数贝叶斯自适应（根据对话反馈调整超参数）
  第2轮：吸引子自动发现（从数据中聚类发现新的误解模式）
  第3轮：力场精细化（根据追问效果调整力场权重）
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape, Attractor


@dataclass
class ConversationRecord:
    """单轮对话记录"""
    state_before: np.ndarray             # 追问前状态
    state_after: np.ndarray              # 追问后状态
    force_applied: np.ndarray            # 施加的追问力
    energy_before: float                 # 追问前能量
    energy_after: float                  # 追问后能量
    question_text: str = ""              # 追问文本
    student_response: str = ""           # 学生回应
    effectiveness: float = 0.0           # 效果评分
    phase_transition: bool = False       # 是否发生了相变


class SelfOptimizer:
    """自优化引擎

    通过累积的对话数据，自动调整 CPTE 算法的参数，
    使系统越来越精准地识别误解和生成有效追问。
    """

    def __init__(self, config: Optional[CPTEConfig] = None):
        self.config = config or DEFAULT_CONFIG

        # 对话历史
        self.conversation_history: List[ConversationRecord] = []

        # 参数自适应历史
        self.parameter_history: List[Dict[str, float]] = []

        # 发现的吸引子
        self.discovered_attractors: List[Dict[str, Any]] = []

        # 力场效果统计
        self.force_effectiveness: Dict[str, List[float]] = defaultdict(list)

        # 优化轮次计数
        self.optimization_rounds = 0

    def record_conversation(self, record: ConversationRecord):
        """记录一轮对话"""
        self.conversation_history.append(record)

    # ── 第1轮：参数贝叶斯自适应 ──────────────────────────────

    def adapt_parameters(self, landscape: EnergyLandscape) -> Dict[str, Any]:
        """第1轮优化：根据对话反馈自适应调整参数

        核心思想：如果追问后学生没有移动（效果差），
        说明参数设置不合理，需要调整。

        调整的参数：
        - γ (damping): 阻尼系数
        - T (temperature): 认知温度
        - attractor depth/width: 吸引子参数
        """
        if len(self.conversation_history) < self.config.min_adaptation_samples:
            return {"status": "insufficient_data", "samples": len(self.conversation_history)}

        # 计算最近 N 轮的效果统计
        recent = self.conversation_history[-20:]
        effects = [r.effectiveness for r in recent]
        mean_effect = np.mean(effects)
        std_effect = np.std(effects)

        adjustments = {}

        # 调整阻尼系数 γ
        # 如果效果差且学生移动小 → 降低阻尼（增加探索性）
        if mean_effect < 0.3:
            new_damping = max(0.3, self.config.damping * 0.9)
            adjustments["damping"] = {
                "old": self.config.damping,
                "new": new_damping,
                "reason": "追问效果差，降低阻尼增加探索"
            }
            self.config.damping = new_damping

        # 如果效果好但不稳定 → 增加阻尼（更稳定的引导）
        elif mean_effect > 0.6 and std_effect > 0.3:
            new_damping = min(0.95, self.config.damping * 1.05)
            adjustments["damping"] = {
                "old": self.config.damping,
                "new": new_damping,
                "reason": "效果好但不稳定，增加阻尼"
            }
            self.config.damping = new_damping

        # 调整认知温度 T
        # 如果学生频繁发生相变 → 温度可能过高
        phase_transitions = sum(1 for r in recent if r.phase_transition)
        if phase_transitions > len(recent) * 0.5:
            new_temp = max(0.05, self.config.temperature * 0.9)
            adjustments["temperature"] = {
                "old": self.config.temperature,
                "new": new_temp,
                "reason": "相变过于频繁，降低温度"
            }
            self.config.temperature = new_temp

        # 如果学生几乎不发生相变 → 温度可能过低
        elif phase_transitions == 0 and len(recent) >= 5:
            new_temp = min(1.0, self.config.temperature * 1.1)
            adjustments["temperature"] = {
                "old": self.config.temperature,
                "new": new_temp,
                "reason": "无相变发生，增加温度促进探索"
            }
            self.config.temperature = new_temp

        # 调整吸引子参数
        attractor_adjustments = self._adapt_attractor_params(landscape, recent)
        if attractor_adjustments:
            adjustments["attractors"] = attractor_adjustments

        self.optimization_rounds += 1
        self.parameter_history.append({
            "round": self.optimization_rounds,
            "damping": self.config.damping,
            "temperature": self.config.temperature,
            "mean_effectiveness": float(mean_effect),
        })

        return {
            "status": "adapted",
            "adjustments": adjustments,
            "mean_effectiveness": float(mean_effect),
            "samples_used": len(recent),
        }

    def _adapt_attractor_params(
        self,
        landscape: EnergyLandscape,
        recent: List[ConversationRecord]
    ) -> Dict[str, Any]:
        """自适应调整吸引子参数"""
        adjustments = {}

        for att in landscape.attractors:
            # 检查有多少对话涉及这个吸引子
            # （通过分析 state_before 是否在吸引子附近）
            involved = []
            for record in recent:
                dist = np.linalg.norm(record.state_before - att.center)
                if dist < att.width * 2:
                    involved.append(record)

            if not involved:
                continue

            # 如果学生经常在这个吸引子中但效果差 → 加深吸引子（更难逃脱 → 需要更强的追问）
            # 或者减小宽度（更精确地定位误解）
            mean_effect = np.mean([r.effectiveness for r in involved])

            if mean_effect < 0.2:
                # 效果很差，可能是吸引子参数不准
                new_width = att.width * 0.95
                adjustments[att.id] = {
                    "width": {"old": att.width, "new": new_width},
                    "reason": "效果差，缩小吸引子范围"
                }
                att.width = new_width

        return adjustments

    # ── 第2轮：吸引子自动发现 ──────────────────────────────

    def discover_attractors(
        self,
        landscape: EnergyLandscape
    ) -> Dict[str, Any]:
        """第2轮优化：从对话数据中自动发现新的误解模式

        算法：
        1. 收集学生"卡住"的状态（效果差、能量高）
        2. 对这些状态聚类
        3. 如果聚类中心不与已有吸引子重叠，添加为新吸引子
        """
        if len(self.conversation_history) < self.config.attractor_discovery_min * 2:
            return {"status": "insufficient_data"}

        # 提取"卡住"的状态点
        stuck_points = []
        for record in self.conversation_history:
            # 效果差且能量高 = 卡在误解中
            if record.effectiveness < 0.3 and record.energy_before > 0:
                stuck_points.append(record.state_before)

        if len(stuck_points) < self.config.attractor_discovery_min:
            return {"status": "no_stuck_points", "count": len(stuck_points)}

        # 简化版 DBSCAN 聚类
        clusters = self._simple_clustering(
            stuck_points,
            eps=self.config.attractor_discovery_eps,
            min_samples=self.config.attractor_discovery_min
        )

        new_attractors = []
        for cluster_center, cluster_size in clusters:
            # 检查是否与已有吸引子重叠
            is_novel = True
            for att in landscape.attractors:
                dist = np.linalg.norm(cluster_center - att.center)
                if dist < att.width:
                    is_novel = False
                    break

            if is_novel:
                # 创建新吸引子
                new_att = Attractor(
                    id=f"discovered_{len(landscape.attractors) + len(new_attractors)}",
                    center=cluster_center,
                    depth=self.config.attractor_depth * 0.8,
                    width=self.config.attractor_width,
                    description=f"自动发现的误解模式（样本数：{cluster_size}）",
                    misconception_type="discovered",
                    severity=min(1.0, cluster_size / 10),
                )
                new_attractors.append(new_att)
                self.discovered_attractors.append(new_att.to_dict())

        return {
            "status": "discovered",
            "new_attractors": len(new_attractors),
            "total_stuck_points": len(stuck_points),
            "clusters_found": len(clusters),
            "attractors": [a.to_dict() for a in new_attractors],
        }

    def _simple_clustering(
        self,
        points: List[np.ndarray],
        eps: float,
        min_samples: int
    ) -> List[Tuple[np.ndarray, int]]:
        """简化版 DBSCAN 聚类"""
        if not points:
            return []

        points_array = np.array(points)
        n = len(points_array)
        visited = [False] * n
        clusters = []

        for i in range(n):
            if visited[i]:
                continue

            # 找邻域内的点
            neighbors = []
            for j in range(n):
                if np.linalg.norm(points_array[i] - points_array[j]) < eps:
                    neighbors.append(j)

            if len(neighbors) < min_samples:
                visited[i] = True
                continue

            # 形成聚类
            cluster_indices = set(neighbors)
            for idx in neighbors:
                visited[idx] = True

            # 计算聚类中心
            cluster_points = points_array[list(cluster_indices)]
            center = np.mean(cluster_points, axis=0)
            clusters.append((center, len(cluster_indices)))

        return clusters

    # ── 第3轮：力场精细化 ──────────────────────────────

    def refine_force_field(
        self,
        landscape: EnergyLandscape
    ) -> Dict[str, Any]:
        """第3轮优化：根据追问效果精细化力场权重

        核心思想：
        - 好的追问方向：强化
        - 坏的追问方向：削弱
        - 探索新方向：逐渐减少随机探索
        """
        if len(self.conversation_history) < self.config.min_adaptation_samples:
            return {"status": "insufficient_data"}

        recent = self.conversation_history[-20:]

        # 分析各维度上的力效果
        dim_effects = np.zeros(self.config.belief_dimensions)
        dim_counts = np.zeros(self.config.belief_dimensions)

        for record in recent:
            force = record.force_applied
            effect = record.effectiveness

            # 找出力的主要分量
            abs_force = np.abs(force)
            top_dims = np.argsort(abs_force)[-3:]

            for d in top_dims:
                dim_effects[d] += effect
                dim_counts[d] += 1

        # 计算每个维度的平均效果
        mask = dim_counts > 0
        dim_avg_effects = np.zeros(self.config.belief_dimensions)
        dim_avg_effects[mask] = dim_effects[mask] / dim_counts[mask]

        # 调整力场权重
        adjustments = {}

        # 效果好的维度 → 增加权重
        for d in range(self.config.belief_dimensions):
            if dim_counts[d] >= 3:
                if dim_avg_effects[d] > 0.5:
                    adjustments[f"dim_{d}_boost"] = float(dim_avg_effects[d])
                elif dim_avg_effects[d] < 0.2:
                    adjustments[f"dim_{d}_reduce"] = float(dim_avg_effects[d])

        # 探索衰减
        old_exploration = self.config.force_gradient_weight
        self.config.exploration_decay *= 0.999  # 缓慢衰减
        adjustments["exploration_decay"] = {
            "old": old_exploration,
            "new": self.config.force_gradient_weight,
        }

        return {
            "status": "refined",
            "adjustments": adjustments,
            "dim_effectiveness": dim_avg_effects.tolist(),
            "samples_used": len(recent),
        }

    # ── 综合优化 ──────────────────────────────────────

    def run_full_optimization(
        self,
        landscape: EnergyLandscape
    ) -> Dict[str, Any]:
        """运行完整的三轮自优化"""
        results = {
            "round_1_parameter_adaptation": self.adapt_parameters(landscape),
            "round_2_attractor_discovery": self.discover_attractors(landscape),
            "round_3_force_refinement": self.refine_force_field(landscape),
            "total_conversations": len(self.conversation_history),
            "optimization_rounds": self.optimization_rounds,
        }

        return results

    def get_optimization_summary(self) -> Dict[str, Any]:
        """获取优化总结"""
        return {
            "total_conversations": len(self.conversation_history),
            "optimization_rounds": self.optimization_rounds,
            "parameter_history": self.parameter_history,
            "discovered_attractors": len(self.discovered_attractors),
            "current_config": {
                "damping": self.config.damping,
                "temperature": self.config.temperature,
                "exploration_decay": self.config.exploration_decay,
            }
        }
