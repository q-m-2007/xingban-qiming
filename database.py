"""
SQLite数据库模块
存储用户信息、对话历史、学习记录
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
    """验证密码"""
    try:
        salt, hashed = stored.split(':', 1)
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == hashed
    except Exception:
        return False


def init_db():
    """初始化数据库表"""
    with get_db() as conn:
        cursor = conn.cursor()

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
        logger.info("数据库初始化完成")


# 用户操作
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


# 对话操作
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


# 学习记录
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
