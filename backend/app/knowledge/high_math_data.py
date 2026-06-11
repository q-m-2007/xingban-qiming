"""
星伴·启明 — 扩展种子数据：高中数学 TOP30 考点

每个考点包含：
  - name: 考点名称
  - description: 考点描述
  - error_types: 常见错误类型列表
  - strategies: 推荐追问策略名称列表
"""

HIGH_MATH_KP = [
    # ── 集合与逻辑 ──────────────────────────────
    {
        "name": "集合的基本运算",
        "description": "交集、并集、补集的概念与运算，Venn图表示",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "general_probe"],
    },
    {
        "name": "充分条件与必要条件",
        "description": "充分条件、必要条件、充要条件的判断",
        "error_types": ["concept_confusion", "logic_error"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    # ── 函数 ──────────────────────────────────
    {
        "name": "函数的概念与性质",
        "description": "定义域、值域、单调性、奇偶性、周期性",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "boundary_explore"],
    },
    {
        "name": "指数函数",
        "description": "y=a^x的图像与性质，指数运算法则",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "对数函数",
        "description": "y=log_a(x)的图像与性质，对数运算法则",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "幂函数",
        "description": "y=x^α的图像与性质，常见幂函数",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "函数的零点",
        "description": "零点存在定理，二分法求零点",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    # ── 三角函数 ──────────────────────────────
    {
        "name": "三角函数的定义",
        "description": "任意角的三角函数定义，单位圆，弧度制",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "general_probe"],
    },
    {
        "name": "三角恒等变换",
        "description": "和差化积、积化和差、二倍角公式、半角公式",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "decompose"],
    },
    {
        "name": "三角函数的图像与性质",
        "description": "y=Asin(ωx+φ)的图像、周期、振幅、相位",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "解三角形",
        "description": "正弦定理、余弦定理、面积公式",
        "error_types": ["formula_misuse", "condition_misread"],
        "strategies": ["formula_misuse", "condition_misread"],
    },
    # ── 数列 ──────────────────────────────────
    {
        "name": "等差数列",
        "description": "通项公式、前n项和公式、性质",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "等比数列",
        "description": "通项公式、前n项和公式、性质",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "数列求和",
        "description": "裂项相消法、错位相减法、分组求和法",
        "error_types": ["formula_misuse", "method_confusion"],
        "strategies": ["formula_misuse", "decompose"],
    },
    # ── 不等式 ────────────────────────────────
    {
        "name": "基本不等式",
        "description": "均值不等式a+b≥2√(ab)，求最值",
        "error_types": ["formula_misuse", "condition_misread"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "线性规划",
        "description": "线性目标函数在约束条件下的最值",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    # ── 立体几何 ──────────────────────────────
    {
        "name": "空间几何体",
        "description": "棱柱、棱锥、棱台、圆柱、圆锥、球的表面积与体积",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "点线面位置关系",
        "description": "平行、垂直的判定与性质",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    {
        "name": "空间向量",
        "description": "空间向量的坐标运算，数量积，向量积",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    # ── 解析几何 ──────────────────────────────
    {
        "name": "直线与方程",
        "description": "斜率、点斜式、两点式、一般式，两直线位置关系",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "圆与方程",
        "description": "圆的标准方程、一般方程，直线与圆的位置关系",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "椭圆",
        "description": "椭圆的标准方程、几何性质、焦点三角形",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "decompose"],
    },
    {
        "name": "双曲线",
        "description": "双曲线的标准方程、几何性质、渐近线",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "decompose"],
    },
    {
        "name": "抛物线",
        "description": "抛物线的标准方程、几何性质、焦点弦",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "decompose"],
    },
    # ── 概率统计 ──────────────────────────────
    {
        "name": "排列组合",
        "description": "分类计数原理、分步计数原理、排列数、组合数",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    {
        "name": "二项式定理",
        "description": "二项式展开式、通项公式、系数性质",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "随机变量及其分布",
        "description": "离散型随机变量、期望、方差、常见分布",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "统计案例",
        "description": "回归分析、独立性检验、相关系数",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    # ── 导数 ──────────────────────────────────
    {
        "name": "导数的概念与运算",
        "description": "导数的定义、基本公式、运算法则",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "导数的应用",
        "description": "单调性、极值、最值、切线方程",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
]


def seed_high_math_kb(kb):
    """
    将高中数学TOP30考点灌入知识库
    
    Args:
        kb: KnowledgeBase实例
        
    Returns:
        添加的知识点数量
    """
    count = 0
    for kp in HIGH_MATH_KP:
        kb.add_knowledge_point(
            name=kp["name"],
            description=kp["description"],
            error_types=kp["error_types"],
            strategies=kp["strategies"],
            grade="高中",
            subject="数学"
        )
        count += 1
    return count
