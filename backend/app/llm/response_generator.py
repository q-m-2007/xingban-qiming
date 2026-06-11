"""
教学回复生成器
根据TeachingDecision + 学生画像，生成个性化教学语言
"""

from typing import Optional, List, Dict, Any
from .client import LLMClient, LLMError


# 策略描述映射
STRATEGY_DESCRIPTIONS = {
    "A_guided": "引导式提问 - 通过问题引导学生自己发现答案",
    "B_hint": "提示+提问 - 给出提示后再提问，帮助学生突破卡点",
    "C_analogy": "类比教学 - 用生活中的例子帮助学生理解抽象概念",
    "D_concept_rebuild": "概念重建 - 纠正学生的错误概念，重新建立正确认知",
    "E_comfort": "安抚降级 - 降低难度，帮助学生重建信心",
    "F_break_inertia": "突破惯性 - 引导学生尝试新的解题方法",
}

# 学生状态描述
STATE_DESCRIPTIONS = {
    "S1_exploring": "主动探索中，思路基本正确",
    "S2_partial_stuck": "局部卡壳，需要提示",
    "S3_deep_stuck": "深度卡住，完全不知道怎么做",
    "S4_concept_error": "存在错误概念，需要纠正",
    "S5_frustrated": "情绪低落，需要安抚",
}

# 思维风格描述
STYLE_DESCRIPTIONS = {
    "visual": "视觉型 - 喜欢用图形、图像理解问题",
    "verbal": "语言型 - 喜欢用文字、定义理解问题",
    "kinesthetic": "动手型 - 喜欢通过尝试、操作来学习",
    "inductive": "归纳型 - 喜欢从例子中总结规律",
    "deductive": "演绎型 - 喜欢从原理推导结论",
    "analogical": "类比型 - 喜欢用已知知识类比新知识",
}


class ResponseGenerator:
    """教学回复生成器"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def generate(
        self,
        strategy: str,
        student_state: str,
        problem: str,
        student_message: str,
        conversation_history: List[str],
        recommended_method: Optional[str] = None,
        reasoning: Optional[str] = None,
        profile: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        生成个性化教学回复

        Args:
            strategy: 教学策略（如 "A_guided", "C_analogy"）
            student_state: 学生状态（如 "S3_deep_stuck"）
            problem: 当前题目
            student_message: 学生刚说的话
            conversation_history: 对话历史
            recommended_method: 推荐的解法
            reasoning: 策略选择理由
            profile: 学生画像

        Returns:
            个性化教学回复
        """
        # 构建系统提示词
        system = self._build_system_prompt()

        # 构建用户提示词
        user_prompt = self._build_user_prompt(
            strategy=strategy,
            student_state=student_state,
            problem=problem,
            student_message=student_message,
            conversation_history=conversation_history,
            recommended_method=recommended_method,
            reasoning=reasoning,
            profile=profile,
        )

        try:
            response = await self.llm.chat(
                prompt=user_prompt,
                system=system,
                temperature=0.7
            )
            return response.strip()
        except LLMError as e:
            # 降级到模板回复
            return self._fallback_response(strategy, student_state, problem, student_message)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是"启明"，一个温柔、耐心的AI数学家教老师。

你的特点：
1. 语气亲切自然，像真人老师一样和学生对话
2. 善于用问题引导学生思考，不直接给答案
3. 会根据学生的思维风格调整教学方式
4. 会用生活中的例子帮助学生理解抽象概念
5. 学生做错时不会批评，而是引导发现错误
6. 学生沮丧时会安抚鼓励

你的教学原则：
- 引导优先：通过提问让学生自己发现答案
- 个性化：根据学生的思维风格选择合适的讲解方式
- 循序渐进：从简单到复杂，逐步深入
- 正向反馈：肯定学生的努力和进步

回复要求：
- 控制在150字以内
- 语气自然亲切
- 不要用"作为AI"之类的自我介绍
- 直接进入教学内容"""

    def _build_user_prompt(
        self,
        strategy: str,
        student_state: str,
        problem: str,
        student_message: str,
        conversation_history: List[str],
        recommended_method: Optional[str],
        reasoning: Optional[str],
        profile: Optional[Dict[str, Any]],
    ) -> str:
        """构建用户提示词"""
        parts = []

        # 学生画像
        if profile:
            style = profile.get("style_label", "未知")
            strengths = profile.get("strengths", [])
            parts.append(f"【学生画像】\n- 思维风格：{style}")
            if strengths:
                parts.append(f"- 擅长：{', '.join(strengths)}")

        # 学生状态
        state_desc = STATE_DESCRIPTIONS.get(student_state, student_state)
        parts.append(f"【学生状态】{state_desc}")

        # 教学策略
        strategy_desc = STRATEGY_DESCRIPTIONS.get(strategy, strategy)
        parts.append(f"【教学策略】{strategy_desc}")
        if reasoning:
            parts.append(f"【策略理由】{reasoning}")

        # 推荐解法
        if recommended_method:
            parts.append(f"【推荐解法】{recommended_method}")

        # 题目
        parts.append(f"【当前题目】{problem}")

        # 对话历史
        if conversation_history:
            history_text = "\n".join([f"- {msg}" for msg in conversation_history[-5:]])
            parts.append(f"【对话历史】\n{history_text}")

        # 学生刚说的话
        parts.append(f"【学生刚说】\"{student_message}\"")

        # 指令
        parts.append("""
【请生成回复】
根据上述信息，生成一段个性化的教学回复。
- 如果学生说"不会"或"不知道"：用类比或引导问题帮助学生开始思考
- 如果学生给错答案：引导学生发现错误，不要直接说"错了"
- 如果学生给对答案：肯定并引导思考其他方法
- 如果学生情绪低落：先安抚鼓励，再降低难度""")

        return "\n\n".join(parts)

    def _fallback_response(
        self,
        strategy: str,
        student_state: str,
        problem: str,
        student_message: str
    ) -> str:
        """降级模板回复"""
        if "analogy" in strategy.lower() or "C" in strategy:
            return f"让我用一个更简单的例子来帮你理解。\n\n对于 {problem}，你能先想想，什么数相乘等于6，相加等于5？"
        elif "hint" in strategy.lower() or "B" in strategy:
            return f"我给你一个提示：试试看看能不能把方程左边因式分解。\n\n你有什么想法？"
        elif "comfort" in strategy.lower() or "E" in strategy:
            return f"没关系，我们慢慢来。\n\n先试试一个简单的问题：x² - 5x + 6 = 0，你觉得x=2是答案吗？代进去试试看。"
        elif "break" in strategy.lower() or "F" in strategy:
            return f"你已经很熟练了，但我想让你试试另一种方法。\n\n对于 {problem}，除了你常用的方法，还能怎么解？"
        else:
            return f"好的，让我们一起来分析 {problem}。\n\n你先说说你的想法，我来帮你看看。"
