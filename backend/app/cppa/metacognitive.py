"""
CPPA 元认知反思模块（优化6）
每道题结束后，给学生一个"思维复盘"
教学生"怎么想"，不只是"怎么做"
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from .cognitive_profile import CognitiveProfile, ForgettingAwareProfile
from .method_bank import MethodBank, Method


@dataclass
class MetacognitiveFeedback:
    """元认知反馈"""
    feedback_type: str             # 'efficiency' | 'strategy' | 'method_awareness' | 'growth'
    message: str                   # 反馈内容
    insight: str                   # 核心洞察
    action_suggestion: str         # 行动建议
    confidence: float              # 反馈置信度


class MetacognitiveReflector:
    """元认知反思生成器"""

    def __init__(self, method_bank: MethodBank):
        self.bank = method_bank

    def reflect(self, problem: str, topic: str,
                method_used: str, method_recommended: str,
                success: bool, time_spent: float,
                profile: ForgettingAwareProfile,
                alternative_methods: List[str] = None) -> Optional[MetacognitiveFeedback]:
        """
        生成元认知反思

        只在有意义的时候生成，不是每道题都给
        """
        feedbacks = []

        # ── 反馈1：效率反思 ──
        # 学生做对了但花了很长时间
        if success and time_spent > 120:
            feedbacks.append(self._efficiency_reflection(
                method_used, time_spent, alternative_methods
            ))

        # ── 反馈2：策略选择反思 ──
        # 学生用的方法不是推荐的方法
        if method_used != method_recommended and success:
            feedbacks.append(self._strategy_reflection(
                method_used, method_recommended, time_spent
            ))

        # ── 反馈3：方法意识反思 ──
        # 学生总是用同一种方法
        if profile.base_profile.divergent < 0.3:
            feedbacks.append(self._method_awareness_reflection(
                method_used, alternative_methods
            ))

        # ── 反馈4：成长反思 ──
        # 学生之前不会，现在会了
        mastery = profile.get_effective_mastery(method_used)
        if success and mastery > 0.7:
            feedbacks.append(self._growth_reflection(method_used))

        # ── 反馈5：遗忘提醒 ──
        need_review = profile.get_methods_needing_review(threshold=0.3)
        if need_review:
            feedbacks.append(self._forgetting_reflection(need_review))

        # 返回最有价值的反馈
        if feedbacks:
            # 优先级：效率 > 策略 > 遗忘 > 方法意识 > 成长
            priority = {'efficiency': 5, 'strategy': 4, 'forgetting': 3,
                       'method_awareness': 2, 'growth': 1}
            feedbacks.sort(key=lambda f: priority.get(f.feedback_type, 0), reverse=True)
            return feedbacks[0]

        return None

    def _efficiency_reflection(self, method_used: str, time_spent: float,
                               alternatives: List[str]) -> MetacognitiveFeedback:
        """效率反思：做对了但太慢"""
        method_obj = self.bank.get_method_by_id(method_used)
        method_name = method_obj.name if method_obj else method_used

        # 找到更快的替代方法
        faster_alternative = None
        if alternatives:
            for alt_id in alternatives:
                alt = self.bank.get_method_by_id(alt_id)
                if alt and alt.efficiency > (method_obj.efficiency if method_obj else 0.5):
                    faster_alternative = alt
                    break

        if faster_alternative:
            return MetacognitiveFeedback(
                feedback_type='efficiency',
                message=f"你用{method_name}做对了，但花了{time_spent:.0f}秒。"
                       f"如果用{faster_alternative.name}，可能更快。",
                insight="同一道题有多种解法，选对方法可以事半功倍",
                action_suggestion=f"以后遇到这类题，先花5秒想想：用{faster_alternative.name}会不会更快？",
                confidence=0.8,
            )

        return MetacognitiveFeedback(
            feedback_type='efficiency',
            message=f"你做对了，但花了{time_spent:.0f}秒。可以想想有没有更快的方法。",
            insight="做对不等于做得好，效率也是能力的一部分",
            action_suggestion="做完一道题后，问问自己：有没有更简洁的方法？",
            confidence=0.6,
        )

    def _strategy_reflection(self, method_used: str, recommended: str,
                             time_spent: float) -> MetacognitiveFeedback:
        """策略选择反思"""
        used_obj = self.bank.get_method_by_id(method_used)
        rec_obj = self.bank.get_method_by_id(recommended)
        used_name = used_obj.name if used_obj else method_used
        rec_name = rec_obj.name if rec_obj else recommended

        return MetacognitiveFeedback(
            feedback_type='strategy',
            message=f"你用了{used_name}，做对了！我本来想推荐{rec_name}。"
                   f"说明你有自己的解题思路，这很好。",
            insight="解题方法没有绝对的对错，关键是你能灵活选择",
            action_suggestion="下次遇到类似的题，试试另一种方法，看看有什么不同",
            confidence=0.7,
        )

    def _method_awareness_reflection(self, method_used: str,
                                     alternatives: List[str]) -> MetacognitiveFeedback:
        """方法意识反思：学生总是用同一种方法"""
        used_obj = self.bank.get_method_by_id(method_used)
        used_name = used_obj.name if used_obj else method_used

        alt_names = []
        if alternatives:
            for alt_id in alternatives[:2]:
                alt = self.bank.get_method_by_id(alt_id)
                if alt:
                    alt_names.append(alt.name)

        if alt_names:
            return MetacognitiveFeedback(
                feedback_type='method_awareness',
                message=f"你一直在用{used_name}，这种方法你很熟练。"
                       f"但你知道吗，还有{'和'.join(alt_names)}也可以解这类题。",
                insight="掌握多种方法 = 拥有多把钥匙，遇到不同的锁都能开",
                action_suggestion=f"下次试试用{alt_names[0]}做一道题，感受一下不同方法的特点",
                confidence=0.7,
            )

        return MetacognitiveFeedback(
            feedback_type='method_awareness',
            message=f"你很擅长{used_name}！多掌握几种方法会让你更灵活。",
            insight="真正的高手不是只会一种方法，而是能根据题目选择最合适的方法",
            action_suggestion="试着了解其他解法，拓展你的解题工具箱",
            confidence=0.5,
        )

    def _growth_reflection(self, method_used: str) -> MetacognitiveFeedback:
        """成长反思：之前不会，现在会了"""
        used_obj = self.bank.get_method_by_id(method_used)
        used_name = used_obj.name if used_obj else method_used

        return MetacognitiveFeedback(
            feedback_type='growth',
            message=f"你在{used_name}上进步很大！现在已经能熟练运用了。",
            insight="学习就是从不会到会的过程，你正在经历这个过程",
            action_suggestion="继续保持，同时可以尝试挑战更难的题目",
            confidence=0.8,
        )

    def _forgetting_reflection(self, need_review: List[str]) -> MetacognitiveFeedback:
        """遗忘提醒"""
        method_names = []
        for mid in need_review[:2]:
            m = self.bank.get_method_by_id(mid)
            if m:
                method_names.append(m.name)

        if method_names:
            return MetacognitiveFeedback(
                feedback_type='forgetting',
                message=f"你有一段时间没用{'和'.join(method_names)}了，可能有点生疏。",
                insight="学习需要定期复习，否则会遗忘",
                action_suggestion=f"建议做几道用{'或'.join(method_names)}的题，巩固一下",
                confidence=0.7,
            )

        return None

    def generate_reflection_prompt(self, problem: str, method_used: str,
                                   success: bool, time_spent: float,
                                   profile: CognitiveProfile) -> str:
        """
        生成LLM反思prompt（供外部LLM调用）

        当需要更自然的反思语言时使用
        """
        return f"""你是一个经验丰富的数学老师。学生刚刚做完一道题，请给他一个简短的思维复盘。

题目：{problem}
学生用的方法：{method_used}
是否做对：{'做对了' if success else '做错了'}
耗时：{time_spent:.0f}秒
学生特点：{profile.get_style_label()}

要求：
1. 先肯定学生做得好的地方
2. 指出可以改进的地方（如果有）
3. 给一个具体的行动建议
4. 语言要自然、亲切，像朋友聊天
5. 不超过3句话
6. 不要说"你错了"，用"可以试试"代替"""
