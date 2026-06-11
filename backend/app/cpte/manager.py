"""
CPTE 认知相变引擎 — 对话管理器

替代 ConversationManagerV2，用认知相变理论驱动对话流程。

流程：
1. LLM 提取信念 → 映射到向量空间
2. 更新能量景观
3. 动力学仿真预测
4. 检测相变时机
5. 计算最优追问方向
6. LLM 生成自然语言追问
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from .config import CPTEConfig, DEFAULT_CONFIG
from .belief_vector import BeliefVector, BeliefDimensionMapper
from .energy_landscape import EnergyLandscape, Attractor
from .dynamics_engine import DynamicsEngine
from .phase_detector import PhaseDetector
from .barrier_calculator import BarrierCalculator
from .escape_planner import EscapePlanner
from .force_optimizer import ForceOptimizer
from .self_optimizer import SelfOptimizer, ConversationRecord
from .knowledge_adapter import KnowledgeAdapter


class CPTEManager:
    """CPTE 对话管理器

    完整的对话处理流程，用认知相变理论替代传统的图冲突检测。
    """

    def __init__(self, config: Optional[CPTEConfig] = None, data_dir: str = "/home/ubuntu/xingban-qiming/data"):
        self.config = config or DEFAULT_CONFIG
        self.N = self.config.belief_dimensions

        # 信念维度映射器
        self.mapper = BeliefDimensionMapper(dimensions=self.N)

        # 知识库适配器
        self.knowledge_adapter = KnowledgeAdapter(data_dir=data_dir, config=self.config)

        # 会话状态
        self.sessions: Dict[str, Dict[str, Any]] = {}

        # 自优化引擎
        self.self_optimizer = SelfOptimizer(config=self.config)

    def init_session(self, session_id: Optional[str] = None, topic: str = "quadratic") -> Dict[str, Any]:
        """初始化会话

        构建该话题的能量景观。
        """
        session_id = session_id or str(uuid.uuid4())

        # 从知识库构建能量景观
        landscape = self.knowledge_adapter.build_landscape_from_knowledge(
            dimensions=self.N,
            textbook_file=f"textbook_L1_{topic}.json" if topic != "quadratic" else "textbook_L1_quadratic.json",
            misconception_file=f"misconceptions_{topic}.json" if topic != "quadratic" else "misconceptions_quadratic.json"
        )

        # 初始化各子系统
        dynamics = DynamicsEngine(landscape, self.config)
        phase_detector = PhaseDetector(self.config)
        barrier_calculator = BarrierCalculator(landscape, self.config)
        escape_planner = EscapePlanner(landscape, self.config)
        force_optimizer = ForceOptimizer(landscape, phase_detector, self.config)

        self.sessions[session_id] = {
            "id": session_id,
            "topic": topic,
            "landscape": landscape,
            "dynamics": dynamics,
            "phase_detector": phase_detector,
            "barrier_calculator": barrier_calculator,
            "escape_planner": escape_planner,
            "force_optimizer": force_optimizer,
            "current_state": None,  # BeliefVector
            "turn_count": 0,
            "created_at": datetime.now().isoformat(),
            "history": [],
        }

        return {
            "session_id": session_id,
            "topic": topic,
            "attractors_count": len(landscape.attractors),
            "has_target": landscape.target_state is not None,
        }

    def process_message(
        self,
        session_id: str,
        student_input: str,
        beliefs_extracted: List[Dict[str, Any]],
        existing_beliefs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """处理学生消息

        Args:
            session_id: 会话 ID
            student_input: 学生输入文本
            beliefs_extracted: LLM 提取的信念列表
            existing_beliefs: 已有的信念列表（用于上下文）

        Returns:
            包含追问策略、相变信号等完整分析结果
        """
        session = self.sessions.get(session_id)
        if not session:
            session_info = self.init_session(session_id)
            session = self.sessions[session_id]

        landscape = session["landscape"]
        dynamics = session["dynamics"]
        phase_detector = session["phase_detector"]
        force_optimizer = session["force_optimizer"]
        self_optimizer = self.self_optimizer

        # Step 1: 将信念映射到向量空间
        belief_vector = self.mapper.map_beliefs_to_vector(
            beliefs_extracted,
            knowledge_context={"topic": session["topic"]}
        )

        # 记录状态变化
        state_before = session["current_state"].vector.copy() if session["current_state"] else np.zeros(self.N)
        state_after = belief_vector.vector.copy()

        # Step 2: 更新能量景观
        energy_before = landscape.energy(state_before)
        energy_after = landscape.energy(state_after)

        # Step 3: 相变检测
        phase_signal = phase_detector.update(state_after, energy_after)

        # Step 4: 计算追问策略
        question_strategy = force_optimizer.compute_question_strategy(state_after)

        # Step 5: 蒙特卡洛仿真预测
        prediction = dynamics.predict_trajectory(state_after)

        # Step 6: 评估上一轮追问效果（如果有）
        turn_evaluation = None
        if session["current_state"] is not None and session["history"]:
            last_force = session["history"][-1].get("force", np.zeros(self.N))
            if isinstance(last_force, list):
                last_force = np.array(last_force)
            turn_evaluation = force_optimizer.evaluate_question_effect(
                state_before, state_after, last_force
            )

            # 记录到自优化器
            self_optimizer.record_conversation(ConversationRecord(
                state_before=state_before,
                state_after=state_after,
                force_applied=last_force,
                energy_before=energy_before,
                energy_after=energy_after,
                effectiveness=turn_evaluation.get("effectiveness", 0.0),
                phase_transition=phase_signal.get("is_critical", False),
            ))

        # 更新会话状态
        session["current_state"] = belief_vector
        session["turn_count"] += 1
        session["history"].append({
            "turn": session["turn_count"],
            "student_input": student_input,
            "state": state_after.tolist(),
            "energy": float(energy_after),
            "phase_signal": phase_signal,
            "force": question_strategy["force"],
            "timestamp": datetime.now().isoformat(),
        })

        return {
            "session_id": session_id,
            "turn_count": session["turn_count"],
            "belief_vector": belief_vector.to_dict(),
            "energy": float(energy_after),
            "energy_change": float(energy_after - energy_before),
            "phase_signal": phase_signal,
            "question_strategy": question_strategy,
            "prediction": prediction,
            "turn_evaluation": turn_evaluation,
            "strategy_for_llm": self._build_llm_strategy(
                question_strategy, phase_signal, belief_vector, session
            ),
        }

    def _build_llm_strategy(
        self,
        question_strategy: Dict[str, Any],
        phase_signal: Dict[str, Any],
        belief_vector: BeliefVector,
        session: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建给 LLM 的追问策略描述

        将 CPTE 的数值分析结果转化为 LLM 可理解的语义描述。
        """
        strategy = question_strategy.get("strategy", {})
        state_analysis = question_strategy.get("state_analysis", {})

        # 维度分析
        dim_analysis = self.mapper.map_vector_to_description(belief_vector)

        llm_strategy = {
            "question_type": strategy.get("question_type", "guide_discovery"),
            "urgency": strategy.get("urgency", "normal"),
            "approach": strategy.get("approach", ""),
            "hints": strategy.get("hints", []),
            "student_strengths": dim_analysis.get("top_strengths", []),
            "student_weaknesses": dim_analysis.get("top_weaknesses", []),
            "coherence": dim_analysis.get("coherence", 0),
            "is_in_attractor": state_analysis.get("in_attractor", False),
            "attractor_description": state_analysis.get("attractor_description", ""),
            "is_critical_point": phase_signal.get("is_critical", False),
            "critical_confidence": phase_signal.get("confidence", 0),
            "turn_count": session.get("turn_count", 0),
        }

        return llm_strategy

    def run_self_optimization(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """运行自优化"""
        if session_id:
            session = self.sessions.get(session_id)
            if session:
                return self.self_optimizer.run_full_optimization(session["landscape"])

        # 对所有会话运行优化
        results = {}
        for sid, session in self.sessions.items():
            results[sid] = self.self_optimizer.run_full_optimization(session["landscape"])
        return results

    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话状态"""
        session = self.sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session_id,
            "topic": session["topic"],
            "turn_count": session["turn_count"],
            "current_state": session["current_state"].to_dict() if session["current_state"] else None,
            "attractors_count": len(session["landscape"].attractors),
            "history_length": len(session["history"]),
        }

    def get_landscape_visualization_data(self, session_id: str) -> Dict[str, Any]:
        """获取能量景观可视化数据"""
        session = self.sessions.get(session_id)
        if not session:
            return {"error": "session_not_found"}

        landscape = session["landscape"]
        current = session["current_state"]

        # 如果有当前状态，计算 2D 切面
        if current:
            center = current.vector
            X, Y, E = landscape.energy_slice_2d(center, axis1=0, axis2=1)
            return {
                "type": "2d_slice",
                "X": X.tolist(),
                "Y": Y.tolist(),
                "E": E.tolist(),
                "center": center.tolist(),
                "attractors": [a.to_dict() for a in landscape.attractors],
                "target": landscape.target_state.tolist() if landscape.target_state is not None else None,
            }

        return {"type": "no_state"}


# 导入 numpy（需要在模块级别）
import numpy as np
