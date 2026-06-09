"""
第1层：感知层（Perception Layer）
职责：知识匹配 + 信念提取 + 情绪检测
铁律：P1响应快（三级匹配）+ P3定位准
目标延迟：<10ms（规则匹配时）
"""

import re
import hashlib
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from .models import (
    PerceptionResult, MatchResult, Belief, PipelineContext
)


class KnowledgeMatcher:
    """三级知识匹配器（P1快速响应）"""

    def __init__(self):
        # 第1级：哈希精确匹配（<1ms）
        self.hash_index: Dict[str, Tuple[str, str]] = {}  # hash -> (topic, question_type)
        # 第2级：规则匹配（<10ms）
        self.rules: List[Tuple[re.Pattern, str, str]] = []  # (pattern, topic, question_type)
        # 第3级：LLM匹配（<500ms，由外部调用）
        self._build_index()

    def _build_index(self):
        """构建匹配索引"""
        # 哈希索引 - 常见问题
        common_questions = {
            "一元一次方程怎么解": ("linear_equation", "solve"),
            "什么是因数": ("factor", "concept"),
            "分数怎么加": ("fraction_add", "compute"),
            "小数怎么乘": ("decimal_multiply", "compute"),
            "长方形面积怎么算": ("rectangle_area", "formula"),
            "三角形面积怎么算": ("triangle_area", "formula"),
            "圆的面积怎么算": ("circle_area", "formula"),
        }
        for question, (topic, qtype) in common_questions.items():
            h = hashlib.md5(question.encode()).hexdigest()
            self.hash_index[h] = (topic, qtype)

        # 规则索引 - 四年级数学知识点
        rule_patterns = [
            # 数与代数
            (r"(大数|亿|万.*读|数位|计数单位)", "large_number", "concept"),
            (r"(因数|倍数|整除|能.*被.*整除)", "factor_multiple", "concept"),
            (r"(质数|素数|合数|质因数)", "prime_number", "concept"),
            (r"(分数|分子|分母|通分|约分)", "fraction", "concept"),
            (r"(小数|十分位|百分位|千分位)", "decimal", "concept"),
            (r"(四则运算|混合运算|运算顺序)", "four_operations", "compute"),
            (r"(加法|减法|乘法|除法).*(定律|性质|交换|结合|分配)", "operation_law", "concept"),
            # 图形与几何
            (r"(角|直角|锐角|钝角|平角|周角)", "angle", "concept"),
            (r"(三角形|等边|等腰|直角三角形)", "triangle", "concept"),
            (r"(平行四边形|梯形|菱形)", "quadrilateral", "concept"),
            (r"(圆|半径|直径|周长|面积)", "circle", "concept"),
            (r"(对称|轴对称|平移|旋转)", "transformation", "concept"),
            # 统计与概率
            (r"(统计|条形|折线|扇形|图表)", "statistics", "concept"),
            (r"(可能性|一定|不可能|可能)", "probability", "concept"),
            # 应用题
            (r"(路程|速度|时间|相遇|追及)", "distance_speed_time", "word_problem"),
            (r"(工作|效率|合作|完成)", "work_problem", "word_problem"),
            (r"(价格|数量|总价|单价)", "price_problem", "word_problem"),
            (r"(年龄|几岁|几年后|几年前)", "age_problem", "word_problem"),
            (r"(鸡兔|头.*脚|只数)", "chicken_rabbit", "word_problem"),
            (r"(盈亏|多.*少|分配)", "surplus_deficit", "word_problem"),
        ]
        for pattern, topic, qtype in rule_patterns:
            self.rules.append((re.compile(pattern), topic, qtype))

    def match(self, text: str) -> MatchResult:
        """三级匹配"""
        import time
        start = time.time()

        # 第1级：哈希精确匹配
        h = hashlib.md5(text.strip().encode()).hexdigest()
        if h in self.hash_index:
            topic, qtype = self.hash_index[h]
            elapsed = (time.time() - start) * 1000
            return MatchResult(
                level=1, topic=topic, question_type=qtype,
                confidence=1.0, time_ms=elapsed
            )

        # 第2级：规则匹配
        for pattern, topic, qtype in self.rules:
            if pattern.search(text):
                elapsed = (time.time() - start) * 1000
                return MatchResult(
                    level=2, topic=topic, question_type=qtype,
                    confidence=0.8, time_ms=elapsed
                )

        # 第3级：需要LLM匹配（返回低置信度）
        elapsed = (time.time() - start) * 1000
        return MatchResult(
            level=3, topic="unknown", question_type="unknown",
            confidence=0.3, time_ms=elapsed
        )


class RuleBasedBeliefExtractor:
    """基于规则的信念提取器（P1快速响应）"""

    # 四年级常见误解模式
    MISCONCEPTION_PATTERNS = [
        # 分数误解
        (r"分母.*越大.*分数越大", "misconception_denominator_bigger",
         "误以为分母越大分数越大", 0.8),
        (r"分子.*越大.*分数越大", "misconception_numerator_bigger",
         "忽略分母比较分数大小", 0.7),
        (r"分数.*就是.*除法", "misconception_fraction_equals_division",
         "混淆分数与除法的关系", 0.5),
        # 小数误解
        (r"小数.*位数.*越多.*越大", "misconception_decimal_digits",
         "误以为小数位数越多数值越大", 0.8),
        (r"0\.\d+.*比.*0\.\d+小", "misconception_decimal_compare",
         "小数比较方法错误", 0.7),
        # 几何误解
        (r"三角形.*面积.*底.*高", "misconception_triangle_area",
         "忘记三角形面积要除以2", 0.9),
        (r"圆.*面积.*2.*π.*r", "misconception_circle_area",
         "混淆圆面积和周长公式", 0.9),
        # 运算误解
        (r"先算.*加法.*再算.*乘法", "misconception_operation_order",
         "运算顺序错误", 0.8),
        (r"0\.\d+.*不是.*分数", "misconception_decimal_not_fraction",
         "误以为小数不是分数", 0.6),
        # 方程误解
        (r"等号.*可以.*移到", "misconception_equals_sign",
         "误解等号的本质", 0.7),
    ]

    def extract(self, text: str) -> List[Belief]:
        """提取学生信念"""
        beliefs = []
        for pattern, belief_id, description, confidence in self.MISCONCEPTION_PATTERNS:
            if re.search(pattern, text):
                beliefs.append(Belief(
                    content=description,
                    confidence=confidence,
                    source=f"rule_{belief_id}",
                ))
        return beliefs


class EmotionDetector:
    """情绪检测器"""

    EMOTION_PATTERNS = {
        "frustrated": [
            (r"(太难了|不会|搞不懂|崩溃|烦死了|不想做|算了|放弃)", 0.8),
            (r"(学不会|看不懂|一头雾水|没思路)", 0.6),
            (r"(too hard|don't want|give up|can't|impossible|frustrated)", 0.8),
            (r"(don't know|no idea|no clue|clueless)", 0.6),
        ],
        "confident": [
            (r"(简单|容易|我会了|知道了|明白了|懂了)", 0.7),
            (r"(做对了|答案是|结果是)", 0.6),
            (r"(easy|simple|got it|understood|know|understand)", 0.7),
            (r"(got the answer|the answer is|the result is)", 0.6),
        ],
        "confused": [
            (r"(为什么|怎么|什么意思|不太懂|不太明白)", 0.5),
            (r"(等一下|嗯\.\.\.|这个嘛)", 0.3),
            (r"(why|how|what does|don't understand|confused)", 0.5),
            (r"(wait|hmm|well|um)", 0.3),
        ],
        "curious": [
            (r"(如果.*呢|为什么.*呢|还有.*吗|可以.*吗)", 0.6),
            (r"(想试试|可以.*吗|有没有)", 0.5),
            (r"(what if|why does|is there|can I|how about)", 0.6),
            (r"(want to try|is it possible|what about)", 0.5),
        ],
    }

    def detect(self, text: str) -> Tuple[str, float]:
        """检测情绪状态"""
        best_emotion = "neutral"
        best_intensity = 0.0

        for emotion, patterns in self.EMOTION_PATTERNS.items():
            for pattern, intensity in patterns:
                if re.search(pattern, text):
                    if intensity > best_intensity:
                        best_emotion = emotion
                        best_intensity = intensity

        return best_emotion, best_intensity


class PerceptionLayer:
    """感知层主类"""

    def __init__(self):
        self.matcher = KnowledgeMatcher()
        self.belief_extractor = RuleBasedBeliefExtractor()
        self.emotion_detector = EmotionDetector()

    def process(self, context: PipelineContext) -> PerceptionResult:
        """处理感知层逻辑"""
        student_input = context.student_input

        # 1. 知识匹配
        match = self.matcher.match(student_input)

        # 2. 信念提取
        beliefs = self.belief_extractor.extract(student_input)

        # 3. 情绪检测
        emotion, intensity = self.emotion_detector.detect(student_input)

        return PerceptionResult(
            match=match,
            beliefs=beliefs,
            emotion=emotion,
            emotion_intensity=intensity,
        )
