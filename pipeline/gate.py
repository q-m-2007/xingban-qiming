"""
第0层：守门层（Gate Layer）
职责：沉默决策 + 思考边界检查 + 输入验证
铁律：E1不替思考 + E2服从节奏 + E5沉默权
目标延迟：<1ms
"""

import re
from typing import List, Optional, Dict
from .models import GateResult, PipelineContext


class SilenceDecisionEngine:
    """沉默决策引擎（E5）"""

    # 5种沉默条件
    SILENCE_PATTERNS = [
        # 学生在思考中
        (r"(等一下|让我想想|别急|我再想想|稍等|wait|let me think|hold on|give me a moment)", "thinking", "学生正在思考"),
        # 学生表达情绪需要空间
        (r"(烦死了|不想说|别问了|让我静静|leave me alone|don't ask|stop asking)", "emotion_space", "学生需要情绪空间"),
        # 学生在自主解题中
        (r"(我试试|我自己来|别帮忙|让我做|let me try|I'll do it|don't help)", "self_solving", "学生自主解题中"),
        # 学生刚回答完需要消化
        (r"(等一下|嗯…|这个嘛|让我整理|wait|hmm|let me organize)", "digesting", "学生在消化信息"),
        # 连续追问过多
        (r"", "too_many_questions", ""),  # 由外部计数器触发
    ]

    def __init__(self, max_consecutive_questions: int = 3):
        self.max_consecutive_questions = max_consecutive_questions
        self.question_count = 0

    def should_stay_silent(self, student_input: str,
                           consecutive_questions: int) -> Optional[GateResult]:
        """判断是否应该保持沉默"""
        # 检查连续追问次数
        if consecutive_questions >= self.max_consecutive_questions:
            return GateResult(
                should_respond=False,
                silence_reason=f"连续追问{consecutive_questions}次，学生需要思考空间",
                boundary_ok=True,
                input_valid=True,
            )

        # 检查沉默模式
        for pattern, reason, detail in self.SILENCE_PATTERNS:
            if pattern and re.search(pattern, student_input):
                return GateResult(
                    should_respond=False,
                    silence_reason=detail,
                    boundary_ok=True,
                    input_valid=True,
                )

        return None


class ThinkingBoundary:
    """思考边界检查（E1）"""

    # 禁止替学生思考的模式
    FORBIDDEN_PATTERNS = [
        (r"答案是\s*\d+", "直接给出答案"),
        (r"结果等于\s*\d+", "直接给出结果"),
        (r"所以\s*[xX]\s*=\s*\d+", "直接给出变量值"),
        (r"你应该先.*然后.*最后", "给出完整解题步骤"),
        (r"这道题用.*公式", "直接指出使用的公式"),
    ]

    def check(self, response_text: str) -> GateResult:
        """检查回复是否违反思考边界"""
        for pattern, reason in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, response_text):
                return GateResult(
                    should_respond=True,  # 仍然回复，但需要修改内容
                    boundary_ok=False,
                    input_valid=True,
                    silence_reason=f"E1违反：{reason}",
                )

        return GateResult(
            should_respond=True,
            boundary_ok=True,
            input_valid=True,
        )


class InputValidator:
    """输入验证"""

    # 无效输入模式
    INVALID_PATTERNS = [
        (r"^[\s]*$", "empty", "空输入"),
        (r"^[\s]*[。，！？\.]{1,3}[\s]*$", "punctuation_only", "只有标点"),
        (r"^[\s]*[a-zA-Z]{1,3}[\s]*$", "meaningless", "无意义字符"),
    ]

    # 非数学话题检测
    OFF_TOPIC_PATTERNS = [
        (r"(今天天气|吃什么|看视频|打游戏|聊天)", "off_topic"),
        (r"(你好|hello|hi|hey)", "greeting"),
    ]

    def validate(self, student_input: str) -> GateResult:
        """验证输入有效性"""
        for pattern, code, desc in self.INVALID_PATTERNS:
            if re.search(pattern, student_input):
                return GateResult(
                    should_respond=False,
                    input_valid=False,
                    silence_reason=f"无效输入：{desc}",
                )

        return GateResult(
            should_respond=True,
            input_valid=True,
            boundary_ok=True,
        )


class GateLayer:
    """守门层主类"""

    def __init__(self):
        self.silence_engine = SilenceDecisionEngine()
        self.thinking_boundary = ThinkingBoundary()
        self.input_validator = InputValidator()
        self._consecutive_questions: Dict[str, int] = {}

    def process(self, context: PipelineContext) -> GateResult:
        """处理守门层逻辑"""
        student_input = context.student_input
        student_id = context.student_id

        # 1. 输入验证
        result = self.input_validator.validate(student_input)
        if not result.input_valid:
            return result

        # 2. 沉默决策
        consecutive = self._consecutive_questions.get(student_id, 0)
        result = self.silence_engine.should_stay_silent(
            student_input, consecutive
        )
        if result is not None:
            return result

        # 3. 正常通过
        self._consecutive_questions[student_id] = 0
        return GateResult(
            should_respond=True,
            input_valid=True,
            boundary_ok=True,
            sanitized_input=student_input.strip(),
        )

    def check_response_boundary(self, response_text: str) -> GateResult:
        """检查回复是否在思考边界内"""
        return self.thinking_boundary.check(response_text)

    def increment_question_count(self, student_id: str):
        """增加追问计数"""
        self._consecutive_questions[student_id] = self._consecutive_questions.get(student_id, 0) + 1

    def reset_question_count(self, student_id: str):
        """重置追问计数"""
        self._consecutive_questions[student_id] = 0
