"""
CPPA 动态难度调节器
根据学生画像和表现，动态调节教学难度和节奏
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

from .cognitive_profile import CognitiveProfile, MethodAttempt


@dataclass
class DifficultyDecision:
    """难度调节决策"""
    level: str                     # 'simplify' | 'standard' | 'challenge' | 'stretch'
    reason: str                    # 调节原因
    suggested_method_mode: str     # 建议的解法推荐模式
    pace: str                      # 'slow' | 'moderate' | 'fast'
    hint_aggressiveness: float     # 提示激进度 [0, 1]
    description: str               # 描述


class DifficultyAdjuster:
    """动态难度调节器"""

    def __init__(self):
        self.window_size = 10  # 最近N次尝试

    def adjust(self, profile: CognitiveProfile,
               recent_attempts: List[MethodAttempt],
               current_topic: str) -> DifficultyDecision:
        """
        根据学生画像和最近表现，决定难度调节策略
        """
        # ── 分析最近表现 ──
        performance = self._analyze_performance(recent_attempts)

        # ── 结合画像做决策 ──
        return self._make_decision(profile, performance)

    def _analyze_performance(self, attempts: List[MethodAttempt]) -> Dict:
        """分析最近表现"""
        recent = attempts[-self.window_size:]
        if not recent:
            return {
                'accuracy': 0.5,
                'avg_time': 120,
                'avg_verification': 1.0,
                'trend': 'stable',
                'frustration_signals': 0,
            }

        accuracy = sum(1 for a in recent if a.success) / len(recent)
        avg_time = sum(a.time_spent for a in recent) / len(recent)
        avg_verification = sum(a.verification_level for a in recent) / len(recent)

        # 趋势：最近5次 vs 之前5次
        if len(recent) >= 10:
            recent_5 = recent[-5:]
            prev_5 = recent[-10:-5]
            recent_acc = sum(1 for a in recent_5 if a.success) / 5
            prev_acc = sum(1 for a in prev_5 if a.success) / 5
            if recent_acc > prev_acc + 0.2:
                trend = 'improving'
            elif recent_acc < prev_acc - 0.2:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        return {
            'accuracy': accuracy,
            'avg_time': avg_time,
            'avg_verification': avg_verification,
            'trend': trend,
        }

    def _make_decision(self, profile: CognitiveProfile,
                       performance: Dict) -> DifficultyDecision:
        """做出难度调节决策"""

        accuracy = performance['accuracy']
        trend = performance['trend']
        abstract = profile.abstract_reasoning
        challenge = profile.challenge_drive

        # ── 规则1：正确率很低 → 简化 ──
        if accuracy < 0.3:
            return DifficultyDecision(
                level='simplify',
                reason=f'最近正确率仅{accuracy:.0%}，需要降低难度',
                suggested_method_mode='comfort',
                pace='slow',
                hint_aggressiveness=0.8,
                description='用最基础的方法，给更多提示，放慢节奏',
            )

        # ── 规则2：正确率下降 → 简化 ──
        if trend == 'declining':
            return DifficultyDecision(
                level='simplify',
                reason='正确率呈下降趋势，需要调整',
                suggested_method_mode='comfort',
                pace='slow',
                hint_aggressiveness=0.7,
                description='回到学生擅长的方法，重建信心',
            )

        # ── 规则3：能力强+正确率高+喜欢挑战 → 提高难度 ──
        if accuracy > 0.8 and abstract > 0.7 and challenge > 0.6:
            return DifficultyDecision(
                level='challenge',
                reason=f'能力强(抽象推理{abstract:.0%})且正确率高({accuracy:.0%})',
                suggested_method_mode='challenge',
                pace='fast',
                hint_aggressiveness=0.2,
                description='给更巧妙的解法，减少提示，增加思考空间',
            )

        # ── 规则4：能力强但不喜欢挑战 → 适度拓展 ──
        if accuracy > 0.7 and abstract > 0.6:
            return DifficultyDecision(
                level='standard',
                reason='能力不错，保持正常节奏',
                suggested_method_mode='expand',
                pace='moderate',
                hint_aggressiveness=0.4,
                description='正常难度，适度引导体验新方法',
            )

        # ── 规则5：正确率上升 → 可以适度提高 ──
        if trend == 'improving':
            return DifficultyDecision(
                level='standard',
                reason='正确率在提升，保持当前节奏',
                suggested_method_mode='expand',
                pace='moderate',
                hint_aggressiveness=0.4,
                description='保持当前难度，引导尝试新方法',
            )

        # ── 默认：标准难度 ──
        return DifficultyDecision(
            level='standard',
            reason='表现正常',
            suggested_method_mode='comfort',
            pace='moderate',
            hint_aggressiveness=0.5,
            description='标准教学节奏',
        )

    def get_hint_level(self, stuck_rounds: int,
                       hint_aggressiveness: float) -> int:
        """
        根据卡壳轮次和提示激进度，决定提示层级

        返回：1=方向提示, 2=公式提示, 3=详细步骤
        """
        base_level = min(3, stuck_rounds)
        adjusted = base_level + (1 if hint_aggressiveness > 0.6 else 0)
        return min(3, max(1, adjusted))

    def should_give_up(self, total_rounds: int,
                       stuck_rounds: int,
                       profile: CognitiveProfile) -> bool:
        """
        判断是否应该放弃追问，直接给讲解

        规则：
        - 追问超过5轮仍卡住 → 放弃
        - 学生注意力短且追问超过3轮 → 放弃
        """
        if total_rounds > 5 and stuck_rounds > 3:
            return True
        if profile.attention_span < 0.3 and stuck_rounds > 3:
            return True
        return False
