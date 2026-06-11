"""
星伴·启明 — 追问状态机

状态流转:
  INITIAL → CHECK_CONDITIONS → CHECK_STRATEGY → CHECK_CALCULATION → EXPLAIN

每个状态返回动作:
  - continue: 继续追问
  - explain:   直接给出解析
  - decompose: 拆解为子问题
"""

from enum import Enum


class QuestionState(str, Enum):
    INITIAL = "initial"
    CHECK_CONDITIONS = "check_conditions"
    CHECK_STRATEGY = "check_strategy"
    CHECK_CALCULATION = "check_calculation"
    EXPLAIN = "explain"


class Action(str, Enum):
    CONTINUE = "continue"
    EXPLAIN = "explain"
    DECOMPOSE = "decompose"


class StateTransition:
    """单个状态转移记录"""

    def __init__(self, state: QuestionState, action: Action, payload: dict = None):
        self.state = state
        self.action = action
        self.payload = payload or {}


class QuestionStateMachine:
    """
    追问状态机 —— 管理每道题的追问流程。

    对于每个 'session_id' 维护独立的状态栈，
    支持分布式/无状态部署（状态可序列化至 Redis / DB）。
    """

    def __init__(self):
        # session_id -> { "state": QuestionState, "history": [...], "context": {...} }
        self._sessions: dict[str, dict] = {}

    # ── 会话管理层 ──────────────────────────────────────────

    def create_session(self, session_id: str, question_text: str) -> dict:
        """创建一个新的追问会话"""
        self._sessions[session_id] = {
            "state": QuestionState.INITIAL,
            "question": question_text,
            "history": [],
            "context": {"round": 0},
        }
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> dict | None:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str):
        self._sessions.pop(session_id, None)

    # ── 状态机核心 ──────────────────────────────────────────

    def next(self, session_id: str, student_answer: str = "") -> StateTransition:
        """
        根据当前状态 + 学生答案，计算下一步动作。

        返回 (new_state, action, payload)
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        current = session["state"]
        session["history"].append(student_answer)
        session["context"]["round"] += 1

        if current == QuestionState.INITIAL:
            return self._on_initial(session)
        elif current == QuestionState.CHECK_CONDITIONS:
            return self._on_check_conditions(session, student_answer)
        elif current == QuestionState.CHECK_STRATEGY:
            return self._on_check_strategy(session, student_answer)
        elif current == QuestionState.CHECK_CALCULATION:
            return self._on_check_calculation(session, student_answer)
        elif current == QuestionState.EXPLAIN:
            return self._on_explain(session)
        else:
            return StateTransition(QuestionState.EXPLAIN, Action.EXPLAIN)

    # ── 每个状态的 handler ──────────────────────────────────

    def _on_initial(self, session: dict) -> StateTransition:
        """初始状态 -> 检查审题条件"""
        session["state"] = QuestionState.CHECK_CONDITIONS
        return StateTransition(
            state=QuestionState.CHECK_CONDITIONS,
            action=Action.CONTINUE,
            payload={"question": session["question"], "hint": "请告诉我你的解题思路和初步答案"},
        )

    def _on_check_conditions(self, session: dict, answer: str) -> StateTransition:
        """检查审题是否准确"""
        session["state"] = QuestionState.CHECK_STRATEGY
        return StateTransition(
            state=QuestionState.CHECK_STRATEGY,
            action=Action.CONTINUE,
            payload={"feedback": "好的，你使用了什么公式或方法来解决这个问题？"},
        )

    def _on_check_strategy(self, session: dict, answer: str) -> StateTransition:
        """检查解题策略 / 公式运用"""
        session["state"] = QuestionState.CHECK_CALCULATION
        return StateTransition(
            state=QuestionState.CHECK_CALCULATION,
            action=Action.CONTINUE,
            payload={"feedback": "能展示一下你的计算过程吗？"},
        )

    def _on_check_calculation(self, session: dict, answer: str) -> StateTransition:
        """检查计算过程"""
        session["state"] = QuestionState.EXPLAIN
        return StateTransition(
            state=QuestionState.EXPLAIN,
            action=Action.EXPLAIN,
            payload={"feedback": "根据你的回答，我注意到以下几点……", "final": True},
        )

    def _on_explain(self, session: dict) -> StateTransition:
        """已结束"""
        return StateTransition(
            state=QuestionState.EXPLAIN,
            action=Action.EXPLAIN,
            payload={"feedback": "追问已结束。", "final": True},
        )

    def get_current_state(self, session_id: str) -> str | None:
        session = self._sessions.get(session_id)
        return session["state"].value if session else None

    def get_history(self, session_id: str) -> list:
        session = self._sessions.get(session_id)
        return session["history"] if session else []
