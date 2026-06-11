"""
CCG对话管理器
管理对话状态和流程
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
from ..engine.belief_extractor import BeliefExtractor
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


class ConversationManager:
    """
    对话管理器
    管理整个对话流程
    """
    
    def __init__(self, store: Optional[SQLiteStore] = None):
        self.store = store or SQLiteStore()
        self.belief_extractor = BeliefExtractor()
        self.conflict_detector = ConflictDetector()
        self.question_generator = QuestionGenerator()
        
        # 活跃会话缓存
        self.active_sessions: Dict[str, CognitiveGraph] = {}
    
    async def process_message(self, request: ChatRequest) -> ChatResponse:
        """
        处理学生消息
        
        Args:
            request: 对话请求
            
        Returns:
            对话响应
        """
        # 获取或创建会话
        session_id = request.session_id or str(uuid.uuid4())
        graph = self._get_or_create_session(session_id)
        
        # 提取信念
        beliefs = await self.belief_extractor.extract_beliefs(
            request.student_input,
            grade=request.context.get("grade", "high_school"),
            subject=request.context.get("subject", "math")
        )
        
        # 检测信念修正（新信念是否覆盖/修正了旧信念）
        await self._detect_belief_updates(graph, beliefs)
        
        # 更新图谱
        for belief in beliefs:
            # 检查是否已存在相似信念
            existing = graph.find_similar_belief(belief.proposition)
            if existing:
                # 更新已有信念
                existing.activate()
                existing.update_confidence(
                    (existing.confidence + belief.confidence) / 2
                )
            else:
                # 添加新信念
                graph.add_belief(belief)
        
        # 检测冲突
        new_conflicts = self.conflict_detector.detect_all_conflicts(graph)
        
        # 获取最高优先级冲突
        highest_priority = self.conflict_detector.detect_all_conflicts(graph)
        ranked = ConflictRanker.rank_conflicts(
            highest_priority,
            student_readiness=self._estimate_student_readiness(graph),
            max_conflicts=1
        )
        
        # 生成追问
        if ranked:
            conflict, priority = ranked[0]
            
            # 更新冲突状态
            conflict.update_status(
                ConflictStatus.EXPOSED,
                action="追问暴露",
                result="生成追问"
            )
            
            # 生成追问
            question_result = await self.question_generator.generate_question(
                conflict=conflict,
                graph=graph,
                emotional_state=self._estimate_emotional_state(request.student_input),
                cognitive_load=self._estimate_cognitive_load(graph),
                round_count=self._get_round_count(graph)
            )
            
            ai_response = question_result["question"]
            question_type = QuestionType(question_result["question_type"])
        else:
            # 无冲突，给出一般性回复
            ai_response = self._generate_general_response(request.student_input)
            question_type = None
        
        # 保存会话
        self._save_session(graph)
        
        # 构建响应
        return ChatResponse(
            session_id=session_id,
            ai_response=ai_response,
            question_type=question_type,
            beliefs_extracted=[b.to_dict() for b in beliefs],
            conflicts_detected=[c.to_dict() for c in new_conflicts],
            thinking_time_allowed=self._calculate_thinking_time(graph),
            state=self._get_conversation_state(graph)
        )
    
    def _get_or_create_session(self, session_id: str) -> CognitiveGraph:
        """获取或创建会话"""
        # 先从缓存获取
        if session_id in self.active_sessions:
            return self.active_sessions[session_id]
        
        # 从存储加载
        graph = self.store.load_session(session_id)
        if graph:
            self.active_sessions[session_id] = graph
            return graph
        
        # 创建新会话
        graph = CognitiveGraph(session_id)
        self.active_sessions[session_id] = graph
        return graph
    
    def _save_session(self, graph: CognitiveGraph):
        """保存会话"""
        self.store.save_session(graph)
    
    async def _detect_belief_updates(self, graph: CognitiveGraph, new_beliefs: List[Belief]):
        """
        检测新信念是否修正/覆盖了旧信念
        
        策略：
        1. 文本包含：新信念文本完全包含旧信念
        2. 解集扩展：旧信念只提到部分解，新信念提到了更多解
        3. 语义覆盖：新旧信念都提到了同一变量的解，但新信念解集更大
        """
        if not graph.beliefs or not new_beliefs:
            return
        
        import re
        
        # 合并所有新信念中提到的 x=N 值
        all_new_values = set()
        for nb in new_beliefs:
            all_new_values.update(re.findall(r'[xX]\s*=\s*(\d+)', nb.proposition))
        
        for old_belief in list(graph.beliefs.values()):
            if old_belief.source == "knowledge_base":
                continue
            
            old_prop = old_belief.proposition.strip()
            deprecated = False
            
            # 策略1：文本包含
            for new_belief in new_beliefs:
                new_prop = new_belief.proposition.strip()
                if len(old_prop) > 4 and old_prop in new_prop:
                    deprecated = True
                    break
            
            # 策略2：解集扩展
            if not deprecated and all_new_values:
                old_values = set(re.findall(r'[xX]\s*=\s*(\d+)', old_prop))
                # 旧信念提到了某变量的解，但新信念集合更大
                if old_values and old_values < all_new_values:
                    deprecated = True
                # 旧信念暗示唯一解，但新信念提到多个值
                if len(all_new_values) > 1:
                    single_hints = ["解是", "答案是", "唯一", "就是", "唯一解", "全部解", "就够了", "不需要再"]
                    if any(h in old_prop for h in single_hints):
                        deprecated = True
            
            # 策略3：新信念已包含正确答案，旧信念的启发式方法被证伪
            if not deprecated:
                # 新信念中有"解是x=M和x=N"这样的完整解
                complete_solution = any(
                    "解是" in nb.proposition and "和" in nb.proposition
                    for nb in new_beliefs
                )
                if complete_solution:
                    incomplete_hints = ["找到一个", "一个解", "不需要", "就够了", "不用再"]
                    if any(h in old_prop for h in incomplete_hints):
                        deprecated = True
            
            if deprecated:
                old_belief.update_confidence(0.15)
        
        # 清理过时冲突
        expired_beliefs = {b.id for b in graph.beliefs.values() if b.confidence < 0.3}
        for cid, c in list(graph.conflicts.items()):
            if c.belief_a_id in expired_beliefs or c.belief_b_id in expired_beliefs:
                c.status = ConflictStatus.RESOLVED
    
    def _estimate_student_readiness(self, graph: CognitiveGraph) -> float:
        """估算学生就绪度"""
        # 简化实现：基于活跃冲突数量
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
        text_lower = text.lower()
        
        # 挫败词汇
        frustrated_words = ["难", "不会", "不懂", "不知道", "放弃"]
        for word in frustrated_words:
            if word in text_lower:
                return "frustrated"
        
        # 积极词汇
        positive_words = ["明白了", "懂了", "会了", "对"]
        for word in positive_words:
            if word in text_lower:
                return "positive"
        
        return "neutral"
    
    def _estimate_cognitive_load(self, graph: CognitiveGraph) -> float:
        """估算认知负荷"""
        # 简化实现：基于信念数量和冲突数量
        belief_count = len(graph.beliefs)
        conflict_count = len(graph.get_active_conflicts())
        
        # 归一化到0-1
        load = min(1.0, (belief_count * 0.1 + conflict_count * 0.2))
        return load
    
    def _get_round_count(self, graph: CognitiveGraph) -> int:
        """获取追问轮次"""
        # 简化实现：统计已暴露的冲突数量
        exposed_count = sum(
            1 for c in graph.conflicts.values()
            if c.status in [ConflictStatus.EXPOSED, ConflictStatus.RESOLVED]
        )
        return exposed_count
    
    def _calculate_thinking_time(self, graph: CognitiveGraph) -> int:
        """计算允许的思考时间"""
        # 基于认知负荷
        load = self._estimate_cognitive_load(graph)
        
        if load < 0.3:
            return 10  # 低负荷，10秒
        elif load < 0.6:
            return 15  # 中负荷，15秒
        else:
            return 20  # 高负荷，20秒
    
    def _get_conversation_state(self, graph: CognitiveGraph) -> str:
        """获取对话状态"""
        active_conflicts = graph.get_active_conflicts()
        
        if not active_conflicts:
            return ConversationState.ACTIVE
        elif len(active_conflicts) > 3:
            return ConversationState.EXPOSING
        else:
            return ConversationState.THINKING
    
    def _generate_general_response(self, student_input: str) -> str:
        """生成一般性回复"""
        # 简化实现
        return "你再说说你的想法？"
    
    def get_session_graph(self, session_id: str) -> Optional[CognitiveGraph]:
        """获取会话图谱"""
        return self._get_or_create_session(session_id)
    
    def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计"""
        graph = self._get_or_create_session(session_id)
        return graph.get_statistics()
