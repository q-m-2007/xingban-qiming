"""
CPPA 证据提取器
优化1：LLM深层语义分析（替代粗糙的关键词匹配）
优化7：兴趣/投入度信号检测
"""
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime


# ──────────────────────────────────────────
# 关键词信号库（LLM不可用时的降级方案）
# ──────────────────────────────────────────

SIGNAL_KEYWORDS = {
    'visual': [
        '画图', '看图', '图形', '图像', '辅助线', '标出来', '连起来',
        '几何', '形状', '坐标', '曲线', '看出来', '直觉上', '平行', '垂直',
    ],
    'verbal': [
        '设x', '列方程', '公式', '代入', '计算', '化简', '根据',
        '由题意', '推导', '移项', '合并', '展开', '因式', '通分',
    ],
    'kinesthetic': [
        '试了', '代入试', '验证', '检验', '试试看', '先试', '再试',
    ],
    'inductive': ['比如', '例如', '举个例子', '我发现', '规律是', '观察到'],
    'deductive': ['根据定理', '由公式', '由定义', '可以推出', '代入公式'],
    'analogical': ['和.*类似', '跟.*一样', '差不多', '这种题', '之前做过'],
    'forward': ['从条件', '已知', '题目说', '由条件', '从.*出发'],
    'backward': ['要证', '要求', '目标是', '反推', '倒着想'],
    'trial': ['先猜', '假设', '不妨设', '假如', '看看对不对'],
}

EMOTION_SIGNALS = {
    'frustrated': ['太难了', '不想做', '算了', '放弃', '学不会', '搞不懂', '崩溃', '烦死了'],
    'confident': ['我会', '简单', '容易', '秒杀', '一眼', '肯定'],
    'uncertain': ['可能', '也许', '不确定', '对吗', '是这样吗', '好像'],
    'engaged': ['然后呢', '为什么', '怎么', '什么意思', '我想想', '让我试试'],
}


# ──────────────────────────────────────────
# 优化1：LLM深层证据提取
# ──────────────────────────────────────────

EXTRACTION_PROMPT = """你是一个教育心理学专家。分析学生的回答，判断其思维特征。

题目：{problem}
学生回答：{response}
历史：{history}

判断维度（每项0-1分，0.5=中性）：

信息获取偏好：
- visual: 学生是否依赖画图、空间想象？注意区分"我在画图"和"我不会画图"
- verbal: 学生是否依赖文字分析、列式？
- kinesthetic: 学生是否喜欢试数、代入验证？

推理方式：
- inductive: 是否从具体例子出发总结？
- deductive: 是否从定理/公式出发推导？
- analogical: 是否套用已知模式？

推导方向：
- forward: 从条件推向结论？
- backward: 从结论反推条件？
- trial: 先猜再验证？

认知特征：
- fast_jump: 思路跳跃，跳过步骤？
- rigorous: 步骤完整详细？
- divergent: 能想到多种方法？

元认知：
- abstract_reasoning: 本次推理的抽象程度 0-1
- reasoning_quality: 本次推理的逻辑质量 0-1

投入度信号（优化7）：
- bored: 学生是否无聊/太简单？
- challenged: 学生是否在享受挑战？
- curious: 学生是否好奇/主动提问？
- engagement_level: 整体投入度 0-1

只输出JSON，不要解释。
{{
    "visual": 0.0, "verbal": 0.0, "kinesthetic": 0.0,
    "inductive": 0.0, "deductive": 0.0, "analogical": 0.0,
    "forward": 0.0, "backward": 0.0, "trial": 0.0,
    "fast_jump": 0.0, "rigorous": 0.0, "divergent": 0.0,
    "abstract_reasoning": 0.0, "reasoning_quality": 0.0,
    "bored": 0.0, "challenged": 0.0, "curious": 0.0, "engagement_level": 0.0
}}"""


# ──────────────────────────────────────────
# 证据提取器
# ──────────────────────────────────────────

class EvidenceExtractor:
    """从学生回答中提取思维特征证据"""

    def __init__(self, use_llm: bool = False, llm_client=None):
        self.use_llm = use_llm
        self.llm_client = llm_client

    def extract(self, student_response: str,
                problem_context: str = '',
                conversation_history: List[str] = None) -> Dict[str, float]:
        """
        提取思维特征证据

        优先用LLM深层分析，降级到关键词匹配
        """
        if self.use_llm and self.llm_client:
            return self._extract_with_llm(
                student_response, problem_context, conversation_history or []
            )
        return self._extract_with_keywords(student_response)

    def _extract_with_keywords(self, response: str) -> Dict[str, float]:
        """关键词匹配（降级方案）"""
        evidence = {}
        for dimension, keywords in SIGNAL_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                if re.search(kw, response):
                    matches += 1
            if matches > 0:
                score = min(0.9, 0.3 + matches * 0.15)
                evidence[dimension] = score

        # 回复特征
        length = len(response)
        if length > 100:
            evidence['rigorous'] = 0.7
        elif length < 20:
            evidence['fast_jump'] = 0.7

        method_keywords = ['方法', '另一种', '还可以', '换个']
        if any(kw in response for kw in method_keywords):
            evidence['divergent'] = 0.7

        return evidence

    def _extract_with_llm(self, response: str, problem: str,
                          history: List[str]) -> Dict[str, float]:
        """LLM深层语义分析"""
        prompt = EXTRACTION_PROMPT.format(
            problem=problem,
            response=response,
            history=' | '.join(history[-3:]) if history else '无'
        )

        try:
            result = self.llm_client.call(prompt)
            import json
            # 提取JSON部分
            json_match = re.search(r'\{[^}]+\}', result, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                return data
        except Exception:
            pass

        # LLM失败，降级到关键词
        return self._extract_with_keywords(response)

    def build_extraction_prompt(self, response: str, problem: str,
                                history: List[str]) -> str:
        """构建LLM提取prompt（供外部调用）"""
        return EXTRACTION_PROMPT.format(
            problem=problem,
            response=response,
            history=' | '.join(history[-3:]) if history else '无'
        )

    def parse_llm_result(self, llm_output: str) -> Dict[str, float]:
        """解析LLM输出"""
        import json
        try:
            json_match = re.search(r'\{[^}]+\}', llm_output, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass
        return {}

    def _detect_emotion(self, response: str) -> str:
        """检测学生情绪"""
        for emotion, keywords in EMOTION_SIGNALS.items():
            if any(kw in response for kw in keywords):
                return emotion
        return 'neutral'


# ──────────────────────────────────────────
# 优化7：投入度信号检测器
# ──────────────────────────────────────────

class EngagementDetector:
    """兴趣/投入度信号检测器"""

    def detect(self, student_response: str, time_spent: float,
               is_correct: bool, is_follow_up_question: bool = False) -> Dict[str, float]:
        """
        检测学生的投入度信号

        返回：{signal_type: score}
        """
        signals = {
            'bored': 0.0,
            'challenged': 0.0,
            'curious': 0.0,
            'frustrated': 0.0,
            'engagement_level': 0.5,
        }

        # ── 无聊信号：快速+正确+简短 ──
        if time_spent < 20 and is_correct and len(student_response) < 30:
            signals['bored'] = 0.7
            signals['engagement_level'] = 0.3

        # ── 挑战享受信号：长思考+正确 ──
        if time_spent > 90 and is_correct:
            signals['challenged'] = 0.8
            signals['engagement_level'] = 0.8

        # ── 好奇信号：主动提问 ──
        question_words = ['为什么', '怎么', '？', '?', '什么', '能不能', '可不可以']
        if any(w in student_response for w in question_words):
            signals['curious'] = 0.9
            signals['engagement_level'] = 0.9

        # ── 挫败信号 ──
        frustration_words = ['太难了', '不会', '不想', '算了', '放弃']
        if any(w in student_response for w in frustration_words):
            signals['frustrated'] = 0.8
            signals['engagement_level'] = 0.2

        # ── 投入信号：详细回答 ──
        if len(student_response) > 80:
            signals['engagement_level'] = max(signals['engagement_level'], 0.7)

        # ── 主动尝试信号 ──
        try_words = ['我试了', '我发现', '我想到', '我觉得']
        if any(w in student_response for w in try_words):
            signals['engagement_level'] = max(signals['engagement_level'], 0.7)

        return signals


# ──────────────────────────────────────────
# 解题过程追踪器
# ──────────────────────────────────────────

class ProcessTracker:
    """追踪学生解题的每一步"""

    def __init__(self):
        self.current_steps: List[Dict] = []
        self.method_detected: Optional[str] = None
        self.error_step: Optional[int] = None

    def start_problem(self, problem_id: str):
        self.current_steps = []
        self.method_detected = None
        self.error_step = None

    def add_step(self, student_response: str, step_index: int):
        step = {
            'index': step_index,
            'content': student_response,
            'detected_action': self._detect_action(student_response),
            'is_correct': None,
            'error_type': None,
        }
        self.current_steps.append(step)
        if self.method_detected is None:
            self.method_detected = self._detect_method(student_response)

    def mark_error(self, step_index: int, error_type: str):
        self.error_step = step_index
        for step in self.current_steps:
            if step['index'] == step_index:
                step['is_correct'] = False
                step['error_type'] = error_type
                break

    def mark_correct(self, step_index: int):
        for step in self.current_steps:
            if step['index'] == step_index:
                step['is_correct'] = True
                break

    def get_process_summary(self) -> Dict:
        return {
            'method': self.method_detected,
            'total_steps': len(self.current_steps),
            'error_step': self.error_step,
            'steps': self.current_steps,
            'completed': self.error_step is None,
        }

    def _detect_action(self, response: str) -> str:
        actions = {
            '设未知数': ['设', '令'],
            '列方程': ['列', '方程', '等式'],
            '展开': ['展开', '乘开'],
            '移项': ['移项', '移'],
            '因式分解': ['因式', '分解'],
            '代入公式': ['代入', '公式'],
            '配方': ['配方', '完全平方'],
            '画图': ['画', '图'],
            '试数': ['试', '代入试'],
            '计算': ['算', '计算', '等于'],
        }
        for action, keywords in actions.items():
            if any(kw in response for kw in keywords):
                return action
        return '未知'

    def _detect_method(self, response: str) -> str:
        method_signals = {
            'factoring': ['因式分解', '提取公因式', '两个括号'],
            'quadratic_formula': ['求根公式', '判别式', '代入公式'],
            'completing_square': ['配方', '完全平方'],
            'graphical': ['画图', '图像', '图形'],
            'trial': ['试', '代入试', '一个一个试'],
        }
        for method, keywords in method_signals.items():
            if any(kw in response for kw in keywords):
                return method
        return 'unknown'
