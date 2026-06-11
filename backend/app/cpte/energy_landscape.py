"""
CPTE 认知相变引擎 — 认知能量景观

核心创新：将学生的认知状态建模为多维能量景观中的粒子。
误解是能量局部极小值（吸引子盆地），正确理解是全局最小值。
学习就是粒子跨越能量壁垒从一个盆地跳到另一个盆地的过程。

能量函数：
    E(b) = -Σᵢ hᵢ·bᵢ - Σᵢ<ⱼ Jᵢⱼ·bᵢ·bⱼ + Σₐ Dₐ·exp(-||b - μₐ||² / 2σₐ²)

    第一项：知识锚点的吸引力（外部场）
    第二项：信念间的耦合（Ising 模型）
    第三项：误解吸引子的势阱
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from .config import CPTEConfig, DEFAULT_CONFIG


@dataclass
class Attractor:
    """误解吸引子

    每个误解对应能量景观中的一个高斯势阱。
    """
    id: str                              # 吸引子 ID
    center: np.ndarray                   # 势阱中心 μₐ（N 维向量）
    depth: float                         # 势阱深度 Dₐ
    width: float                         # 势阱宽度 σₐ
    description: str = ""                # 误解描述
    misconception_type: str = ""         # 误解类型
    severity: float = 0.5               # 严重度 [0, 1]
    teaching_value: float = 0.5         # 教学价值 [0, 1]
    activation_count: int = 0           # 被激活次数
    metadata: Dict[str, Any] = field(default_factory=dict)

    def potential(self, b: np.ndarray) -> float:
        """计算该吸引子在点 b 处的势能贡献"""
        diff = b - self.center
        dist_sq = np.dot(diff, diff)
        return self.depth * np.exp(-dist_sq / (2 * self.width ** 2))

    def gradient(self, b: np.ndarray) -> np.ndarray:
        """计算该吸引子的势能梯度（指向吸引子中心）"""
        diff = b - self.center
        dist_sq = np.dot(diff, diff)
        potential = self.depth * np.exp(-dist_sq / (2 * self.width ** 2))
        return potential * diff / (self.width ** 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "center": self.center.tolist(),
            "depth": self.depth,
            "width": self.width,
            "description": self.description,
            "misconception_type": self.misconception_type,
            "severity": self.severity,
            "teaching_value": self.teaching_value,
            "activation_count": self.activation_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Attractor':
        return cls(
            id=data["id"],
            center=np.array(data["center"]),
            depth=data["depth"],
            width=data["width"],
            description=data.get("description", ""),
            misconception_type=data.get("misconception_type", ""),
            severity=data.get("severity", 0.5),
            teaching_value=data.get("teaching_value", 0.5),
            activation_count=data.get("activation_count", 0),
        )


class EnergyLandscape:
    """认知能量景观

    管理整个能量函数：外部场 + 信念交互 + 误解吸引子。
    提供能量计算、梯度计算、景观分析等核心功能。
    """

    def __init__(self, dimensions: int = 16, config: Optional[CPTEConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self.N = dimensions

        # 外部场 h（知识锚点的吸引力）
        self.external_field = np.zeros(self.N)

        # 交互矩阵 J（信念间耦合，对称矩阵）
        self.coupling_matrix = np.zeros((self.N, self.N))

        # 误解吸引子列表
        self.attractors: List[Attractor] = []

        # 正确理解的目标位置
        self.target_state: Optional[np.ndarray] = None

        # 景观统计
        self._energy_cache: Dict[str, float] = {}

    def set_external_field(self, field: np.ndarray):
        """设置外部场（知识锚点）"""
        assert len(field) == self.N
        self.external_field = field.copy()

    def set_coupling_matrix(self, matrix: np.ndarray):
        """设置信念交互矩阵"""
        assert matrix.shape == (self.N, self.N)
        self.coupling_matrix = matrix.copy()
        # 确保对称
        self.coupling_matrix = (self.coupling_matrix + self.coupling_matrix.T) / 2

    def set_target_state(self, target: np.ndarray):
        """设置正确理解的目标状态"""
        assert len(target) == self.N
        self.target_state = target.copy()

    def add_attractor(self, attractor: Attractor):
        """添加误解吸引子"""
        assert len(attractor.center) == self.N
        self.attractors.append(attractor)
        self._energy_cache.clear()

    def remove_attractor(self, attractor_id: str) -> bool:
        """移除误解吸引子"""
        for i, att in enumerate(self.attractors):
            if att.id == attractor_id:
                self.attractors.pop(i)
                self._energy_cache.clear()
                return True
        return False

    # ── 能量计算 ──────────────────────────────────────────

    def energy(self, b: np.ndarray) -> float:
        """计算总能量 E(b)

        E(b) = -h·b - b^T·J·b + Σₐ Dₐ·exp(-||b-μₐ||²/2σₐ²)
        """
        assert len(b) == self.N

        # 项1：外部场能量
        field_energy = -np.dot(self.external_field, b)

        # 项2：交互能量（Ising 项）
        interaction_energy = -np.dot(b, np.dot(self.coupling_matrix, b))

        # 项3：误解吸引子能量
        attractor_energy = sum(att.potential(b) for att in self.attractors)

        return float(field_energy + interaction_energy + attractor_energy)

    def energy_components(self, b: np.ndarray) -> Dict[str, float]:
        """分解计算各项能量"""
        field_energy = -np.dot(self.external_field, b)
        interaction_energy = -np.dot(b, np.dot(self.coupling_matrix, b))
        attractor_energies = {att.id: att.potential(b) for att in self.attractors}

        return {
            "field": float(field_energy),
            "interaction": float(interaction_energy),
            "attractors": attractor_energies,
            "total": float(field_energy + interaction_energy + sum(attractor_energies.values()))
        }

    # ── 梯度计算 ──────────────────────────────────────────

    def gradient(self, b: np.ndarray) -> np.ndarray:
        """计算能量梯度 ∇E(b)

        ∇E(b) = -h - 2·J·b + Σₐ (Dₐ/σₐ²)·(b-μₐ)·exp(-||b-μₐ||²/2σₐ²)
        """
        assert len(b) == self.N

        # 项1：外部场梯度
        grad_field = -self.external_field

        # 项2：交互梯度
        grad_interaction = -2.0 * np.dot(self.coupling_matrix, b)

        # 项3：吸引子梯度
        grad_attractors = np.zeros(self.N)
        for att in self.attractors:
            grad_attractors += att.gradient(b)

        return grad_field + grad_interaction + grad_attractors

    def gradient_components(self, b: np.ndarray) -> Dict[str, np.ndarray]:
        """分解计算各项梯度"""
        grad_field = -self.external_field
        grad_interaction = -2.0 * np.dot(self.coupling_matrix, b)
        grad_attractors = {att.id: att.gradient(b) for att in self.attractors}

        return {
            "field": grad_field,
            "interaction": grad_interaction,
            "attractors": grad_attractors,
            "total": grad_field + grad_interaction + sum(grad_attractors.values())
        }

    # ── 景观分析 ──────────────────────────────────────────

    def find_local_minima(self, n_starts: int = 50, n_steps: int = 200) -> List[Dict[str, Any]]:
        """通过梯度下降找到景观中的局部极小值

        从随机起点出发，沿梯度下降找到极小值。
        """
        minima = []
        seen = set()

        for _ in range(n_starts):
            # 随机起点
            b = np.random.uniform(-1, 1, self.N)

            # 梯度下降
            for _ in range(n_steps):
                grad = self.gradient(b)
                b = b - self.config.damping * 0.01 * grad
                b = np.clip(b, -1, 1)

            # 检查是否是新发现的极小值
            key = self._discretize(b)
            if key not in seen:
                seen.add(key)
                minima.append({
                    "position": b.copy(),
                    "energy": self.energy(b),
                    "is_target": self._is_near_target(b),
                    "nearest_attractor": self._find_nearest_attractor(b)
                })

        # 按能量排序
        minima.sort(key=lambda x: x["energy"])
        return minima

    def compute_curvature(self, b: np.ndarray, direction: Optional[np.ndarray] = None) -> float:
        """计算指定方向上的曲率（二阶导数）

        用于判断当前位置是谷底、山顶还是鞍点。
        """
        eps = 1e-4
        if direction is None:
            direction = np.random.randn(self.N)
            direction /= np.linalg.norm(direction)

        # 数值二阶导数
        b_plus = b + eps * direction
        b_minus = b - eps * direction
        curvature = (self.energy(b_plus) - 2 * self.energy(b) + self.energy(b_minus)) / (eps ** 2)

        return float(curvature)

    def energy_slice_2d(
        self,
        center: np.ndarray,
        axis1: int = 0,
        axis2: int = 1,
        range_val: float = 1.5,
        resolution: int = 50
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """计算 2D 能量切面（用于可视化）

        返回 (X, Y, E) 网格数据。
        """
        x = np.linspace(-range_val, range_val, resolution)
        y = np.linspace(-range_val, range_val, resolution)
        X, Y = np.meshgrid(x, y)

        E = np.zeros_like(X)
        for i in range(resolution):
            for j in range(resolution):
                b = center.copy()
                b[axis1] = X[i, j]
                b[axis2] = Y[i, j]
                E[i, j] = self.energy(b)

        return X, Y, E

    # ── 辅助方法 ──────────────────────────────────────────

    def _discretize(self, b: np.ndarray, precision: int = 1) -> str:
        """将连续向量离散化为哈希键"""
        rounded = np.round(b, precision)
        return str(rounded.tobytes())

    def _is_near_target(self, b: np.ndarray, threshold: float = 0.3) -> bool:
        """检查是否接近目标状态"""
        if self.target_state is None:
            return False
        return np.linalg.norm(b - self.target_state) < threshold

    def _find_nearest_attractor(self, b: np.ndarray) -> Optional[str]:
        """找到最近的吸引子"""
        if not self.attractors:
            return None
        distances = [(att.id, np.linalg.norm(b - att.center)) for att in self.attractors]
        distances.sort(key=lambda x: x[1])
        return distances[0][0]

    def get_attractor_by_id(self, attractor_id: str) -> Optional[Attractor]:
        """根据 ID 获取吸引子"""
        for att in self.attractors:
            if att.id == attractor_id:
                return att
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimensions": self.N,
            "external_field": self.external_field.tolist(),
            "coupling_matrix": self.coupling_matrix.tolist(),
            "attractors": [att.to_dict() for att in self.attractors],
            "target_state": self.target_state.tolist() if self.target_state is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: Optional[CPTEConfig] = None) -> 'EnergyLandscape':
        landscape = cls(dimensions=data["dimensions"], config=config)
        landscape.external_field = np.array(data["external_field"])
        landscape.coupling_matrix = np.array(data["coupling_matrix"])
        landscape.attractors = [Attractor.from_dict(a) for a in data.get("attractors", [])]
        if data.get("target_state"):
            landscape.target_state = np.array(data["target_state"])
        return landscape
