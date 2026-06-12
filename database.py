"""
SQLite数据库模块
存储用户信息、对话历史、学习记录、知识库、用户画像
"""

import sqlite3
import hashlib
import secrets
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "data" / "xingban.db"


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def hash_password(password: str, salt: str = None) -> tuple:
    """哈希密码"""
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + ':' + hashed.hex()


def verify_password(password: str, stored: str) -> bool:
    """验证密码（兼容旧版明文密码）"""
    try:
        if ':' in stored:
            salt, hashed = stored.split(':', 1)
            new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
            return new_hash.hex() == hashed
        else:
            return password == stored
    except Exception:
        return False


def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()

        # 用户表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                grade TEXT DEFAULT '四年级',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 用户画像表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                user_id INTEGER PRIMARY KEY,
                visual REAL DEFAULT 0.5,
                verbal REAL DEFAULT 0.5,
                kinesthetic REAL DEFAULT 0.5,
                inductive REAL DEFAULT 0.5,
                deductive REAL DEFAULT 0.5,
                analogical REAL DEFAULT 0.5,
                fast_jump REAL DEFAULT 0.5,
                rigorous REAL DEFAULT 0.5,
                divergent REAL DEFAULT 0.5,
                abstract_reasoning REAL DEFAULT 0.5,
                challenge_drive REAL DEFAULT 0.5,
                persistence REAL DEFAULT 0.5,
                metacognition REAL DEFAULT 0.5,
                collaboration REAL DEFAULT 0.5,
                creativity REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.3,
                data_points INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 对话历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                topic TEXT DEFAULT '',
                state TEXT DEFAULT '',
                emotion TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 学习记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                question TEXT DEFAULT '',
                answer TEXT DEFAULT '',
                is_correct INTEGER DEFAULT 0,
                time_spent REAL DEFAULT 0,
                difficulty REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 年级表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0
            )
        """)

        # 知识点表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                grade_id INTEGER NOT NULL,
                parent_id INTEGER DEFAULT NULL,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                description TEXT DEFAULT '',
                difficulty REAL DEFAULT 0.5,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (grade_id) REFERENCES grades(id),
                FOREIGN KEY (parent_id) REFERENCES knowledge_points(id)
            )
        """)

        # 题目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER NOT NULL,
                type TEXT DEFAULT 'calculation',
                content TEXT NOT NULL,
                answer TEXT NOT NULL,
                explanation TEXT DEFAULT '',
                difficulty REAL DEFAULT 0.5,
                options TEXT DEFAULT '[]',
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            )
        """)

        # 误解模式表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS misconceptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER NOT NULL,
                pattern TEXT NOT NULL,
                description TEXT NOT NULL,
                counter_example TEXT DEFAULT '',
                principle TEXT DEFAULT '',
                rebuild_question TEXT DEFAULT '',
                severity REAL DEFAULT 0.5,
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            )
        """)

        # 解题方法表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS methods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                knowledge_point_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                steps TEXT DEFAULT '[]',
                difficulty REAL DEFAULT 0.5,
                FOREIGN KEY (knowledge_point_id) REFERENCES knowledge_points(id)
            )
        """)

        conn.commit()
        logger.info("数据库初始化完成")

        # 初始化基础数据
        _init_base_data(conn)


def _init_base_data(conn):
    """初始化基础数据"""
    cursor = conn.cursor()

    # 检查是否已有数据
    cursor.execute("SELECT COUNT(*) FROM grades")
    if cursor.fetchone()[0] > 0:
        return

    # 初始化年级
    grades = [
        ('一年级', '基础数数和简单加减', 1),
        ('二年级', '两位数运算和简单几何', 2),
        ('三年级', '乘除法和分数初步', 3),
        ('四年级', '大数认识和小数', 4),
        ('五年级', '分数运算和简易方程', 5),
        ('六年级', '比和比例、圆的面积', 6),
    ]
    cursor.executemany("INSERT INTO grades (name, description, sort_order) VALUES (?, ?, ?)", grades)

    # 初始化四年级知识点
    cursor.execute("SELECT id FROM grades WHERE name='四年级'")
    grade4_id = cursor.fetchone()[0]

    kps = [
        (grade4_id, None, '大数认识', 'large_number', '亿以内数的认识', 0.3),
        (grade4_id, None, '三位数乘两位数', 'multiply_3x2', '三位数乘两位数的计算', 0.5),
        (grade4_id, None, '除数是两位数的除法', 'divide_2digit', '除数是两位数的除法', 0.5),
        (grade4_id, None, '四则混合运算', 'four_operations', '运算顺序和简便计算', 0.4),
        (grade4_id, None, '小数的意义', 'decimal_concept', '小数的意义和性质', 0.5),
        (grade4_id, None, '小数加减法', 'decimal_add_sub', '小数的加法和减法', 0.5),
        (grade4_id, None, '角的度量', 'angle_measure', '角的分类和度量', 0.4),
        (grade4_id, None, '平行四边形', 'parallelogram', '平行四边形的特征', 0.5),
        (grade4_id, None, '梯形', 'trapezoid', '梯形的特征', 0.5),
        (grade4_id, None, '条形统计图', 'bar_chart', '条形统计图的认识', 0.3),
    ]
    cursor.executemany(
        "INSERT INTO knowledge_points (grade_id, parent_id, name, code, description, difficulty) VALUES (?, ?, ?, ?, ?, ?)",
        kps
    )

    # 初始化误解模式
    misconceptions = [
        (None, '分母越大分数越大', 'fraction_denominator', '误以为分母越大分数越大',
         '1/2和1/4哪个大？', '分数比较要看整体大小', '想想披萨切的份数越多，每块越小'),
        (None, '三角形面积不除以2', 'triangle_area', '忘记三角形面积要除以2',
         '底4高3的三角形面积是12还是6？', '三角形是平行四边形的一半', '把长方形沿对角线剪开看看'),
        (None, '运算顺序错误', 'operation_order', '先算加法再算乘法',
         '2+3×4等于20还是14？', '先乘除后加减', '有括号要先算括号里面的'),
        (None, '小数位数越多越大', 'decimal_digits', '误以为小数位数越多数值越大',
         '0.5和0.12哪个大？', '小数比较从高位开始', '想想5角和1角2分哪个多'),
    ]

    cursor.execute("SELECT id FROM knowledge_points WHERE code='four_operations'")
    kp_id = cursor.fetchone()[0]

    for m in misconceptions:
        cursor.execute(
            "INSERT INTO misconceptions (knowledge_point_id, pattern, description, counter_example, principle, rebuild_question) VALUES (?, ?, ?, ?, ?, ?)",
            (kp_id, m[0], m[2], m[3], m[4], m[5])
        )

    conn.commit()
    logger.info("基础数据初始化完成")


# ═══════════════════════════════════════════
# 用户画像操作
# ═══════════════════════════════════════════

def save_user_profile(user_id: int, profile: Dict):
    """保存用户画像"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO user_profiles
            (user_id, visual, verbal, kinesthetic, inductive, deductive, analogical,
             fast_jump, rigorous, divergent, abstract_reasoning, challenge_drive,
             persistence, metacognition, collaboration, creativity, confidence, data_points, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            user_id,
            profile.get('visual', 0.5), profile.get('verbal', 0.5),
            profile.get('kinesthetic', 0.5), profile.get('inductive', 0.5),
            profile.get('deductive', 0.5), profile.get('analogical', 0.5),
            profile.get('fast_jump', 0.5), profile.get('rigorous', 0.5),
            profile.get('divergent', 0.5), profile.get('abstract_reasoning', 0.5),
            profile.get('challenge_drive', 0.5), profile.get('persistence', 0.5),
            profile.get('metacognition', 0.5), profile.get('collaboration', 0.5),
            profile.get('creativity', 0.5), profile.get('confidence', 0.3),
            profile.get('data_points', 0)
        ))
        conn.commit()


def get_user_profile(user_id: int) -> Optional[Dict]:
    """获取用户画像"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


# ═══════════════════════════════════════════
# 用户操作
# ═══════════════════════════════════════════

def create_user(username: str, password: str, nickname: str = "") -> Optional[Dict]:
    """创建用户（密码哈希存储）"""
    hashed = hash_password(password)
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
                (username, hashed, nickname or username)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return {"id": user_id, "username": username, "nickname": nickname or username}
        except sqlite3.IntegrityError:
            return None


def get_user(username: str, password: str) -> Optional[Dict]:
    """验证用户登录"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, nickname, grade, password FROM users WHERE username=?",
            (username,)
        )
        row = cursor.fetchone()
        if row and verify_password(password, row['password']):
            return {"id": row['id'], "username": row['username'],
                    "nickname": row['nickname'], "grade": row['grade']}
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """根据ID获取用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, nickname, grade FROM users WHERE id=?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


# ═══════════════════════════════════════════
# 对话操作
# ═══════════════════════════════════════════

def save_message(user_id: int, session_id: str, role: str, content: str,
                 topic: str = "", state: str = "", emotion: str = ""):
    """保存消息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversations (user_id, session_id, role, content, topic, state, emotion) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, session_id, role, content, topic, state, emotion)
        )
        conn.commit()


def get_conversation_history(user_id: int, session_id: str, limit: int = 20) -> List[Dict]:
    """获取对话历史"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, topic, state, emotion, created_at FROM conversations WHERE user_id=? AND session_id=? ORDER BY id DESC LIMIT ?",
            (user_id, session_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in reversed(rows)]


def get_user_sessions(user_id: int) -> List[Dict]:
    """获取用户的会话列表"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT session_id, MAX(created_at) as last_time, COUNT(*) as message_count
               FROM conversations WHERE user_id=? GROUP BY session_id ORDER BY last_time DESC""",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


# ═══════════════════════════════════════════
# 学习记录
# ═══════════════════════════════════════════

def save_learning_record(user_id: int, topic: str, question: str, answer: str,
                         is_correct: bool, time_spent: float, difficulty: float):
    """保存学习记录"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO learning_records (user_id, topic, question, answer, is_correct, time_spent, difficulty) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, topic, question, answer, 1 if is_correct else 0, time_spent, difficulty)
        )
        conn.commit()


def get_learning_stats(user_id: int) -> Dict:
    """获取学习统计"""
    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM learning_records WHERE user_id=?", (user_id,))
        total = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM learning_records WHERE user_id=? AND is_correct=1", (user_id,))
        correct = cursor.fetchone()[0]

        cursor.execute(
            "SELECT topic, COUNT(*) as count, SUM(is_correct) as correct FROM learning_records WHERE user_id=? GROUP BY topic",
            (user_id,)
        )
        topics = [dict(r) for r in cursor.fetchall()]

        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total if total > 0 else 0,
            "topics": topics,
        }


def get_recent_performance(user_id: int, limit: int = 10) -> List[Dict]:
    """获取最近表现"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT topic, is_correct, time_spent, difficulty, created_at FROM learning_records WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_conversation_count(user_id: int, session_id: str) -> int:
    """获取对话轮次"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id=? AND session_id=? AND role='assistant'",
            (user_id, session_id)
        )
        return cursor.fetchone()[0]


# ═══════════════════════════════════════════
# 知识库操作
# ═══════════════════════════════════════════

def get_grades() -> List[Dict]:
    """获取所有年级"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM grades ORDER BY sort_order")
        return [dict(r) for r in cursor.fetchall()]


def get_knowledge_points(grade_id: int) -> List[Dict]:
    """获取年级的知识点"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM knowledge_points WHERE grade_id=? ORDER BY sort_order",
            (grade_id,)
        )
        return [dict(r) for r in cursor.fetchall()]


def get_knowledge_point_by_code(code: str) -> Optional[Dict]:
    """根据代码获取知识点"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_points WHERE code=?", (code,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_questions(knowledge_point_id: int, limit: int = 10) -> List[Dict]:
    """获取知识点的题目"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM questions WHERE knowledge_point_id=? ORDER BY RANDOM() LIMIT ?",
            (knowledge_point_id, limit)
        )
        return [dict(r) for r in cursor.fetchall()]


def get_misconceptions(knowledge_point_id: int) -> List[Dict]:
    """获取知识点的误解模式"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM misconceptions WHERE knowledge_point_id=?",
            (knowledge_point_id,)
        )
        return [dict(r) for r in cursor.fetchall()]


def get_methods(knowledge_point_id: int) -> List[Dict]:
    """获取知识点的解题方法"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM methods WHERE knowledge_point_id=?",
            (knowledge_point_id,)
        )
        return [dict(r) for r in cursor.fetchall()]


def search_knowledge(query: str) -> List[Dict]:
    """搜索知识点"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM knowledge_points WHERE name LIKE ? OR description LIKE ?",
            (f'%{query}%', f'%{query}%')
        )
        return [dict(r) for r in cursor.fetchall()]
