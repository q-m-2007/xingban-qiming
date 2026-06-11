"""
SQLite数据库模块
存储用户信息、对话历史、学习记录
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "xingban.db"


def get_db():
    """获取数据库连接"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
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

    conn.commit()
    conn.close()


# 用户操作
def create_user(username: str, password: str, nickname: str = "") -> Optional[Dict]:
    """创建用户"""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, nickname) VALUES (?, ?, ?)",
            (username, password, nickname or username)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"id": user_id, "username": username, "nickname": nickname or username}
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user(username: str, password: str) -> Optional[Dict]:
    """验证用户登录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, nickname, grade FROM users WHERE username=? AND password=?",
        (username, password)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """根据ID获取用户"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, username, nickname, grade FROM users WHERE id=?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


# 对话操作
def save_message(user_id: int, session_id: str, role: str, content: str,
                 topic: str = "", state: str = "", emotion: str = ""):
    """保存消息"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_id, session_id, role, content, topic, state, emotion) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, session_id, role, content, topic, state, emotion)
    )
    conn.commit()
    conn.close()


def get_conversation_history(user_id: int, session_id: str, limit: int = 20) -> List[Dict]:
    """获取对话历史"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, topic, state, emotion, created_at FROM conversations WHERE user_id=? AND session_id=? ORDER BY id DESC LIMIT ?",
        (user_id, session_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]


def get_user_sessions(user_id: int) -> List[Dict]:
    """获取用户的会话列表"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT session_id, MAX(created_at) as last_time, COUNT(*) as message_count
           FROM conversations WHERE user_id=? GROUP BY session_id ORDER BY last_time DESC""",
        (user_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 学习记录
def save_learning_record(user_id: int, topic: str, question: str, answer: str,
                         is_correct: bool, time_spent: float, difficulty: float):
    """保存学习记录"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO learning_records (user_id, topic, question, answer, is_correct, time_spent, difficulty) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, topic, question, answer, 1 if is_correct else 0, time_spent, difficulty)
    )
    conn.commit()
    conn.close()


def get_learning_stats(user_id: int) -> Dict:
    """获取学习统计"""
    conn = get_db()
    cursor = conn.cursor()

    # 总题数
    cursor.execute("SELECT COUNT(*) FROM learning_records WHERE user_id=?", (user_id,))
    total = cursor.fetchone()[0]

    # 正确数
    cursor.execute("SELECT COUNT(*) FROM learning_records WHERE user_id=? AND is_correct=1", (user_id,))
    correct = cursor.fetchone()[0]

    # 各话题统计
    cursor.execute(
        "SELECT topic, COUNT(*) as count, SUM(is_correct) as correct FROM learning_records WHERE user_id=? GROUP BY topic",
        (user_id,)
    )
    topics = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total > 0 else 0,
        "topics": topics,
    }


# 初始化
init_db()
