"""
第4层：个性化层（Personalization Layer）
职责：难度调节 + 节奏控制 + 惯性检测
铁律：E2服从节奏 + E3不优化短期 + P4自进化
目标延迟：<5ms
"""

import math
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .models import (
    PersonalizationResult, PacingDecision, PipelineContext,
    CognitiveProfile, StudentState
)


class DifficultyAdjuster:
    """难度调节器（E3不优化短期）"""

    # E3关键：独立解决率权重最高
    WEIGHT_INDEPENDENT_SOLVE = 0.4  # 独立解决率权重
    WEIGHT_ACCURACY = 0.3           # 正确率权重
    WEIGHT_SPEED = 0.2              # 速度权重
    WEIGHT_CONSISTENCY = 0.1        # 一致性权重

    def adjust(self, profile: CognitiveProfile,
               recent_performance: List[Dict],
               current_state: StudentState) -> float:
        """调节难度级别"""
        if not recent_performance:
            return 0.5  # 默认中等难度

        # 计算各项指标
        independent_solve_rate = self._calc_independent_solve(recent_performance)
        accuracy = self._calc_accuracy(recent_performance)
        speed_score = self._calc_speed_score(recent_performance)
        consistency = self._calc_consistency(recent_performance)

        # E3：独立解决率权重最高
        difficulty = (
            self.WEIGHT_INDEPENDENT_SOLVE * independent_solve_rate +
            self.WEIGHT_ACCURACY * accuracy +
            self.WEIGHT_SPEED * speed_score +
            self.WEIGHT_CONSISTENCY * consistency
        )

        # 根据状态调整
        if current_state == StudentState.FRUSTRATED:
            difficulty = max(0.1, difficulty - 0.3)
        elif current_state == StudentState.DEEP_STUCK:
            difficulty = max(0.2, difficulty - 0.2)
        elif current_state == StudentState.CONCEPT_ERROR:
            difficulty = max(0.2, difficulty - 0.1)

        return min(1.0, max(0.0, difficulty))

    def _calc_independent_solve(self, performance: List[Dict]) -> float:
        """计算独立解决率"""
        if not performance:
            return 0.5
        independent = sum(1 for p in performance if p.get("independent", False))
        return independent / len(performance)

    def _calc_accuracy(self, performance: List[Dict]) -> float:
        """计算正确率"""
        if not performance:
            return 0.5
        correct = sum(1 for p in performance if p.get("correct", False))
        return correct / len(performance)

    def _calc_speed_score(self, performance: List[Dict]) -> float:
        """计算速度得分"""
        if not performance:
            return 0.5
        times = [p.get("time_spent", 60) for p in performance]
        avg_time = sum(times) / len(times)
        # 假设理想时间是60秒
        if avg_time <= 30:
            return 1.0
        elif avg_time <= 60:
            return 0.8
        elif avg_time <= 120:
            return 0.5
        else:
            return 0.3

    def _calc_consistency(self, performance: List[Dict]) -> float:
        """计算一致性"""
        if len(performance) < 2:
            return 0.5
        results = [1 if p.get("correct", False) else 0 for p in performance]
        # 计算连续正确/错误的变化次数
        changes = sum(1 for i in range(1, len(results)) if results[i] != results[i-1])
        # 变化越少越一致
        return max(0.0, 1.0 - changes / len(results))


class PacingController:
    """节奏控制器（E2服从学生节奏）"""

    # E2关键：以学生思维速度为准
    THINKING_TIME_THRESHOLDS = {
        "quick": 10,      # 快速思考
        "normal": 30,     # 正常思考
        "slow": 60,       # 慢速思考
        "very_slow": 120, # 非常慢
    }

    def control(self, student_id: str, time_since_last_response: float,
                consecutive_questions: int,
                current_state: StudentState) -> PacingDecision:
        """控制追问节奏"""
        # E2：学生需要更多时间时等待
        if time_since_last_response < self.THINKING_TIME_THRESHOLDS["quick"]:
            # 学生可能还没想好
            if consecutive_questions >= 2:
                return PacingDecision(
                    should_wait=True,
                    wait_seconds=5.0,
                    reason="学生正在思考，等待",
                )

        # 情绪崩溃时给更多空间
        if current_state == StudentState.FRUSTRATED:
            return PacingDecision(
                should_wait=True,
                wait_seconds=10.0,
                reason="学生情绪崩溃，给更多空间",
            )

        # 深度卡壳时给更多时间
        if current_state == StudentState.DEEP_STUCK:
            if time_since_last_response < self.THINKING_TIME_THRESHOLDS["slow"]:
                return PacingDecision(
                    should_wait=True,
                    wait_seconds=8.0,
                    reason="学生深度卡壳，给更多思考时间",
                )

        # 沉默状态
        if current_state == StudentState.SILENT:
            return PacingDecision(
                should_wait=True,
                wait_seconds=15.0,
                reason="学生沉默，等待主动表达",
            )

        # 正常节奏
        return PacingDecision(
            should_wait=False,
            reason="正常节奏",
        )


class InertiaDetector:
    """惯性检测器（P4自进化）"""

    def __init__(self):
        self.method_history: Dict[str, List[str]] = {}

    def detect(self, student_id: str, method_used: str) -> Optional[str]:
        """检测方法惯性"""
        if student_id not in self.method_history:
            self.method_history[student_id] = []

        history = self.method_history[student_id]
        history.append(method_used)

        # 保留最近10次
        if len(history) > 10:
            self.method_history[student_id] = history[-10:]
            history = self.method_history[student_id]

        # 检测惯性：最近5次中同一方法出现3次以上
        if len(history) >= 5:
            recent = history[-5:]
            for method in set(recent):
                if recent.count(method) >= 3:
                    return method

        return None

    def get_alternative_method(self, dominant_method: str,
                               available_methods: List[str]) -> Optional[str]:
        """获取替代方法"""
        for method in available_methods:
            if method != dominant_method:
                return method
        return None


class PersonalizationLayer:
    """个性化层主类"""

    def __init__(self, db_module=None):
        self.difficulty_adjuster = DifficultyAdjuster()
        self.pacing_controller = PacingController()
        self.inertia_detector = InertiaDetector()
        self.db = db_module
        self._last_response_time: Dict[str, float] = {}
        self._consecutive_questions: Dict[str, int] = {}

    def process(self, context: PipelineContext) -> PersonalizationResult:
        """处理个性化层逻辑"""
        profile = context.profile
        state = context.reasoning.state if context.reasoning else StudentState.EXPLORING
        student_id = context.student_id

        # 1. 难度调节
        recent_performance = self._get_recent_performance(student_id)
        difficulty = self.difficulty_adjuster.adjust(
            profile, recent_performance, state
        )

        # 2. 节奏控制
        time_since_last = self._get_time_since_last_response(student_id)
        consecutive = self._get_consecutive_questions(student_id)
        pacing = self.pacing_controller.control(
            student_id, time_since_last, consecutive, state
        )

        # 3. 惯性检测
        last_method = self._get_last_method(student_id)
        inertia_method = self.inertia_detector.detect(
            student_id, last_method
        )

        # 更新状态
        import time
        self._last_response_time[student_id] = time.time()
        if state in [StudentState.DEEP_STUCK, StudentState.PARTIAL_STUCK]:
            self._consecutive_questions[student_id] = consecutive + 1
        else:
            self._consecutive_questions[student_id] = 0

        return PersonalizationResult(
            difficulty_level=difficulty,
            pacing=pacing,
            inertia_detected=inertia_method is not None,
            inertia_method=inertia_method or "",
        )

    def _get_recent_performance(self, student_id: str) -> List[Dict]:
        """获取最近表现"""
        if self.db:
            try:
                return self.db.get_recent_performance(int(student_id), limit=10)
            except Exception:
                pass
        return []

    def _get_time_since_last_response(self, student_id: str) -> float:
        """获取距离上次回复的时间（秒）"""
        import time
        last_time = self._last_response_time.get(student_id, 0)
        if last_time == 0:
            return 30.0
        return time.time() - last_time

    def _get_consecutive_questions(self, student_id: str) -> int:
        """获取连续追问次数"""
        return self._consecutive_questions.get(student_id, 0)

    def _get_last_method(self, student_id: str) -> str:
        """获取上次使用的方法"""
        return ""
