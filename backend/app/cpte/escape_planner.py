"""
CPTE 认知相变引擎 — 逃逸路径规划器

规划从当前认知状态（被困在误解吸引子中）到正确理解的最优路径。
不是简单地指向目标，而是找到能量最低的逃逸通道。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape, Attractor
from .barrier_calculator import BarrierCalculator


class EscapePlanner:
    """逃逸路径规划器

    核心功能：
    1. 判断学生是否被困在误解吸引子中
    2. 找到最低能量壁垒的逃逸方向
    3. 规划分步逃逸路径（多步追问策略）
    """

    def __init__(self, landscape: EnergyLandscape, config: Optional[CPTEConfig] = None):
        self.landscape = landscape
        self.config = config or DEFAULT_CONFIG
        self.barrier_calculator = BarrierCalculator(landscape, config)

    def analyze_current_state(
        self,
        current_state: np.ndarray
    ) -> Dict[str, Any]:
        """分析当前认知状态

        判断：
        - 是否在误解吸引子中？
        - 在哪个吸引子中？
        - 距离吸引子中心多远？
        - 距离正确理解多远？
        """
        result = {
            "in_attractor": False,
            "attractor_id": None,
            "attractor_description": "",
            "distance_to_center": 0.0,
            "distance_to_target": 0.0,
            "energy": float(self.landscape.energy(current_state)),
            "local_curvature": 0.0,
        }

        # 检查是否在某个吸引子的影响范围内
        min_dist = float('inf')
        nearest_attractor = None

        for att in self.landscape.attractors:
            dist = np.linalg.norm(current_state - att.center)
            if dist < att.width * 2 and dist < min_dist:
                min_dist = dist
                nearest_attractor = att

        if nearest_attractor:
            result["in_attractor"] = True
            result["attractor_id"] = nearest_attractor.id
            result["attractor_description"] = nearest_attractor.description
            result["distance_to_center"] = float(min_dist)

        # 距离正确理解
        if self.landscape.target_state is not None:
            result["distance_to_target"] = float(
                np.linalg.norm(current_state - self.landscape.target_state)
            )

        # 局部曲率
        result["local_curvature"] = self.landscape.compute_curvature(current_state)

        return result

    def plan_escape(
        self,
        current_state: np.ndarray,
        n_waypoints: int = 3
    ) -> Dict[str, Any]:
        """规划逃逸路径

        不是直接指向目标（可能需要跨越很高的壁垒），
        而是找到能量最低的逃逸通道，分步到达目标。

        Args:
            current_state: 当前认知状态
            n_waypoints: 中间路径点数量

        Returns:
            逃逸路径规划
        """
        target = self.landscape.target_state
        if target is None:
            return {"error": "no_target_state", "waypoints": []}

        # 直接路径的壁垒
        direct_barrier = self.barrier_calculator.compute_barrier(current_state, target)

        # 尝试找到更低壁垒的路径（通过中间点）
        best_path = self._find_low_barrier_path(current_state, target, n_waypoints)

        # 如果分步路径更好，使用分步路径
        if best_path["total_barrier"] < direct_barrier["barrier_height"]:
            return {
                "strategy": "stepwise",
                "direct_barrier": direct_barrier["barrier_height"],
                "stepwise_barrier": best_path["total_barrier"],
                "improvement": direct_barrier["barrier_height"] - best_path["total_barrier"],
                "waypoints": best_path["waypoints"],
                "waypoint_energies": best_path["energies"],
                "escape_direction": best_path["initial_direction"].tolist(),
            }
        else:
            return {
                "strategy": "direct",
                "direct_barrier": direct_barrier["barrier_height"],
                "stepwise_barrier": best_path["total_barrier"],
                "improvement": 0.0,
                "waypoints": [target.tolist()],
                "escape_direction": self._compute_escape_direction(current_state).tolist(),
            }

    def compute_optimal_question_direction(
        self,
        current_state: np.ndarray
    ) -> np.ndarray:
        """计算最优追问方向

        综合考虑：
        1. 能量下降方向（自然趋向低能量态）
        2. 指向正确理解的方向
        3. 逃离最近吸引子的方向
        """
        target = self.landscape.target_state
        if target is None:
            return self._compute_escape_direction(current_state)

        # 方向1：能量梯度下降方向
        grad = self.landscape.gradient(current_state)
        grad_norm = np.linalg.norm(grad)
        if grad_norm > 1e-10:
            direction_gradient = -grad / grad_norm
        else:
            direction_gradient = np.zeros_like(current_state)

        # 方向2：指向正确理解
        to_target = target - current_state
        target_norm = np.linalg.norm(to_target)
        if target_norm > 1e-10:
            direction_target = to_target / target_norm
        else:
            direction_target = np.zeros_like(current_state)

        # 方向3：逃离最近吸引子
        direction_escape = self._compute_escape_direction(current_state)

        # 加权组合
        w_grad = self.config.force_gradient_weight
        w_target = self.config.force_target_weight
        w_escape = 0.3

        combined = w_grad * direction_gradient + w_target * direction_target + w_escape * direction_escape

        # 归一化
        combined_norm = np.linalg.norm(combined)
        if combined_norm > 1e-10:
            combined /= combined_norm

        return combined

    def _compute_escape_direction(self, state: np.ndarray) -> np.ndarray:
        """计算逃离最近吸引子的方向（远离吸引子中心）"""
        if not self.landscape.attractors:
            return np.zeros(self.landscape.N)

        # 找最近的吸引子
        min_dist = float('inf')
        nearest = None
        for att in self.landscape.attractors:
            dist = np.linalg.norm(state - att.center)
            if dist < min_dist:
                min_dist = dist
                nearest = att

        if nearest is None or min_dist < 1e-10:
            return np.zeros(self.landscape.N)

        # 方向：远离吸引子中心
        direction = state - nearest.center
        direction /= np.linalg.norm(direction)

        return direction

    def _find_low_barrier_path(
        self,
        start: np.ndarray,
        end: np.ndarray,
        n_waypoints: int
    ) -> Dict[str, Any]:
        """搜索低壁垒路径

        策略：在能量景观中随机采样中间点，
        找到使总壁垒最小的路径。
        """
        best_total_barrier = float('inf')
        best_waypoints = []
        best_energies = []
        best_direction = np.zeros_like(start)

        # 尝试多条随机路径
        n_attempts = 20
        for _ in range(n_attempts):
            # 生成随机中间点
            waypoints = []
            for j in range(n_waypoints):
                t = (j + 1) / (n_waypoints + 1)
                # 在线性插值基础上加随机扰动
                base = (1 - t) * start + t * end
                noise = np.random.randn(len(start)) * 0.2
                waypoint = np.clip(base + noise, -1, 1)
                waypoints.append(waypoint)

            # 计算每段的壁垒
            all_points = [start] + waypoints + [end]
            segment_barriers = []
            for i in range(len(all_points) - 1):
                barrier = self.barrier_calculator.compute_barrier_simple(
                    all_points[i], all_points[i + 1]
                )
                segment_barriers.append(barrier)

            total_barrier = max(segment_barriers)  # 瓶颈壁垒

            if total_barrier < best_total_barrier:
                best_total_barrier = total_barrier
                best_waypoints = [w.tolist() for w in waypoints]
                best_energies = [float(self.landscape.energy(w)) for w in waypoints]
                best_direction = waypoints[0] - start
                if np.linalg.norm(best_direction) > 1e-10:
                    best_direction /= np.linalg.norm(best_direction)

        return {
            "total_barrier": best_total_barrier,
            "waypoints": best_waypoints,
            "energies": best_energies,
            "initial_direction": best_direction,
        }
