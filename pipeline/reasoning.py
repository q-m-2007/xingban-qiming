"""
第3层：推理层（Reasoning Layer）
职责：认知图谱 + 冲突检测 + 冲突排序
铁律：P2逻辑准 + P3定位准
目标延迟：<10ms
"""

from typing import List, Dict, Optional
from datetime import datetime
from .models import (
    ReasoningResult, Conflict, ConflictType, StudentState,
    PipelineContext, Misconception
)


class CognitiveGraph:
    """认知图谱（P2逻辑准）"""

    # 四年级知识图谱
    KNOWLEDGE_GRAPH = {
        # 数与代数
        "number_concept": {
            "depends_on": [],
            "related_to": ["large_number", "factor_multiple"],
            "misconceptions": ["misconception_number_line"],
        },
        "large_number": {
            "depends_on": ["number_concept"],
            "related_to": ["place_value"],
            "misconceptions": ["misconception_place_value"],
        },
        "factor_multiple": {
            "depends_on": ["number_concept", "division"],
            "related_to": ["prime_number", "fraction"],
            "misconceptions": ["misconception_factor"],
        },
        "prime_number": {
            "depends_on": ["factor_multiple"],
            "related_to": ["prime_factorization"],
            "misconceptions": ["misconception_prime"],
        },
        "fraction": {
            "depends_on": ["factor_multiple", "division"],
            "related_to": ["decimal", "percentage"],
            "misconceptions": [
                "misconception_denominator_bigger",
                "misconception_fraction_equals_division",
            ],
        },
        "decimal": {
            "depends_on": ["fraction", "number_line"],
            "related_to": ["percentage"],
            "misconceptions": ["misconception_decimal_digits"],
        },
        # 图形与几何
        "angle": {
            "depends_on": [],
            "related_to": ["triangle", "quadrilateral"],
            "misconceptions": ["misconception_angle"],
        },
        "triangle": {
            "depends_on": ["angle", "line_segment"],
            "related_to": ["quadrilateral", "area"],
            "misconceptions": ["misconception_triangle_area"],
        },
        "quadrilateral": {
            "depends_on": ["angle", "line_segment"],
            "related_to": ["triangle", "area"],
            "misconceptions": ["misconception_quadrilateral"],
        },
        "circle": {
            "depends_on": ["pi_concept", "measurement"],
            "related_to": ["area", "perimeter"],
            "misconceptions": ["misconception_circle_area"],
        },
        # 运算
        "four_operations": {
            "depends_on": ["number_concept"],
            "related_to": ["operation_law", "equation"],
            "misconceptions": ["misconception_operation_order"],
        },
        "operation_law": {
            "depends_on": ["four_operations"],
            "related_to": ["simplification"],
            "misconceptions": ["misconception_commutative"],
        },
        # 方程
        "equation": {
            "depends_on": ["four_operations", "equality"],
            "related_to": ["word_problem"],
            "misconceptions": ["misconception_equals_sign"],
        },
        # 应用题
        "word_problem": {
            "depends_on": ["four_operations"],
            "related_to": ["equation"],
            "misconceptions": [],
        },
    }

    def get_related_misconceptions(self, topic: str) -> List[str]:
        """获取话题相关的误解"""
        if topic in self.KNOWLEDGE_GRAPH:
            return self.KNOWLEDGE_GRAPH[topic].get("misconceptions", [])
        return []

    def get_dependencies(self, topic: str) -> List[str]:
        """获取前置依赖"""
        if topic in self.KNOWLEDGE_GRAPH:
            return self.KNOWLEDGE_GRAPH[topic].get("depends_on", [])
        return []

    def get_related_topics(self, topic: str) -> List[str]:
        """获取相关话题"""
        if topic in self.KNOWLEDGE_GRAPH:
            return self.KNOWLEDGE_GRAPH[topic].get("related_to", [])
        return []


class ConflictDetector:
    """冲突检测器"""

    def detect(self, student_input: str, beliefs: List,
               topic: str, graph: CognitiveGraph) -> List[Conflict]:
        """检测认知冲突"""
        conflicts = []

        # 基于信念检测冲突
        for belief in beliefs:
            # 逻辑冲突：信念与知识图谱矛盾
            if self._is_logical_conflict(belief, topic, graph):
                conflicts.append(Conflict(
                    id=f"logical_{belief.source}",
                    type=ConflictType.LOGICAL,
                    description=f"信念与事实矛盾：{belief.content}",
                    severity=belief.confidence,
                    teaching_value=0.8,
                    readiness=0.7,
                    novelty=0.5,
                ))

            # 边界冲突：信念在知识边界上
            if self._is_boundary_conflict(belief, topic):
                conflicts.append(Conflict(
                    id=f"boundary_{belief.source}",
                    type=ConflictType.BOUNDARY,
                    description=f"信念在知识边界：{belief.content}",
                    severity=0.5,
                    teaching_value=0.6,
                    readiness=0.8,
                    novelty=0.3,
                ))

        # 检测路径依赖冲突
        path_conflict = self._detect_path_dependency(topic, graph)
        if path_conflict:
            conflicts.append(path_conflict)

        # 计算优先级
        for conflict in conflicts:
            conflict.priority = (
                conflict.severity *
                conflict.teaching_value *
                conflict.readiness *
                conflict.novelty
            )

        return conflicts

    def _is_logical_conflict(self, belief, topic: str,
                             graph: CognitiveGraph) -> bool:
        """检测逻辑冲突"""
        related_misconceptions = graph.get_related_misconceptions(topic)
        for mis_id in related_misconceptions:
            if mis_id in belief.source or mis_id in belief.content:
                return True
        return False

    def _is_boundary_conflict(self, belief, topic: str) -> bool:
        """检测边界冲突"""
        boundary_keywords = ["不确定", "可能", "也许", "大概", "似乎"]
        return any(kw in belief.content for kw in boundary_keywords)

    def _detect_path_dependency(self, topic: str,
                                graph: CognitiveGraph) -> Optional[Conflict]:
        """检测路径依赖冲突"""
        dependencies = graph.get_dependencies(topic)
        if not dependencies:
            return None

        return Conflict(
            id=f"path_dep_{topic}",
            type=ConflictType.PATH_DEPENDENCY,
            description=f"依赖前置知识：{', '.join(dependencies)}",
            severity=0.4,
            teaching_value=0.5,
            readiness=0.6,
            novelty=0.2,
        )


class ConflictRanker:
    """冲突排序器"""

    def rank(self, conflicts: List[Conflict]) -> List[Conflict]:
        """按优先级排序冲突"""
        return sorted(conflicts, key=lambda c: c.priority, reverse=True)


class StateClassifier:
    """学生状态分类器"""

    def classify(self, student_input: str, emotion: str,
                 misconceptions: List[Misconception],
                 conflicts: List[Conflict]) -> StudentState:
        """分类学生状态"""
        # 情绪崩溃
        if emotion == "frustrated":
            return StudentState.FRUSTRATED

        # 沉默
        if not student_input or len(student_input.strip()) < 2:
            return StudentState.SILENT

        # 概念错误
        if misconceptions:
            return StudentState.CONCEPT_ERROR

        # 深度卡壳
        stuck_signals = [
            "不知道", "不会", "没思路", "想不出来", "完全不会",
            "don't know", "no idea", "no clue", "can't think", "completely lost",
        ]
        if any(s in student_input.lower() for s in stuck_signals):
            return StudentState.DEEP_STUCK

        # 局部卡壳
        partial_signals = [
            "这一步", "这里", "不会算", "怎么算", "公式是什么",
            "this step", "here", "don't know how", "how to calculate", "what formula",
        ]
        if any(s in student_input.lower() for s in partial_signals):
            return StudentState.PARTIAL_STUCK

        # 默认：探索
        return StudentState.EXPLORING


class ReasoningLayer:
    """推理层主类"""

    def __init__(self):
        self.graph = CognitiveGraph()
        self.conflict_detector = ConflictDetector()
        self.conflict_ranker = ConflictRanker()
        self.state_classifier = StateClassifier()

    def process(self, context: PipelineContext) -> ReasoningResult:
        """处理推理层逻辑"""
        student_input = context.student_input
        beliefs = context.perception.beliefs if context.perception else []
        misconceptions = context.validation.misconceptions if context.validation else []
        emotion = context.perception.emotion if context.perception else "neutral"
        topic = context.topic

        # 1. 检测冲突
        conflicts = self.conflict_detector.detect(
            student_input, beliefs, topic, self.graph
        )

        # 2. 排序冲突
        ranked_conflicts = self.conflict_ranker.rank(conflicts)

        # 3. 分类学生状态
        state = self.state_classifier.classify(
            student_input, emotion, misconceptions, ranked_conflicts
        )

        # 4. 获取最高优先级冲突
        top_conflict = ranked_conflicts[0] if ranked_conflicts else None

        return ReasoningResult(
            state=state,
            conflicts=ranked_conflicts,
            top_conflict=top_conflict,
        )
