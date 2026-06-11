"""
CPPA 学习路径规划器（优化5）
跨题目优化学习序列，不只是逐题推荐
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .cognitive_profile import (
    CognitiveProfile, ForgettingAwareProfile, MethodHistory, MethodAttempt
)
from .method_bank import MethodBank, Method


@dataclass
class PathStep:
    """学习路径中的一步"""
    step_index: int
    problem_id: str
    topic: str
    recommended_method: str
    mode: str                    # 'comfort' | 'expand' | 'challenge' | 'review'
    purpose: str                 # 'build_confidence' | 'learn_new' | 'practice' | 'review' | 'challenge'
    estimated_time: float        # 预计耗时（秒）
    difficulty: float            # 难度 [0, 1]


@dataclass
class LearningPath:
    """完整的学习路径"""
    student_id: str
    topic: str
    steps: List[PathStep] = field(default_factory=list)
    current_step: int = 0
    created_at: str = ''
    status: str = 'active'       # 'active' | 'completed' | 'paused'

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def get_next_step(self) -> Optional[PathStep]:
        """获取下一步"""
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def advance(self):
        """进入下一步"""
        self.current_step += 1
        if self.current_step >= len(self.steps):
            self.status = 'completed'

    def get_progress(self) -> float:
        """获取进度 [0, 1]"""
        if not self.steps:
            return 0.0
        return self.current_step / len(self.steps)


class LearningPathPlanner:
    """学习路径规划器"""

    def __init__(self, method_bank: MethodBank):
        self.bank = method_bank

    def plan(self, profile: ForgettingAwareProfile,
             history: MethodHistory,
             topic: str,
             num_problems: int = 8) -> LearningPath:
        """
        规划学习路径

        策略：
        1. 前2-3题：用擅长的方法建立信心
        2. 中间2-3题：引入新方法或复习遗忘的方法
        3. 最后2题：混合练习或挑战
        """
        path = LearningPath(
            student_id=profile.base_profile.student_id,
            topic=topic,
        )

        methods = self.bank.get_methods(topic)
        if not methods:
            return path

        # 获取学生的解法偏好
        method_dist = history.get_method_distribution()
        preferred = max(method_dist, key=method_dist.get) if method_dist else methods[0].id

        # 获取需要复习的方法
        need_review = profile.get_methods_needing_review(threshold=0.3)

        # 阶段1：建立信心（前30%的问题）
        confidence_count = max(2, int(num_problems * 0.3))
        for i in range(confidence_count):
            path.steps.append(PathStep(
                step_index=len(path.steps),
                problem_id=f'{topic}_conf_{i}',
                topic=topic,
                recommended_method=preferred,
                mode='comfort',
                purpose='build_confidence',
                estimated_time=60,
                difficulty=0.3,
            ))

        # 阶段2：拓展或复习（中间40%）
        expand_count = max(2, int(num_problems * 0.4))

        # 优先复习遗忘的方法
        for i, method_id in enumerate(need_review[:expand_count]):
            path.steps.append(PathStep(
                step_index=len(path.steps),
                problem_id=f'{topic}_review_{i}',
                topic=topic,
                recommended_method=method_id,
                mode='expand',
                purpose='review',
                estimated_time=90,
                difficulty=0.4,
            ))

        # 剩余的用新方法
        remaining = expand_count - len(need_review[:expand_count])
        new_methods = [m for m in methods if m.id != preferred and m.id not in need_review]
        for i in range(remaining):
            method = new_methods[i % len(new_methods)] if new_methods else methods[0]
            path.steps.append(PathStep(
                step_index=len(path.steps),
                problem_id=f'{topic}_expand_{i}',
                topic=topic,
                recommended_method=method.id,
                mode='expand',
                purpose='learn_new',
                estimated_time=120,
                difficulty=0.5,
            ))

        # 阶段3：混合练习+挑战（最后30%）
        challenge_count = num_problems - confidence_count - expand_count
        all_methods = [m.id for m in methods]
        for i in range(challenge_count):
            method_id = all_methods[i % len(all_methods)]
            path.steps.append(PathStep(
                step_index=len(path.steps),
                problem_id=f'{topic}_challenge_{i}',
                topic=topic,
                recommended_method=method_id,
                mode='challenge' if i == challenge_count - 1 else 'expand',
                purpose='challenge' if i == challenge_count - 1 else 'practice',
                estimated_time=120 if i < challenge_count - 1 else 180,
                difficulty=0.6 if i < challenge_count - 1 else 0.8,
            ))

        return path

    def adapt_path(self, path: LearningPath,
                   profile: ForgettingAwareProfile,
                   history: MethodHistory,
                   last_result: MethodAttempt) -> LearningPath:
        """
        根据最新结果动态调整路径

        如果学生连续做错 → 降低难度，插入复习
        如果学生快速做对 → 提高难度，跳过简单题
        """
        recent = history.attempts[-5:]
        if len(recent) < 3:
            return path

        recent_accuracy = sum(1 for a in recent if a.success) / len(recent)

        # 连续做错 → 插入复习
        if recent_accuracy < 0.3:
            current = path.get_next_step()
            if current and current.purpose != 'review':
                # 在当前位置插入一个复习步骤
                review_step = PathStep(
                    step_index=current.step_index,
                    problem_id=f'{path.topic}_emergency_review',
                    topic=path.topic,
                    recommended_method=last_result.method_used,
                    mode='comfort',
                    purpose='review',
                    estimated_time=60,
                    difficulty=0.2,
                )
                path.steps.insert(path.current_step, review_step)

        # 连续快速做对 → 跳过简单题
        if recent_accuracy > 0.9 and all(a.time_spent < 30 for a in recent):
            current = path.get_next_step()
            if current and current.difficulty < 0.4:
                path.advance()  # 跳过这道简单题

        return path


# ──────────────────────────────────────────
# 学习会话管理器
# ──────────────────────────────────────────

@dataclass
class LearningSession:
    """一次学习会话"""
    session_id: str
    student_id: str
    topic: str
    path: Optional[LearningPath] = None
    start_time: str = ''
    problems_attempted: int = 0
    problems_correct: int = 0
    total_time: float = 0.0
    status: str = 'active'

    def __post_init__(self):
        if not self.start_time:
            self.start_time = datetime.now().isoformat()

    def get_session_summary(self) -> Dict:
        return {
            'session_id': self.session_id,
            'topic': self.topic,
            'problems_attempted': self.problems_attempted,
            'problems_correct': self.problems_correct,
            'accuracy': self.problems_correct / max(self.problems_attempted, 1),
            'total_time': self.total_time,
            'progress': self.path.get_progress() if self.path else 0.0,
        }
