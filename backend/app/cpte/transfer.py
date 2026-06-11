"""
优化4: 跨知识点迁移学习

不同知识点的认知状态不是孤立的。
理解"一元一次方程"会影响"一元二次方程"的理解。
解代数题的能力会迁移到解几何题。

用叠加景观的方式建模这种迁移效应。
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from .energy_landscape import EnergyLandscape


# 知识点之间的迁移矩阵（先验知识）
# 值越大 → 迁移效应越强
TRANSFER_PRIORS = {
    # 代数内部迁移
    ("linear_equation", "quadratic_equation"): 0.7,
    ("quadratic_equation", "linear_equation"): 0.3,
    ("linear_equation", "system_of_equations"): 0.6,
    ("quadratic_equation", "system_of_equations"): 0.5,
    ("factoring", "quadratic_equation"): 0.8,
    ("quadratic_equation", "factoring"): 0.4,

    # 代数→几何迁移
    ("quadratic_equation", "parabola"): 0.6,
    ("linear_equation", "linear_function"): 0.8,
    ("system_of_equations", "intersection"): 0.5,

    # 通用数学能力迁移
    ("computation", "algebra"): 0.4,
    ("computation", "geometry"): 0.3,
    ("logic", "proof"): 0.7,
    ("algebra", "geometry"): 0.3,
}


class CrossTopicTransfer:
    """跨知识点迁移管理器

    通过叠加多个知识点的能量景观来建模迁移效应。
    学生在知识点 A 上的认知状态会影响他在知识点 B 上的能量景观。
    """

    def __init__(self, dimensions: int = 16):
        self.dimensions = dimensions
        self.landscapes: Dict[str, EnergyLandscape] = {}
        self.transfer_matrix: Dict[Tuple[str, str], float] = dict(TRANSFER_PRIORS)

    def register_topic(self, topic: str, landscape: EnergyLandscape):
        """注册一个知识点的能量景观"""
        self.landscapes[topic] = landscape

    def set_transfer_weight(self, source: str, target: str, weight: float):
        """设置迁移权重"""
        self.transfer_matrix[(source, target)] = np.clip(weight, 0, 1)

    def compute_transferred_field(
        self,
        target_topic: str,
        student_states: Dict[str, np.ndarray]
    ) -> np.ndarray:
        """计算迁移后的外部场

        将学生在其他知识点上的认知状态"迁移"到目标知识点，
        影响目标知识点的外部场。

        Args:
            target_topic: 目标知识点
            student_states: 学生在各知识点上的状态 {topic: state_vector}

        Returns:
            迁移后的外部场修正量
        """
        transferred_field = np.zeros(self.dimensions)

        for source_topic, source_state in student_states.items():
            if source_topic == target_topic:
                continue

            # 获取迁移权重
            weight = self.transfer_matrix.get((source_topic, target_topic), 0.0)
            if weight < 0.05:
                continue

            # 获取源景观
            source_landscape = self.landscapes.get(source_topic)
            if source_landscape is None:
                continue

            # 迁移效应 = 权度 × 源状态 × 源景观的场方向
            source_field = source_landscape.external_field
            field_direction = source_field / (np.linalg.norm(source_field) + 1e-10)

            # 迁移量：源状态中正确的部分会增强目标的场
            source_correctness = np.mean(np.clip(source_state, 0, 1))
            transfer_amount = weight * source_correctness * field_direction

            transferred_field += transfer_amount

        return transferred_field

    def compute_transferred_attractors(
        self,
        target_topic: str,
        student_states: Dict[str, np.ndarray]
    ) -> List[Dict[str, Any]]:
        """计算迁移产生的新吸引子

        如果学生在源知识点上有严重误解，
        这个误解可能迁移到目标知识点。
        """
        new_attractors = []

        for source_topic, source_state in student_states.items():
            if source_topic == target_topic:
                continue

            weight = self.transfer_matrix.get((source_topic, target_topic), 0.0)
            if weight < 0.2:
                continue

            source_landscape = self.landscapes.get(source_topic)
            if source_landscape is None:
                continue

            # 检查学生是否在源知识点的误解中
            for att in source_landscape.attractors:
                dist = np.linalg.norm(source_state - att.center)
                if dist < att.width * 1.5:
                    # 学生在这个误解中，可能迁移
                    # 迁移后的吸引子位置 = 源吸引子中心（映射到目标空间）
                    transferred_center = att.center.copy()

                    new_attractors.append({
                        "source_topic": source_topic,
                        "source_attractor_id": att.id,
                        "center": transferred_center.tolist(),
                        "depth": att.depth * weight * 0.5,  # 迁移后的深度会减弱
                        "width": att.width * 0.8,
                        "transfer_weight": weight,
                        "description": f"从{source_topic}迁移的误解：{att.description}",
                    })

        return new_attractors

    def compute_transfer_benefit(
        self,
        source_topic: str,
        target_topic: str,
        source_improvement: float
    ) -> float:
        """计算源知识点的进步对目标知识点的收益

        Args:
            source_topic: 源知识点
            target_topic: 目标知识点
            source_improvement: 源知识点的改善幅度

        Returns:
            目标知识点的预期收益
        """
        weight = self.transfer_matrix.get((source_topic, target_topic), 0.0)
        return weight * source_improvement * 0.5  # 迁移效应是原效应的 50%

    def get_learning_priority(
        self,
        student_states: Dict[str, np.ndarray],
        target_topics: List[str]
    ) -> List[Dict[str, Any]]:
        """根据迁移效应推荐学习优先级

        优先学习迁移价值最高的知识点（学一个，帮一片）。
        """
        priorities = []

        for topic in target_topics:
            # 计算该知识点能迁移到多少其他知识点
            total_transfer_out = 0
            for other_topic in target_topics:
                if other_topic != topic:
                    weight = self.transfer_matrix.get((topic, other_topic), 0.0)
                    total_transfer_out += weight

            # 计算该知识点当前的掌握程度
            state = student_states.get(topic)
            mastery = float(np.mean(np.clip(state, 0, 1))) if state is not None else 0.0

            # 优先级 = 迁移价值 × (1 - 掌握程度)
            priority = total_transfer_out * (1 - mastery)

            priorities.append({
                "topic": topic,
                "mastery": mastery,
                "transfer_out_value": total_transfer_out,
                "priority": priority,
            })

        priorities.sort(key=lambda x: x["priority"], reverse=True)
        return priorities

    def build_superposed_landscape(
        self,
        primary_topic: str,
        student_states: Dict[str, np.ndarray]
    ) -> EnergyLandscape:
        """构建叠加后的能量景观

        将所有相关知识点的迁移效应叠加到主知识点的景观上。
        """
        primary = self.landscapes.get(primary_topic)
        if primary is None:
            raise ValueError(f"知识点 {primary_topic} 未注册")

        # 创建景观副本
        superposed = EnergyLandscape(dimensions=self.dimensions)
        superposed.external_field = primary.external_field.copy()
        superposed.coupling_matrix = primary.coupling_matrix.copy()
        superposed.target_state = primary.target_state.copy() if primary.target_state is not None else None
        superposed.attractors = list(primary.attractors)

        # 叠加迁移场
        transferred_field = self.compute_transferred_field(primary_topic, student_states)
        superposed.external_field += transferred_field

        # 叠加迁移吸引子
        transferred_attractors = self.compute_transferred_attractors(primary_topic, student_states)
        for ta in transferred_attractors:
            from .energy_landscape import Attractor
            att = Attractor(
                id=f"transfer_{ta['source_topic']}_{ta['source_attractor_id']}",
                center=np.array(ta["center"]),
                depth=ta["depth"],
                width=ta["width"],
                description=ta["description"],
                misconception_type="transferred",
                severity=ta["transfer_weight"],
            )
            superposed.add_attractor(att)

        return superposed
