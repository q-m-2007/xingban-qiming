"""
CPTE 认知相变引擎 — 知识库适配器

将 L1-L4 知识库数据转换为能量景观参数：
- L1 课本知识 → 外部场 h（正确理解的吸引力）
- L3 误解模式 → 吸引子（误解势阱）
- L2 题型解法 → 交互矩阵 J（信念间的耦合）
- L4 追问策略 → 力场权重调整
"""

import json
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape, Attractor
from .belief_vector import BeliefDimensionMapper


class KnowledgeAdapter:
    """知识库适配器

    读取 L1-L4 知识库 JSON 文件，
    转换为 CPTE 能量景观的参数。
    """

    def __init__(self, data_dir: str = "/home/ubuntu/xingban-qiming/data", config: Optional[CPTEConfig] = None):
        self.data_dir = Path(data_dir)
        self.config = config or DEFAULT_CONFIG
        self.mapper = BeliefDimensionMapper(dimensions=config.belief_dimensions if config else 16)

        # 缓存
        self._textbook_data: Optional[Dict] = None
        self._misconception_data: Optional[Dict] = None

    def load_textbook(self, filename: str = "textbook_L1_quadratic.json") -> Dict[str, Any]:
        """加载 L1 课本知识"""
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self._textbook_data = json.load(f)
        return self._textbook_data or {}

    def load_misconceptions(self, filename: str = "misconceptions_quadratic.json") -> Dict[str, Any]:
        """加载 L3 误解模式"""
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                self._misconception_data = json.load(f)
        return self._misconception_data or {}

    def build_landscape_from_knowledge(
        self,
        dimensions: int = 16,
        textbook_file: str = "textbook_L1_quadratic.json",
        misconception_file: str = "misconceptions_quadratic.json"
    ) -> EnergyLandscape:
        """从知识库构建完整的能量景观

        Returns:
            配置好的 EnergyLandscape 实例
        """
        landscape = EnergyLandscape(dimensions=dimensions, config=self.config)

        # 加载数据
        textbook = self.load_textbook(textbook_file)
        misconceptions = self.load_misconceptions(misconception_file)

        # Step 1: 从 L1 构建外部场（正确理解的吸引力）
        self._build_external_field(landscape, textbook)

        # Step 2: 从 L3 构建误解吸引子
        self._build_attractors(landscape, misconceptions)

        # Step 3: 设置目标状态（完全正确的理解）
        self._set_target_state(landscape, textbook)

        # Step 4: 构建交互矩阵
        self._build_coupling_matrix(landscape, textbook)

        return landscape

    def _build_external_field(self, landscape: EnergyLandscape, textbook: Dict):
        """从课本知识构建外部场

        外部场 h 代表"正确知识的吸引力"。
        每个知识点在各维度上有不同的权重。
        """
        field = np.zeros(landscape.N)
        knowledge_points = textbook.get("knowledge_points", [])

        for kp in knowledge_points:
            # 将知识点映射到维度向量
            kp_vector = self._knowledge_point_to_vector(kp, landscape.N)
            field += kp_vector

        # 归一化
        if np.any(np.abs(field) > 0):
            field = field / (np.max(np.abs(field)) + 1e-10) * self.config.field_strength

        landscape.set_external_field(field)

    def _build_attractors(self, landscape: EnergyLandscape, misconceptions: Dict):
        """从误解模式构建吸引子

        每个误解对应一个高斯势阱。
        误解越严重，势阱越深。
        """
        miscon = misconceptions.get("misconceptions", [])

        for mc in miscon:
            # 将误解描述映射到向量空间
            center = self._misconception_to_vector(mc, landscape.N)

            # 根据严重度调整吸引子深度
            severity = mc.get("severity", "medium")
            severity_map = {"low": 0.3, "medium": 0.5, "high": 0.8}
            severity_val = severity_map.get(severity, 0.5)

            attractor = Attractor(
                id=mc.get("id", f"M_{len(landscape.attractors)}"),
                center=center,
                depth=self.config.attractor_depth * severity_val,
                width=self.config.attractor_width,
                description=mc.get("description", ""),
                misconception_type=mc.get("trigger", ""),
                severity=severity_val,
                teaching_value=0.7,  # 误解的教学价值通常较高
            )
            landscape.add_attractor(attractor)

    def _set_target_state(self, landscape: EnergyLandscape, textbook: Dict):
        """设置目标状态（完全正确的理解）

        目标状态 = 所有知识点的正确理解的加权平均
        """
        knowledge_points = textbook.get("knowledge_points", [])
        if not knowledge_points:
            return

        target = np.zeros(landscape.N)
        for kp in knowledge_points:
            kp_vector = self._knowledge_point_to_vector(kp, landscape.N)
            target += kp_vector

        # 归一化到 [-1, 1]
        target = target / (len(knowledge_points))
        target = np.clip(target, -1, 1)

        landscape.set_target_state(target)

    def _build_coupling_matrix(self, landscape: EnergyLandscape, textbook: Dict):
        """构建信念交互矩阵

        知识点之间的前置/关联关系 → 信念维度之间的耦合强度
        """
        matrix = np.zeros((landscape.N, landscape.N))
        knowledge_points = textbook.get("knowledge_points", [])

        # 简化实现：相邻知识点之间有正耦合
        for i, kp1 in enumerate(knowledge_points):
            for j, kp2 in enumerate(knowledge_points[i+1:], i+1):
                # 基于知识点 ID 的相似度确定耦合强度
                coupling = self._compute_knowledge_coupling(kp1, kp2)
                vec1 = self._knowledge_point_to_vector(kp1, landscape.N)
                vec2 = self._knowledge_point_to_vector(kp2, landscape.N)

                # 交互矩阵 = 耦合强度 × 维度向量的外积
                matrix += coupling * np.outer(vec1, vec2)

        # 对称化
        matrix = (matrix + matrix.T) / 2

        # 归一化
        max_val = np.max(np.abs(matrix))
        if max_val > 0:
            matrix = matrix / max_val * self.config.coupling_strength

        landscape.set_coupling_matrix(matrix)

    def _knowledge_point_to_vector(self, kp: Dict, n: int) -> np.ndarray:
        """将知识点映射到 N 维向量"""
        text = kp.get("name", "") + " " + kp.get("definition", "")
        return self.mapper._semantic_hash(text)[:n] if len(self.mapper._semantic_hash(text)) >= n else self.mapper._semantic_hash(text)

    def _misconception_to_vector(self, mc: Dict, n: int) -> np.ndarray:
        """将误解映射到 N 维向量"""
        text = mc.get("description", "") + " " + mc.get("trigger", "")
        vec = self.mapper._semantic_hash(text)
        if len(vec) < n:
            vec = np.pad(vec, (0, n - len(vec)))
        return vec[:n]

    def _compute_knowledge_coupling(self, kp1: Dict, kp2: Dict) -> float:
        """计算两个知识点之间的耦合强度"""
        # 简化：基于 ID 的数字差
        id1 = kp1.get("id", "K000")
        id2 = kp2.get("id", "K000")
        try:
            num1 = int(id1.replace("K", ""))
            num2 = int(id2.replace("K", ""))
            # 相邻知识点耦合强
            distance = abs(num1 - num2)
            return max(0, 1.0 - distance * 0.1)
        except ValueError:
            return 0.3
