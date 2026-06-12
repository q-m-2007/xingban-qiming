"""
知识库初始数据导入脚本
运行: python init_knowledge.py
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "xingban.db"


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_grades(conn):
    """初始化年级数据"""
    cursor = conn.cursor()

    grades = [
        ('一年级', '20以内加减法、认识图形', 1),
        ('二年级', '100以内加减法、乘法口诀、长度单位', 2),
        ('三年级', '万以内加减法、多位数乘一位数、分数初步', 3),
        ('四年级', '大数认识、三位数乘两位数、小数', 4),
        ('五年级', '小数乘除法、简易方程、多边形面积', 5),
        ('六年级', '分数乘除法、比和比例、圆的面积', 6),
    ]

    for g in grades:
        cursor.execute(
            "INSERT OR IGNORE INTO grades (name, description, sort_order) VALUES (?, ?, ?)",
            g
        )

    conn.commit()
    print(f"✓ 初始化 {len(grades)} 个年级")


def init_knowledge_points(conn):
    """初始化知识点"""
    cursor = conn.cursor()

    # 获取年级ID
    cursor.execute("SELECT id, name FROM grades")
    grade_map = {row['name']: row['id'] for row in cursor.fetchall()}

    knowledge_points = {
        '一年级': [
            ('认识1-20', 'number_1_20', '认识20以内的数', 0.2),
            ('10以内加减法', 'add_sub_10', '10以内的加法和减法', 0.3),
            ('20以内加减法', 'add_sub_20', '20以内的加法和减法', 0.4),
            ('认识图形', 'shape_basic', '长方形、正方形、三角形、圆', 0.2),
        ],
        '二年级': [
            ('100以内加减法', 'add_sub_100', '100以内的加法和减法', 0.4),
            ('乘法口诀', 'multiplication_table', '九九乘法表', 0.5),
            ('表内乘法', 'multiply_table', '用乘法口诀计算', 0.5),
            ('表内除法', 'divide_table', '用乘法口诀求商', 0.5),
            ('长度单位', 'length_unit', '厘米、米的认识', 0.3),
            ('角的认识', 'angle_basic', '直角、锐角、钝角', 0.3),
        ],
        '三年级': [
            ('万以内加减法', 'add_sub_10000', '万以内的加法和减法', 0.5),
            ('多位数乘一位数', 'multiply_1digit', '多位数乘一位数', 0.5),
            ('多位数除以一位数', 'divide_1digit', '多位数除以一位数', 0.5),
            ('分数初步', 'fraction_intro', '分数的初步认识', 0.5),
            ('小数初步', 'decimal_intro', '小数的初步认识', 0.5),
            ('时间单位', 'time_unit', '时、分、秒', 0.3),
            ('长方形和正方形', 'rectangle_square', '周长计算', 0.4),
        ],
        '四年级': [
            ('大数认识', 'large_number', '亿以内数的认识', 0.4),
            ('三位数乘两位数', 'multiply_3x2', '三位数乘两位数', 0.6),
            ('除数是两位数的除法', 'divide_2digit', '除数是两位数的除法', 0.6),
            ('四则混合运算', 'four_operations', '运算顺序和简便计算', 0.5),
            ('小数的意义', 'decimal_meaning', '小数的意义和性质', 0.5),
            ('小数加减法', 'decimal_add_sub', '小数的加法和减法', 0.5),
            ('角的度量', 'angle_measure', '角的分类和度量', 0.4),
            ('平行四边形', 'parallelogram', '平行四边形的特征', 0.5),
            ('梯形', 'trapezoid', '梯形的特征', 0.5),
            ('条形统计图', 'bar_chart', '条形统计图的认识', 0.3),
        ],
        '五年级': [
            ('小数乘法', 'decimal_multiply', '小数乘法', 0.6),
            ('小数除法', 'decimal_divide', '小数除法', 0.6),
            ('简易方程', 'simple_equation', '用字母表示数、解方程', 0.6),
            ('平行四边形面积', 'area_parallelogram', '平行四边形面积公式', 0.6),
            ('三角形面积', 'area_triangle', '三角形面积公式', 0.6),
            ('梯形面积', 'area_trapezoid', '梯形面积公式', 0.6),
            ('组合图形面积', 'area_composite', '组合图形的面积', 0.7),
            ('可能性', 'probability', '事件发生的可能性', 0.4),
        ],
        '六年级': [
            ('分数乘法', 'fraction_multiply', '分数乘法', 0.7),
            ('分数除法', 'fraction_divide', '分数除法', 0.7),
            ('比和比例', 'ratio_proportion', '比的意义和性质', 0.7),
            ('圆的认识', 'circle', '圆的特征', 0.6),
            ('圆的周长', 'circle_perimeter', '圆的周长公式', 0.7),
            ('圆的面积', 'circle_area', '圆的面积公式', 0.7),
            ('百分数', 'percentage', '百分数的意义和应用', 0.6),
            ('扇形统计图', 'pie_chart', '扇形统计图的认识', 0.5),
        ],
    }

    count = 0
    for grade_name, kps in knowledge_points.items():
        grade_id = grade_map.get(grade_name)
        if not grade_id:
            continue
        for name, code, desc, diff in kps:
            cursor.execute(
                "INSERT OR IGNORE INTO knowledge_points (grade_id, name, code, description, difficulty) VALUES (?, ?, ?, ?, ?)",
                (grade_id, name, code, desc, diff)
            )
            count += 1

    conn.commit()
    print(f"✓ 初始化 {count} 个知识点")


def init_misconceptions(conn):
    """初始化误解模式"""
    cursor = conn.cursor()

    misconceptions = [
        # 分数相关
        ('fraction_intro', '分母越大分数越大', '误以为分母越大分数越大',
         '1/2和1/4哪个大？', '分数比较要看整体大小', '想想披萨切的份数越多，每块越小'),
        ('fraction_intro', '分子分母分别比较', '比较分数时分别比较分子分母',
         '2/3和3/4哪个大？', '要通分后比较', '先通分再比较大小'),

        # 小数相关
        ('decimal_meaning', '小数位数越多越大', '误以为小数位数越多数值越大',
         '0.5和0.12哪个大？', '小数比较从高位开始', '想想5角和1角2分哪个多'),
        ('decimal_add_sub', '小数点对齐错误', '加减法时小数点没对齐',
         '1.2+3.45怎么算？', '小数点要对齐', '把小数点对齐再计算'),

        # 面积相关
        ('area_triangle', '三角形面积不除以2', '忘记三角形面积要除以2',
         '底4高3的三角形面积是？', '三角形是平行四边形的一半', '把长方形沿对角线剪开看看'),
        ('area_trapezoid', '梯形面积公式错误', '梯形面积公式记错',
         '上底3下底5高4的梯形面积是？', '梯形面积=(上底+下底)×高÷2', '两个梯形拼成平行四边形'),

        # 运算相关
        ('four_operations', '运算顺序错误', '先算加法再算乘法',
         '2+3×4等于？', '先乘除后加减', '有括号要先算括号里面的'),
        ('four_operations', '分配律错误', '乘法分配律使用错误',
         '25×(4+8)怎么算？', '分别相乘再相加', '25×4+25×8'),

        # 方程相关
        ('simple_equation', '等号两边不同操作', '方程变形时两边操作不一致',
         'x+3=7怎么解？', '等号两边同时操作', '两边同时减去3'),

        # 周长相关
        ('rectangle_square', '周长公式错误', '长方形周长公式记错',
         '长5宽3的长方形周长是？', '周长=(长+宽)×2', '围着走一圈的长度'),
    ]

    count = 0
    for kp_code, pattern, desc, counter, principle, rebuild in misconceptions:
        cursor.execute("SELECT id FROM knowledge_points WHERE code=?", (kp_code,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT INTO misconceptions (knowledge_point_id, pattern, description, counter_example, principle, rebuild_question) VALUES (?, ?, ?, ?, ?, ?)",
                (row['id'], pattern, desc, counter, principle, rebuild)
            )
            count += 1

    conn.commit()
    print(f"✓ 初始化 {count} 个误解模式")


def init_questions(conn):
    """初始化题目"""
    cursor = conn.cursor()

    questions = [
        # 四年级题目
        ('four_operations', 'calculation', '计算：25×4+75×4=', '400', '用分配律：(25+75)×4=100×4=400', 0.5),
        ('four_operations', 'calculation', '计算：100-25×3=', '25', '先算乘法：25×3=75，再算减法：100-75=25', 0.5),
        ('four_operations', 'calculation', '计算：(125+75)×8=', '1600', '先算括号：125+75=200，再算乘法：200×8=1600', 0.6),

        ('decimal_add_sub', 'calculation', '计算：3.5+2.78=', '6.28', '小数点对齐：3.50+2.78=6.28', 0.5),
        ('decimal_add_sub', 'calculation', '计算：10-3.65=', '6.35', '小数点对齐：10.00-3.65=6.35', 0.5),

        ('large_number', 'fill', '30500000读作：________', '三千零五十万', '先分级，再读数', 0.4),
        ('large_number', 'fill', '八千零二万零三百写作：________', '80020300', '从高位写起，哪位上是0就写0', 0.5),

        ('angle_measure', 'choice', '直角是多少度？\nA. 45° B. 90° C. 180° D. 360°', 'B', '直角是90度', 0.3),

        ('parallelogram', 'fill', '平行四边形的对边________且________', '平行、相等', '平行四边形的特征', 0.4),

        # 五年级题目
        ('area_triangle', 'calculation', '三角形底6cm，高4cm，面积是多少？', '12平方厘米', '三角形面积=底×高÷2=6×4÷2=12', 0.6),
        ('area_parallelogram', 'calculation', '平行四边形底8cm，高5cm，面积是多少？', '40平方厘米', '平行四边形面积=底×高=8×5=40', 0.5),
        ('simple_equation', 'solve', '解方程：2x+5=13', 'x=4', '2x=13-5=8，x=8÷2=4', 0.6),

        # 六年级题目
        ('circle_area', 'calculation', '圆的半径是3cm，面积是多少？（π取3.14）', '28.26平方厘米', '圆的面积=πr²=3.14×9=28.26', 0.7),
        ('circle_perimeter', 'calculation', '圆的直径是10cm，周长是多少？（π取3.14）', '31.4厘米', '圆的周长=πd=3.14×10=31.4', 0.6),
    ]

    count = 0
    for kp_code, qtype, content, answer, explanation, difficulty in questions:
        cursor.execute("SELECT id FROM knowledge_points WHERE code=?", (kp_code,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT INTO questions (knowledge_point_id, type, content, answer, explanation, difficulty) VALUES (?, ?, ?, ?, ?, ?)",
                (row['id'], qtype, content, answer, explanation, difficulty)
            )
            count += 1

    conn.commit()
    print(f"✓ 初始化 {count} 道题目")


def init_methods(conn):
    """初始化解题方法"""
    cursor = conn.cursor()

    methods = [
        ('four_operations', '分配律', '用乘法分配律简便计算',
         json.dumps(["观察算式结构", "提取公因数", "用分配律展开", "分别计算后相加"]), 0.5),
        ('four_operations', '结合律', '用乘法结合律简便计算',
         json.dumps(["观察因数特征", "找能凑整的因数", "用结合律重新组合", "分别计算"]), 0.5),
        ('decimal_add_sub', '小数加减法', '小数加减法计算方法',
         json.dumps(["小数点对齐", "从低位算起", "满十进一或借一当十", "点上小数点"]), 0.5),
        ('area_triangle', '三角形面积', '三角形面积计算方法',
         json.dumps(["确认底和高", "底×高", "再÷2", "写上单位"]), 0.6),
        ('simple_equation', '解方程', '解简易方程的方法',
         json.dumps(["观察方程结构", "移项变号", "合并同类项", "系数化为1", "检验"]), 0.6),
    ]

    count = 0
    for kp_code, name, desc, steps, difficulty in methods:
        cursor.execute("SELECT id FROM knowledge_points WHERE code=?", (kp_code,))
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "INSERT INTO methods (knowledge_point_id, name, description, steps, difficulty) VALUES (?, ?, ?, ?, ?)",
                (row['id'], name, desc, steps, difficulty)
            )
            count += 1

    conn.commit()
    print(f"✓ 初始化 {count} 个解题方法")


def main():
    """主函数"""
    print("=== 星伴·启明 知识库初始化 ===\n")

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()

    try:
        init_grades(conn)
        init_knowledge_points(conn)
        init_misconceptions(conn)
        init_questions(conn)
        init_methods(conn)
        print("\n✓ 知识库初始化完成！")
    except Exception as e:
        print(f"\n✗ 初始化失败: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
