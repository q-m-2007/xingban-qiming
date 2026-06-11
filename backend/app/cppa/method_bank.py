"""
CPPA 多解法知识库
每道题有多种解法，每种解法有认知需求、难度、效率等属性
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ──────────────────────────────────────────
# 解法定义
# ──────────────────────────────────────────

@dataclass
class Method:
    """解法定义"""
    id: str                          # 解法唯一标识
    name: str                        # 解法名称
    topic: str                       # 知识点/题目类型
    difficulty: float                # 难度 [0, 1]
    efficiency: float                # 效率 [0, 1]（越高效越高）
    generalizability: float          # 可推广性 [0, 1]
    cognitive_requirements: Dict[str, float] = field(default_factory=dict)
    steps: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    when_to_use: str = ''            # 适用场景描述
    common_errors: List[str] = field(default_factory=list)


# ──────────────────────────────────────────
# 一元二次方程解法库
# ──────────────────────────────────────────

QUADRATIC_METHODS = [
    Method(
        id='factoring',
        name='因式分解法',
        topic='一元二次方程',
        difficulty=0.3,
        efficiency=0.9,
        generalizability=0.6,
        cognitive_requirements={
            'visual': 0.2, 'verbal': 0.3, 'kinesthetic': 0.5,
            'inductive': 0.6, 'deductive': 0.2, 'analogical': 0.3,
            'forward': 0.3, 'backward': 0.2, 'trial': 0.5,
            'fast_jump': 0.3, 'rigorous': 0.3, 'divergent': 0.2,
            'abstract_reasoning': 0.3, 'challenge_drive': 0.2,
        },
        steps=[
            '将方程化为一般形式 ax²+bx+c=0',
            '找两个数，加起来等于b，乘起来等于ac',
            '将方程写成两个括号相乘的形式',
            '令每个括号等于0，求解',
        ],
        when_to_use='当方程可以分解为两个整数因式时（判别式为完全平方数）',
        common_errors=[
            '忘记先化为一般形式（右边=0）',
            '找错因数组合',
            '令括号等于0后忘记验证',
        ],
    ),
    Method(
        id='quadratic_formula',
        name='求根公式法',
        topic='一元二次方程',
        difficulty=0.5,
        efficiency=0.7,
        generalizability=1.0,
        cognitive_requirements={
            'visual': 0.1, 'verbal': 0.8, 'kinesthetic': 0.2,
            'inductive': 0.1, 'deductive': 0.7, 'analogical': 0.2,
            'forward': 0.5, 'backward': 0.2, 'trial': 0.1,
            'fast_jump': 0.2, 'rigorous': 0.7, 'divergent': 0.1,
            'abstract_reasoning': 0.5, 'challenge_drive': 0.3,
        },
        steps=[
            '确定a, b, c的值（注意符号）',
            '计算判别式 Δ = b² - 4ac',
            '代入公式 x = (-b ± √Δ) / (2a)',
            '化简得到两个根',
        ],
        when_to_use='任何一元二次方程，尤其当因式分解困难时',
        common_errors=[
            'b忘记带符号',
            '分母写成a而不是2a',
            '判别式计算错误',
            '±只取一个值',
        ],
    ),
    Method(
        id='completing_square',
        name='配方法',
        topic='一元二次方程',
        difficulty=0.6,
        efficiency=0.5,
        generalizability=0.8,
        cognitive_requirements={
            'visual': 0.4, 'verbal': 0.5, 'kinesthetic': 0.3,
            'inductive': 0.2, 'deductive': 0.6, 'analogical': 0.3,
            'forward': 0.6, 'backward': 0.3, 'trial': 0.2,
            'fast_jump': 0.2, 'rigorous': 0.7, 'divergent': 0.2,
            'abstract_reasoning': 0.6, 'challenge_drive': 0.4,
        },
        steps=[
            '将二次项系数化为1（两边除以a）',
            '将常数项移到等号右边',
            '方程两边加上一次项系数一半的平方',
            '左边写成完全平方式',
            '开平方求解',
        ],
        when_to_use='当需要推导求根公式，或方程接近完全平方时',
        common_errors=[
            '忘记先化二次项系数为1',
            '配方时加减不一致',
            '开平方后忘记±',
        ],
    ),
    Method(
        id='graphical',
        name='图像法',
        topic='一元二次方程',
        difficulty=0.4,
        efficiency=0.6,
        generalizability=0.7,
        cognitive_requirements={
            'visual': 0.9, 'verbal': 0.1, 'kinesthetic': 0.3,
            'inductive': 0.3, 'deductive': 0.2, 'analogical': 0.3,
            'forward': 0.4, 'backward': 0.3, 'trial': 0.3,
            'fast_jump': 0.4, 'rigorous': 0.2, 'divergent': 0.3,
            'abstract_reasoning': 0.4, 'challenge_drive': 0.2,
        },
        steps=[
            '画出 y = ax²+bx+c 的图像',
            '找到图像与x轴的交点',
            '交点的横坐标就是方程的根',
        ],
        when_to_use='判断根的个数、估计根的大致范围、函数相关问题',
        common_errors=[
            '图像画得不准确',
            '忘记抛物线开口方向',
            '交点判断错误',
        ],
    ),
    Method(
        id='direct_observation',
        name='直接观察法',
        topic='一元二次方程',
        difficulty=0.2,
        efficiency=0.95,
        generalizability=0.3,
        cognitive_requirements={
            'visual': 0.5, 'verbal': 0.2, 'kinesthetic': 0.5,
            'inductive': 0.5, 'deductive': 0.1, 'analogical': 0.3,
            'forward': 0.3, 'backward': 0.2, 'trial': 0.7,
            'fast_jump': 0.6, 'rigorous': 0.1, 'divergent': 0.2,
            'abstract_reasoning': 0.2, 'challenge_drive': 0.1,
        },
        steps=[
            '观察方程的特殊形式',
            '直接看出解（如 x²=4 → x=±2）',
        ],
        when_to_use='特殊形式的方程（如 x²=k, (x-a)²=k）',
        common_errors=[
            '忘记负根',
            '开方后忘记±',
        ],
    ),
]


# ──────────────────────────────────────────
# 类比题库
# ──────────────────────────────────────────

@dataclass
class AnalogyProblem:
    """类比题"""
    id: str
    topic: str                       # 知识点
    method: str                      # 对应的解法
    level: int                       # 难度层级 1-5
    problem: str                     # 题目
    answer: str                      # 答案
    guide_question: str              # 引导问题
    purpose: str                     # 这道类比题的目的


ANALOGY_PROBLEMS = {
    'factoring': [
        AnalogyProblem(
            id='ana_fact_1', topic='一元二次方程', method='factoring',
            level=1,
            problem='x² = 4',
            answer='x = 2 或 x = -2',
            guide_question='x等于多少时，x²等于4？',
            purpose='建立"一个方程可以有两个解"的直觉',
        ),
        AnalogyProblem(
            id='ana_fact_2', topic='一元二次方程', method='factoring',
            level=2,
            problem='x² - 5x + 6 = 0',
            answer='x = 2 或 x = 3',
            guide_question='能不能找两个数，加起来等于-5，乘起来等于6？',
            purpose='建立因式分解的基本思路',
        ),
        AnalogyProblem(
            id='ana_fact_3', topic='一元二次方程', method='factoring',
            level=3,
            problem='2x² - 5x + 3 = 0',
            answer='x = 3/2 或 x = 1',
            guide_question='试试 (2x-?)(x-?)=0 的形式？',
            purpose='处理有系数的因式分解',
        ),
    ],
    'quadratic_formula': [
        AnalogyProblem(
            id='ana_qf_1', topic='一元二次方程', method='quadratic_formula',
            level=1,
            problem='x² + 2x + 1 = 0',
            answer='x = -1',
            guide_question='判别式Δ等于多少？',
            purpose='熟悉判别式的计算',
        ),
        AnalogyProblem(
            id='ana_qf_2', topic='一元二次方程', method='quadratic_formula',
            level=2,
            problem='x² - 3x + 2 = 0',
            answer='x = 1 或 x = 2',
            guide_question='代入求根公式，分子分母分别是什么？',
            purpose='练习完整的求根公式流程',
        ),
    ],
    'completing_square': [
        AnalogyProblem(
            id='ana_cs_1', topic='一元二次方程', method='completing_square',
            level=1,
            problem='x² + 4x + 4 = 0',
            answer='x = -2',
            guide_question='左边能不能写成 (x+?)² 的形式？',
            purpose='认识完全平方式',
        ),
        AnalogyProblem(
            id='ana_cs_2', topic='一元二次方程', method='completing_square',
            level=2,
            problem='x² + 6x + 5 = 0',
            answer='x = -1 或 x = -5',
            guide_question='x²+6x+9等于多少？那x²+6x+5比它少多少？',
            purpose='练习配方的核心步骤',
        ),
    ],
}


# ──────────────────────────────────────────
# 变式题库（用于三阶验证）
# ──────────────────────────────────────────

@dataclass
class VariantProblem:
    """变式题"""
    id: str
    original_topic: str
    method: str
    level: int                      # 1=原题重做, 2=变式, 3=逆向
    problem: str
    answer: str
    reverse_question: str = ''       # 逆向问题（level=3时）


VARIANT_PROBLEMS = {
    'factoring': [
        VariantProblem(
            id='var_fact_1', original_topic='一元二次方程',
            method='factoring', level=1,
            problem='x² - 5x + 6 = 0',
            answer='x = 2 或 x = 3',
        ),
        VariantProblem(
            id='var_fact_2', original_topic='一元二次方程',
            method='factoring', level=2,
            problem='x² - 7x + 12 = 0',
            answer='x = 3 或 x = 4',
        ),
        VariantProblem(
            id='var_fact_3', original_topic='一元二次方程',
            method='factoring', level=3,
            problem='x² - 5x + 6 = 0',
            answer='x = 2 或 x = 3',
            reverse_question='为什么因式分解法能找到方程的解？它的数学原理是什么？',
        ),
    ],
    'quadratic_formula': [
        VariantProblem(
            id='var_qf_1', original_topic='一元二次方程',
            method='quadratic_formula', level=1,
            problem='2x² - 3x + 1 = 0',
            answer='x = 1 或 x = 1/2',
        ),
        VariantProblem(
            id='var_qf_2', original_topic='一元二次方程',
            method='quadratic_formula', level=2,
            problem='3x² + 2x - 1 = 0',
            answer='x = 1/3 或 x = -1',
        ),
        VariantProblem(
            id='var_qf_3', original_topic='一元二次方程',
            method='quadratic_formula', level=3,
            problem='2x² - 3x + 1 = 0',
            answer='x = 1 或 x = 1/2',
            reverse_question='求根公式是怎么推导出来的？为什么分母是2a？',
        ),
    ],
}


# ──────────────────────────────────────────
# 解法库管理器
# ──────────────────────────────────────────

class MethodBank:
    """解法库管理器"""

    def __init__(self):
        self.methods: Dict[str, List[Method]] = {}
        self.analogy_problems: Dict[str, List[AnalogyProblem]] = {}
        self.variant_problems: Dict[str, List[VariantProblem]] = {}

        # 加载内置数据
        self._load_builtin()

    def _load_builtin(self):
        """加载内置解法库"""
        self.methods['一元二次方程'] = QUADRATIC_METHODS
        self.analogy_problems = ANALOGY_PROBLEMS
        self.variant_problems = VARIANT_PROBLEMS

    def get_methods(self, topic: str) -> List[Method]:
        """获取某个知识点的所有解法"""
        return self.methods.get(topic, [])

    def get_method_by_id(self, method_id: str) -> Optional[Method]:
        """根据ID获取解法"""
        for methods in self.methods.values():
            for m in methods:
                if m.id == method_id:
                    return m
        return None

    def get_analogy_problems(self, method_id: str,
                             max_level: int = 3) -> List[AnalogyProblem]:
        """获取某解法的类比题"""
        problems = self.analogy_problems.get(method_id, [])
        return [p for p in problems if p.level <= max_level]

    def get_variant_problems(self, method_id: str) -> List[VariantProblem]:
        """获取某解法的变式题"""
        return self.variant_problems.get(method_id, [])

    def add_custom_method(self, topic: str, method: Method):
        """添加自定义解法"""
        if topic not in self.methods:
            self.methods[topic] = []
        self.methods[topic].append(method)

    def add_custom_analogy(self, method_id: str, problem: AnalogyProblem):
        """添加自定义类比题"""
        if method_id not in self.analogy_problems:
            self.analogy_problems[method_id] = []
        self.analogy_problems[method_id].append(problem)
