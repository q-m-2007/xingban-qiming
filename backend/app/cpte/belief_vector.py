"""
CPTE 认知相变引擎 — 信念状态向量

将 LLM 提取的结构化信念映射到 N 维连续向量空间，
作为能量景观和动力学仿真的基础数据结构。
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import hashlib


@dataclass
class BeliefVector:
    """信念状态向量

    将学生的认知状态表示为 N 维向量 b ∈ [-1, 1]^N
    - -1: 完全错误的理解
    -  0: 不确定/模糊
    - +1: 完全正确的理解
    """
    vector: np.ndarray                    # N 维信念向量
    dimension_labels: List[str] = field(default_factory=list)  # 每个维度的语义标签
    source_belief_ids: List[str] = field(default_factory=list)  # 来源信念 ID
    timestamp: float = 0.0               # 时间戳

    @property
    def dimension(self) -> int:
        return len(self.vector)

    @property
    def norm(self) -> float:
        return float(np.linalg.norm(self.vector))

    @property
    def mean_activation(self) -> float:
        """序参数 φ: 平均激活度"""
        return float(np.mean(self.vector))

    @property
    def coherence(self) -> float:
        """认知一致性: 向量各分量的一致程度"""
        if len(self.vector) < 2:
            return 1.0
        return float(1.0 - np.std(self.vector))

    def similarity(self, other: 'BeliefVector') -> float:
        """与另一个信念向量的余弦相似度"""
        dot = np.dot(self.vector, other.vector)
        norm_product = self.norm * other.norm
        if norm_product < 1e-10:
            return 0.0
        return float(dot / norm_product)

    def distance(self, other: 'BeliefVector') -> float:
        """欧氏距离"""
        return float(np.linalg.norm(self.vector - other.vector))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "vector": self.vector.tolist(),
            "dimension_labels": self.dimension_labels,
            "source_belief_ids": self.source_belief_ids,
            "timestamp": self.timestamp,
            "norm": self.norm,
            "mean_activation": self.mean_activation,
            "coherence": self.coherence
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeliefVector':
        return cls(
            vector=np.array(data["vector"]),
            dimension_labels=data.get("dimension_labels", []),
            source_belief_ids=data.get("source_belief_ids", []),
            timestamp=data.get("timestamp", 0.0)
        )


class BeliefDimensionMapper:
    """信念维度映射器

    将 LLM 提取的结构化信念文本映射到 N 维向量空间。
    使用语义哈希 + 知识点锚定的方式，而非简单的 embedding。
    """

    # 数学认知的 16 个核心维度（由领域知识定义）
    DEFAULT_DIMENSIONS = [
        "概念理解",       # 对定义/定理的理解准确度
        "公式记忆",       # 公式的正确记忆程度
        "计算能力",       # 数值计算的正确性
        "逻辑推理",       # 推理链条的完整性
        "条件判断",       # 对适用条件的识别
        "方法选择",       # 选择合适解法的能力
        "结果验证",       # 检验答案的习惯
        "概念关联",       # 与其他知识点的联系
        "边界意识",       # 对特殊情况的敏感度
        "抽象能力",       # 从具体到一般的提升
        "逆向思维",       # 逆运算/反证的使用
        "多元视角",       # 多种解法的掌握
        "元认知",         # 对自身理解的觉察
        "迁移能力",       # 应用到新场景的能力
        "直觉判断",       # 数学直觉的准确性
        "形式化表达",     # 数学语言的规范使用
    ]

    def __init__(self, dimensions: int = 16, dimension_labels: Optional[List[str]] = None):
        self.dimensions = dimensions
        self.labels = dimension_labels or self.DEFAULT_DIMENSIONS[:dimensions]

        # 知识点→维度的权重映射（从知识库学习）
        self._knowledge_weights: Dict[str, np.ndarray] = {}
        # 误解→维度的影响映射
        self._misconception_impacts: Dict[str, np.ndarray] = {}

    def register_knowledge_point(self, point_id: str, weights: np.ndarray):
        """注册知识点在各维度上的权重"""
        assert len(weights) == self.dimensions
        self._knowledge_weights[point_id] = weights / (np.sum(np.abs(weights)) + 1e-10)

    def register_misconception(self, misconception_id: str, impact: np.ndarray):
        """注册误解在各维度上的负面影响"""
        assert len(impact) == self.dimensions
        self._misconception_impacts[misconception_id] = impact

    def map_beliefs_to_vector(
        self,
        beliefs: List[Dict[str, Any]],
        knowledge_context: Optional[Dict[str, Any]] = None
    ) -> BeliefVector:
        """将 LLM 提取的信念列表映射到 N 维向量

        Args:
            beliefs: LLM 输出的信念列表，每个含 proposition, confidence, type 等
            knowledge_context: 知识库上下文

        Returns:
            BeliefVector 对象
        """
        if not beliefs:
            return BeliefVector(
                vector=np.zeros(self.dimensions),
                dimension_labels=self.labels
            )

        # 初始化累加向量
        accumulated = np.zeros(self.dimensions)
        weights_sum = np.zeros(self.dimensions)

        for belief in beliefs:
            proposition = belief.get("proposition", "")
            confidence = belief.get("confidence", 0.5)
            belief_type = belief.get("type", "concept")
            layer = belief.get("layer", "表层")

            # 计算该信念在每个维度上的贡献
            dim_vector = self._compute_dimension_vector(
                proposition, confidence, belief_type, layer
            )

            # 置信度作为权重
            weight = confidence
            accumulated += dim_vector * weight
            weights_sum += weight

        # 归一化
        if np.any(weights_sum > 0):
            mask = weights_sum > 0
            accumulated[mask] /= weights_sum[mask]

        # 裁剪到 [-1, 1]
        accumulated = np.clip(accumulated, -1.0, 1.0)

        return BeliefVector(
            vector=accumulated,
            dimension_labels=self.labels,
            source_belief_ids=[b.get("id", "") for b in beliefs if b.get("id")]
        )

    def _compute_dimension_vector(
        self,
        proposition: str,
        confidence: float,
        belief_type: str,
        layer: str
    ) -> np.ndarray:
        """计算单个信念在各维度上的贡献值"""
        vec = np.zeros(self.dimensions)

        # 基于信念类型的维度权重
        type_weights = {
            "concept":      [1.0, 0.6, 0.2, 0.3, 0.4, 0.2, 0.1, 0.7, 0.3, 0.5, 0.1, 0.2, 0.3, 0.4, 0.2, 0.5],
            "procedure":    [0.3, 0.8, 0.9, 0.6, 0.5, 0.9, 0.4, 0.2, 0.3, 0.2, 0.3, 0.5, 0.2, 0.3, 0.3, 0.6],
            "heuristic":    [0.4, 0.3, 0.3, 0.4, 0.6, 0.7, 0.2, 0.4, 0.5, 0.3, 0.5, 0.6, 0.4, 0.5, 0.8, 0.2],
            "presupposition": [0.6, 0.2, 0.1, 0.5, 0.8, 0.3, 0.1, 0.5, 0.7, 0.6, 0.4, 0.3, 0.7, 0.4, 0.5, 0.3],
        }
        raw = type_weights.get(belief_type, [0.5] * 16)
        base_weights = np.array(raw[:self.dimensions]) if len(raw) >= self.dimensions else np.array(raw + [0.5] * (self.dimensions - len(raw)))

        # 层级修正（深层信念影响更大）
        layer_multiplier = {"表层": 0.6, "中层": 0.8, "深层": 1.0}
        multiplier = layer_multiplier.get(layer, 0.6)

        # 命题内容的语义哈希（确定性映射到维度）
        content_hash = self._semantic_hash(proposition)

        # 最终向量 = 置信度 × 类型权重 × 层级乘数 × 内容哈希调制
        vec = confidence * base_weights * multiplier * content_hash

        return vec

    def _semantic_hash(self, text: str) -> np.ndarray:
        """将文本语义哈希到 N 维向量

        使用确定性哈希，确保相同文本总是映射到相同向量。
        不同文本的向量近似正交（适合做维度选择）。
        """
        # 多个哈希种子
        seeds = [hashlib.md5(f"{text}_{i}".encode()).hexdigest() for i in range(self.dimensions)]

        vec = np.zeros(self.dimensions)
        for i, seed in enumerate(seeds):
            # 从哈希值生成 [-1, 1] 的数值
            val = int(seed[:8], 16) / 0xFFFFFFFF  # [0, 1]
            vec[i] = 2.0 * val - 1.0  # [-1, 1]

        # 归一化
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm

        return vec

    def map_vector_to_description(self, vec: BeliefVector) -> Dict[str, Any]:
        """将向量映射回可读的维度描述"""
        descriptions = []
        for i, (label, value) in enumerate(zip(vec.dimension_labels, vec.vector)):
            if abs(value) > 0.1:
                level = "强" if abs(value) > 0.6 else "中" if abs(value) > 0.3 else "弱"
                direction = "正向" if value > 0 else "负向"
                descriptions.append({
                    "dimension": label,
                    "value": float(value),
                    "level": level,
                    "direction": direction
                })

        descriptions.sort(key=lambda x: abs(x["value"]), reverse=True)

        return {
            "top_strengths": [d for d in descriptions if d["value"] > 0][:3],
            "top_weaknesses": [d for d in descriptions if d["value"] < 0][:3],
            "coherence": vec.coherence,
            "mean_activation": vec.mean_activation
        }
