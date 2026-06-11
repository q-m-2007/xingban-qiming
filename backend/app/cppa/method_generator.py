"""
CPPA 解法库自动生成器（优化4）
用LLM为任意知识点生成多解法+类比题+变式题
"""
import json
import re
from typing import Dict, List, Optional

from .method_bank import Method, AnalogyProblem, VariantProblem, MethodBank


# ──────────────────────────────────────────
# LLM生成Prompt模板
# ──────────────────────────────────────────

METHOD_GENERATION_PROMPT = """你是一个资深数学教研专家。为以下知识点生成完整的多解法知识库。

知识点：{topic}
年级：{grade}
教材版本：{textbook}

请生成以下内容（JSON格式）：

1. 解法列表（至少3种，包含所有常见方法）：
{{
    "methods": [
        {{
            "id": "method_id",
            "name": "解法名称",
            "difficulty": 0.0-1.0,
            "efficiency": 0.0-1.0,
            "generalizability": 0.0-1.0,
            "cognitive_requirements": {{
                "visual": 0.0-1.0, "verbal": 0.0-1.0, "kinesthetic": 0.0-1.0,
                "inductive": 0.0-1.0, "deductive": 0.0-1.0, "analogical": 0.0-1.0,
                "forward": 0.0-1.0, "backward": 0.0-1.0, "trial": 0.0-1.0,
                "fast_jump": 0.0-1.0, "rigorous": 0.0-1.0, "divergent": 0.0-1.0,
                "abstract_reasoning": 0.0-1.0, "challenge_drive": 0.0-1.0
            }},
            "steps": ["步骤1", "步骤2", ...],
            "when_to_use": "适用场景",
            "common_errors": ["常见错误1", "常见错误2"]
        }}
    ]
}}

2. 每种解法的类比题（3个难度层级）：
{{
    "analogy_problems": {{
        "method_id": [
            {{
                "level": 1,
                "problem": "简单题目",
                "answer": "答案",
                "guide_question": "引导问题",
                "purpose": "这道题的目的"
            }},
            {{"level": 2, ...}},
            {{"level": 3, ...}}
        ]
    }}
}}

3. 每种解法的变式题（3道）：
{{
    "variant_problems": {{
        "method_id": [
            {{
                "level": 1,
                "problem": "原题重做",
                "answer": "答案"
            }},
            {{
                "level": 2,
                "problem": "变式题",
                "answer": "答案"
            }},
            {{
                "level": 3,
                "problem": "原题",
                "answer": "答案",
                "reverse_question": "逆向问题：为什么这样做？"
            }}
        ]
    }}
}}

只输出JSON，不要解释。"""


# ──────────────────────────────────────────
# 解法库生成器
# ──────────────────────────────────────────

class MethodGenerator:
    """用LLM自动生成解法库"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def generate_for_topic(self, topic: str, grade: str = '九年级',
                           textbook: str = '人教版') -> Dict:
        """
        为一个知识点生成完整的解法库

        返回：{'methods': [...], 'analogy_problems': {...}, 'variant_problems': {...}}
        """
        if not self.llm_client:
            return self._generate_builtin(topic)

        prompt = METHOD_GENERATION_PROMPT.format(
            topic=topic, grade=grade, textbook=textbook
        )

        try:
            result = self.llm_client.call(prompt)
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            print(f"LLM生成失败: {e}，使用内置数据")

        return self._generate_builtin(topic)

    def _generate_builtin(self, topic: str) -> Dict:
        """内置的解法库（一元二次方程）"""
        if topic == '一元二次方程':
            return {
                'methods': [
                    {
                        'id': 'factoring', 'name': '因式分解法',
                        'difficulty': 0.3, 'efficiency': 0.9, 'generalizability': 0.6,
                        'cognitive_requirements': {
                            'visual': 0.2, 'verbal': 0.3, 'kinesthetic': 0.5,
                            'inductive': 0.6, 'deductive': 0.2, 'analogical': 0.3,
                            'forward': 0.3, 'backward': 0.2, 'trial': 0.5,
                            'fast_jump': 0.3, 'rigorous': 0.3, 'divergent': 0.2,
                            'abstract_reasoning': 0.3, 'challenge_drive': 0.2,
                        },
                        'steps': ['化为一般形式', '找因数组合', '写成括号形式', '求解'],
                        'when_to_use': '可分解为整数因式时',
                        'common_errors': ['忘记化为一般形式', '找错因数'],
                    },
                    {
                        'id': 'quadratic_formula', 'name': '求根公式法',
                        'difficulty': 0.5, 'efficiency': 0.7, 'generalizability': 1.0,
                        'cognitive_requirements': {
                            'visual': 0.1, 'verbal': 0.8, 'kinesthetic': 0.2,
                            'inductive': 0.1, 'deductive': 0.7, 'analogical': 0.2,
                            'forward': 0.5, 'backward': 0.2, 'trial': 0.1,
                            'fast_jump': 0.2, 'rigorous': 0.7, 'divergent': 0.1,
                            'abstract_reasoning': 0.5, 'challenge_drive': 0.3,
                        },
                        'steps': ['确定a,b,c', '计算判别式', '代入公式', '化简'],
                        'when_to_use': '任何一元二次方程',
                        'common_errors': ['b忘带符号', '分母写错'],
                    },
                    {
                        'id': 'completing_square', 'name': '配方法',
                        'difficulty': 0.6, 'efficiency': 0.5, 'generalizability': 0.8,
                        'cognitive_requirements': {
                            'visual': 0.4, 'verbal': 0.5, 'kinesthetic': 0.3,
                            'inductive': 0.2, 'deductive': 0.6, 'analogical': 0.3,
                            'forward': 0.6, 'backward': 0.3, 'trial': 0.2,
                            'fast_jump': 0.2, 'rigorous': 0.7, 'divergent': 0.2,
                            'abstract_reasoning': 0.6, 'challenge_drive': 0.4,
                        },
                        'steps': ['化系数为1', '移常数项', '配方', '开方求解'],
                        'when_to_use': '推导公式或接近完全平方时',
                        'common_errors': ['忘记化系数', '配方加减不一致'],
                    },
                ],
                'analogy_problems': {
                    'factoring': [
                        {'level': 1, 'problem': 'x² = 4', 'answer': 'x = ±2',
                         'guide_question': 'x等于多少时x²等于4？', 'purpose': '建立两解直觉'},
                        {'level': 2, 'problem': 'x² - 5x + 6 = 0', 'answer': 'x = 2 或 3',
                         'guide_question': '找两个数加起来-5乘起来6？', 'purpose': '因式分解基础'},
                    ],
                    'quadratic_formula': [
                        {'level': 1, 'problem': 'x² + 2x + 1 = 0', 'answer': 'x = -1',
                         'guide_question': '判别式等于多少？', 'purpose': '熟悉判别式'},
                    ],
                },
                'variant_problems': {
                    'factoring': [
                        {'level': 1, 'problem': 'x² - 5x + 6 = 0', 'answer': 'x = 2 或 3'},
                        {'level': 2, 'problem': 'x² - 7x + 12 = 0', 'answer': 'x = 3 或 4'},
                        {'level': 3, 'problem': 'x² - 5x + 6 = 0', 'answer': 'x = 2 或 3',
                         'reverse_question': '因式分解法的数学原理是什么？'},
                    ],
                },
            }
        return {'methods': [], 'analogy_problems': {}, 'variant_problems': {}}

    def load_into_bank(self, topic: str, data: Dict, bank: MethodBank):
        """将生成的数据加载到解法库"""
        # 加载解法
        for m_data in data.get('methods', []):
            method = Method(
                id=m_data['id'],
                name=m_data['name'],
                topic=topic,
                difficulty=m_data.get('difficulty', 0.5),
                efficiency=m_data.get('efficiency', 0.5),
                generalizability=m_data.get('generalizability', 0.5),
                cognitive_requirements=m_data.get('cognitive_requirements', {}),
                steps=m_data.get('steps', []),
                when_to_use=m_data.get('when_to_use', ''),
                common_errors=m_data.get('common_errors', []),
            )
            bank.add_custom_method(topic, method)

        # 加载类比题
        for method_id, problems in data.get('analogy_problems', {}).items():
            for p in problems:
                analogy = AnalogyProblem(
                    id=f'gen_{method_id}_{p["level"]}',
                    topic=topic,
                    method=method_id,
                    level=p['level'],
                    problem=p['problem'],
                    answer=p['answer'],
                    guide_question=p.get('guide_question', ''),
                    purpose=p.get('purpose', ''),
                )
                bank.add_custom_analogy(method_id, analogy)

        # 加载变式题
        for method_id, problems in data.get('variant_problems', {}).items():
            for p in problems:
                variant = VariantProblem(
                    id=f'var_{method_id}_{p["level"]}',
                    original_topic=topic,
                    method=method_id,
                    level=p['level'],
                    problem=p['problem'],
                    answer=p['answer'],
                    reverse_question=p.get('reverse_question', ''),
                )
                if method_id not in bank.variant_problems:
                    bank.variant_problems[method_id] = []
                bank.variant_problems[method_id].append(variant)


# ──────────────────────────────────────────
# 批量生成器
# ──────────────────────────────────────────

class BatchMethodGenerator:
    """批量为多个知识点生成解法库"""

    def __init__(self, llm_client=None):
        self.generator = MethodGenerator(llm_client)

    def generate_for_topics(self, topics: List[Dict[str, str]],
                            bank: MethodBank) -> int:
        """
        批量生成

        topics: [{'topic': '一元二次方程', 'grade': '九年级', 'textbook': '人教版'}, ...]
        返回：成功生成的知识点数量
        """
        success_count = 0
        for t in topics:
            try:
                data = self.generator.generate_for_topic(
                    t['topic'], t.get('grade', '九年级'), t.get('textbook', '人教版')
                )
                if data.get('methods'):
                    self.generator.load_into_bank(t['topic'], data, bank)
                    success_count += 1
            except Exception as e:
                print(f"生成 {t['topic']} 失败: {e}")
        return success_count
