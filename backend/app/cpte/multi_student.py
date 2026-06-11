"""
优化7: 多学生迁移学习

从多个学生的对话数据中学习通用的误解模式和最优追问策略。
解决冷启动问题：新学生不需要从零开始。

核心思想：
- 误解是共性的（很多学生犯同样的错）
- 最优追问策略是可迁移的
- 能量景观的参数可以跨学生共享
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class StudentProfile:
    """学生画像"""
    student_id: str
    topics: List[str] = field(default_factory=list)
    total_interactions: int = 0
    mean_effectiveness: float = 0.0
    misconception_pattern: Optional[np.ndarray] = None
    learning_rate: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "topics": self.topics,
            "total_interactions": self.total_interactions,
            "mean_effectiveness": self.mean_effectiveness,
            "learning_rate": self.learning_rate,
        }


@dataclass
class CollectiveKnowledge:
    """集体知识

    从所有学生的数据中提取的通用模式。
    """
    # 通用误解模式（吸引子参数的统计分布）
    attractor_distributions: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 通用最优追问方向
    effective_force_directions: Dict[str, np.ndarray] = field(default_factory=dict)

    # 各知识点的平均能量景观参数
    landscape_params: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # 学生聚类（不同学习风格）
    learning_style_clusters: Dict[str, np.ndarray] = field(default_factory=dict)


class MultiStudentTransfer:
    """多学生迁移学习管理器

    从多个学生的对话数据中学习通用知识，
    并将这些知识迁移到新学生。
    """

    def __init__(self, dimensions: int = 16):
        self.dimensions = dimensions

        # 学生画像库
        self.students: Dict[str, StudentProfile] = {}

        # 集体知识
        self.collective = CollectiveKnowledge()

        # 对话记录（用于学习）
        self.interaction_log: List[Dict[str, Any]] = []

        # 学习到的通用模式
        self._common_misconceptions: List[Dict[str, Any]] = []
        self._effective_strategies: List[Dict[str, Any]] = []

    def register_student(
        self,
        student_id: str,
        topics: Optional[List[str]] = None
    ) -> StudentProfile:
        """注册学生"""
        if student_id not in self.students:
            self.students[student_id] = StudentProfile(
                student_id=student_id,
                topics=topics or [],
            )
        return self.students[student_id]

    def log_interaction(
        self,
        student_id: str,
        topic: str,
        state_before: np.ndarray,
        state_after: np.ndarray,
        question_force: np.ndarray,
        effectiveness: float,
        phase_transition: bool = False
    ):
        """记录一次交互"""
        self.interaction_log.append({
            "student_id": student_id,
            "topic": topic,
            "state_before": state_before.tolist(),
            "state_after": state_after.tolist(),
            "force": question_force.tolist(),
            "effectiveness": effectiveness,
            "phase_transition": phase_transition,
            "timestamp": datetime.now().isoformat(),
        })

        # 更新学生画像
        student = self.students.get(student_id)
        if student:
            student.total_interactions += 1
            student.mean_effectiveness = (
                (student.mean_effectiveness * (student.total_interactions - 1) + effectiveness)
                / student.total_interactions
            )
            if topic not in student.topics:
                student.topics.append(topic)

    def learn_collective_knowledge(self) -> Dict[str, Any]:
        """从所有交互数据中学习集体知识

        三步：
        1. 聚类发现通用误解模式
        2. 分析有效追问方向
        3. 提取通用能量景观参数
        """
        if len(self.interaction_log) < 10:
            return {"status": "insufficient_data", "interactions": len(self.interaction_log)}

        results = {
            "misconceptions_discovered": 0,
            "strategies_learned": 0,
            "students_analyzed": len(self.students),
        }

        # Step 1: 发现通用误解模式
        misconceptions = self._discover_common_misconceptions()
        self._common_misconceptions = misconceptions
        results["misconceptions_discovered"] = len(misconceptions)

        # Step 2: 分析有效追问方向
        strategies = self._analyze_effective_strategies()
        self._effective_strategies = strategies
        results["strategies_learned"] = len(strategies)

        # Step 3: 提取通用景观参数
        landscape_params = self._extract_common_landscape_params()
        self.collective.landscape_params = landscape_params

        return results

    def _discover_common_misconceptions(self) -> List[Dict[str, Any]]:
        """发现通用误解模式

        从"卡住"的交互中聚类，找到多个学生共有的误解。
        """
        # 收集"卡住"的状态
        stuck_states = []
        for log in self.interaction_log:
            if log["effectiveness"] < 0.3:
                stuck_states.append(np.array(log["state_before"]))

        if len(stuck_states) < 3:
            return []

        # 聚类
        from sklearn.cluster import DBSCAN
        states_array = np.array(stuck_states)
        clustering = DBSCAN(eps=0.3, min_samples=2).fit(states_array)

        misconceptions = []
        for label in set(clustering.labels_):
            if label == -1:
                continue

            cluster_mask = clustering.labels_ == label
            cluster_states = states_array[cluster_mask]
            center = np.mean(cluster_states, axis=0)
            size = int(np.sum(cluster_mask))

            # 计算有多少不同学生
            student_ids = set()
            idx = 0
            for log in self.interaction_log:
                if log["effectiveness"] < 0.3:
                    if cluster_mask[idx]:
                        student_ids.add(log["student_id"])
                    idx += 1

            misconceptions.append({
                "center": center.tolist(),
                "size": size,
                "unique_students": len(student_ids),
                "prevalence": len(student_ids) / max(1, len(self.students)),
            })

        misconceptions.sort(key=lambda x: x["prevalence"], reverse=True)
        return misconceptions

    def _analyze_effective_strategies(self) -> List[Dict[str, Any]]:
        """分析有效追问策略

        找到效果好的追问方向，提取通用模式。
        """
        effective = [log for log in self.interaction_log if log["effectiveness"] > 0.5]
        if not effective:
            return []

        # 按话题分组
        by_topic = defaultdict(list)
        for log in effective:
            by_topic[log["topic"]].append(log)

        strategies = []
        for topic, logs in by_topic.items():
            forces = np.array([log["force"] for log in logs])
            mean_force = np.mean(forces, axis=0)

            # 找出力的主要方向
            abs_force = np.abs(mean_force)
            top_dims = np.argsort(abs_force)[-3:][::-1]

            strategies.append({
                "topic": topic,
                "mean_force": mean_force.tolist(),
                "top_dimensions": top_dims.tolist(),
                "sample_count": len(logs),
                "mean_effectiveness": float(np.mean([l["effectiveness"] for l in logs])),
            })

        return strategies

    def _extract_common_landscape_params(self) -> Dict[str, Dict[str, float]]:
        """提取通用能量景观参数

        分析各话题的平均能量变化、吸引子深度等。
        """
        by_topic = defaultdict(list)
        for log in self.interaction_log:
            topic = log.get("topic", "unknown")
            delta = np.array(log["state_after"]) - np.array(log["state_before"])
            by_topic[topic].append({
                "delta_norm": float(np.linalg.norm(delta)),
                "effectiveness": log["effectiveness"],
                "phase_transition": log["phase_transition"],
            })

        params = {}
        for topic, records in by_topic.items():
            if len(records) < 3:
                continue

            delta_norms = [r["delta_norm"] for r in records]
            effectiveness = [r["effectiveness"] for r in records]
            pt_rate = np.mean([r["phase_transition"] for r in records])

            params[topic] = {
                "mean_delta_norm": float(np.mean(delta_norms)),
                "std_delta_norm": float(np.std(delta_norms)),
                "mean_effectiveness": float(np.mean(effectiveness)),
                "phase_transition_rate": float(pt_rate),
                "sample_count": len(records),
            }

        return params

    def get_cold_start_params(
        self,
        student_id: str,
        topic: str
    ) -> Dict[str, Any]:
        """为新学生获取冷启动参数

        基于集体知识，为新学生的能量景观提供初始参数。
        """
        # 查找该话题的通用误解
        topic_misconceptions = [
            m for m in self._common_misconceptions
            if m["prevalence"] > 0.1  # 至少 10% 的学生犯过
        ]

        # 查找该话题的有效策略
        topic_strategies = [
            s for s in self._effective_strategies
            if s["topic"] == topic
        ]

        # 查找相似学生
        similar_students = self._find_similar_students(student_id, topic)

        return {
            "initial_attractors": topic_misconceptions[:5],
            "recommended_strategies": topic_strategies[:3],
            "similar_students": [s.to_dict() for s in similar_students[:3]],
            "landscape_params": self.collective.landscape_params.get(topic, {}),
        }

    def _find_similar_students(
        self,
        student_id: str,
        topic: str
    ) -> List[StudentProfile]:
        """找到与当前学生相似的历史学生"""
        current = self.students.get(student_id)
        if current is None:
            return []

        candidates = [
            s for s in self.students.values()
            if s.student_id != student_id and topic in s.topics
        ]

        # 按学习率相似度排序
        if current.total_interactions > 0:
            candidates.sort(
                key=lambda s: abs(s.learning_rate - current.learning_rate)
            )
        else:
            # 冷启动：按交互量排序（经验最丰富的排前面）
            candidates.sort(key=lambda s: s.total_interactions, reverse=True)

        return candidates

    def transfer_landscape_params(
        self,
        source_student_id: str,
        target_student_id: str,
        topic: str,
        transfer_weight: float = 0.3
    ) -> Dict[str, Any]:
        """在学生之间迁移能量景观参数

        用源学生的参数为目标学生提供初始值。
        """
        source = self.students.get(source_student_id)
        target = self.students.get(target_student_id)

        if source is None or target is None:
            return {"error": "student_not_found"}

        # 获取源学生该话题的交互记录
        source_interactions = [
            log for log in self.interaction_log
            if log["student_id"] == source_student_id and log.get("topic") == topic
        ]

        if not source_interactions:
            return {"error": "no_source_data"}

        # 提取源学生的参数
        forces = np.array([log["force"] for log in source_interactions])
        mean_force = np.mean(forces, axis=0)

        # 计算迁移后的参数
        transferred = {
            "mean_force": (mean_force * transfer_weight).tolist(),
            "transfer_weight": transfer_weight,
            "source_interactions": len(source_interactions),
            "source_effectiveness": source.mean_effectiveness,
        }

        return transferred

    def get_collective_summary(self) -> Dict[str, Any]:
        """获取集体知识总结"""
        return {
            "total_students": len(self.students),
            "total_interactions": len(self.interaction_log),
            "common_misconceptions": len(self._common_misconceptions),
            "effective_strategies": len(self._effective_strategies),
            "topics_covered": list(self.collective.landscape_params.keys()),
            "mean_student_effectiveness": float(np.mean([
                s.mean_effectiveness for s in self.students.values()
                if s.total_interactions > 0
            ])) if self.students else 0,
        }
