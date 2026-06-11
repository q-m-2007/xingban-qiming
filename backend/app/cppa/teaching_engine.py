"""
CPPA 教学策略调度引擎（集成全部7项优化）
整合画像、解法推荐、惯性检测、难度调节、学习路径、元认知、投入度
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .cognitive_profile import (
    CognitiveProfile, ForgettingAwareProfile, ProfileUpdater,
    ColdStartInitializer, MethodHistory, MethodAttempt, ALL_DIMENSIONS
)
from .evidence_extractor import EvidenceExtractor, EngagementDetector, ProcessTracker
from .method_bank import MethodBank, Method, AnalogyProblem
from .method_recommender import MethodRecommender
from .inertia_detector import InertiaDetector, InertiaReport
from .difficulty_adjuster import DifficultyAdjuster, DifficultyDecision
from .learning_path import LearningPathPlanner, LearningPath, PathStep
from .metacognitive import MetacognitiveReflector, MetacognitiveFeedback
from .method_generator import MethodGenerator


class StudentState:
    EXPLORING = 'S1_exploring'
    PARTIAL_STUCK = 'S2_partial'
    DEEP_STUCK = 'S3_deep_stuck'
    CONCEPT_ERROR = 'S4_concept'
    FRUSTRATED = 'S5_frustrated'


class TeachingStrategy:
    GUIDED_QUESTIONING = 'A_guided'
    HINT_THEN_QUESTION = 'B_hint'
    ANALOGY_TEACHING = 'C_analogy'
    CONCEPT_REBUILD = 'D_concept'
    COMFORT_DOWNGRADE = 'E_comfort'
    BREAK_INERTIA = 'F_inertia'


CONCEPT_ERRORS = {
    'divide_by_variable': {
        'pattern': ['两边除以x得', '两边同除以x', '除以x得到', '约掉x得'],
        'principle': '不能除以可能等于0的量',
        'anchor': '除法有陷阱',
        'rebuild_question': '如果x=0，方程左边是多少？右边呢？x=0是解吗？',
    },
    'sign_error_move': {
        'pattern': ['移项不变号', '移过去不变', '直接移过去'],
        'principle': '移项的本质是等式两边同时加减',
        'anchor': '移项要变号',
        'rebuild_question': '移项的时候，符号变了吗？',
    },
    'discriminant_sign': {
        'pattern': ['判别式是b²-4ac', 'b取正值'],
        'principle': 'b要带符号代入',
        'anchor': 'b自带正负',
        'rebuild_question': '方程中b是正还是负？代入时要带符号吗？',
    },
    'formula_denominator': {
        'pattern': ['分母是a', '除以a就行'],
        'principle': '分母是2a不是a',
        'anchor': '2a是底线',
        'rebuild_question': '求根公式的分母是a还是2a？',
    },
    'factor_without_zero': {
        'pattern': ['直接令括号等于0', '分解后直接等于0'],
        'principle': '必须先化为标准形式（右边=0）',
        'anchor': '先归零再拆',
        'rebuild_question': '方程右边是0吗？如果不是，要先做什么？',
    },
}


@dataclass
class TeachingDecision:
    """完整的教学决策"""
    strategy: str
    state: str
    recommended_method: Optional[str] = None
    method_mode: str = 'comfort'
    difficulty_level: str = 'standard'
    pace: str = 'moderate'
    hint_level: int = 1
    hint_content: str = ''
    analogy_problem: Optional[AnalogyProblem] = None
    question_to_ask: str = ''
    teaching_style: Dict = field(default_factory=dict)
    inertia_report: Optional[InertiaReport] = None
    # 优化新增
    metacognitive_feedback: Optional[MetacognitiveFeedback] = None
    engagement_signals: Dict = field(default_factory=dict)
    learning_path_step: Optional[PathStep] = None
    needs_review: List[str] = field(default_factory=list)
    reasoning: str = ''
    confidence: float = 0.5


class TeachingEngine:
    """教学策略调度引擎（集成全部优化）"""

    def __init__(self, use_llm: bool = False, llm_client=None):
        # 核心模块
        self.method_bank = MethodBank()
        self.profile_updater = ProfileUpdater()
        self.cold_start = ColdStartInitializer()
        self.evidence_extractor = EvidenceExtractor(use_llm=use_llm, llm_client=llm_client)
        self.engagement_detector = EngagementDetector()
        self.method_recommender = MethodRecommender(self.method_bank)
        self.inertia_detector = InertiaDetector()
        self.difficulty_adjuster = DifficultyAdjuster()
        self.process_tracker = ProcessTracker()
        # 优化新增模块
        self.path_planner = LearningPathPlanner(self.method_bank)
        self.metacognitive = MetacognitiveReflector(self.method_bank)
        self.method_generator = MethodGenerator(llm_client)
        # 存储
        self.profiles: Dict[str, ForgettingAwareProfile] = {}
        self.histories: Dict[str, MethodHistory] = {}
        self.learning_paths: Dict[str, LearningPath] = {}

    # ──────────────────────────────────────
    # 公共接口
    # ──────────────────────────────────────

    def get_or_create_profile(self, student_id: str) -> ForgettingAwareProfile:
        if student_id not in self.profiles:
            base = self.cold_start.initialize(student_id)
            self.profiles[student_id] = ForgettingAwareProfile(base_profile=base)
        return self.profiles[student_id]

    def get_or_create_history(self, student_id: str) -> MethodHistory:
        if student_id not in self.histories:
            self.histories[student_id] = MethodHistory()
        return self.histories[student_id]

    def generate_method_bank(self, topic: str, grade: str = '九年级'):
        """优化4：用LLM为新知识点生成解法库"""
        data = self.method_generator.generate_for_topic(topic, grade)
        if data.get('methods'):
            self.method_generator.load_into_bank(topic, data, self.method_bank)

    def plan_learning_path(self, student_id: str, topic: str,
                           num_problems: int = 8) -> LearningPath:
        """优化5：规划学习路径"""
        profile = self.get_or_create_profile(student_id)
        history = self.get_or_create_history(student_id)
        path = self.path_planner.plan(profile, history, topic, num_problems)
        self.learning_paths[student_id] = path
        return path

    def process_student_response(
        self,
        student_id: str,
        student_response: str,
        problem: str,
        topic: str,
        conversation_history: List[str],
        step_index: int = 0,
        time_spent: float = 60.0,
        is_correct: Optional[bool] = None,
    ) -> TeachingDecision:
        """处理学生回答，生成教学决策（核心入口）"""

        # ── Step 1: 获取画像和历史 ──
        fprofile = self.get_or_create_profile(student_id)
        profile = fprofile.base_profile
        history = self.get_or_create_history(student_id)

        # ── Step 2: 优化1 - 提取证据，更新画像 ──
        evidence = self.evidence_extractor.extract(
            student_response, problem, conversation_history
        )
        profile = self.profile_updater.update(profile, evidence)

        # ── Step 3: 优化7 - 检测投入度 ──
        engagement = self.engagement_detector.detect(
            student_response, time_spent, is_correct or False
        )
        fprofile.add_engagement(engagement)

        # ── Step 4: 追踪解题过程 ──
        self.process_tracker.add_step(student_response, step_index)

        # ── Step 5: 判断学生状态 ──
        state = self._classify_state(student_response, conversation_history)

        # ── Step 6: 检测惯性 ──
        inertia = self.inertia_detector.detect(student_id, history)

        # ── Step 7: 难度调节 ──
        difficulty = self.difficulty_adjuster.adjust(profile, history.attempts, topic)

        # ── Step 8: 选择教学策略 ──
        decision = self._select_strategy(
            state=state, fprofile=fprofile, profile=profile,
            history=history, inertia=inertia, difficulty=difficulty,
            topic=topic, student_response=student_response,
            conversation_history=conversation_history,
            time_spent=time_spent, is_correct=is_correct,
            engagement=engagement,
        )

        return decision

    def record_outcome(self, student_id: str, problem_id: str,
                       topic: str, method_used: str,
                       success: bool, time_spent: float,
                       steps_count: int, verification_level: int,
                       error_type: Optional[str] = None):
        """记录教学结果（含遗忘强化）"""
        history = self.get_or_create_history(student_id)
        attempt = MethodAttempt(
            student_id=student_id, problem_id=problem_id,
            problem_type=topic, method_used=method_used,
            success=success, time_spent=time_spent,
            steps_count=steps_count, verification_level=verification_level,
            error_type=error_type,
        )
        history.add_attempt(attempt)

        # 优化3：更新方法掌握度（含遗忘）
        fprofile = self.get_or_create_profile(student_id)
        fprofile.practice_method(method_used, success)

        # 优化5：动态调整学习路径
        if student_id in self.learning_paths:
            path = self.learning_paths[student_id]
            self.path_planner.adapt_path(path, fprofile, history, attempt)

    # ──────────────────────────────────────
    # 状态分类
    # ──────────────────────────────────────

    def _classify_state(self, response: str, history: List[str]) -> str:
        frustrated_signals = [
            '太难了', '不想做', '算了', '放弃', '学不会', '搞不懂',
            '崩溃', '烦死了', '不想学', '受不了',
        ]
        if any(s in response for s in frustrated_signals):
            return StudentState.FRUSTRATED

        for error_id, error_info in CONCEPT_ERRORS.items():
            if any(p in response for p in error_info['pattern']):
                if self._is_actually_making_error(response):
                    return StudentState.CONCEPT_ERROR

        stuck_signals = [
            '不知道', '不会', '没思路', '想不出来',
            '完全不会', '不知道从哪', '看不懂', '一头雾水',
        ]
        if any(s in response for s in stuck_signals):
            return StudentState.DEEP_STUCK

        partial_signals = [
            '这一步', '这里', '不会算', '怎么算',
            '公式是什么', '忘了', '记不清',
        ]
        if any(s in response for s in partial_signals):
            return StudentState.PARTIAL_STUCK

        return StudentState.EXPLORING

    def _is_actually_making_error(self, response: str) -> bool:
        question_signals = ['怎么', '如何', '什么', '？', '?', '吗', '呢']
        if any(q in response for q in question_signals):
            return False
        negation_signals = ['不能', '不应该', '不对', '是错的', '错误']
        if any(n in response for n in negation_signals):
            return False
        return True

    # ──────────────────────────────────────
    # 策略选择
    # ──────────────────────────────────────

    def _select_strategy(self, state, fprofile, profile, history,
                         inertia, difficulty, topic, student_response,
                         conversation_history, time_spent, is_correct,
                         engagement) -> TeachingDecision:

        # 优先级1：情绪崩溃
        if state == StudentState.FRUSTRATED:
            return self._strategy_comfort(fprofile, topic)

        # 优先级2：概念错误
        if state == StudentState.CONCEPT_ERROR:
            return self._strategy_concept_rebuild(student_response, fprofile, topic)

        # 优先级3：深度卡壳
        if state == StudentState.DEEP_STUCK:
            return self._strategy_analogy(fprofile, topic)

        # 优先级4：局部卡壳
        if state == StudentState.PARTIAL_STUCK:
            return self._strategy_hint(fprofile, topic, conversation_history)

        # 优先级5：惯性突破
        if inertia and inertia.strength > 0.5:
            return self._strategy_break_inertia(fprofile, topic, inertia)

        # 默认：追问引导
        decision = self._strategy_guided(fprofile, topic)

        # 优化6：附加元认知反馈
        if is_correct is not None:
            all_methods = [m.id for m in self.method_bank.get_methods(topic)]
            mc = self.metacognitive.reflect(
                problem=student_response, topic=topic,
                method_used=decision.recommended_method or 'unknown',
                method_recommended=decision.recommended_method or 'unknown',
                success=is_correct, time_spent=time_spent,
                profile=fprofile, alternative_methods=all_methods,
            )
            decision.metacognitive_feedback = mc

        # 优化7：附加投入度信号
        decision.engagement_signals = engagement

        # 优化3：附加需要复习的方法
        decision.needs_review = fprofile.get_methods_needing_review()

        return decision

    # ──────────────────────────────────────
    # 各策略实现
    # ──────────────────────────────────────

    def _strategy_guided(self, fprofile, topic) -> TeachingDecision:
        method = self.method_recommender.recommend_best(
            topic, fprofile.base_profile, mode='comfort'
        )
        return TeachingDecision(
            strategy=TeachingStrategy.GUIDED_QUESTIONING,
            state=StudentState.EXPLORING,
            recommended_method=method.id if method else None,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning='学生在主动探索，继续引导',
            confidence=0.7,
        )

    def _strategy_hint(self, fprofile, topic, history) -> TeachingDecision:
        hint_level = self.difficulty_adjuster.get_hint_level(len(history), 0.5)
        method = self.method_recommender.recommend_best(
            topic, fprofile.base_profile, mode='comfort'
        )
        return TeachingDecision(
            strategy=TeachingStrategy.HINT_THEN_QUESTION,
            state=StudentState.PARTIAL_STUCK,
            recommended_method=method.id if method else None,
            hint_level=hint_level,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning=f'局部卡壳，给L{hint_level}提示',
            confidence=0.6,
        )

    def _strategy_analogy(self, fprofile, topic) -> TeachingDecision:
        method = self.method_recommender.recommend_best(
            topic, fprofile.base_profile, mode='comfort'
        )
        analogy = None
        if method:
            analogies = self.method_bank.get_analogy_problems(method.id)
            if analogies:
                analogy = min(analogies, key=lambda a: a.level)
        return TeachingDecision(
            strategy=TeachingStrategy.ANALOGY_TEACHING,
            state=StudentState.DEEP_STUCK,
            recommended_method=method.id if method else None,
            analogy_problem=analogy,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning='深度卡壳，用类比题建立思路',
            confidence=0.7,
        )

    def _strategy_concept_rebuild(self, response, fprofile, topic) -> TeachingDecision:
        detected = None
        for error_id, info in CONCEPT_ERRORS.items():
            if any(p in response for p in info['pattern']):
                detected = info
                break
        question = detected['rebuild_question'] if detected else ''
        return TeachingDecision(
            strategy=TeachingStrategy.CONCEPT_REBUILD,
            state=StudentState.CONCEPT_ERROR,
            question_to_ask=question,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning=f'概念错误：{detected["principle"] if detected else "未知"}',
            confidence=0.8,
        )

    def _strategy_comfort(self, fprofile, topic) -> TeachingDecision:
        return TeachingDecision(
            strategy=TeachingStrategy.COMFORT_DOWNGRADE,
            state=StudentState.FRUSTRATED,
            method_mode='comfort', pace='slow', hint_level=3,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning='情绪崩溃，先安抚再降级',
            confidence=0.8,
        )

    def _strategy_break_inertia(self, fprofile, topic, inertia) -> TeachingDecision:
        return TeachingDecision(
            strategy=TeachingStrategy.BREAK_INERTIA,
            state=StudentState.EXPLORING,
            recommended_method=inertia.suggested_alternative,
            method_mode='expand',
            inertia_report=inertia,
            teaching_style=self._determine_style(fprofile.base_profile),
            reasoning=f'惯性思维：{inertia.dominant_method}占比{inertia.dominant_ratio:.0%}',
            confidence=0.7,
        )

    # ──────────────────────────────────────
    # 教学风格
    # ──────────────────────────────────────

    def _determine_style(self, profile: CognitiveProfile) -> Dict:
        style = {}
        if profile.fast_jump > 0.6:
            style['pace'] = 'fast'
        elif profile.rigorous > 0.6:
            style['pace'] = 'slow'
        else:
            style['pace'] = 'moderate'
        if profile.verbal > 0.6:
            style['language'] = 'precise'
        elif profile.visual > 0.6:
            style['language'] = 'vivid'
        else:
            style['language'] = 'practical'
        if profile.challenge_drive > 0.6:
            style['challenge'] = 'high'
        else:
            style['challenge'] = 'moderate'
        return style

    # ──────────────────────────────────────
    # 诊断报告
    # ──────────────────────────────────────

    def get_student_diagnosis(self, student_id: str) -> str:
        fprofile = self.get_or_create_profile(student_id)
        profile = fprofile.base_profile
        history = self.get_or_create_history(student_id)

        lines = [f"═══ 学生诊断报告 ═══\n"]
        lines.append(f"【思维画像】{profile.get_style_label()}")
        lines.append(f"  置信度：{profile.confidence:.0%}  数据点：{profile.data_points}次\n")

        lines.append("  信息获取偏好：")
        for d in ['visual', 'verbal', 'kinesthetic']:
            val = getattr(profile, d)
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            labels = {'visual': '视觉型', 'verbal': '语言型', 'kinesthetic': '动手型'}
            lines.append(f"    {labels[d]:6s} {bar} {val:.0%}")

        lines.append("\n  推理方式：")
        for d in ['inductive', 'deductive', 'analogical']:
            val = getattr(profile, d)
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            labels = {'inductive': '归纳型', 'deductive': '演绎型', 'analogical': '类比型'}
            lines.append(f"    {labels[d]:6s} {bar} {val:.0%}")

        lines.append("\n  认知特征：")
        for d in ['fast_jump', 'rigorous', 'divergent', 'abstract_reasoning', 'challenge_drive']:
            val = getattr(profile, d)
            bar = '█' * int(val * 20) + '░' * (20 - int(val * 20))
            labels = {'fast_jump': '跳跃思维', 'rigorous': '严谨思维', 'divergent': '发散思维',
                     'abstract_reasoning': '抽象推理', 'challenge_drive': '挑战偏好'}
            lines.append(f"    {labels[d]:8s} {bar} {val:.0%}")

        # 优化3：方法掌握度
        if fprofile.method_masteries:
            lines.append("\n【方法掌握度】（含遗忘）")
            for mid, mm in fprofile.method_masteries.items():
                effective = mm.apply_forgetting()
                m = self.method_bank.get_method_by_id(mid)
                name = m.name if m else mid
                lines.append(f"  {name}: {effective:.0%} (练习{mm.practice_count}次)")

        # 惯性检测
        inertia = self.inertia_detector.detect(student_id, history)
        if inertia:
            lines.append(f"\n【惯性检测】⚠️ {inertia.dominant_method} 占比{inertia.dominant_ratio:.0%}")
            lines.append(f"  强度{inertia.strength:.0%}，建议切换：{inertia.suggested_alternative}")
        else:
            lines.append(f"\n【惯性检测】✅ 无显著惯性")

        # 优化7：投入度
        engagement = fprofile.get_avg_engagement()
        lines.append(f"\n【投入度】")
        lines.append(f"  无聊：{engagement.get('bored',0):.0%}  挑战享受：{engagement.get('challenged',0):.0%}")
        lines.append(f"  好奇：{engagement.get('curious',0):.0%}  挫败：{engagement.get('frustrated',0):.0%}")

        return '\n'.join(lines)
