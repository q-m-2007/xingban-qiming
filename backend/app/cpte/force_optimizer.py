"""
CPTE 认知相变引擎 — 追问力场优化器

将追问问题建模为施加在认知状态上的力。
最优追问方向由能量景观的几何结构决定。

F_optimal = -γ·∇E(b) + λ·(b_correct - b)

即同时沿能量下降方向和指向正确理解的方向施加力。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape
from .escape_planner import EscapePlanner
from .phase_detector import PhaseDetector


class ForceOptimizer:
    """追问力场优化器

    计算最优追问力，并将力的方向转换为追问策略描述。
    LLM 负责将策略描述转化为自然语言追问。
    """

    def __init__(
        self,
        landscape: EnergyLandscape,
        phase_detector: PhaseDetector,
        config: Optional[CPTEConfig] = None
    ):
        self.landscape = landscape
        self.phase_detector = phase_detector
        self.config = config or DEFAULT_CONFIG
        self.escape_planner = EscapePlanner(landscape, config)

    def compute_optimal_force(
        self,
        current_state: np.ndarray
    ) -> np.ndarray:
        """计算最优追问力

        F = λ_grad · (-∇E/||∇E||) + λ_target · (b_target - b)/||b_target - b||

        综合三个方向：
        1. 能量下降方向
        2. 指向正确理解方向
        3. 逃离吸引子方向
        """
        target = self.landscape.target_state
        if target is None:
            # 无目标时，只沿能量下降方向
            grad = self.landscape.gradient(current_state)
            grad_norm = np.linalg.norm(grad)
            if grad_norm > 1e-10:
                return -grad / grad_norm * self.config.force_magnitude_limit
            return np.zeros(self.landscape.N)

        # 使用 escape_planner 计算综合方向
        direction = self.escape_planner.compute_optimal_question_direction(current_state)

        # 力的大小：根据与目标的距离调整
        dist_to_target = np.linalg.norm(current_state - target)
        force_magnitude = min(
            self.config.force_magnitude_limit,
            dist_to_target * 0.5  # 距离越远，力越大
        )

        return direction * force_magnitude

    def compute_question_strategy(
        self,
        current_state: np.ndarray
    ) -> Dict[str, Any]:
        """计算追问策略

        不仅返回力的方向，还返回语义化的策略描述，
        供 LLM 生成自然语言追问时参考。
        """
        # 分析当前状态
        state_analysis = self.escape_planner.analyze_current_state(current_state)

        # 检测相变信号
        energy = self.landscape.energy(current_state)
        phase_signal = self.phase_detector.update(current_state, energy)

        # 计算最优力
        force = self.compute_optimal_force(current_state)

        # 计算壁垒
        target = self.landscape.target_state
        barrier_info = None
        if target is not None:
            barrier_info = self.escape_planner.barrier_calculator.estimate_escape_probability(
                current_state, target
            )

        # 生成策略描述
        strategy = self._build_strategy_description(
            state_analysis, phase_signal, force, barrier_info
        )

        return {
            "force": force.tolist(),
            "force_magnitude": float(np.linalg.norm(force)),
            "state_analysis": state_analysis,
            "phase_signal": {
                "is_critical": phase_signal["is_critical"],
                "critical_type": phase_signal["critical_type"],
                "confidence": phase_signal["confidence"],
                "susceptibility": phase_signal["susceptibility"],
            },
            "barrier_info": barrier_info,
            "strategy": strategy,
        }

    def _build_strategy_description(
        self,
        state_analysis: Dict[str, Any],
        phase_signal: Dict[str, Any],
        force: np.ndarray,
        barrier_info: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """构建追问策略描述

        输出结构化的策略信息，供 LLM 翻译成自然语言。
        """
        strategy = {
            "question_type": "guide_discovery",
            "direction_description": "",
            "urgency": "normal",
            "approach": "",
            "hints": [],
        }

        # 根据相变信号调整紧迫性
        if phase_signal["is_critical"]:
            strategy["urgency"] = "high"
            strategy["hints"].append("学生处于认知临界点，轻轻一推就可能突破")

        # 根据所在吸引子调整策略
        if state_analysis["in_attractor"]:
            att_desc = state_analysis["attractor_description"]
            strategy["hints"].append(f"学生当前被困在误解中：{att_desc}")
            strategy["approach"] = "先让学生意识到自己的矛盾，再引导探索"

            if state_analysis["distance_to_center"] < 0.2:
                strategy["hints"].append("学生深陷误解，需要温和但有力的引导")
            else:
                strategy["hints"].append("学生在误解边缘，有可能自行跳出")
        else:
            strategy["approach"] = "引导学生向正确理解靠近"

        # 根据力的方向描述追问方向
        force_norm = np.linalg.norm(force)
        if force_norm > 0.1:
            # 找出力的主要分量
            abs_force = np.abs(force)
            top_dims = np.argsort(abs_force)[-3:][::-1]

            direction_parts = []
            for dim_idx in top_dims:
                if abs_force[dim_idx] > 0.05:
                    direction = "正向" if force[dim_idx] > 0 else "负向"
                    direction_parts.append(f"维度{dim_idx}({direction})")

            strategy["direction_description"] = "主要在 " + "、".join(direction_parts) + " 方向施加影响"

        # 根据壁垒高度调整策略
        if barrier_info:
            if barrier_info.get("probability", 0) > 0.5:
                strategy["question_type"] = "guide_discovery"
                strategy["hints"].append("壁垒较低，温和引导即可")
            elif barrier_info.get("probability", 0) > 0.1:
                strategy["question_type"] = "counterexample"
                strategy["hints"].append("壁垒中等，需要有力的反例或边界探索")
            else:
                strategy["question_type"] = "decompose"
                strategy["hints"].append("壁垒很高，需要分步拆解")

        return strategy

    def evaluate_question_effect(
        self,
        state_before: np.ndarray,
        state_after: np.ndarray,
        applied_force: np.ndarray
    ) -> Dict[str, Any]:
        """评估追问效果

        比较追问前后的状态变化，判断追问是否有效。
        """
        # 状态变化
        delta = state_after - state_before
        delta_magnitude = np.linalg.norm(delta)

        # 能量变化
        energy_before = self.landscape.energy(state_before)
        energy_after = self.landscape.energy(state_after)
        energy_change = energy_after - energy_before

        # 方向一致性（追问力方向与实际移动方向的点积）
        force_norm = np.linalg.norm(applied_force)
        if force_norm > 1e-10 and delta_magnitude > 1e-10:
            force_dir = applied_force / force_norm
            delta_dir = delta / delta_magnitude
            direction_alignment = float(np.dot(force_dir, delta_dir))
        else:
            direction_alignment = 0.0

        # 距离目标的变化
        target = self.landscape.target_state
        dist_change = 0.0
        if target is not None:
            dist_before = np.linalg.norm(state_before - target)
            dist_after = np.linalg.norm(state_after - target)
            dist_change = dist_before - dist_after  # 正值=靠近目标

        # 效果评分
        effectiveness = 0.0
        if energy_change < 0:
            effectiveness += 0.3  # 能量下降
        if direction_alignment > 0:
            effectiveness += 0.3 * direction_alignment  # 方向一致
        if dist_change > 0:
            effectiveness += 0.4 * min(1.0, dist_change)  # 靠近目标

        return {
            "delta_magnitude": float(delta_magnitude),
            "energy_change": float(energy_change),
            "direction_alignment": float(direction_alignment),
            "distance_to_target_change": float(dist_change),
            "effectiveness": float(effectiveness),
            "is_effective": effectiveness > 0.3,
        }
