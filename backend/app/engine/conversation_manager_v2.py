"""
CCG对话管理器 v2
统一的信念演化流程

核心改进：
1. 信念提取和淘汰合并为一次LLM调用
2. 被淘汰信念的冲突自动resolved
3. 冲突检测只看活跃信念，避免重复
4. 对话状态感知：学生刚修正误解时，追问深化而非重复暴露
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models.ccg_models import (
    Belief, Conflict, ChatRequest, ChatResponse,
    ConflictStatus, QuestionType
)
from ..graph.cognitive_graph import CognitiveGraph
from ..storage.sqlite_store import SQLiteStore
from ..engine.belief_extractor_v2 import BeliefExtractorV2
from ..engine.conflict_detector import ConflictDetector, ConflictRanker
from ..engine.question_generator import QuestionGenerator


class ConversationState:
    """对话状态"""
    INIT = "init"
    ACTIVE = "active"
    THINKING = "thinking"
    EXPOSING = "exposing"
    RESOLVING = "resolving"
    PAUSED = "paused"
    COMPLETED = "completed"


class ConversationManagerV2:
    """
    对话管理器 v2

    流程：
    1. 提取新信念 + 识别被淘汰的旧信念（一次LLM调用）
    2. 淘汰旧信念（置信度降到0.1）
    3. 清理涉及被淘汰信念的冲突
    4. 添加新信念到图谱
    5. 检测新冲突（只看活跃信念）
    6. 生成追问
    """

    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or SQLiteStore()
        self.belief_extractor = BeliefExtractorV2()
        self.conflict_detector = ConflictDetector()
        self.question_generator = QuestionGenerator()
        self.active_sessions: Dict[str, CognitiveGraph] = {}

    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """处理学生消息"""
        # 获取或创建会话
        session_id = request.session_id or str(uuid.uuid4())
        graph = self._get_or_create_session(session_id)

        # 获取当前活跃信念（用于上下文）
        active_beliefs = [b for b in graph.beliefs.values() if b.confidence > 0.3]

        # Step 1: 统一提取新信念 + 识别被淘汰的旧信念
        new_beliefs, superseded_ids = await self.belief_extractor.extract_and_update(
            request.student_input,
            existing_beliefs=active_beliefs,
            grade=request.context.get("grade", "high_school"),
            subject=request.context.get("subject", "math")
        )

        # Step 2: 淘汰旧信念
        for belief_id in superseded_ids:
            belief = graph.get_belief(belief_id)
            if belief:
                belief.update_confidence(0.1)
                belief.metadata["superseded"] = True
                belief.metadata["superseded_at"] = datetime.now().isoformat()

        # Step 3: 清理涉及被淘汰信念的冲突
        self._cleanup_obsolete_conflicts(graph, superseded_ids)

        # Step 4: 添加新信念
        for belief in new_beliefs:
            existing = graph.find_similar_belief(belief.proposition)
            if existing and existing.confidence > 0.3:
                existing.activate()
                existing.update_confidence(
                    (existing.confidence + belief.confidence) / 2
                )
            else:
                graph.add_belief(belief)

        # Step 5: 检测新冲突（直接用主图，LLM检测器内部已过滤活跃信念）
        new_conflicts = self.conflict_detector.detect_all_conflicts(graph)

        # 将新冲突添加到主图（去重）
        for conflict in new_conflicts:
            if not self._conflict_exists(graph, conflict.belief_a_id, conflict.belief_b_id):
                graph.add_conflict(conflict)

        # Step 6: 选择最高优先级冲突并生成追问
        ranked = ConflictRanker.rank_conflicts(
            graph.get_active_conflicts(),
            student_readiness=self._estimate_student_readiness(graph),
            max_conflicts=1
        )

        if ranked:
            conflict, priority = ranked[0]
            conflict.update_status(
                ConflictStatus.EXPOSED,
                action="追问暴露",
                result="生成追问"
            )

            question_result = await self.question_generator.generate_question(
                conflict=conflict,
                graph=graph,
                student_input=request.student_input,
                emotional_state=self._estimate_emotional_state(request.student_input),
                cognitive_load=self._estimate_cognitive_load(graph),
                round_count=self._get_round_count(graph)
            )

            ai_response = question_result["question"]
            question_type = QuestionType(question_result["question_type"])
        else:
            ai_response = self._generate_response(
                request.student_input, new_beliefs, superseded_ids
            )
            question_type = None

        # 保存会话
        self._save_session(graph)

        return ChatResponse(
            session_id=session_id,
            ai_response=ai_response,
            question_type=question_type,
            beliefs_extracted=[b.to_dict() for b in new_beliefs],
            conflicts_detected=[c.to_dict() for c in new_conflicts],
            thinking_time_allowed=self._calculate_thinking_time(graph),
            state=self._get_conversation_state(graph)
        )

    def _get_or_create_session(self, session_id: str) -> CognitiveGraph:
        """获取或创建会话"""
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]

        graph = self.store.load_session(session_id)
        if graph:
            self.active_sessions[session_id] = graph
            return graph

        graph = CognitiveGraph(session_id)
        self.active_sessions[session_id] = graph
        return graph

    def _save_session(self, graph: CognitiveGraph):
        """保存会话"""
        self.store.save_session(graph)

    def _cleanup_obsolete_conflicts(self, graph: CognitiveGraph, superseded_ids: List[str]):
        """清理涉及被淘汰信念的冲突"""
        if not superseded_ids:
            return

        superseded_set = set(superseded_ids)
        for cid, conflict in list(graph.conflicts.items()):
            if (conflict.belief_a_id in superseded_set or
                conflict.belief_b_id in superseded_set):
                if conflict.status in [ConflictStatus.ACTIVE, ConflictStatus.EXPOSED]:
                    conflict.update_status(
                        ConflictStatus.RESOLVED,
                        action="信念淘汰",
                        result="旧信念被新输入取代"
                    )

    def _conflict_exists(self, graph: CognitiveGraph, belief_a_id: str, belief_b_id: str) -> bool:
        """检查冲突是否已存在"""
        for conflict in graph.conflicts.values():
            if conflict.status in [ConflictStatus.RESOLVED, ConflictStatus.ABANDONED]:
                continue
            if ((conflict.belief_a_id == belief_a_id and conflict.belief_b_id == belief_b_id) or
                (conflict.belief_a_id == belief_b_id and conflict.belief_b_id == belief_a_id)):
                return True
        return False

    def _make_active_view(self, graph: CognitiveGraph) -> CognitiveGraph:
        """创建只包含活跃信念的图谱视图"""
        view = CognitiveGraph(graph.session_id)

        # 只复制活跃信念（置信度>0.3，非知识库来源）
        for belief in graph.beliefs.values():
            if belief.confidence > 0.3:
                view.beliefs[belief.id] = belief

        return view

    def _estimate_student_readiness(self, graph: CognitiveGraph) -> float:
        """估算学生就绪度"""
        active_conflicts = len(graph.get_active_conflicts())
        if active_conflicts == 0:
            return 1.0
        elif active_conflicts <= 2:
            return 0.8
        elif active_conflicts <= 5:
            return 0.6
        else:
            return 0.4

    def _estimate_emotional_state(self, text: str) -> str:
        """估算情绪状态"""
        frustrated_words = ["难", "不会", "不懂", "不知道", "放弃"]
        for word in frustrated_words:
            if word in text:
                return "frustrated"

        positive_words = ["明白了", "懂了", "会了", "对", "原来"]
        for word in positive_words:
            if word in text:
                return "positive"

        return "neutral"

    def _estimate_cognitive_load(self, graph: CognitiveGraph) -> float:
        """估算认知负荷"""
        belief_count = len([b for b in graph.beliefs.values() if b.confidence > 0.3])
        conflict_count = len(graph.get_active_conflicts())
        return min(1.0, (belief_count * 0.1 + conflict_count * 0.2))

    def _get_round_count(self, graph: CognitiveGraph) -> int:
        """获取追问轮次"""
        return sum(
            1 for c in graph.conflicts.values()
            if c.status in [ConflictStatus.EXPOSED, ConflictStatus.RESOLVED, ConflictStatus.RESOLVED_AI_ASSISTED]
        )

    def _calculate_thinking_time(self, graph: CognitiveGraph) -> int:
        """计算允许的思考时间"""
        load = self._estimate_cognitive_load(graph)
        if load < 0.3:
            return 10
        elif load < 0.6:
            return 15
        else:
            return 20

    def _get_conversation_state(self, graph: CognitiveGraph) -> str:
        """获取对话状态"""
        active_conflicts = graph.get_active_conflicts()
        if not active_conflicts:
            return ConversationState.ACTIVE
        elif len(active_conflicts) > 3:
            return ConversationState.EXPOSING
        else:
            return ConversationState.THINKING

    def _generate_response(
        self,
        student_input: str,
        new_beliefs: List[Belief],
        superseded_ids: List[str]
    ) -> str:
        """
        生成无冲突时的回复 - 自然口语化
        """
        if superseded_ids:
            return "诶，你是怎么想到改过来的？"
        elif new_beliefs:
            return "嗯，然后呢？"
        else:
            return "你说说看？"

    def get_session_graph(self, session_id: str) -> Optional[CognitiveGraph]:
        """获取会话图谱"""
        return self._get_or_create_session(session_id)

    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计"""
        graph = self._get_or_create_session(session_id)
        return graph.get_statistics()
