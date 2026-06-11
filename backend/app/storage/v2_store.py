"""
星伴·启明 V2.0 持久化存储
SQLite实现，存储学生画像、对话历史、解法掌握度等
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List


class V2Store:
    """V2数据持久化存储"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'v2.db')
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # 学生表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    openid TEXT PRIMARY KEY,
                    nickname TEXT DEFAULT '',
                    avatar TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    last_active TEXT DEFAULT (datetime('now', 'localtime'))
                )
            ''')

            # 会话表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    topic TEXT DEFAULT 'quadratic_equation',
                    problem_context TEXT DEFAULT '',
                    current_phase TEXT DEFAULT 'exploration',
                    current_energy REAL DEFAULT 0.5,
                    message_count INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (student_id) REFERENCES students(openid)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_student ON sessions(student_id)')

            # 对话历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    strategy TEXT DEFAULT '',
                    student_state TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)')

            # 认知画像表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profiles (
                    student_id TEXT PRIMARY KEY,
                    profile_data TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (student_id) REFERENCES students(openid)
                )
            ''')

            # 解法掌握度表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS method_masteries (
                    student_id TEXT NOT NULL,
                    method_id TEXT NOT NULL,
                    mastery_data TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now', 'localtime')),
                    PRIMARY KEY (student_id, method_id),
                    FOREIGN KEY (student_id) REFERENCES students(openid)
                )
            ''')

            # 投入度历史表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS engagement_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    engagement_data TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (student_id) REFERENCES students(openid)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_engagement_student ON engagement_history(student_id)')

            # 解题记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS method_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    problem_id TEXT DEFAULT '',
                    problem_type TEXT DEFAULT '',
                    method_used TEXT DEFAULT '',
                    success INTEGER DEFAULT 0,
                    time_spent REAL DEFAULT 0,
                    steps_count INTEGER DEFAULT 0,
                    verification_level INTEGER DEFAULT 0,
                    error_type TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now', 'localtime')),
                    FOREIGN KEY (student_id) REFERENCES students(openid)
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_attempts_student ON method_attempts(student_id)')

            conn.commit()
        finally:
            conn.close()

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # === 学生 ===

    def get_or_create_student(self, openid: str, nickname: str = '') -> Dict:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM students WHERE openid = ?', (openid,))
            row = cursor.fetchone()
            if row:
                cursor.execute(
                    "UPDATE students SET last_active = datetime('now', 'localtime') WHERE openid = ?",
                    (openid,)
                )
                conn.commit()
                return {'openid': row[0], 'nickname': row[1], 'avatar': row[2]}
            else:
                cursor.execute(
                    'INSERT INTO students (openid, nickname) VALUES (?, ?)',
                    (openid, nickname)
                )
                conn.commit()
                return {'openid': openid, 'nickname': nickname, 'avatar': ''}
        finally:
            conn.close()

    # === 会话 ===

    def create_session(self, session_id: str, student_id: str, topic: str = 'quadratic_equation', problem_context: str = '') -> Dict:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO sessions (session_id, student_id, topic, problem_context) VALUES (?, ?, ?, ?)',
                (session_id, student_id, topic, problem_context)
            )
            conn.commit()
            return {
                'session_id': session_id, 'student_id': student_id,
                'topic': topic, 'problem_context': problem_context,
                'current_phase': 'exploration', 'current_energy': 0.5, 'message_count': 0
            }
        finally:
            conn.close()

    def get_session(self, session_id: str) -> Optional[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'session_id': row[0], 'student_id': row[1], 'topic': row[2],
                'problem_context': row[3], 'current_phase': row[4],
                'current_energy': row[5], 'message_count': row[6]
            }
        finally:
            conn.close()

    def update_session(self, session_id: str, **kwargs):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            sets = []
            vals = []
            for k, v in kwargs.items():
                sets.append(f'{k} = ?')
                vals.append(v)
            sets.append("updated_at = datetime('now', 'localtime')")
            vals.append(session_id)
            cursor.execute(f"UPDATE sessions SET {', '.join(sets)} WHERE session_id = ?", vals)
            conn.commit()
        finally:
            conn.close()

    def get_active_session(self, student_id: str, topic: str = None) -> Optional[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            if topic:
                cursor.execute(
                    "SELECT * FROM sessions WHERE student_id = ? AND topic = ? ORDER BY updated_at DESC LIMIT 1",
                    (student_id, topic)
                )
            else:
                cursor.execute(
                    "SELECT * FROM sessions WHERE student_id = ? ORDER BY updated_at DESC LIMIT 1",
                    (student_id,)
                )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'session_id': row[0], 'student_id': row[1], 'topic': row[2],
                'problem_context': row[3], 'current_phase': row[4],
                'current_energy': row[5], 'message_count': row[6]
            }
        finally:
            conn.close()

    def list_sessions(self, student_id: str, limit: int = 20) -> List[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE student_id = ? ORDER BY updated_at DESC LIMIT ?",
                (student_id, limit)
            )
            rows = cursor.fetchall()
            return [{
                'session_id': r[0], 'student_id': r[1], 'topic': r[2],
                'problem_context': r[3], 'current_phase': r[4],
                'current_energy': r[5], 'message_count': r[6]
            } for r in rows]
        finally:
            conn.close()

    # === 对话消息 ===

    def save_message(self, session_id: str, role: str, content: str, strategy: str = '', student_state: str = ''):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO messages (session_id, role, content, strategy, student_state) VALUES (?, ?, ?, ?, ?)',
                (session_id, role, content, strategy, student_state)
            )
            conn.commit()
        finally:
            conn.close()

    def get_messages(self, session_id: str, limit: int = 50) -> List[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT role, content, strategy, student_state, created_at FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            )
            rows = cursor.fetchall()
            rows.reverse()
            return [{
                'role': r[0], 'content': r[1], 'strategy': r[2],
                'student_state': r[3], 'created_at': r[4]
            } for r in rows]
        finally:
            conn.close()

    # === 认知画像 ===

    def save_profile(self, student_id: str, profile_data: Dict):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO profiles (student_id, profile_data, updated_at) VALUES (?, ?, datetime('now', 'localtime'))",
                (student_id, json.dumps(profile_data, ensure_ascii=False))
            )
            conn.commit()
        finally:
            conn.close()

    def load_profile(self, student_id: str) -> Optional[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT profile_data FROM profiles WHERE student_id = ?', (student_id,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()

    # === 解法掌握度 ===

    def save_method_mastery(self, student_id: str, method_id: str, mastery_data: Dict):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO method_masteries (student_id, method_id, mastery_data, updated_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                (student_id, method_id, json.dumps(mastery_data, ensure_ascii=False))
            )
            conn.commit()
        finally:
            conn.close()

    def load_method_masteries(self, student_id: str) -> Dict[str, Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT method_id, mastery_data FROM method_masteries WHERE student_id = ?', (student_id,))
            rows = cursor.fetchall()
            return {r[0]: json.loads(r[1]) for r in rows}
        finally:
            conn.close()

    # === 投入度 ===

    def save_engagement(self, student_id: str, engagement_data: Dict):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO engagement_history (student_id, engagement_data) VALUES (?, ?)',
                (student_id, json.dumps(engagement_data, ensure_ascii=False))
            )
            # 只保留最近50条
            cursor.execute(
                "DELETE FROM engagement_history WHERE student_id = ? AND id NOT IN (SELECT id FROM engagement_history WHERE student_id = ? ORDER BY id DESC LIMIT 50)",
                (student_id, student_id)
            )
            conn.commit()
        finally:
            conn.close()

    def load_engagement_history(self, student_id: str, limit: int = 50) -> List[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT engagement_data FROM engagement_history WHERE student_id = ? ORDER BY id DESC LIMIT ?',
                (student_id, limit)
            )
            rows = cursor.fetchall()
            rows.reverse()
            return [json.loads(r[0]) for r in rows]
        finally:
            conn.close()

    # === 解题记录 ===

    def save_method_attempt(self, student_id: str, attempt_data: Dict):
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO method_attempts
                (student_id, problem_id, problem_type, method_used, success, time_spent, steps_count, verification_level, error_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (student_id, attempt_data.get('problem_id', ''),
                 attempt_data.get('problem_type', ''), attempt_data.get('method_used', ''),
                 1 if attempt_data.get('success') else 0,
                 attempt_data.get('time_spent', 0), attempt_data.get('steps_count', 0),
                 attempt_data.get('verification_level', 0), attempt_data.get('error_type', ''))
            )
            conn.commit()
        finally:
            conn.close()

    def load_method_attempts(self, student_id: str, limit: int = 100) -> List[Dict]:
        conn = self._conn()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM method_attempts WHERE student_id = ? ORDER BY id DESC LIMIT ?",
                (student_id, limit)
            )
            rows = cursor.fetchall()
            return [{
                'id': r[0], 'student_id': r[1], 'problem_id': r[2],
                'problem_type': r[3], 'method_used': r[4], 'success': bool(r[5]),
                'time_spent': r[6], 'steps_count': r[7], 'verification_level': r[8],
                'error_type': r[9], 'created_at': r[10]
            } for r in rows]
        finally:
            conn.close()

    # === 批量保存（减少数据库连接次数） ===

    def save_session_state(self, session_id: str, student_id: str, session_data: Dict,
                           profile_data: Dict = None, masteries: Dict = None,
                           engagement: Dict = None, attempt: Dict = None):
        conn = self._conn()
        try:
            cursor = conn.cursor()

            # 更新会话
            cursor.execute(
                "UPDATE sessions SET current_phase=?, current_energy=?, message_count=?, updated_at=datetime('now','localtime') WHERE session_id=?",
                (session_data.get('current_phase', 'exploration'),
                 session_data.get('current_energy', 0.5),
                 session_data.get('message_count', 0), session_id)
            )

            # 保存画像
            if profile_data:
                cursor.execute(
                    "INSERT OR REPLACE INTO profiles (student_id, profile_data, updated_at) VALUES (?, ?, datetime('now', 'localtime'))",
                    (student_id, json.dumps(profile_data, ensure_ascii=False))
                )

            # 保存掌握度
            if masteries:
                for method_id, mastery_data in masteries.items():
                    cursor.execute(
                        "INSERT OR REPLACE INTO method_masteries (student_id, method_id, mastery_data, updated_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                        (student_id, method_id, json.dumps(mastery_data, ensure_ascii=False))
                    )

            # 保存投入度
            if engagement:
                cursor.execute(
                    'INSERT INTO engagement_history (student_id, engagement_data) VALUES (?, ?)',
                    (student_id, json.dumps(engagement, ensure_ascii=False))
                )

            # 保存解题记录
            if attempt:
                cursor.execute(
                    '''INSERT INTO method_attempts
                    (student_id, problem_id, problem_type, method_used, success, time_spent, steps_count, verification_level, error_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (student_id, attempt.get('problem_id', ''),
                     attempt.get('problem_type', ''), attempt.get('method_used', ''),
                     1 if attempt.get('success') else 0,
                     attempt.get('time_spent', 0), attempt.get('steps_count', 0),
                     attempt.get('verification_level', 0), attempt.get('error_type', ''))
                )

            conn.commit()
        finally:
            conn.close()

    # === 统计 ===

    def get_student_stats(self, student_id: str) -> Dict:
        conn = self._conn()
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM sessions WHERE student_id = ?", (student_id,))
            session_count = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM messages m JOIN sessions s ON m.session_id = s.session_id WHERE s.student_id = ? AND m.role = 'user'",
                (student_id,)
            )
            message_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM method_attempts WHERE student_id = ?", (student_id,))
            attempt_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM method_attempts WHERE student_id = ? AND success = 1", (student_id,))
            success_count = cursor.fetchone()[0]

            return {
                'session_count': session_count,
                'message_count': message_count,
                'attempt_count': attempt_count,
                'success_count': success_count,
                'success_rate': success_count / attempt_count if attempt_count > 0 else 0
            }
        finally:
            conn.close()
