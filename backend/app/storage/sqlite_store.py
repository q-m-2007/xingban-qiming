"""
CCG认知图谱 - SQLite持久化层
管理图谱的存储和恢复
"""

import sqlite3
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from ..graph.cognitive_graph import CognitiveGraph
from ..models.ccg_models import (
    Belief, BeliefRelation, Conflict,
    BeliefType, RelationType, ConflictType, ConflictStatus
)


class SQLiteStore:
    """
    SQLite持久化存储
    管理多个会话的认知图谱
    """

    def __init__(self, db_path: str = "/home/ubuntu/xingban-qiming/data/ccg.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    graph_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # 信念表（用于快速查询）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS beliefs (
                    belief_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    proposition TEXT NOT NULL,
                    type TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    source TEXT,
                    timestamp TEXT NOT NULL,
                    last_activated TEXT NOT NULL,
                    activation_count INTEGER DEFAULT 1,
                    stability REAL DEFAULT 0.5,
                    emotional_tag TEXT DEFAULT 'neutral',
                    metadata TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # 冲突表（用于统计和分析）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conflicts (
                    conflict_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    belief_a_id TEXT NOT NULL,
                    belief_b_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    severity REAL NOT NULL,
                    teaching_value REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    history TEXT DEFAULT '[]',
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                )
            """)
            
            # 创建索引
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_beliefs_session ON beliefs(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_beliefs_type ON beliefs(type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_session ON conflicts(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status)")
            
            conn.commit()

    # ── 会话操作 ────────────────────────────────────────────────

    def save_session(self, graph: CognitiveGraph) -> bool:
        """保存整个会话图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.now().isoformat()
                graph_data = json.dumps(graph.to_dict(), ensure_ascii=False)
                
                # 插入或更新会话
                cursor.execute("""
                    INSERT OR REPLACE INTO sessions (session_id, graph_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (graph.session_id, graph_data, graph.created_at.isoformat(), now))
                
                # 清除旧的信念和冲突记录
                cursor.execute("DELETE FROM beliefs WHERE session_id = ?", (graph.session_id,))
                cursor.execute("DELETE FROM conflicts WHERE session_id = ?", (graph.session_id,))
                
                # 插入信念
                for belief in graph.beliefs.values():
                    cursor.execute("""
                        INSERT INTO beliefs (
                            belief_id, session_id, proposition, type, confidence,
                            source, timestamp, last_activated, activation_count,
                            stability, emotional_tag, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        belief.id, graph.session_id, belief.proposition,
                        belief.type.value, belief.confidence, belief.source,
                        belief.timestamp.isoformat(), belief.last_activated.isoformat(),
                        belief.activation_count, belief.stability,
                        belief.emotional_tag.value, json.dumps(belief.metadata)
                    ))
                
                # 插入冲突
                for conflict in graph.conflicts.values():
                    cursor.execute("""
                        INSERT INTO conflicts (
                            conflict_id, session_id, belief_a_id, belief_b_id,
                            type, severity, teaching_value, status,
                            created_at, updated_at, history
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        conflict.id, graph.session_id, conflict.belief_a_id,
                        conflict.belief_b_id, conflict.type.value, conflict.severity,
                        conflict.teaching_value, conflict.status.value,
                        conflict.created_at.isoformat(), conflict.updated_at.isoformat(),
                        json.dumps(conflict.history)
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"保存会话失败: {e}")
            return False

    def load_session(self, session_id: str) -> Optional[CognitiveGraph]:
        """加载会话图谱"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT graph_data FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                graph_data = json.loads(row[0])
                return CognitiveGraph.from_dict(graph_data)
        except Exception as e:
            print(f"加载会话失败: {e}")
            return None

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM beliefs WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM conflicts WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    def list_sessions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """列出所有会话"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT session_id, created_at, updated_at, metadata
                    FROM sessions
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,))
                
                sessions = []
                for row in cursor.fetchall():
                    sessions.append({
                        "session_id": row[0],
                        "created_at": row[1],
                        "updated_at": row[2],
                        "metadata": json.loads(row[3]) if row[3] else {}
                    })
                
                return sessions
        except Exception as e:
            print(f"列出会话失败: {e}")
            return []

    # ── 信念查询 ────────────────────────────────────────────────

    def get_beliefs_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有信念"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM beliefs
                    WHERE session_id = ?
                    ORDER BY confidence DESC
                """, (session_id,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询信念失败: {e}")
            return []

    def get_beliefs_by_type(self, session_id: str, belief_type: BeliefType) -> List[Dict[str, Any]]:
        """按类型获取信念"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM beliefs
                    WHERE session_id = ? AND type = ?
                    ORDER BY confidence DESC
                """, (session_id, belief_type.value))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询信念失败: {e}")
            return []

    # ── 冲突查询 ────────────────────────────────────────────────

    def get_conflicts_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """获取会话的所有冲突"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM conflicts
                    WHERE session_id = ?
                    ORDER BY severity DESC
                """, (session_id,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询冲突失败: {e}")
            return []

    def get_active_conflicts(self, session_id: str) -> List[Dict[str, Any]]:
        """获取活跃冲突"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM conflicts
                    WHERE session_id = ? AND status = 'active'
                    ORDER BY severity DESC
                """, (session_id,))
                
                columns = [description[0] for description in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"查询冲突失败: {e}")
            return []

    # ── 统计分析 ────────────────────────────────────────────────

    def get_global_statistics(self) -> Dict[str, Any]:
        """获取全局统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 会话总数
                cursor.execute("SELECT COUNT(*) FROM sessions")
                total_sessions = cursor.fetchone()[0]
                
                # 信念总数
                cursor.execute("SELECT COUNT(*) FROM beliefs")
                total_beliefs = cursor.fetchone()[0]
                
                # 冲突总数
                cursor.execute("SELECT COUNT(*) FROM conflicts")
                total_conflicts = cursor.fetchone()[0]
                
                # 活跃冲突数
                cursor.execute("SELECT COUNT(*) FROM conflicts WHERE status = 'active'")
                active_conflicts = cursor.fetchone()[0]
                
                # 信念类型分布
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM beliefs
                    GROUP BY type
                """)
                belief_type_dist = {row[0]: row[1] for row in cursor.fetchall()}
                
                # 冲突类型分布
                cursor.execute("""
                    SELECT type, COUNT(*) as count
                    FROM conflicts
                    GROUP BY type
                """)
                conflict_type_dist = {row[0]: row[1] for row in cursor.fetchall()}
                
                return {
                    "total_sessions": total_sessions,
                    "total_beliefs": total_beliefs,
                    "total_conflicts": total_conflicts,
                    "active_conflicts": active_conflicts,
                    "belief_type_distribution": belief_type_dist,
                    "conflict_type_distribution": conflict_type_dist
                }
        except Exception as e:
            print(f"获取统计失败: {e}")
            return {}

    # ── 数据维护 ────────────────────────────────────────────────

    def cleanup_old_sessions(self, days: int = 30) -> int:
        """清理旧会话"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cutoff_date = datetime.now().isoformat()
                cursor.execute("""
                    SELECT session_id FROM sessions
                    WHERE updated_at < datetime('now', ?)
                """, (f'-{days} days',))
                
                old_sessions = [row[0] for row in cursor.fetchall()]
                
                for session_id in old_sessions:
                    self.delete_session(session_id)
                
                return len(old_sessions)
        except Exception as e:
            print(f"清理失败: {e}")
            return 0

    def backup_database(self, backup_path: str) -> bool:
        """备份数据库"""
        try:
            import shutil
            shutil.copy2(self.db_path, backup_path)
            return True
        except Exception as e:
            print(f"备份失败: {e}")
            return False
