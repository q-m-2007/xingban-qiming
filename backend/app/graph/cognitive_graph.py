"""
CCG认知图谱 - 基于NetworkX的图结构封装
管理信念节点、关系边、冲突记录
"""

import networkx as nx
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import json

from ..models.ccg_models import (
    Belief, BeliefRelation, Conflict,
    BeliefType, RelationType, ConflictType, ConflictStatus
)


class CognitiveGraph:
    """
    认知图谱核心类
    使用NetworkX有向图存储学生的信念网络
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.graph = nx.DiGraph()
        self.beliefs: Dict[str, Belief] = {}
        self.relations: Dict[str, BeliefRelation] = {}
        self.conflicts: Dict[str, Conflict] = {}
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    # ── 信念操作 ────────────────────────────────────────────────

    def add_belief(self, belief: Belief) -> str:
        """添加信念节点"""
        self.beliefs[belief.id] = belief
        self.graph.add_node(belief.id, **belief.to_dict())
        self.updated_at = datetime.now()
        return belief.id

    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """获取信念"""
        return self.beliefs.get(belief_id)

    def update_belief(self, belief_id: str, updates: Dict[str, Any]) -> bool:
        """更新信念"""
        if belief_id not in self.beliefs:
            return False
        
        belief = self.beliefs[belief_id]
        for key, value in updates.items():
            if hasattr(belief, key):
                setattr(belief, key, value)
        
        # 更新图节点
        self.graph.nodes[belief_id].update(belief.to_dict())
        self.updated_at = datetime.now()
        return True

    def remove_belief(self, belief_id: str) -> bool:
        """删除信念"""
        if belief_id not in self.beliefs:
            return False
        
        del self.beliefs[belief_id]
        self.graph.remove_node(belief_id)
        
        # 删除相关关系
        related_relations = [
            rid for rid, r in self.relations.items()
            if r.source_id == belief_id or r.target_id == belief_id
        ]
        for rid in related_relations:
            del self.relations[rid]
        
        self.updated_at = datetime.now()
        return True

    def find_similar_belief(self, proposition: str, threshold: float = 0.9) -> Optional[Belief]:
        """查找相似信念（简单字符串匹配，后续可用向量）"""
        proposition_lower = proposition.lower().strip()
        
        for belief in self.beliefs.values():
            # 简单相似度计算
            existing_lower = belief.proposition.lower().strip()
            if existing_lower == proposition_lower:
                return belief
            
            # 包含关系
            if proposition_lower in existing_lower or existing_lower in proposition_lower:
                if len(proposition_lower) > 5 and len(existing_lower) > 5:
                    return belief
        
        return None

    def get_beliefs_by_type(self, belief_type: BeliefType) -> List[Belief]:
        """按类型获取信念"""
        return [b for b in self.beliefs.values() if b.type == belief_type]

    def get_active_beliefs(self, min_confidence: float = 0.5) -> List[Belief]:
        """获取活跃信念（置信度>阈值）"""
        return [b for b in self.beliefs.values() if b.confidence >= min_confidence]

    # ── 关系操作 ────────────────────────────────────────────────

    def add_relation(self, relation: BeliefRelation) -> str:
        """添加关系边"""
        # 验证节点存在
        if relation.source_id not in self.beliefs:
            raise ValueError(f"源信念不存在: {relation.source_id}")
        if relation.target_id not in self.beliefs:
            raise ValueError(f"目标信念不存在: {relation.target_id}")
        
        self.relations[relation.id] = relation
        self.graph.add_edge(
            relation.source_id,
            relation.target_id,
            relation_id=relation.id,
            **relation.to_dict()
        )
        self.updated_at = datetime.now()
        return relation.id

    def get_relation(self, relation_id: str) -> Optional[BeliefRelation]:
        """获取关系"""
        return self.relations.get(relation_id)

    def get_relations_for_belief(self, belief_id: str) -> List[BeliefRelation]:
        """获取信念的所有关系"""
        return [
            r for r in self.relations.values()
            if r.source_id == belief_id or r.target_id == belief_id
        ]

    def get_contradicting_beliefs(self, belief_id: str) -> List[Belief]:
        """获取与指定信念矛盾的所有信念"""
        contradicting = []
        for relation in self.relations.values():
            if relation.type == RelationType.CONTRADICTS:
                if relation.source_id == belief_id:
                    target = self.beliefs.get(relation.target_id)
                    if target:
                        contradicting.append(target)
                elif relation.target_id == belief_id:
                    source = self.beliefs.get(relation.source_id)
                    if source:
                        contradicting.append(source)
        return contradicting

    # ── 冲突操作 ────────────────────────────────────────────────

    def add_conflict(self, conflict: Conflict) -> str:
        """添加冲突"""
        self.conflicts[conflict.id] = conflict
        self.updated_at = datetime.now()
        return conflict.id

    def get_conflict(self, conflict_id: str) -> Optional[Conflict]:
        """获取冲突"""
        return self.conflicts.get(conflict_id)

    def get_active_conflicts(self) -> List[Conflict]:
        """获取所有活跃冲突"""
        return [c for c in self.conflicts.values() if c.status == ConflictStatus.ACTIVE]

    def get_conflicts_for_belief(self, belief_id: str) -> List[Conflict]:
        """获取信念相关的所有冲突"""
        return [
            c for c in self.conflicts.values()
            if c.belief_a_id == belief_id or c.belief_b_id == belief_id
        ]

    def get_highest_priority_conflict(self, student_readiness: float = 1.0) -> Optional[Conflict]:
        """获取最高优先级的冲突"""
        active_conflicts = self.get_active_conflicts()
        if not active_conflicts:
            return None
        
        # 计算每个冲突的新颖度（避免重复追问同一冲突）
        conflict_type_counts = {}
        for c in active_conflicts:
            conflict_type_counts[c.type] = conflict_type_counts.get(c.type, 0) + 1
        
        def calculate_novelty(conflict: Conflict) -> float:
            count = conflict_type_counts.get(conflict.type, 0)
            return max(0, 1 - (count / 3))
        
        # 按优先级排序
        scored_conflicts = [
            (c, c.calculate_priority(student_readiness, calculate_novelty(c)))
            for c in active_conflicts
        ]
        scored_conflicts.sort(key=lambda x: x[1], reverse=True)
        
        return scored_conflicts[0][0] if scored_conflicts else None

    # ── 统计信息 ────────────────────────────────────────────────

    def get_statistics(self) -> Dict[str, Any]:
        """获取图谱统计信息"""
        return {
            "session_id": self.session_id,
            "total_beliefs": len(self.beliefs),
            "total_relations": len(self.relations),
            "total_conflicts": len(self.conflicts),
            "active_conflicts": len(self.get_active_conflicts()),
            "belief_types": {
                bt.value: len(self.get_beliefs_by_type(bt))
                for bt in BeliefType
            },
            "avg_confidence": (
                sum(b.confidence for b in self.beliefs.values()) / len(self.beliefs)
                if self.beliefs else 0
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    # ── 序列化 ────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "session_id": self.session_id,
            "beliefs": [b.to_dict() for b in self.beliefs.values()],
            "relations": [r.to_dict() for r in self.relations.values()],
            "conflicts": [c.to_dict() for c in self.conflicts.values()],
            "statistics": self.get_statistics(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveGraph':
        """从字典反序列化"""
        graph = cls(data["session_id"])
        graph.created_at = datetime.fromisoformat(data["created_at"])
        graph.updated_at = datetime.fromisoformat(data["updated_at"])
        
        # 恢复信念
        for belief_data in data.get("beliefs", []):
            belief = Belief(**belief_data)
            graph.beliefs[belief.id] = belief
            graph.graph.add_node(belief.id, **belief.to_dict())
        
        # 恢复关系
        for relation_data in data.get("relations", []):
            relation = BeliefRelation(**relation_data)
            graph.relations[relation.id] = relation
            graph.graph.add_edge(
                relation.source_id,
                relation.target_id,
                relation_id=relation.id,
                **relation.to_dict()
            )
        
        # 恢复冲突
        for conflict_data in data.get("conflicts", []):
            conflict = Conflict(**conflict_data)
            graph.conflicts[conflict.id] = conflict
        
        return graph
