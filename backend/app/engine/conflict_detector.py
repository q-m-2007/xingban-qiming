"""
CCG冲突检测器
检测学生信念之间的冲突
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from ..models.ccg_models import (
    Belief, BeliefRelation, Conflict,
    BeliefType, RelationType, ConflictType, ConflictStatus
)
from ..graph.cognitive_graph import CognitiveGraph


class ConflictDetector:
    """
    冲突检测器
    检测学生认知图谱中的各类冲突
    """
    
    # 冲突类型权重
    CONFLICT_CLARITY = {
        ConflictType.LOGICAL: 1.0,
        ConflictType.BOUNDARY: 0.8,
        ConflictType.CONFIDENCE: 0.6,
        ConflictType.PATH_DEPENDENCY: 0.7
    }
    
    def detect_all_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        检测所有类型的冲突
        
        Args:
            graph: 认知图谱
            
        Returns:
            检测到的冲突列表
        """
        conflicts = []
        
        # 规则1：逻辑矛盾检测
        conflicts.extend(self.detect_logical_conflicts(graph))
        
        # 规则2：边界矛盾检测
        conflicts.extend(self.detect_boundary_conflicts(graph))
        
        # 规则3：置信度矛盾检测
        conflicts.extend(self.detect_confidence_conflicts(graph))
        
        # 规则4：路径依赖矛盾检测
        conflicts.extend(self.detect_path_dependency_conflicts(graph))
        
        # 规则5：LLM辅助误解检测（当规则检测无结果时）
        if not conflicts:
            llm_conflicts = self.detect_llm_conflicts(graph)
            if llm_conflicts:
                conflicts.extend(llm_conflicts)
        
        return conflicts
    
    def detect_logical_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        规则1：逻辑矛盾检测
        
        如果 A 逻辑蕴含 P，且 B 逻辑蕴含 ¬P，且两者置信度均 > 0.5：
        创建 LOGICAL 类型冲突
        """
        conflicts = []
        
        # 获取所有蕴含关系
        implies_relations = [
            r for r in graph.relations.values()
            if r.type == RelationType.IMPLIES
        ]
        
        # 检查矛盾的蕴含
        for i, rel_a in enumerate(implies_relations):
            for rel_b in implies_relations[i+1:]:
                # 检查是否指向矛盾的结论
                if self._are_contradictory(graph, rel_a.target_id, rel_b.target_id):
                    belief_a = graph.get_belief(rel_a.source_id)
                    belief_b = graph.get_belief(rel_b.source_id)
                    
                    if (belief_a and belief_b and 
                        belief_a.confidence > 0.5 and belief_b.confidence > 0.5):
                        
                        # 检查是否已存在相同冲突
                        if not self._conflict_exists(graph, belief_a.id, belief_b.id):
                            conflict = self._create_conflict(
                                belief_a, belief_b,
                                ConflictType.LOGICAL,
                                graph
                            )
                            conflicts.append(conflict)
        
        # 检查直接矛盾的信念
        for rel in graph.relations.values():
            if rel.type == RelationType.CONTRADICTS:
                belief_a = graph.get_belief(rel.source_id)
                belief_b = graph.get_belief(rel.target_id)
                
                if (belief_a and belief_b and 
                    belief_a.confidence > 0.5 and belief_b.confidence > 0.5):
                    
                    if not self._conflict_exists(graph, belief_a.id, belief_b.id):
                        conflict = self._create_conflict(
                            belief_a, belief_b,
                            ConflictType.LOGICAL,
                            graph
                        )
                        conflicts.append(conflict)
        
        return conflicts
    
    def detect_boundary_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        规则2：边界矛盾检测
        
        如果 A 在条件X下成立，但学生将其应用于条件Y（且Y与X有本质差异）：
        创建 BOUNDARY 类型冲突
        """
        conflicts = []
        
        # 获取所有信念
        beliefs = list(graph.beliefs.values())
        
        for i, belief_a in enumerate(beliefs):
            for belief_b in beliefs[i+1:]:
                # 检查是否是同一概念在不同条件下
                if self._same_concept_different_conditions(belief_a, belief_b):
                    # 检查学生是否混淆了条件
                    if self._student_confuses_conditions(graph, belief_a, belief_b):
                        if not self._conflict_exists(graph, belief_a.id, belief_b.id):
                            conflict = self._create_conflict(
                                belief_a, belief_b,
                                ConflictType.BOUNDARY,
                                graph
                            )
                            conflicts.append(conflict)
        
        return conflicts
    
    def detect_confidence_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        规则3：置信度矛盾检测
        
        如果学生同时持有信念A和信念B，且 A 和 B 语义矛盾，且两者置信度均 > 0.5：
        创建 CONFIDENCE 类型冲突
        """
        conflicts = []
        
        beliefs = list(graph.beliefs.values())
        
        for i, belief_a in enumerate(beliefs):
            for belief_b in beliefs[i+1:]:
                # 检查语义矛盾
                if self._semantically_contradictory(belief_a, belief_b):
                    # 检查置信度
                    if belief_a.confidence > 0.5 and belief_b.confidence > 0.5:
                        if not self._conflict_exists(graph, belief_a.id, belief_b.id):
                            conflict = self._create_conflict(
                                belief_a, belief_b,
                                ConflictType.CONFIDENCE,
                                graph
                            )
                            conflicts.append(conflict)
        
        return conflicts
    
    def detect_path_dependency_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        规则4：路径依赖矛盾检测
        
        如果学生用路径P推导出信念A，用路径Q推导出信念B，
        且 P 和 Q 的假设前提互斥，但学生未意识到：
        创建 PATH_DEPENDENCY 类型冲突
        """
        conflicts = []
        
        # 获取所有前提性信念
        presuppositions = graph.get_beliefs_by_type(BeliefType.PRESUPPOSITION)
        
        for i, pre_a in enumerate(presuppositions):
            for pre_b in presuppositions[i+1:]:
                # 检查前提是否互斥
                if self._premises_mutually_exclusive(pre_a, pre_b):
                    # 找到依赖这些前提的信念
                    beliefs_a = self._get_dependent_beliefs(graph, pre_a.id)
                    beliefs_b = self._get_dependent_beliefs(graph, pre_b.id)
                    
                    for belief_a in beliefs_a:
                        for belief_b in beliefs_b:
                            if (belief_a.confidence > 0.5 and 
                                belief_b.confidence > 0.5 and
                                not self._conflict_exists(graph, belief_a.id, belief_b.id)):
                                
                                conflict = self._create_conflict(
                                    belief_a, belief_b,
                                    ConflictType.PATH_DEPENDENCY,
                                    graph
                                )
                                conflicts.append(conflict)
        
        return conflicts
    
    def detect_llm_conflicts(self, graph: CognitiveGraph) -> List[Conflict]:
        """
        规则5：LLM辅助误解检测
        
        只在以下条件满足时触发：
        1. 规则检测未发现冲突
        2. 图谱中没有已存在的活跃冲突
        3. 活跃信念中可能存在误解
        """
        import asyncio
        
        # 如果已有活跃冲突，不重复检测
        if graph.get_active_conflicts():
            return []
        
        # 只看活跃信念（置信度>0.3，排除知识库）
        beliefs = [b for b in graph.beliefs.values() 
                   if b.confidence > 0.3 and b.source != "knowledge_base"]
        if not beliefs:
            return []
        
        # 清理旧的知识库信念（避免累积），但保留有活跃冲突的
        old_kb = [b for b in graph.beliefs.values() if b.source == "knowledge_base"]
        active_conflict_beliefs = set()
        for c in graph.get_active_conflicts():
            active_conflict_beliefs.add(c.belief_a_id)
            active_conflict_beliefs.add(c.belief_b_id)
        for kb in old_kb:
            if kb.id not in active_conflict_beliefs:
                graph.remove_belief(kb.id)
        
        belief_texts = [f"- {b.proposition}（置信度{b.confidence}）" for b in beliefs]
        beliefs_str = "\n".join(belief_texts)
        
        prompt = f"""分析以下学生信念，判断是否存在数学误解或不完整的理解。

学生信念：
{beliefs_str}

请判断：
1. 这些信念中是否存在错误的数学理解？
2. 是否存在"只找到部分解"的情况？
3. 是否存在概念上的不完整理解？

只在确实存在误解时返回true。如果学生的理解基本正确，返回false。

请返回JSON格式：
{{
    "has_misconception": true/false,
    "misconception_description": "误解描述",
    "correct_understanding": "正确的数学理解",
    "related_belief": "相关的错误信念文本"
}}"""
        
        try:
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._llm_detect_misconception(prompt, graph, beliefs)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._llm_detect_misconception(prompt, graph, beliefs)
                )
        except Exception as e:
            print(f"LLM冲突检测失败: {e}")
            return []
    
    async def _llm_detect_misconception(
        self, prompt: str, graph: CognitiveGraph, beliefs: List[Belief]
    ) -> List[Conflict]:
        """异步执行LLM误解检测"""
        from ..engine.llm_client import generate_structured
        
        schema = {
            "has_misconception": "boolean",
            "misconception_description": "string",
            "correct_understanding": "string",
            "related_belief": "string"
        }
        
        result = await generate_structured(prompt, schema)
        
        if not result.get("has_misconception"):
            return []
        
        # 找到相关的错误信念
        related_text = result.get("related_belief", "")
        target_belief = None
        
        # 优先精确匹配
        for b in beliefs:
            if related_text and related_text in b.proposition:
                target_belief = b
                break
        
        # 模糊匹配（关键词重叠）
        if not target_belief and related_text:
            related_words = set(related_text)
            best_score = 0
            for b in beliefs:
                overlap = len(related_words & set(b.proposition))
                if overlap > best_score:
                    best_score = overlap
                    target_belief = b
        
        # 最后兜底：置信度最高的信念
        if not target_belief and beliefs:
            target_belief = max(beliefs, key=lambda b: b.confidence)
        
        if not target_belief:
            return []
        
        # 创建"正确理解"信念
        correct_belief = Belief(
            proposition=result.get("correct_understanding", "正确的数学理解"),
            type=target_belief.type,
            confidence=0.9,
            source="knowledge_base",
            emotional_tag=target_belief.emotional_tag,
            metadata={"layer": "知识库", "source": "llm_analysis"}
        )
        
        graph.add_belief(correct_belief)
        
        # 创建冲突
        if not self._conflict_exists(graph, target_belief.id, correct_belief.id):
            conflict = self._create_conflict(
                target_belief, correct_belief,
                ConflictType.CONFIDENCE,
                graph
            )
            return [conflict]
        
        return []
    
    # ── 辅助方法 ────────────────────────────────────────────────
    
    def _are_contradictory(self, graph: CognitiveGraph, belief_a_id: str, belief_b_id: str) -> bool:
        """检查两个信念是否矛盾"""
        # 检查直接矛盾关系
        for rel in graph.relations.values():
            if rel.type == RelationType.CONTRADICTS:
                if ((rel.source_id == belief_a_id and rel.target_id == belief_b_id) or
                    (rel.source_id == belief_b_id and rel.target_id == belief_a_id)):
                    return True
        
        # 检查语义矛盾（简单规则）
        belief_a = graph.get_belief(belief_a_id)
        belief_b = graph.get_belief(belief_b_id)
        
        if belief_a and belief_b:
            return self._semantically_contradictory(belief_a, belief_b)
        
        return False
    
    def _semantically_contradictory(self, belief_a: Belief, belief_b: Belief) -> bool:
        """
        检查语义矛盾（简单规则）
        后续可用向量相似度优化
        """
        prop_a = belief_a.proposition.lower().strip()
        prop_b = belief_b.proposition.lower().strip()
        
        # 简单规则：同一变量不同值
        import re
        
        # 匹配 x=3 和 x=5 的模式
        pattern = r'([a-zA-Z])\s*=\s*(\d+)'
        match_a = re.search(pattern, prop_a)
        match_b = re.search(pattern, prop_b)
        
        if match_a and match_b:
            var_a, val_a = match_a.groups()
            var_b, val_b = match_b.groups()
            if var_a == var_b and val_a != val_b:
                return True
        
        return False
    
    def _same_concept_different_conditions(self, belief_a: Belief, belief_b: Belief) -> bool:
        """检查是否是同一概念在不同条件下"""
        # 简单实现：检查命题是否相似但条件不同
        # 后续可用NLP优化
        return False
    
    def _student_confuses_conditions(self, graph: CognitiveGraph, belief_a: Belief, belief_b: Belief) -> bool:
        """检查学生是否混淆了条件"""
        # 简单实现
        return False
    
    def _premises_mutually_exclusive(self, pre_a: Belief, pre_b: Belief) -> bool:
        """检查前提是否互斥"""
        # 简单规则：检查是否矛盾
        return self._semantically_contradictory(pre_a, pre_b)
    
    def _get_dependent_beliefs(self, graph: CognitiveGraph, premise_id: str) -> List[Belief]:
        """获取依赖指定前提的信念"""
        dependent = []
        
        for rel in graph.relations.values():
            if rel.type == RelationType.PREREQUISITE and rel.target_id == premise_id:
                belief = graph.get_belief(rel.source_id)
                if belief:
                    dependent.append(belief)
        
        return dependent
    
    def _conflict_exists(self, graph: CognitiveGraph, belief_a_id: str, belief_b_id: str) -> bool:
        """检查冲突是否已存在"""
        for conflict in graph.conflicts.values():
            if ((conflict.belief_a_id == belief_a_id and conflict.belief_b_id == belief_b_id) or
                (conflict.belief_a_id == belief_b_id and conflict.belief_b_id == belief_a_id)):
                return True
        return False
    
    def _create_conflict(
        self,
        belief_a: Belief,
        belief_b: Belief,
        conflict_type: ConflictType,
        graph: CognitiveGraph
    ) -> Conflict:
        """创建冲突记录"""
        severity = self._calculate_severity(belief_a, belief_b, conflict_type)
        teaching_value = self._calculate_teaching_value(belief_a, belief_b, graph)
        
        conflict = Conflict(
            belief_a_id=belief_a.id,
            belief_b_id=belief_b.id,
            type=conflict_type,
            severity=severity,
            teaching_value=teaching_value,
            status=ConflictStatus.ACTIVE
        )
        
        # 添加到图谱
        graph.add_conflict(conflict)
        
        return conflict
    
    def _calculate_severity(
        self,
        belief_a: Belief,
        belief_b: Belief,
        conflict_type: ConflictType
    ) -> float:
        """
        计算冲突严重度
        
        Severity(C) = confidence(A) × confidence(B) × contradiction_clarity
        """
        clarity = self.CONFLICT_CLARITY.get(conflict_type, 0.5)
        return belief_a.confidence * belief_b.confidence * clarity
    
    def _calculate_teaching_value(
        self,
        belief_a: Belief,
        belief_b: Belief,
        graph: CognitiveGraph
    ) -> float:
        """
        计算教学价值
        
        TeachingValue(C) = impact_scope × knowledge_position × transferability
        """
        # 简化实现：基于信念的激活次数和稳定性
        impact_scope = min(1.0, (belief_a.activation_count + belief_b.activation_count) / 10)
        knowledge_position = (belief_a.stability + belief_b.stability) / 2
        transferability = 0.5  # 默认值
        
        return impact_scope * knowledge_position * transferability


class ConflictRanker:
    """
    冲突排序器
    根据优先级排序冲突
    """
    
    @staticmethod
    def rank_conflicts(
        conflicts: List[Conflict],
        student_readiness: float = 1.0,
        max_conflicts: int = 5
    ) -> List[Tuple[Conflict, float]]:
        """
        排序冲突
        
        Args:
            conflicts: 冲突列表
            student_readiness: 学生就绪度
            max_conflicts: 最大返回数量
            
        Returns:
            排序后的冲突列表（冲突，优先级分数）
        """
        if not conflicts:
            return []
        
        # 计算每个冲突类型的出现次数
        type_counts = {}
        for c in conflicts:
            type_counts[c.type] = type_counts.get(c.type, 0) + 1
        
        # 计算新颖度
        def calculate_novelty(conflict: Conflict) -> float:
            count = type_counts.get(conflict.type, 0)
            return max(0, 1 - (count / 3))
        
        # 计算优先级
        scored_conflicts = []
        for conflict in conflicts:
            novelty = calculate_novelty(conflict)
            priority = conflict.calculate_priority(student_readiness, novelty)
            scored_conflicts.append((conflict, priority))
        
        # 排序
        scored_conflicts.sort(key=lambda x: x[1], reverse=True)
        
        return scored_conflicts[:max_conflicts]
