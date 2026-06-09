"""
第5层：决策层（Decision Layer）
职责：统一决策 + 模板生成 + 边界检查
铁律：E1不替思考 + E7可解释性
目标延迟：<5ms（模板生成时）
"""

from typing import Dict, List, Optional
from .models import (
    DecisionResult, InquiryType, PipelineContext,
    StudentState, ConflictType, Misconception
)


class InquiryTemplates:
    """追问模板库（E1不替思考）"""

    TEMPLATES = {
        # 引导式追问（探索状态）
        InquiryType.GUIDED: {
            "default": [
                "你能说说你是怎么想的吗？",
                "这一步你是怎么考虑的？",
                "你觉得下一步应该做什么？",
                "你能解释一下你的思路吗？",
            ],
            "fraction": [
                "分数的分子和分母分别表示什么？",
                "你能用图形来表示这个分数吗？",
                "这两个分数，你觉得哪个更大？为什么？",
            ],
            "decimal": [
                "小数点后面的数字表示什么？",
                "你能把这两个小数在数轴上标出来吗？",
                "比较小数大小时，应该先看哪一位？",
            ],
            "geometry": [
                "你能描述一下这个图形的特征吗？",
                "这个角大概有多少度？你是怎么估计的？",
                "你能找到这个图形中的对称轴吗？",
            ],
            "equation": [
                "等号两边现在相等吗？",
                "如果要让两边相等，你觉得应该怎么做？",
                "你能检验一下你的答案吗？",
            ],
        },
        # 提示式追问（局部卡壳）
        InquiryType.HINT: {
            "default": [
                "想想我们之前学过的……",
                "这道题和我们做过的哪道题有点像？",
                "你已经做对了一部分，接下来……",
                "提示：注意看题目中的这个条件……",
            ],
            "L1": ["你已经做对了一部分，接下来……"],
            "L2": ["想想我们之前学过的……", "这道题和我们做过的哪道题有点像？"],
            "L3": ["提示：注意看题目中的这个条件……"],
        },
        # 类比式追问（深度卡壳）
        InquiryType.ANALOGY: {
            "default": [
                "我们先看一个简单的例子……",
                "想象一下，如果你有{items}个苹果……",
                "这就像{scenario}一样……",
            ],
            "fraction": [
                "想象一个披萨切成4块，你吃了1块，这就是1/4",
                "就像分蛋糕一样，分的份数就是分母，吃了几份就是分子",
            ],
            "decimal": [
                "就像钱一样，1.5元就是1元5角",
                "0.1就像把1米分成10份，取其中1份",
            ],
        },
        # 概念重建（概念错误）
        InquiryType.CONCEPT: {
            "default": [
                "我们来想想这个概念的本质……",
                "你觉得{concept}是什么意思？",
                "我们用一个例子来理解……",
            ],
            "misconception_denominator_bigger": [
                "1/2和1/4，哪个大？为什么分母大的反而小？",
                "想想披萨：切成2块吃1块 vs 切成4块吃1块，哪个吃得多？",
            ],
            "misconception_triangle_area": [
                "一个底4高3的长方形，面积是多少？",
                "如果把这个长方形沿对角线剪开，三角形的面积是多少？",
            ],
            "misconception_operation_order": [
                "2+3×4，应该先算什么？为什么？",
                "如果有括号 (2+3)×4，结果一样吗？为什么？",
            ],
            "misconception_decimal_digits": [
                "0.5和0.12，哪个大？为什么？",
                "想想钱：5角 vs 1角2分，哪个多？",
            ],
        },
        # 沉默
        InquiryType.SILENCE: {
            "default": [
                "",  # 不说话
            ],
        },
    }

    def get_template(self, inquiry_type: InquiryType,
                     topic: str = "", sub_key: str = "") -> str:
        """获取追问模板"""
        import random

        templates = self.TEMPLATES.get(inquiry_type, {})
        if sub_key and sub_key in templates:
            return random.choice(templates[sub_key])

        topic_templates = templates.get(topic, [])
        if topic_templates:
            return random.choice(topic_templates)

        return random.choice(templates.get("default", ["你能说说你的想法吗？"]))


class ThinkingBoundaryChecker:
    """思考边界检查器（E1）"""

    # 禁止替学生思考的模式
    FORBIDDEN_PATTERNS = [
        (r"答案是\s*\d+", "直接给出答案"),
        (r"结果等于\s*\d+", "直接给出结果"),
        (r"所以\s*[xX]\s*=\s*\d+", "直接给出变量值"),
        (r"你应该先.*然后.*最后", "给出完整解题步骤"),
        (r"这道题用.*公式", "直接指出使用的公式"),
        (r"正确答案是", "直接给出正确答案"),
        (r"你应该这样做", "直接指导做法"),
    ]

    def check(self, response: str) -> bool:
        """检查是否违反思考边界，返回True表示安全"""
        for pattern, reason in self.FORBIDDEN_PATTERNS:
            if __import__('re').search(pattern, response):
                return False
        return True

    def sanitize(self, response: str) -> str:
        """清洗违反边界的回复"""
        import re
        # 替换直接给答案的表述
        sanitized = response
        sanitized = re.sub(r"答案是\s*\d+", "你觉得答案是多少呢？", sanitized)
        sanitized = re.sub(r"结果等于\s*\d+", "你觉得结果是多少呢？", sanitized)
        sanitized = re.sub(r"正确答案是.*?[。！？]", "你能再想想吗？", sanitized)
        return sanitized


class DecisionExplainer:
    """决策解释器（E7可解释性）"""

    def explain(self, inquiry_type: InquiryType,
                state: StudentState,
                topic: str,
                template: str,
                reasoning_factors: Dict) -> str:
        """生成决策解释"""
        factors = []
        if reasoning_factors.get("state"):
            factors.append(f"学生状态：{reasoning_factors['state']}")
        if reasoning_factors.get("emotion"):
            factors.append(f"情绪：{reasoning_factors['emotion']}")
        if reasoning_factors.get("conflict"):
            factors.append(f"冲突：{reasoning_factors['conflict']}")
        if reasoning_factors.get("difficulty"):
            factors.append(f"难度：{reasoning_factors['difficulty']:.0%}")

        explanation = f"[决策] {inquiry_type.value} | " + " | ".join(factors)
        return explanation


class DecisionLayer:
    """决策层主类"""

    def __init__(self):
        self.templates = InquiryTemplates()
        self.boundary_checker = ThinkingBoundaryChecker()
        self.explainer = DecisionExplainer()

    def process(self, context: PipelineContext) -> DecisionResult:
        """处理决策层逻辑"""
        state = context.reasoning.state if context.reasoning else StudentState.EXPLORING
        topic = context.topic
        conflict = context.reasoning.top_conflict if context.reasoning else None

        # 1. 根据状态选择追问类型
        inquiry_type = self._select_inquiry_type(state, conflict)

        # 2. 获取模板
        sub_key = self._get_sub_key(state, conflict, context.validation)
        template = self.templates.get_template(inquiry_type, topic, sub_key)

        # 3. 检查思考边界
        if not self.boundary_checker.check(template):
            template = self.boundary_checker.sanitize(template)

        # 4. 检查是否需要注入"我也不会"
        thinking_injected = False
        if state == StudentState.DEEP_STUCK and conflict:
            if conflict.type == ConflictType.LOGICAL:
                template = f"这个问题我也要想想……{template}"
                thinking_injected = True

        # 5. 生成解释
        reasoning_factors = {
            "state": state.value,
            "emotion": context.perception.emotion if context.perception else "neutral",
            "conflict": conflict.description if conflict else "",
            "difficulty": context.personalization.difficulty_level if context.personalization else 0.5,
        }
        explanation = self.explainer.explain(
            inquiry_type, state, topic, template, reasoning_factors
        )

        return DecisionResult(
            inquiry_type=inquiry_type,
            response_text=template,
            template_id=f"{inquiry_type.value}_{topic}",
            thinking_injected=thinking_injected,
            reasoning=explanation,
            confidence=0.7,
        )

    def _select_inquiry_type(self, state: StudentState,
                             conflict=None) -> InquiryType:
        """选择追问类型"""
        if state == StudentState.FRUSTRATED:
            return InquiryType.SILENCE
        if state == StudentState.SILENT:
            return InquiryType.SILENCE
        if state == StudentState.CONCEPT_ERROR:
            return InquiryType.CONCEPT
        if state == StudentState.DEEP_STUCK:
            return InquiryType.ANALOGY
        if state == StudentState.PARTIAL_STUCK:
            return InquiryType.HINT
        return InquiryType.GUIDED

    def _get_sub_key(self, state: StudentState,
                     conflict=None, validation=None) -> str:
        """获取模板子键"""
        if conflict and conflict.type == ConflictType.LOGICAL:
            # 从冲突描述中提取误解ID
            for mis_id in ["misconception_denominator_bigger",
                           "misconception_triangle_area",
                           "misconception_operation_order",
                           "misconception_decimal_digits"]:
                if mis_id in conflict.description:
                    return mis_id
        return ""
