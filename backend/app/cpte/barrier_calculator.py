"""
CPTE 认知相变引擎 — 能量壁垒计算器

计算从当前认知状态到正确理解之间的能量壁垒。
使用简化版 NEB（Nudged Elastic Band）方法：
在两点之间插入一系列"弹性珠子"，沿路径找鞍点（能量最高点）。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape


class BarrierCalculator:
    """能量壁垒计算器

    计算从当前状态到目标状态的能量壁垒 ΔE，
    用于估计逃逸概率和设计追问策略。
    """

    def __init__(self, landscape: EnergyLandscape, config: Optional[CPTEConfig] = None):
        self.landscape = landscape
        self.config = config or DEFAULT_CONFIG

    def compute_barrier(
        self,
        start: np.ndarray,
        end: np.ndarray,
        n_images: Optional[int] = None,
        n_iterations: int = 100
    ) -> Dict[str, Any]:
        """计算两点之间的能量壁垒

        使用简化 NEB 方法：
        1. 在起点和终点之间线性插值生成初始路径
        2. 迭代优化路径，使每个点（除端点）沿垂直于路径方向的梯度下降
        3. 找到路径上的最高能量点（鞍点）

        Args:
            start: 起始状态（当前认知）
            end: 终止状态（正确理解）
            n_images: 路径上的采样点数
            n_iterations: 迭代优化步数

        Returns:
            壁垒信息
        """
        n_images = n_images or self.config.barrier_path_samples

        # Step 1: 生成初始路径（线性插值）
        path = self._initialize_path(start, end, n_images)

        # Step 2: NEB 优化
        path = self._neb_optimize(path, n_iterations)

        # Step 3: 计算路径能量剖面
        energies = [self.landscape.energy(p) for p in path]

        # Step 4: 找鞍点
        saddle_idx = int(np.argmax(energies))
        saddle_energy = energies[saddle_idx]
        start_energy = energies[0]
        end_energy = energies[-1]

        # 壁垒高度（从起点到鞍点）
        barrier_height = saddle_energy - start_energy

        # 路径长度
        path_length = sum(
            np.linalg.norm(path[i + 1] - path[i])
            for i in range(len(path) - 1)
        )

        return {
            "barrier_height": float(barrier_height),
            "saddle_energy": float(saddle_energy),
            "start_energy": float(start_energy),
            "end_energy": float(end_energy),
            "saddle_position": path[saddle_idx].tolist(),
            "saddle_index": saddle_idx,
            "path_length": float(path_length),
            "energy_profile": energies,
            "path": [p.tolist() for p in path],
            "is_surmountable": barrier_height < 5.0,  # 阈值可调
        }

    def compute_barrier_simple(
        self,
        start: np.ndarray,
        end: np.ndarray
    ) -> float:
        """简化版壁垒计算（快速估算）

        沿直线路径找最高能量点，不做 NEB 优化。
        用于实时计算场景。
        """
        n = self.config.barrier_path_samples
        energies = []

        for i in range(n + 1):
            t = i / n
            point = (1 - t) * start + t * end
            energies.append(self.landscape.energy(point))

        max_energy = max(energies)
        start_energy = energies[0]

        return float(max_energy - start_energy)

    def estimate_escape_probability(
        self,
        current_state: np.ndarray,
        target_state: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """估计从当前状态逃逸到目标状态的概率

        使用 Arrhenius 公式：P = exp(-ΔE / T)
        """
        target = target_state if target_state is not None else self.landscape.target_state
        if target is None:
            return {
                "probability": 0.0,
                "barrier_height": float('inf'),
                "reason": "no_target_state"
            }

        barrier = self.compute_barrier(current_state, target)
        T = self.config.escape_temperature

        if T <= 0:
            probability = 0.0
        else:
            probability = float(np.exp(-barrier["barrier_height"] / T))

        return {
            "probability": probability,
            "barrier_height": barrier["barrier_height"],
            "temperature": T,
            "is_likely": probability > 0.1,
        }

    def _initialize_path(
        self,
        start: np.ndarray,
        end: np.ndarray,
        n_images: int
    ) -> List[np.ndarray]:
        """线性插值生成初始路径"""
        path = []
        for i in range(n_images + 2):
            t = i / (n_images + 1)
            point = (1 - t) * start + t * end
            path.append(point)
        return path

    def _neb_optimize(
        self,
        path: List[np.ndarray],
        n_iterations: int
    ) -> List[np.ndarray]:
        """NEB（Nudged Elastic Band）优化

        核心思想：
        - 每个中间点沿垂直于路径方向的能量梯度下降
        - 同时保持路径上各点的均匀间距（弹性力）
        """
        path = [p.copy() for p in path]
        n = len(path)
        spring_constant = 1.0  # 弹簧常数

        for iteration in range(n_iterations):
            step_size = 0.01 * (1 - iteration / n_iterations)  # 逐渐减小步长

            new_path = [path[0]]  # 起点不变

            for i in range(1, n - 1):
                # 计算路径切线方向
                tangent = path[i + 1] - path[i - 1]
                tangent_norm = np.linalg.norm(tangent)
                if tangent_norm > 1e-10:
                    tangent /= tangent_norm

                # 能量梯度
                grad = self.landscape.gradient(path[i])

                # 垂直于切线的梯度分量（NEB 核心）
                grad_parallel = np.dot(grad, tangent) * tangent
                grad_perpendicular = grad - grad_parallel

                # 弹簧力（保持均匀间距）
                dist_prev = np.linalg.norm(path[i] - path[i - 1])
                dist_next = np.linalg.norm(path[i + 1] - path[i])
                spring_force = spring_constant * (dist_next - dist_prev) * tangent

                # 总力 = 垂直梯度 + 弹簧力的切线分量
                total_force = -grad_perpendicular + spring_force

                # 更新位置
                new_point = path[i] + step_size * total_force
                new_point = np.clip(new_point, -1, 1)
                new_path.append(new_point)

            new_path.append(path[-1])  # 终点不变
            path = new_path

        return path

    def find_multiple_barriers(
        self,
        current_state: np.ndarray,
        targets: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """计算到多个目标状态的壁垒

        用于比较不同正确理解路径的难度。
        """
        barriers = []
        for i, target in enumerate(targets):
            barrier = self.compute_barrier(current_state, target)
            barrier["target_index"] = i
            barriers.append(barrier)

        # 按壁垒高度排序（最容易跨越的排前面）
        barriers.sort(key=lambda x: x["barrier_height"])
        return barriers
