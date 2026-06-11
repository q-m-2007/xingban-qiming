"""
星伴·启明 — 追问策略库

策略基类 + 按错误类型区分的追问策略实现。
每种策略返回追问提示词 (follow-up prompt) 和预期的动作。
"""

from abc import ABC, abstractmethod
from typing import Optional


class QuestionStrategy(ABC):
    """追问策略基类"""

    @abstractmethod
    def get_name(self) -> str:
        ...

    @abstractmethod
    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        """
        返回:
          { "action": "continue"|"explain"|"decompose",
            "prompt": str,
            "hints": [str, ...] }
        """
        ...


# ── 具体策略 ──────────────────────────────────────────────


class ConditionMisreadStrategy(QuestionStrategy):
    """审题不清：遗漏或误解已知条件"""

    def get_name(self) -> str:
        return "condition_misread"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "continue",
            "prompt": "再仔细读一下题目，看看有没有遗漏的条件？",
            "hints": ["圈出题目中的每个已知量", "检查单位是否统一"],
        }


class FormulaMisuseStrategy(QuestionStrategy):
    """公式误用/策略错误"""

    def get_name(self) -> str:
        return "formula_misuse"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "continue",
            "prompt": "你用的是哪个公式？这个公式适用于什么情况？",
            "hints": ["回忆公式的使用条件", "检查变量是否对应"],
        }


class CalculationErrorStrategy(QuestionStrategy):
    """计算错误"""

    def get_name(self) -> str:
        return "calculation_error"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "continue",
            "prompt": "再验算一下你的计算步骤，可以分步写给我看。",
            "hints": ["重点检查正负号", "检查分数运算", "可以用估算验证结果"],
        }


class ConceptConfusionStrategy(QuestionStrategy):
    """概念混淆"""

    def get_name(self) -> str:
        return "concept_confusion"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "explain",
            "prompt": "这个知识点容易混淆，我先帮你梳理一下相关概念……",
            "hints": ["区别这两个概念", "它们各自适用的场景"],
        }


class DecomposeStrategy(QuestionStrategy):
    """需要拆解为子问题"""

    def get_name(self) -> str:
        return "decompose"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "decompose",
            "prompt": "这道题比较复杂，我们把它拆成几个小问题一步步来解决。",
            "hints": ["先求中间量", "分情况讨论"],
        }


class GeneralProbeStrategy(QuestionStrategy):
    """通用追问（兜底）"""

    def get_name(self) -> str:
        return "general_probe"

    def generate_prompt(self, question: str, student_answer: str, **kwargs) -> dict:
        return {
            "action": "continue",
            "prompt": "能再详细说说你的解题过程吗？",
            "hints": [],
        }


# ── 策略注册表 ──────────────────────────────────────────────


class StrategyRegistry:
    """
    策略注册表 —— 运行时按错误类型/考点名称查找对应的追问策略。
    可被 LLM 调用识别，也可手动映射。
    """

    def __init__(self):
        self._strategies: dict[str, QuestionStrategy] = {}

    def register(self, strategy: QuestionStrategy):
        self._strategies[strategy.get_name()] = strategy

    def get(self, name: str) -> Optional[QuestionStrategy]:
        return self._strategies.get(name)

    def all(self) -> list[QuestionStrategy]:
        return list(self._strategies.values())

    def default_prompt(self) -> dict:
        return GeneralProbeStrategy().generate_prompt("", "")


# 创建全局策略注册表实例，注册所有内置策略
default_registry = StrategyRegistry()
for s in [
    ConditionMisreadStrategy(),
    FormulaMisuseStrategy(),
    CalculationErrorStrategy(),
    ConceptConfusionStrategy(),
    DecomposeStrategy(),
    GeneralProbeStrategy(),
]:
    default_registry.register(s)
