"""
CPPA (Cognitive Profile & Personalization Algorithm) v2.0
认知画像与个性化教学算法 — 全部7项优化集成版

优化1：LLM深层证据提取
优化2：主动探测策略
优化3：遗忘感知画像
优化4：LLM自动生成解法库
优化5：学习路径规划
优化6：元认知反思
优化7：兴趣/投入度信号检测
"""

from .cognitive_profile import (
    CognitiveProfile, ProfileUpdater, ColdStartInitializer,
    MethodHistory, MethodAttempt, MethodMastery, ForgettingAwareProfile,
    ALL_DIMENSIONS, DIMENSION_GROUPS, DIMENSION_DESCRIPTIONS,
)
from .evidence_extractor import (
    EvidenceExtractor, EngagementDetector, ProcessTracker, EXTRACTION_PROMPT,
)
from .method_bank import (
    Method, AnalogyProblem, VariantProblem, MethodBank,
    QUADRATIC_METHODS, ANALOGY_PROBLEMS, VARIANT_PROBLEMS,
)
from .method_recommender import MethodRecommender
from .inertia_detector import InertiaDetector, InertiaReport, compute_inertia_barrier
from .difficulty_adjuster import DifficultyAdjuster, DifficultyDecision
from .learning_path import LearningPathPlanner, LearningPath, PathStep, LearningSession
from .metacognitive import MetacognitiveReflector, MetacognitiveFeedback
from .method_generator import MethodGenerator, BatchMethodGenerator
from .teaching_engine import (
    TeachingEngine, TeachingDecision, StudentState, TeachingStrategy, CONCEPT_ERRORS,
)
from .teaching_record import TeachingRecord, TeachingRecordStore
