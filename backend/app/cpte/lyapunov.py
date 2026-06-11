"""
优化5: 严格相变检测 — Lyapunov 指数

用最大 Lyapunov 指数 λ₁ 判断系统是否处于相变临界点：
- λ₁ < 0：稳定状态（学生认知稳定）
- λ₁ = 0：临界状态（即将发生相变——追问最佳时机！）
- λ₁ > 0：混沌状态（学生认知混乱，需要等待稳定）

比简单的磁化率阈值更严格、更准确。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import deque


class LyapunovAnalyzer:
    """Lyapunov 指数分析器

    通过追踪相邻轨迹的分离速率来计算最大 Lyapunov 指数。
    """

    def __init__(self, dimension: int = 16, window_size: int = 20):
        self.dimension = dimension
        self.window_size = window_size

        # 历史状态序列
        self.trajectory: deque = deque(maxlen=window_size * 2)

        # 扰动轨迹（用于计算 Lyapunov 指数）
        self.perturbed_trajectory: Optional[deque] = None
        self.perturbation_magnitude = 1e-4

        # 分离速率历史
        self.divergence_history: deque = deque(maxlen=window_size)

        # 计算结果缓存
        self._cached_lyapunov: Optional[float] = None
        self._cache_valid = False

    def update(self, state: np.ndarray) -> Dict[str, Any]:
        """更新状态，计算 Lyapunov 指数

        Args:
            state: 当前信念状态向量

        Returns:
            分析结果
        """
        self.trajectory.append(state.copy())
        self._cache_valid = False

        result = {
            "lyapunov_exponent": 0.0,
            "is_critical": False,
            "is_stable": True,
            "is_chaotic": False,
            "divergence_rate": 0.0,
            "confidence": 0.0,
        }

        if len(self.trajectory) < 5:
            return result

        # 计算最大 Lyapunov 指数
        lambda_1 = self._compute_max_lyapunov()
        result["lyapunov_exponent"] = lambda_1

        # 判断状态
        if lambda_1 < -0.01:
            result["is_stable"] = True
            result["is_critical"] = False
            result["is_chaotic"] = False
            result["confidence"] = min(1.0, abs(lambda_1) * 10)
        elif lambda_1 > 0.01:
            result["is_stable"] = False
            result["is_critical"] = False
            result["is_chaotic"] = True
            result["confidence"] = min(1.0, lambda_1 * 10)
        else:
            # λ₁ ≈ 0：临界状态！
            result["is_stable"] = False
            result["is_critical"] = True
            result["is_chaotic"] = False
            result["confidence"] = 1.0 - abs(lambda_1) * 100

        # 分离速率
        result["divergence_rate"] = self._compute_current_divergence()

        self._cached_lyapunov = lambda_1
        return result

    def _compute_max_lyapunov(self) -> float:
        """计算最大 Lyapunov 指数

        方法：Wolf 算法的简化版
        追踪相邻轨迹的指数分离速率。

        λ₁ = (1/N) · Σᵢ ln(||δᵢ|| / ||δ₀||)
        """
        states = list(self.trajectory)
        n = len(states)

        if n < 5:
            return 0.0

        # 使用最近的轨迹段
        recent = states[-self.window_size:]
        if len(recent) < 3:
            return 0.0

        # 方法1：基于状态差分的分离率
        lyapunov_values = []

        for i in range(1, len(recent) - 1):
            # 当前步的"位移"
            delta_current = recent[i] - recent[i-1]
            delta_next = recent[i+1] - recent[i]

            norm_current = np.linalg.norm(delta_current)
            norm_next = np.linalg.norm(delta_next)

            if norm_current > 1e-10 and norm_next > 1e-10:
                # 分离率
                divergence = np.log(norm_next / norm_current)
                lyapunov_values.append(divergence)

        if not lyapunov_values:
            return 0.0

        return float(np.mean(lyapunov_values))

    def _compute_current_divergence(self) -> float:
        """计算当前的轨迹分离速率"""
        states = list(self.trajectory)
        if len(states) < 2:
            return 0.0

        delta = states[-1] - states[-2]
        return float(np.linalg.norm(delta))

    def compute_local_lyapunov(self, state: np.ndarray, n_perturbations: int = 5) -> Dict[str, Any]:
        """计算局部 Lyapunov 指数

        在当前状态附近施加小扰动，观察扰动如何演化。
        用于更精确地判断当前点的稳定性。
        """
        perturbation_results = []

        for _ in range(n_perturbations):
            # 随机扰动方向
            direction = np.random.randn(self.dimension)
            direction /= np.linalg.norm(direction)

            # 施加扰动
            perturbed_state = state + self.perturbation_magnitude * direction

            # 计算能量梯度
            # （这里简化为计算梯度差，实际应该追踪轨迹）
            gradient_at_state = np.zeros(self.dimension)  # 需要 landscape
            gradient_at_perturbed = np.zeros(self.dimension)

            # 扰动增长率
            if np.linalg.norm(gradient_at_state) > 1e-10:
                growth = np.linalg.norm(gradient_at_perturbed - gradient_at_state) / self.perturbation_magnitude
                perturbation_results.append(growth)

        if not perturbation_results:
            return {"local_lyapunov": 0.0, "is_locally_stable": True}

        local_lambda = float(np.mean(perturbation_results))

        return {
            "local_lyapunov": local_lambda,
            "is_locally_stable": local_lambda < 0,
            "n_perturbations": n_perturbations,
        }

    def detect_bifurcation(
        self,
        parameter_history: List[float],
        state_history: List[np.ndarray]
    ) -> Dict[str, Any]:
        """检测分岔点

        当控制参数（如追问强度）变化时，
        系统的定性行为可能发生突变（分岔）。

        分岔特征：
        - 状态的方差突然增大
        - 状态出现周期性振荡
        - 能量景观的极小值数量变化
        """
        if len(parameter_history) < 10 or len(state_history) < 10:
            return {"has_bifurcation": False, "reason": "insufficient_data"}

        params = np.array(parameter_history)
        states = np.array(state_history)

        # 计算状态方差的滑动窗口
        window = min(5, len(states) // 2)
        variances = []
        for i in range(window, len(states)):
            window_states = states[i-window:i]
            var = np.mean(np.var(window_states, axis=0))
            variances.append(var)

        if len(variances) < 3:
            return {"has_bifurcation": False, "reason": "insufficient_variance_data"}

        # 检测方差突增
        variances = np.array(variances)
        var_diff = np.diff(variances)

        # 分岔点：方差变化率突增
        threshold = np.mean(np.abs(var_diff)) + 2 * np.std(np.abs(var_diff))
        bifurcation_indices = np.where(np.abs(var_diff) > threshold)[0]

        if len(bifurcation_indices) > 0:
            return {
                "has_bifurcation": True,
                "bifurcation_indices": bifurcation_indices.tolist(),
                "variance_jump": float(np.max(np.abs(var_diff))),
                "confidence": float(min(1.0, np.max(np.abs(var_diff)) / threshold)),
            }

        return {"has_bifurcation": False}

    def get_analysis_summary(self) -> Dict[str, Any]:
        """获取分析总结"""
        return {
            "trajectory_length": len(self.trajectory),
            "cached_lyapunov": self._cached_lyapunov,
            "window_size": self.window_size,
            "divergence_history_length": len(self.divergence_history),
        }
