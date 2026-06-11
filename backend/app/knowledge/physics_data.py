"""
星伴·启明 — 扩展种子数据：高中物理 TOP30 考点

每个考点包含：
  - name: 考点名称
  - description: 考点描述
  - error_types: 常见错误类型列表
  - strategies: 推荐追问策略名称列表
"""

PHYSICS_KP = [
    # ── 力学 ──────────────────────────────────
    {
        "name": "匀变速直线运动",
        "description": "速度公式、位移公式、速度-位移公式、自由落体",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "牛顿运动定律",
        "description": "牛顿第一、第二、第三定律，受力分析",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    {
        "name": "力的合成与分解",
        "description": "平行四边形法则、三角形法则、正交分解",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    {
        "name": "摩擦力",
        "description": "静摩擦力、滑动摩擦力、摩擦因数",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "boundary_explore"],
    },
    {
        "name": "共点力平衡",
        "description": "平衡条件、三力汇交原理、整体法与隔离法",
        "error_types": ["concept_confusion", "method_confusion"],
        "strategies": ["concept_confusion", "decompose"],
    },
    {
        "name": "曲线运动",
        "description": "运动的合成与分解、抛体运动、圆周运动",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "万有引力与航天",
        "description": "万有引力定律、天体运动、宇宙速度",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "功和功率",
        "description": "功的定义、正功负功、功率、机车启动问题",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "动能定理",
        "description": "动能、动能定理、应用动能定理解题",
        "error_types": ["formula_misuse", "condition_misread"],
        "strategies": ["formula_misuse", "decompose"],
    },
    {
        "name": "机械能守恒定律",
        "description": "重力势能、弹性势能、机械能守恒条件",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    # ── 动量 ──────────────────────────────────
    {
        "name": "动量定理",
        "description": "动量、冲量、动量定理",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "动量守恒定律",
        "description": "动量守恒条件、碰撞、爆炸、反冲",
        "error_types": ["concept_confusion", "condition_misread"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    # ── 振动与波 ──────────────────────────────
    {
        "name": "机械振动",
        "description": "简谐运动、单摆、振动图像",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "机械波",
        "description": "波的形成、波长、频率、波速、波的干涉衍射",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    # ── 热学 ──────────────────────────────────
    {
        "name": "分子动理论",
        "description": "分子热运动、布朗运动、分子力",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "general_probe"],
    },
    {
        "name": "气体实验定律",
        "description": "玻意耳定律、查理定律、盖-吕萨克定律",
        "error_types": ["formula_misuse", "condition_misread"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "热力学定律",
        "description": "热力学第一定律、能量守恒、热力学第二定律",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    # ── 电学 ──────────────────────────────────
    {
        "name": "电场强度",
        "description": "点电荷电场、电场线、电场叠加",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "电势与电势能",
        "description": "电势、电势差、等势面、电势能",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    {
        "name": "电容器",
        "description": "电容定义、平行板电容器、电容器的串并联",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "欧姆定律",
        "description": "欧姆定律、电阻定律、串并联电路",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
    {
        "name": "电功与电功率",
        "description": "电功、电功率、焦耳定律、电热",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    {
        "name": "闭合电路欧姆定律",
        "description": "电动势、内阻、路端电压、电源效率",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "磁场",
        "description": "磁感应强度、磁通量、安培力、洛伦兹力",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "电磁感应",
        "description": "法拉第电磁感应定律、楞次定律、自感",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "counterexample"],
    },
    {
        "name": "交变电流",
        "description": "正弦交流电、有效值、变压器、远距离输电",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "concept_confusion"],
    },
    # ── 光学 ──────────────────────────────────
    {
        "name": "光的折射",
        "description": "折射定律、全反射、临界角",
        "error_types": ["formula_misuse", "concept_confusion"],
        "strategies": ["formula_misuse", "boundary_explore"],
    },
    {
        "name": "光的干涉",
        "description": "双缝干涉、薄膜干涉、光的衍射",
        "error_types": ["concept_confusion", "calculation_error"],
        "strategies": ["concept_confusion", "decompose"],
    },
    # ── 原子物理 ──────────────────────────────
    {
        "name": "原子结构",
        "description": "卢瑟福模型、玻尔模型、能级跃迁",
        "error_types": ["concept_confusion", "formula_misuse"],
        "strategies": ["concept_confusion", "formula_misuse"],
    },
    {
        "name": "原子核",
        "description": "核反应方程、质能方程、半衰期",
        "error_types": ["formula_misuse", "calculation_error"],
        "strategies": ["formula_misuse", "calculation_error"],
    },
]


def seed_physics_kb(kb):
    """
    将高中物理TOP30考点灌入知识库
    
    Args:
        kb: KnowledgeBase实例
        
    Returns:
        添加的知识点数量
    """
    count = 0
    for kp in PHYSICS_KP:
        kb.add_knowledge_point(
            name=kp["name"],
            description=kp["description"],
            error_types=kp["error_types"],
            strategies=kp["strategies"],
            grade="高中",
            subject="物理"
        )
        count += 1
    return count
