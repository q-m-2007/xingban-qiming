"""
统一数据模型
所有层共享的数据结构
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime


# ═══════════════════════════════════════════
# 枚举类型
# ═══════════════════════════════════════════

class StudentState(Enum):
    EXPLORING = "exploring"          # 主动探索
    PARTIAL_STUCK = "partial_stuck"  # 局部卡壳
    DEEP_STUCK = "deep_stuck"        # 深度卡壳
    CONCEPT_ERROR = "concept_error"  # 概念错误
    FRUSTRATED = "frustrated"        # 情绪崩溃
    SILENT = "silent"                # 沉默


class ConflictType(Enum):
    LOGICAL = "logical"              # 逻辑冲突
    BOUNDARY = "boundary"            # 边界冲突
    CONFIDENCE = "confidence"        # 置信度冲突
    PATH_DEPENDENCY = "path_dep"     # 路径依赖


class MisconceptionState(Enum):
    ACTIVE = "ACTIVE"                # 活跃误解
    FADING = "FADING"                # 衰退中
    RESOLVED = "RESOLVED"            # 已解决
    RECURRING = "RECURRING"          # 复发


class InquiryType(Enum):
    GUIDED = "guided"                # 引导式追问
    HINT = "hint"                    # 提示式追问
    ANALOGY = "analogy"              # 类比式追问
    CONCEPT = "concept"              # 概念重建
    SILENCE = "silence"              # 保持沉默


# ═══════════════════════════════════════════
# 第0层：守门层输出
# ═══════════════════════════════════════════

@dataclass
class GateResult:
    """守门层判断结果"""
    should_respond: bool             # 是否应该回复
    silence_reason: str = ""         # 沉默原因
    input_valid: bool = True         # 输入是否有效
    boundary_ok: bool = True         # 是否在思考边界内
    sanitized_input: str = ""        # 清洗后的输入


# ═══════════════════════════════════════════
# 第1层：感知层输出
# ═══════════════════════════════════════════

@dataclass
class MatchResult:
    """知识匹配结果"""
    level: int = 0                   # 匹配级别 0=LLM 1=规则 2=哈希
    topic: str = ""                  # 匹配到的知识点
    question_type: str = ""          # 题型
    confidence: float = 0.0          # 匹配置信度
    time_ms: float = 0.0             # 耗时


@dataclass
class Belief:
    """学生信念"""
    content: str                     # 信念内容
    confidence: float                # 置信度 0-1
    source: str = ""                 # 来源
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerceptionResult:
    """感知层输出"""
    match: MatchResult
    beliefs: List[Belief] = field(default_factory=list)
    emotion: str = "neutral"         # 情绪状态
    emotion_intensity: float = 0.0   # 情绪强度


# ═══════════════════════════════════════════
# 第2层：验证层输出
# ═══════════════════════════════════════════

@dataclass
class Misconception:
    """误解实例"""
    id: str                          # 误解ID
    type: str                        # 误解类型
    content: str                     # 误解内容
    state: MisconceptionState = MisconceptionState.ACTIVE
    evidence_count: int = 0          # 证据次数
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationIssue:
    """验证层发现的问题"""
    type: str                        # 问题类型
    content: str                     # 问题内容
    severity: float = 0.5            # 严重程度 0-1


@dataclass
class ValidationResult:
    """验证层输出"""
    misconceptions: List[Misconception] = field(default_factory=list)
    issues: List[ValidationIssue] = field(default_factory=list)
    prerequisite_ok: bool = True     # 前置知识是否满足


# ═══════════════════════════════════════════
# 第3层：推理层输出
# ═══════════════════════════════════════════

@dataclass
class Conflict:
    """认知冲突"""
    id: str
    type: ConflictType
    description: str                 # 冲突描述
    severity: float = 0.5            # 严重程度
    teaching_value: float = 0.5      # 教学价值
    readiness: float = 0.5           # 学生准备度
    novelty: float = 0.5            # 新颖度
    priority: float = 0.0            # 优先级 = severity * teaching_value * readiness * novelty


@dataclass
class ReasoningResult:
    """推理层输出"""
    state: StudentState              # 学生状态
    conflicts: List[Conflict] = field(default_factory=list)
    top_conflict: Optional[Conflict] = None  # 最高优先级冲突


# ═══════════════════════════════════════════
# 第4层：个性化层输出
# ═══════════════════════════════════════════

@dataclass
class PacingDecision:
    """节奏决策"""
    should_wait: bool = False        # 是否应该等待
    wait_seconds: float = 0.0        # 等待时长
    reason: str = ""                 # 原因


@dataclass
class PersonalizationResult:
    """个性化层输出"""
    difficulty_level: float = 0.5    # 难度级别 0-1
    pacing: PacingDecision = field(default_factory=PacingDecision)
    inertia_detected: bool = False   # 是否检测到惯性
    inertia_method: str = ""         # 惯性方法


# ═══════════════════════════════════════════
# 第5层：决策层输出
# ═══════════════════════════════════════════

@dataclass
class DecisionResult:
    """决策层输出"""
    inquiry_type: InquiryType        # 追问类型
    response_text: str = ""          # 回复文本
    template_id: str = ""            # 使用的模板ID
    thinking_injected: bool = False  # 是否注入了"我也不会"
    reasoning: str = ""              # 决策理由
    confidence: float = 0.5          # 置信度


# ═══════════════════════════════════════════
# 第6层：执行层输出
# ═══════════════════════════════════════════

@dataclass
class ExecutionResult:
    """执行层输出"""
    final_response: str              # 最终回复
    explanation: str = ""            # 可解释性报告（E7）
    timestamp: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════
# 学生画像
# ═══════════════════════════════════════════

@dataclass
class CognitiveProfile:
    """学生认知画像"""
    student_id: str
    # 15维画像
    visual: float = 0.5
    verbal: float = 0.5
    kinesthetic: float = 0.5
    inductive: float = 0.5
    deductive: float = 0.5
    analogical: float = 0.5
    fast_jump: float = 0.5
    rigorous: float = 0.5
    divergent: float = 0.5
    abstract_reasoning: float = 0.5
    challenge_drive: float = 0.5
    persistence: float = 0.5
    metacognition: float = 0.5
    collaboration: float = 0.5
    creativity: float = 0.5
    # 元数据
    confidence: float = 0.3
    data_points: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


# ═══════════════════════════════════════════
# 管道上下文（贯穿所有层）
# ═══════════════════════════════════════════

@dataclass
class PipelineContext:
    """管道上下文，贯穿所有层"""
    # 输入
    student_id: str = ""
    student_input: str = ""
    conversation_history: List[str] = field(default_factory=list)
    topic: str = ""
    # 各层输出
    gate: Optional[GateResult] = None
    perception: Optional[PerceptionResult] = None
    validation: Optional[ValidationResult] = None
    reasoning: Optional[ReasoningResult] = None
    personalization: Optional[PersonalizationResult] = None
    decision: Optional[DecisionResult] = None
    execution: Optional[ExecutionResult] = None
    # 学生画像
    profile: Optional[CognitiveProfile] = None
    # 元数据
    start_time: datetime = field(default_factory=datetime.now)
    layer_times: Dict[str, float] = field(default_factory=dict)
