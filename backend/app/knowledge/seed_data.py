"""
星伴·启明 — 种子数据：初中数学 TOP30 考点

每个考点包含：
  - name: 考点名称
  - description: 考点描述
  - error_types: 常见错误类型列表
  - strategies: 推荐追问策略名称列表
"""

TOP30_KP = [
    # ── 数与代数 ──────────────────────────────
    {
        "name": "有理数运算",
        "description": "有理数的加减乘除乘方混合运算，含绝对值、相反数、倒数",
        "error_types": ["calculation_error", "concept_confusion"],
        "strategies": ["calculation_error", "general_probe"],
    },
    {
        "name": "实数与平方根",
        "description": "平方根、立方根、无理数的概念与运算，实数比较大小",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "calculation_error"],
    },
    {
        "name": "整式运算",
        "description": "合并同类项、去括号、整式的加减乘除、幂运算",
        "error_types": ["calculation_error", "concept_confusion"],
        "strategies": ["calculation_error", "general_probe"],
    },
    {
        "name": "因式分解",
        "description": "提公因式法、公式法（平方差、完全平方）、十字相乘法",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "分式运算",
        "description": "分式的约分、通分、加减乘除、分式方程",
        "error_types": ["calculation_error", "formula_misuse"],
        "strategies": ["calculation_error", "formula_misuse"],
    },
    {
        "name": "一元一次方程",
        "description": "一元一次方程的解法：移项、合并同类项、系数化为1",
        "error_types": ["calculation_error", "condition_misread"],
        "strategies": ["calculation_error", "condition_misread"],
    },
    {
        "name": "二元一次方程组",
        "description": "代入消元法、加减消元法解二元一次方程组",
        "error_types": ["calculation_error", "formula_misuse"],
        "strategies": ["calculation_error", "formula_misuse"],
    },
    {
        "name": "一元二次方程",
        "description": "配方法、公式法、因式分解法解一元二次方程，判别式",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error", "decompose"],
    },
    {
        "name": "一元二次方程根与系数的关系",
        "description": "韦达定理：x₁+x₂=-b/a, x₁·x₂=c/a",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "不等式（组）",
        "description": "一元一次不等式的解法、不等式组的解集、数轴表示",
        "error_types": ["calculation_error", "concept_confusion"],
        "strategies": ["calculation_error", "concept_confusion"],
    },
    # ── 函数 ──────────────────────────────────
    {
        "name": "平面直角坐标系",
        "description": "点的坐标、象限、对称点、距离公式",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "condition_misread"],
    },
    {
        "name": "一次函数",
        "description": "一次函数y=kx+b的图像与性质，待定系数法求解析式",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "反比例函数",
        "description": "反比例函数y=k/x的图像与性质，k的几何意义",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "二次函数",
        "description": "二次函数y=ax²+bx+c的图像、顶点、对称轴、最值",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error", "decompose"],
    },
    {
        "name": "二次函数的实际应用",
        "description": "抛物线型的实际问题（最大利润、最大面积、运动轨迹）",
        "error_types": ["condition_misread", "formula_misuse"],
        "strategies": ["condition_misread", "formula_misuse", "decompose"],
    },
    # ── 几何 ──────────────────────────────────
    {
        "name": "平行线与相交线",
        "description": "三线八角、平行线判定与性质、垂线、距离",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "condition_misread"],
    },
    {
        "name": "三角形内角和与外角",
        "description": "三角形内角和180°、外角定理、三角形分类",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "calculation_error"],
    },
    {
        "name": "全等三角形",
        "description": "SSS/SAS/ASA/AAS/HL判定，全等三角形的性质",
        "error_types": ["condition_misread", "concept_confusion"],
        "strategies": ["condition_misread", "concept_confusion"],
    },
    {
        "name": "等腰三角形",
        "description": "等边对等角、三线合一、等边三角形的性质与判定",
        "error_types": ["condition_misread", "concept_confusion"],
        "strategies": ["condition_misread", "concept_confusion"],
    },
    {
        "name": "勾股定理",
        "description": "直角三角形a²+b²=c²及其逆定理、勾股数",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "多边形内角和与外角和",
        "description": "n边形内角和(n-2)×180°、外角和360°",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "平行四边形",
        "description": "平行四边形、矩形、菱形、正方形的性质与判定",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "condition_misread"],
    },
    {
        "name": "相似三角形",
        "description": "AA/SAS/SSS判定、相似比、面积比",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "圆的基本性质",
        "description": "垂径定理、圆周角定理、圆心角、弧、弦的关系",
        "error_types": ["condition_misread", "concept_confusion"],
        "strategies": ["condition_misread", "concept_confusion"],
    },
    {
        "name": "直线与圆的位置关系",
        "description": "切线的判定与性质、切线长定理、割线定理",
        "error_types": ["formula_misuse", "condition_misread"],
        "strategies": ["formula_misuse", "condition_misread"],
    },
    # ── 统计与概率 ────────────────────────────
    {
        "name": "数据的收集与整理",
        "description": "频数分布表、直方图、扇形图、平均数、中位数、众数",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "calculation_error"],
    },
    {
        "name": "方差与标准差",
        "description": "方差公式、标准差、离散程度分析",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "概率计算",
        "description": "列举法、树状图、列表法求概率",
        "error_types": ["condition_misread", "calculation_error"],
        "strategies": ["condition_misread", "calculation_error"],
    },
    # ── 综合 ──────────────────────────────────
    {
        "name": "几何图形的变换",
        "description": "平移、旋转、轴对称、中心对称的性质与作图",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "condition_misread"],
    },
    {
        "name": "动态几何问题",
        "description": "动点问题中的函数关系、最值、分类讨论",
        "error_types": ["condition_misread", "formula_misuse"],
        "strategies": ["decompose", "condition_misread", "formula_misuse"],
    },
]


def seed_knowledge_base(kb):
    """
    将 TOP30 考点灌入 ChromaDB 知识库。

    Args:
        kb: KnowledgeBase 实例

    Returns:
        添加的知识点数量
    """
    count = 0
    for kp in TOP30_KP:
        kb.add_knowledge_point(
            name=kp["name"],
            description=kp["description"],
            error_types=kp["error_types"],
            strategies=kp["strategies"],
        )
        count += 1
    return count
