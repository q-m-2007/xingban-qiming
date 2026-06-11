"""
CCG（Cognitive Conflict Graph）核心数据模型
认知冲突图谱算法 - 信念、关系、冲突
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


# ── 枚举类型 ────────────────────────────────────────────────


class BeliefType(str, Enum):
    """信念类型"""
    CONCEPT = "concept"              # 概念性信念（"移项是把一项从等号一边移到另一边"）
    PROCEDURE = "procedure"          # 程序性信念（"解方程的步骤是：去分母→去括号→移项→合并→系数化1"）
    HEURISTIC = "heuristic"          # 启发式信念（"看到'最大值'三个字，先想二次函数顶点"）
    PRESUPPOSITION = "presupposition" # 前提性信念（"一个方程只有一个解"）


class EmotionalTag(str, Enum):
    """情感标记"""
    NEUTRAL = "neutral"              # 中性
    ATTACHED = "attached"            # 学生对此信念有情感依附（如"我自己想出来的"）
    INSECURE = "insecure"            # 学生对此信念不自信


class RelationType(str, Enum):
    """信念关系类型"""
    IMPLIES = "implies"              # 源蕴含目标（"等式两边同加减"蕴含"移项需要变号"）
    CONTRADICTS = "contradicts"      # 源与目标矛盾
    PREREQUISITE = "prerequisite"    # 源是目标的前置条件
    GENERALIZES = "generalizes"      # 源是目标的泛化
    EXEMPLIFIES = "exemplifies"      # 源是目标的具体化
    ASSOCIATES = "associates"        # 源与目标经常同时被调用


class ConflictType(str, Enum):
    """冲突类型"""
    LOGICAL = "logical"              # 逻辑矛盾（A蕴含P，B蕴含¬P）
    BOUNDARY = "boundary"            # 边界矛盾（A在条件X下成立，B在条件Y下成立）
    CONFIDENCE = "confidence"        # 置信度矛盾（同时持有A和¬A，且两者置信度均>0.5）
    PATH_DEPENDENCY = "path_dependency" # 路径依赖矛盾（A和B各自正确，但推理路径冲突）


class ConflictStatus(str, Enum):
    """冲突状态"""
    ACTIVE = "active"                # 活跃中，未被学生觉察
    EXPOSED = "exposed"              # 已被追问暴露，学生正在处理
    RESOLVED = "resolved"            # 学生已自行修正
    RESOLVED_AI_ASSISTED = "resolved_ai" # 在AI引导下修正
    ABANDONED = "abandoned"          # 学生暂时放弃处理
    RECURRING = "recurring"          # 曾被解决但又复现


class QuestionType(str, Enum):
    """追问类型"""
    GUIDE_DISCOVERY = "guide_discovery"    # 引导发现型
    COUNTEREXAMPLE = "counterexample"      # 反例挑战型
    BOUNDARY_EXPLORE = "boundary_explore"  # 边界探索型
    PATH_COMPARE = "path_compare"          # 路径对比型
    DECOMPOSE = "decompose"                # 拆解引导型


# ── 核心数据模型 ────────────────────────────────────────────────


class Belief(BaseModel):
    """信念节点"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一标识")
    proposition: str = Field(..., description="信念的命题表述")
    type: BeliefType = Field(..., description="信念类型")
    confidence: float = Field(default=0.5, ge=0, le=1, description="置信度 [0, 1]")
    source: str = Field(default="inference", description="来源追溯")
    timestamp: datetime = Field(default_factory=datetime.now, description="首次建立时间")
    last_activated: datetime = Field(default_factory=datetime.now, description="最近激活时间")
    activation_count: int = Field(default=1, description="激活总次数")
    stability: float = Field(default=0.5, ge=0, le=1, description="稳定性 [0, 1]")
    emotional_tag: EmotionalTag = Field(default=EmotionalTag.NEUTRAL, description="情感标记")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="扩展元数据")

    def activate(self):
        """激活信念"""
        self.last_activated = datetime.now()
        self.activation_count += 1

    def update_confidence(self, new_confidence: float):
        """更新置信度"""
        self.confidence = max(0, min(1, new_confidence))
        self.last_activated = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "proposition": self.proposition,
            "type": self.type.value,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "last_activated": self.last_activated.isoformat(),
            "activation_count": self.activation_count,
            "stability": self.stability,
            "emotional_tag": self.emotional_tag.value,
            "metadata": self.metadata
        }


class BeliefRelation(BaseModel):
    """信念关系边"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="关系ID")
    source_id: str = Field(..., description="源信念ID")
    target_id: str = Field(..., description="目标信念ID")
    type: RelationType = Field(..., description="关系类型")
    strength: float = Field(default=0.5, ge=0, le=1, description="关系强度 [0, 1]")
    detected_by: str = Field(default="inference", description="检测方式")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type.value,
            "strength": self.strength,
            "detected_by": self.detected_by,
            "created_at": self.created_at.isoformat()
        }


class Conflict(BaseModel):
    """冲突记录"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="冲突ID")
    belief_a_id: str = Field(..., description="冲突方A")
    belief_b_id: str = Field(..., description="冲突方B")
    type: ConflictType = Field(..., description="冲突类型")
    severity: float = Field(default=0.5, ge=0, le=1, description="严重度 [0, 1]")
    teaching_value: float = Field(default=0.5, ge=0, le=1, description="教学价值 [0, 1]")
    status: ConflictStatus = Field(default=ConflictStatus.ACTIVE, description="状态")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    history: List[Dict[str, Any]] = Field(default_factory=list, description="处理历史")

    def update_status(self, new_status: ConflictStatus, action: str = "", result: str = ""):
        """更新冲突状态"""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "old_status": self.status.value,
            "new_status": new_status.value,
            "action": action,
            "result": result
        })
        self.status = new_status
        self.updated_at = datetime.now()

    def calculate_priority(self, student_readiness: float = 1.0, novelty: float = 1.0) -> float:
        """计算优先级"""
        return self.severity * self.teaching_value * student_readiness * novelty

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "belief_a_id": self.belief_a_id,
            "belief_b_id": self.belief_b_id,
            "type": self.type.value,
            "severity": self.severity,
            "teaching_value": self.teaching_value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "history": self.history
        }


# ── 请求/响应模型 ────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """对话请求"""
    session_id: Optional[str] = Field(None, description="会话ID（首次为空，自动生成）")
    student_input: str = Field(..., description="学生输入")
    context: Dict[str, Any] = Field(default_factory=lambda: {
        "grade": "high_school",
        "subject": "math"
    }, description="上下文信息")


class ChatResponse(BaseModel):
    """对话响应"""
    session_id: str = Field(..., description="会话ID")
    ai_response: str = Field(..., description="AI回复")
    question_type: Optional[QuestionType] = Field(None, description="追问类型")
    beliefs_extracted: List[Dict[str, Any]] = Field(default_factory=list, description="提取的信念")
    conflicts_detected: List[Dict[str, Any]] = Field(default_factory=list, description="检测到的冲突")
    thinking_time_allowed: int = Field(default=15, description="允许思考时间（秒）")
    state: str = Field(default="active", description="对话状态")


class GraphResponse(BaseModel):
    """认知图谱响应"""
    session_id: str = Field(..., description="会话ID")
    beliefs: List[Dict[str, Any]] = Field(default_factory=list, description="信念列表")
    relations: List[Dict[str, Any]] = Field(default_factory=list, description="关系列表")
    conflicts: List[Dict[str, Any]] = Field(default_factory=list, description="冲突列表")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计信息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    service: str = "星伴·启明 CCG追问引擎"
    version: str = "1.0.0"
    algorithm: str = "CCG (Cognitive Conflict Graph)"
    active_sessions: int = 0


class ErrorResponse(BaseModel):
    """错误响应"""
    detail: str
    error_code: Optional[str] = None
