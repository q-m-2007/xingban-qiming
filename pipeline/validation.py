"""
第2层：验证层（Validation Layer）
职责：误解验证 + 边界校验 + 前置知识检查
铁律：E4防过拟合（3次证据才确认）+ P2逻辑准
目标延迟：<5ms
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .models import (
    ValidationResult, Misconception, ValidationIssue,
    MisconceptionState, PipelineContext
)


class MisconceptionValidator:
    """误解验证器（E4防过拟合）"""

    # 四年级常见误解库
    MISCONCEPTION_LIBRARY = {
        "misconception_denominator_bigger": {
            "type": "fraction_order",
            "description": "误以为分母越大分数越大",
            "principle": "分数比较要看整体大小，1/2 > 1/4",
            "counter_example": "1/2和1/4哪个大？分母大的1/4反而小",
            "prerequisite": ["fraction_concept"],
        },
        "misconception_triangle_area": {
            "type": "formula_missing",
            "description": "忘记三角形面积要除以2",
            "principle": "三角形是平行四边形的一半",
            "counter_example": "底4高3的三角形，面积是12还是6？",
            "prerequisite": ["parallelogram_area"],
        },
        "misconception_operation_order": {
            "type": "operation_order",
            "description": "运算顺序错误",
            "principle": "先乘除后加减，有括号先算括号",
            "counter_example": "2+3×4等于20还是14？",
            "prerequisite": ["four_operations"],
        },
        "misconception_decimal_digits": {
            "type": "decimal_compare",
            "description": "误以为小数位数越多数值越大",
            "principle": "小数比较从高位开始逐位比",
            "counter_example": "0.5和0.12哪个大？位数多的0.12反而小",
            "prerequisite": ["decimal_concept"],
        },
        "misconception_circle_area": {
            "type": "formula_confusion",
            "description": "混淆圆面积和周长公式",
            "principle": "面积=πr²，周长=2πr",
            "counter_example": "半径3的圆，面积是28.26还是18.84？",
            "prerequisite": ["circle_concept"],
        },
        "misconception_equals_sign": {
            "type": "equation_concept",
            "description": "误解等号的本质",
            "principle": "等号表示两边相等，不是运算指令",
            "counter_example": "3+4=7，7=3+4，两边都要成立",
            "prerequisite": ["equation_concept"],
        },
    }

    def __init__(self):
        # 误解状态跟踪：student_id -> misconception_id -> state
        self.states: Dict[str, Dict[str, Misconception]] = {}
        # 证据计数：student_id -> misconception_id -> count
        self.evidence_counts: Dict[str, Dict[str, int]] = {}
        # 最后出现时间：student_id -> misconception_id -> datetime
        self.last_seen: Dict[str, Dict[str, datetime]] = {}

    def validate(self, student_id: str, beliefs: List,
                 topic: str) -> ValidationResult:
        """验证学生信念，识别误解"""
        misconceptions = []
        issues = []

        for belief in beliefs:
            # 从信念中提取误解ID
            mis_id = self._extract_misconception_id(belief.content)
            if not mis_id:
                continue

            # E4：需要3次独立证据才确认
            count = self._add_evidence(student_id, mis_id)

            if count >= 3:
                # 已确认的误解
                state = self._get_state(student_id, mis_id)
                misconceptions.append(Misconception(
                    id=mis_id,
                    type=self.MISCONCEPTION_LIBRARY[mis_id]["type"],
                    content=belief.content,
                    state=state,
                    evidence_count=count,
                ))
            elif count >= 1:
                # 疑似误解，记录但不确认
                issues.append(ValidationIssue(
                    type="suspected_misconception",
                    content=f"疑似{belief.content}（证据{count}/3）",
                    severity=0.3 * count,
                ))

        return ValidationResult(
            misconceptions=misconceptions,
            issues=issues,
            prerequisite_ok=self._check_prerequisites(student_id, topic),
        )

    def _extract_misconception_id(self, belief_content: str) -> Optional[str]:
        """从信念内容提取误解ID"""
        for mis_id, info in self.MISCONCEPTION_LIBRARY.items():
            if info["description"] in belief_content or mis_id in belief_content:
                return mis_id
        return None

    def _add_evidence(self, student_id: str, mis_id: str) -> int:
        """添加证据，返回累计证据数"""
        if student_id not in self.evidence_counts:
            self.evidence_counts[student_id] = {}
        if mis_id not in self.evidence_counts[student_id]:
            self.evidence_counts[student_id][mis_id] = 0

        self.evidence_counts[student_id][mis_id] += 1
        return self.evidence_counts[student_id][mis_id]

    def _get_state(self, student_id: str, mis_id: str) -> MisconceptionState:
        """获取误解状态"""
        if student_id not in self.states:
            self.states[student_id] = {}

        if mis_id not in self.states[student_id]:
            self.states[student_id][mis_id] = Misconception(
                id=mis_id,
                type=self.MISCONCEPTION_LIBRARY[mis_id]["type"],
                content=self.MISCONCEPTION_LIBRARY[mis_id]["description"],
                state=MisconceptionState.ACTIVE,
            )

        return self.states[student_id][mis_id].state

    def _check_prerequisites(self, student_id: str, topic: str) -> bool:
        """检查前置知识是否满足"""
        # 四年级前置知识检查
        prerequisite_map = {
            "fraction": ["number_concept", "division"],
            "decimal": ["fraction", "number_line"],
            "triangle": ["angle", "line_segment"],
            "circle": ["pi_concept", "measurement"],
            "equation": ["four_operations", "equality"],
        }
        # 简化实现：假设前置知识满足
        return True

    def update_state(self, student_id: str, mis_id: str,
                     new_state: MisconceptionState):
        """更新误解状态"""
        if student_id not in self.states:
            self.states[student_id] = {}
        if mis_id in self.states[student_id]:
            self.states[student_id][mis_id].state = new_state


class BoundaryChecker:
    """边界校验器"""

    # 四年级知识范围
    GRADE_SCOPE = {
        "number": ["大数认识", "因数与倍数", "分数的意义", "小数的意义"],
        "operation": ["四则运算", "运算定律", "简便计算"],
        "geometry": ["角的度量", "平行四边形", "梯形", "三角形", "圆"],
        "measurement": ["面积", "周长", "体积初步"],
        "statistics": ["条形统计图", "折线统计图"],
        "algebra": ["用字母表示数", "简易方程"],
    }

    def check(self, topic: str, question_type: str) -> List[ValidationIssue]:
        """检查是否在知识边界内"""
        issues = []

        # 检查是否超出四年级范围
        advanced_topics = [
            "一元二次方程", "二次函数", "勾股定理", "三角函数",
            "概率论", "微积分", "向量", "矩阵",
        ]
        for advanced in advanced_topics:
            if advanced in topic or advanced in question_type:
                issues.append(ValidationIssue(
                    type="out_of_scope",
                    content=f"超出四年级范围：{advanced}",
                    severity=0.8,
                ))

        return issues


class PrerequisiteChecker:
    """前置知识检查器"""

    PREREQUISITE_GRAPH = {
        "fraction": ["number_concept", "division"],
        "decimal": ["fraction", "number_line"],
        "triangle": ["angle", "line_segment"],
        "circle": ["pi_concept", "measurement"],
        "equation": ["four_operations", "equality"],
        "area": ["measurement", "multiplication"],
        "perimeter": ["measurement", "addition"],
    }

    def check(self, student_id: str, topic: str,
              profile=None) -> bool:
        """检查前置知识是否满足"""
        if topic not in self.PREREQUISITE_GRAPH:
            return True  # 未知话题，假设满足

        prerequisites = self.PREREQUISITE_GRAPH[topic]
        # 简化实现：假设前置知识满足
        # 实际实现应检查学生画像中的知识掌握度
        return True


class ValidationLayer:
    """验证层主类"""

    def __init__(self):
        self.misconception_validator = MisconceptionValidator()
        self.boundary_checker = BoundaryChecker()
        self.prerequisite_checker = PrerequisiteChecker()

    def process(self, context: PipelineContext) -> ValidationResult:
        """处理验证层逻辑"""
        student_id = context.student_id
        beliefs = context.perception.beliefs if context.perception else []
        topic = context.topic

        # 1. 误解验证
        result = self.misconception_validator.validate(
            student_id, beliefs, topic
        )

        # 2. 边界校验
        boundary_issues = self.boundary_checker.check(topic, "")
        result.issues.extend(boundary_issues)

        # 3. 前置知识检查
        result.prerequisite_ok = self.prerequisite_checker.check(
            student_id, topic, context.profile
        )

        return result
