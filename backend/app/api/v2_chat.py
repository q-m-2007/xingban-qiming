"""
星伴·启明 V2.0 集成API
CPTE + CPPA 双算法集成

核心流程：
1. 接收学生消息
2. CPPA提取证据、更新画像
3. CPPA判断学生状态、选择教学策略
4. CPTE判断是否需要相变、调节教学力度
5. 生成个性化教学响应
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
import json
import uuid
import time
import tempfile
import edge_tts
import os

from ..cppa.teaching_engine import TeachingEngine
from ..cppa.cognitive_profile import CognitiveProfile, ForgettingAwareProfile, ColdStartInitializer
from ..cppa.method_bank import MethodBank
from ..cppa.learning_path import LearningPathPlanner
from ..cppa.metacognitive import MetacognitiveReflector
from ..llm.client import LLMClient, LLMError
from ..llm.response_generator import ResponseGenerator
from ..storage.v2_store import V2Store
import httpx


# ── 请求/响应模型 ────────────────────────────────────────────


class V2ChatRequest(BaseModel):
    """V2对话请求"""
    session_id: Optional[str] = Field(None, description="会话ID，首次为空则自动创建")
    student_id: str = Field(..., description="学生ID")
    message: str = Field(..., description="学生消息")
    problem_context: Optional[str] = Field(None, description="当前题目上下文")
    topic: str = Field("quadratic_equation", description="当前知识点")

class TTSRequest(BaseModel):
    """TTS请求"""
    text: str = Field(..., description="要转换的文本")


class V2ChatResponse(BaseModel):
    """V2对话响应"""
    session_id: str
    teaching_strategy: str = Field(..., description="使用的教学策略")
    response: str = Field(..., description="AI回复内容")
    student_state: str = Field(..., description="学生状态")
    energy_level: float = Field(..., description="教学能量等级 0-1")
    phase: str = Field(..., description="当前认知阶段")
    profile_snapshot: Dict[str, Any] = Field(..., description="学生画像快照")
    recommended_method: Optional[str] = Field(None, description="推荐的解法")
    metacognitive_feedback: Optional[str] = Field(None, description="元认知反馈")
    engagement: str = Field(..., description="学生投入度")
    difficulty_adjustment: str = Field(..., description="难度调节建议")
    next_step_suggestion: Optional[str] = Field(None, description="下一步建议")


class V2DiagnosisResponse(BaseModel):
    """学生诊断报告"""
    student_id: str
    cognitive_profile: Dict[str, float]
    method_mastery: Dict[str, Any]
    engagement_history: List[Dict[str, Any]]
    inertia: Optional[Dict[str, Any]]
    learning_path: Optional[Dict[str, Any]]
    recommendations: List[str]


class V2MethodRequest(BaseModel):
    """解法推荐请求"""
    student_id: str
    topic: str = Field("quadratic_equation")
    mode: str = Field("comfort", description="comfort/expand/challenge")


class V2MethodResponse(BaseModel):
    """解法推荐响应"""
    recommended_method: str
    score: float
    reason: str
    alternatives: List[Dict[str, Any]]


class LoginRequest(BaseModel):
    """微信登录请求"""
    code: str = Field(..., description="微信登录code")

class LoginResponse(BaseModel):
    """微信登录响应"""
    openid: str
    nickname: str = ""

class STTResponse(BaseModel):
    """语音转文字响应"""
    text: str


# ── 会话管理 ────────────────────────────────────────────────


class V2Session:
    """V2会话：集成CPTE+CPPA+LLM"""

    def __init__(self, session_id: str, student_id: str, topic: str):
        self.session_id = session_id
        self.student_id = student_id
        self.topic = topic
        self.created_at = time.time()
        self.message_count = 0
        self.conversation_history: List[str] = []

        # CPPA引擎（内部管理画像和历史）
        self.engine = TeachingEngine(use_llm=False)

        # LLM组件
        self.llm_client = LLMClient()
        self.response_generator = ResponseGenerator(self.llm_client)

        # 当前状态
        self.current_phase = "exploration"  # exploration/transition/consolidation
        self.current_energy = 0.5
        self.current_problem = None
        self.learning_path = None


# 全局会话存储
_sessions: Dict[str, V2Session] = {}

# Whisper模型（懒加载）
_whisper_model = None


def get_or_create_session(session_id: Optional[str], student_id: str, topic: str) -> V2Session:
    """获取或创建会话"""
    if session_id and session_id in _sessions:
        return _sessions[session_id]

    store = get_store()

    # 尝试从数据库恢复会话
    if session_id:
        db_session = store.get_session(session_id)
        if db_session:
            session = V2Session(session_id, student_id, topic)
            session.current_phase = db_session.get('current_phase', 'exploration')
            session.current_energy = db_session.get('current_energy', 0.5)
            session.message_count = db_session.get('message_count', 0)
            # 恢复对话历史
            messages = store.get_messages(session_id, limit=20)
            session.conversation_history = [m['content'] for m in messages if m['role'] == 'user']
            _sessions[session_id] = session
            return session

    # 创建新会话
    new_id = session_id or "v2_" + uuid.uuid4().hex[:8]
    session = V2Session(new_id, student_id, topic)
    _sessions[new_id] = session

    # 保存到数据库
    try:
        store.create_session(new_id, student_id, topic)
    except Exception as e:
        print(f"[SESSION SAVE ERROR] {e}")

    return session


def get_whisper_model():
    """获取Whisper模型（懒加载）"""
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("base")
    return _whisper_model


# ── API路由 ──────────────────────────────────────────────────

router = APIRouter(prefix="/api/v2", tags=["v2-integrated"])

# 全局存储实例
_store = V2Store()

def get_store() -> V2Store:
    return _store


@router.post("/chat/message", response_model=V2ChatResponse)
async def v2_send_message(request: Request):
    """
    V2对话接口：CPTE+CPPA集成

    核心流程：
    1. CPPA分析学生响应，提取证据
    2. CPPA更新认知画像
    3. CPPA判断学生状态（5种状态）
    4. CPPA选择教学策略（6种策略）
    5. CPTE判断相变点，调节教学力度
    6. 生成个性化教学响应
    """
    try:
        # 解析请求体，处理编码问题
        raw_body = await request.body()
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except UnicodeDecodeError:
            body = json.loads(raw_body.decode('gbk'))

        # 打印请求数据用于调试
        print(f"[DEBUG] 收到请求: {json.dumps(body, ensure_ascii=False)}")

        # 从dict解析请求
        chat_req = V2ChatRequest(
            session_id=body.get('session_id'),
            student_id=body.get('student_id', 'anonymous'),
            message=body.get('message', ''),
            problem_context=body.get('problem_context'),
            topic=body.get('topic', 'quadratic_equation')
        )
        print(f"[DEBUG] 解析后: student_id={chat_req.student_id}, message={chat_req.message}, topic={chat_req.topic}")

        # 确保学生存在
        store = get_store()
        store.get_or_create_student(chat_req.student_id)

        session = get_or_create_session(
            chat_req.session_id, chat_req.student_id, chat_req.topic
        )

        # 保存用户消息到数据库
        store.save_message(session.session_id, 'user', chat_req.message)
        session.message_count += 1

        # ── Step 1: CPPA处理学生响应 ──
        session.conversation_history.append(chat_req.message)
        decision = session.engine.process_student_response(
            student_id=chat_req.student_id,
            student_response=chat_req.message,
            problem=chat_req.problem_context or "当前题目",
            topic=chat_req.topic,
            conversation_history=session.conversation_history,
            step_index=session.message_count
        )

        student_state = decision.state
        strategy = decision.strategy

        # ── Step 2: LLM生成个性化回复 ──
        # 获取学生画像信息
        profile = session.engine.get_or_create_profile(chat_req.student_id)
        base_profile = profile.base_profile
        profile_info = {
            "style_label": base_profile.get_style_label() if hasattr(base_profile, 'get_style_label') else "未知",
            "strengths": _get_top_strengths(base_profile),
        }

        try:
            response = await session.response_generator.generate(
                strategy=strategy,
                student_state=student_state,
                problem=chat_req.problem_context or "当前题目",
                student_message=chat_req.message,
                conversation_history=session.conversation_history,
                recommended_method=decision.recommended_method,
                reasoning=decision.reasoning,
                profile=profile_info,
            )
        except Exception as e:
            # LLM调用失败，降级到模板回复
            response = _generate_teaching_response(
                strategy=strategy,
                student_state=student_state,
                problem=chat_req.problem_context or "当前题目",
                student_message=chat_req.message,
                recommended_method=decision.recommended_method,
                hint_level=decision.hint_level,
                reasoning=decision.reasoning
            )

        # ── Step 2: CPTE分析认知阶段 ──
        cpte_state = {
            "energy": session.current_energy,
            "phase": session.current_phase,
            "student_state": student_state,
            "message_count": session.message_count
        }

        # 根据学生状态调节能量
        if student_state in ["deep_stuck", "concept_error", "frustrated"]:
            # 学生困难时，增加教学能量
            session.current_energy = min(1.0, session.current_energy + 0.2)
        elif student_state == "exploring":
            # 学生探索时，保持中等能量
            session.current_energy = max(0.3, session.current_energy - 0.1)

        # 判断是否需要相变
        if session.current_energy > 0.8 and session.current_phase == "exploration":
            session.current_phase = "transition"
        elif session.current_energy < 0.4 and session.current_phase == "transition":
            session.current_phase = "consolidation"

        # ── Step 3: 元认知反馈 ──
        metacognitive_msg = None
        if decision.metacognitive_feedback:
            metacognitive_msg = decision.metacognitive_feedback.message

        # ── Step 4: 难度调节 ──
        difficulty = decision.difficulty_level

        # ── Step 5: 推荐解法 ──
        recommended_method = decision.recommended_method

        # ── Step 6: 投入度 ──
        engagement = decision.engagement_signals.get("state", "neutral") if decision.engagement_signals else "neutral"

        # ── Step 7: 生成下一步建议 ──
        next_step = _generate_next_step(student_state, strategy, decision.recommended_method)

        return V2ChatResponse(
            session_id=session.session_id,
            teaching_strategy=strategy,
            response=response,
            student_state=student_state,
            energy_level=round(session.current_energy, 2),
            phase=session.current_phase,
            profile_snapshot={
                "student_state": student_state,
                "engagement": engagement,
                "message_count": session.message_count,
                "confidence": decision.confidence
            },
            recommended_method=recommended_method,
            metacognitive_feedback=metacognitive_msg,
            engagement=engagement,
            difficulty_adjustment=difficulty,
            next_step_suggestion=next_step
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chat/{session_id}/diagnosis", response_model=V2DiagnosisResponse)
async def v2_get_diagnosis(session_id: str):
    """
    获取学生诊断报告

    包含：认知画像、解法掌握度、惯性分析、学习路径
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    session = _sessions[session_id]

    # 获取学生画像
    profile = session.engine.get_or_create_profile(session.student_id)
    diagnosis_text = session.engine.get_student_diagnosis(session.student_id)

    # 提取画像数据
    base_profile = profile.base_profile
    cognitive_profile = {
        "visual": base_profile.visual,
        "verbal": base_profile.verbal,
        "kinesthetic": base_profile.kinesthetic,
        "inductive": base_profile.inductive,
        "deductive": base_profile.deductive,
        "analogical": base_profile.analogical,
        "forward": base_profile.forward,
        "backward": base_profile.backward,
        "trial": base_profile.trial,
        "fast_jump": base_profile.fast_jump,
        "rigorous": base_profile.rigorous,
        "divergent": base_profile.divergent,
        "abstract_reasoning": base_profile.abstract_reasoning,
        "challenge_drive": base_profile.challenge_drive,
        "attention_span": base_profile.attention_span
    }

    return V2DiagnosisResponse(
        student_id=session.student_id,
        cognitive_profile=cognitive_profile,
        method_mastery={},
        engagement_history=[],
        inertia=None,
        learning_path=session.learning_path.__dict__ if session.learning_path else None,
        recommendations=[diagnosis_text]
    )


@router.post("/method/recommend", response_model=V2MethodResponse)
async def v2_recommend_method(request: V2MethodRequest):
    """
    解法推荐

    根据学生画像推荐最适合的解题方法
    """
    # 查找学生会话
    session = None
    for s in _sessions.values():
        if s.student_id == chat_req.student_id:
            session = s
            break

    if not session:
        raise HTTPException(status_code=404, detail="学生会话不存在")

    # 获取学生画像
    profile = session.engine.get_or_create_profile(chat_req.student_id)

    # 推荐解法
    from ..cppa.method_recommender import MethodRecommender
    from ..cppa.method_bank import MethodBank
    bank = MethodBank()
    recommender = MethodRecommender(bank)
    result = recommender.recommend(
        profile=profile.base_profile,
        topic=chat_req.topic,
        mode=request.mode
    )

    return V2MethodResponse(
        recommended_method=result.get("method", "unknown"),
        score=result.get("score", 0),
        reason=result.get("reason", ""),
        alternatives=result.get("alternatives", [])
    )


@router.get("/chat/{session_id}/path")
async def v2_get_learning_path(session_id: str):
    """
    获取学习路径

    返回个性化的学习计划
    """
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="会话不存在")

    session = _sessions[session_id]

    if session.learning_path is None:
        # 生成学习路径
        profile = session.engine.get_or_create_profile(session.student_id)
        history = session.engine.get_or_create_history(session.student_id)
        session.learning_path = session.engine.path_planner.plan(
            profile=profile,
            history=history,
            topic=session.topic
        )

    return {
        "session_id": session_id,
        "path": session.learning_path.__dict__ if hasattr(session.learning_path, '__dict__') else session.learning_path
    }


@router.post("/method/generate")
async def v2_generate_methods(topic: str):
    """
    为指定知识点生成解法库

    使用LLM自动生成多种解法
    """
    from ..cppa.method_generator import MethodGenerator
    generator = MethodGenerator()
    result = generator.generate_for_topic(topic)

    return {
        "topic": topic,
        "methods": result.get("methods", []),
        "analogy_problems": result.get("analogy_problems", []),
        "variant_problems": result.get("variant_problems", [])
    }


@router.post("/stt", response_model=STTResponse)
async def speech_to_text(audio: UploadFile = File(...)):
    """
    语音转文字接口

    接收音频文件，使用Whisper模型进行语音识别
    支持微信小程序录音格式（mp3/wav/m4a/aac等）
    """
    try:
        # 读取音频内容
        audio_content = await audio.read()

        if not audio_content or len(audio_content) < 100:
            raise HTTPException(status_code=400, detail="音频文件为空或太短")

        # 确定文件后缀
        if audio.filename:
            suffix = os.path.splitext(audio.filename)[1]
        elif audio.content_type:
            # 从content_type推断
            type_map = {
                'audio/mpeg': '.mp3',
                'audio/mp3': '.mp3',
                'audio/wav': '.wav',
                'audio/x-wav': '.wav',
                'audio/mp4': '.m4a',
                'audio/m4a': '.m4a',
                'audio/aac': '.aac',
                'audio/ogg': '.ogg',
            }
            suffix = type_map.get(audio.content_type, '.mp3')
        else:
            suffix = '.mp3'  # 微信录音默认mp3

        # 保存临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(audio_content)
            temp_file_path = temp_file.name

        try:
            # 加载Whisper模型并进行识别
            model = get_whisper_model()
            result = model.transcribe(temp_file_path, language="zh")
            text = result["text"].strip()

            if not text:
                return STTResponse(text="")

            return STTResponse(text=text)

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


@router.post("/login", response_model=LoginResponse)
async def wechat_login(request: LoginRequest):
    """
    微信登录

    用code换取openid，返回用户唯一标识
    """
    # 微信小程序appid和secret
    appid = "wx8765432109876543"  # TODO: 替换为真实appid
    secret = "your_secret_here"  # TODO: 替换为真实secret

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.weixin.qq.com/sns/jscode2session",
                params={
                    "appid": appid,
                    "secret": secret,
                    "js_code": request.code,
                    "grant_type": "authorization_code"
                },
                timeout=10
            )
            data = resp.json()

        if "openid" not in data:
            # 开发模式：用code生成模拟openid
            import hashlib
            openid = "dev_" + hashlib.md5(request.code.encode()).hexdigest()[:16]
        else:
            openid = data["openid"]

        # 创建或获取学生
        store = get_store()
        student = store.get_or_create_student(openid)

        return LoginResponse(openid=openid, nickname=student.get("nickname", ""))

    except Exception as e:
        print(f"[LOGIN ERROR] {e}")
        # 降级：用code生成模拟openid
        import hashlib
        openid = "dev_" + hashlib.md5(request.code.encode()).hexdigest()[:16]
        store = get_store()
        store.get_or_create_student(openid)
        return LoginResponse(openid=openid)


@router.get("/health")
async def v2_health():
    """V2健康检查"""
    return {
        "status": "ok",
        "service": "星伴·启明 V2.0",
        "algorithm": "CPTE + CPPA 双算法集成",
        "version": "2.0.0",
        "active_sessions": len(_sessions),
        "features": [
            "认知画像构建",
            "教学策略选择",
            "解法推荐",
            "惯性检测",
            "学习路径规划",
            "元认知反思",
            "投入度检测",
            "语音转文字"
        ]
    }


# ── 辅助函数 ────────────────────────────────────────────────


def _get_top_strengths(profile: CognitiveProfile, n: int = 3) -> List[str]:
    """获取学生最擅长的认知维度"""
    dims = {
        "visual": profile.visual,
        "verbal": profile.verbal,
        "kinesthetic": profile.kinesthetic,
        "inductive": profile.inductive,
        "deductive": profile.deductive,
        "analogical": profile.analogical,
        "forward": profile.forward,
        "backward": profile.backward,
        "trial": profile.trial,
        "fast_jump": profile.fast_jump,
        "rigorous": profile.rigorous,
        "divergent": profile.divergent,
        "abstract_reasoning": profile.abstract_reasoning,
        "challenge_drive": profile.challenge_drive,
        "attention_span": profile.attention_span
    }
    sorted_dims = sorted(dims.items(), key=lambda x: x[1], reverse=True)
    return [d[0] for d in sorted_dims[:n]]


def _generate_recommendations(session: V2Session) -> List[str]:
    """生成教学建议"""
    recommendations = []

    # 获取学生画像
    profile = session.engine.get_or_create_profile(session.student_id)
    base_profile = profile.base_profile

    # 基于认知画像的建议
    if base_profile.visual > 0.7:
        recommendations.append("该学生视觉能力强，建议多使用图形化讲解")
    if base_profile.verbal > 0.7:
        recommendations.append("该学生语言能力强，建议多用文字描述和定义")
    if base_profile.kinesthetic > 0.7:
        recommendations.append("该学生动手能力强，建议让学生多尝试、多演算")
    if base_profile.challenge_drive > 0.7:
        recommendations.append("该学生挑战欲强，建议适当增加难度")
    if base_profile.attention_span < 0.3:
        recommendations.append("该学生注意力持续时间短，建议分段讲解")

    return recommendations


def _generate_teaching_response(
    strategy: str,
    student_state: str,
    problem: str,
    student_message: str,
    recommended_method: Optional[str],
    hint_level: int,
    reasoning: str
) -> str:
    """根据教学策略生成回复内容"""

    # 策略A：引导式提问
    if "guided" in strategy.lower() or "A" in strategy:
        if "不知道" in student_message or "不会" in student_message:
            return f"好的，让我们一起来分析这道题。\n\n首先，你看看这个方程 {problem}，你觉得可以用什么方法来解？是因式分解、配方法，还是求根公式？\n\n先告诉我你的第一想法。"
        return f"很好，你在思考了。{reasoning}\n\n继续说说你的思路，你觉得下一步应该怎么做？"

    # 策略B：提示+提问
    elif "hint" in strategy.lower() or "B" in strategy:
        hints = {
            1: f"我给你一个提示：对于 {problem}，先看看能不能把它写成两个因式相乘的形式。",
            2: f"再给你一个提示：想想什么数相乘等于常数项，相加等于一次项系数？",
            3: f"最后一个提示：试试 x=2 或 x=3，看看方程是否成立。"
        }
        hint = hints.get(hint_level, hints[1])
        return f"{hint}\n\n得到这个提示后，你现在有什么想法？"

    # 策略C：类比教学
    elif "analogy" in strategy.lower() or "C" in strategy:
        return f"让我用一个更简单的例子来帮你理解。\n\n想象你有一个矩形，面积是6平方米，长和宽的和是5米。你觉得长和宽分别是多少？\n\n这个问题和你现在的方程 {problem} 其实是一样的道理。你能发现它们之间的联系吗？"

    # 策略D：概念重建
    elif "concept" in strategy.lower() or "rebuild" in strategy.lower() or "D" in strategy:
        return f"我发现你可能对某个概念有些误解，让我们重新梳理一下。\n\n对于二次方程 ax²+bx+c=0，因式分解的核心思想是：找到两个数，它们的乘积等于 ac，和等于 b。\n\n对于 {problem}，你能找到这样的两个数吗？"

    # 策略E：安抚降级
    elif "comfort" in strategy.lower() or "E" in strategy:
        return f"没关系，学习就是一个过程，每个人都会遇到困难。\n\n让我们换一个更简单的问题开始：\n\n你能解这个方程吗：x² - 5x + 6 = 0？\n\n提示：试试 x=2，看看会发生什么。"

    # 策略F：突破惯性
    elif "break" in strategy.lower() or "inertia" in strategy.lower() or "F" in strategy:
        if recommended_method:
            return f"我注意到你一直用同一种方法解题。让我们试试不同的思路。\n\n这次试试用【{recommended_method}】方法来解 {problem}。\n\n虽然一开始可能不习惯，但多一种方法就多一条路。"
        return f"你已经很熟练了，但我想让你试试另一种方法。\n\n对于 {problem}，除了你常用的方法，还能怎么解？试试换个角度思考。"

    # 默认回复
    return f"让我们继续思考这道题：{problem}\n\n你能告诉我你现在想到哪里了吗？"



# === 文字转语音接口 ===

@router.post("/tts")
async def text_to_speech(request: Request):
    """
    文字转语音接口

    接收文本，返回音频文件（mp3格式）
    使用edge-tts，支持中文语音
    """
    try:
        raw_body = await request.body()
        try:
            body = json.loads(raw_body.decode('utf-8'))
        except UnicodeDecodeError:
            body = json.loads(raw_body.decode('gbk'))
    except Exception as e:
        print(f"[TTS ERROR] 解析请求失败: {e}")
        body = {}

    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="请提供text字段")

    # 限制文本长度
    if len(text) > 500:
        text = text[:500]

    try:
        # 使用edge-tts生成语音
        # zh-CN-YunxiNeural - 女声，温柔亲切，适合教学
        communicate = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+5%")
        audio_data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        if not audio_data:
            raise HTTPException(status_code=500, detail="语音生成失败")

        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=speech.mp3"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="语音生成失败")

@router.get("/student/{student_id}/stats")
async def get_student_stats(student_id: str):
    """获取学生学习统计"""
    store = get_store()
    stats = store.get_student_stats(student_id)
    sessions = store.list_sessions(student_id, limit=10)
    return {
        "student_id": student_id,
        "stats": stats,
        "recent_sessions": sessions,
    }

@router.get("/student/{student_id}/history")
async def get_student_history(student_id: str, session_id: str = None):
    """获取学生对话历史"""
    store = get_store()
    if session_id:
        messages = store.get_messages(session_id)
        return {"session_id": session_id, "messages": messages}
    else:
        sessions = store.list_sessions(student_id, limit=5)
        result = []
        for s in sessions:
            msgs = store.get_messages(s['session_id'], limit=10)
            result.append({"session": s, "messages": msgs})
        return {"sessions": result}


def _generate_next_step(student_state: str, strategy: str, recommended_method: Optional[str]) -> str:
    """生成下一步建议"""
    if "frustrated" in student_state.lower():
        return "降低难度，从更简单的题目开始，帮助学生重建信心"
    elif "deep_stuck" in student_state.lower():
        return "先回顾基础概念，用类比或图示帮助学生理解"
    elif "concept_error" in student_state.lower():
        return "指出错误概念，引导学生重新理解正确的方法"
    elif "partial_stuck" in student_state.lower():
        return "给一个提示，帮助学生突破当前的卡点"
    elif "exploring" in student_state.lower():
        if recommended_method:
            return f"继续引导学生尝试【{recommended_method}】方法"
        return "继续引导学生探索不同的解题思路"
    return "保持当前节奏，观察学生的反应"
