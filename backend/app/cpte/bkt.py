"""
优化6: 贝叶斯知识追踪 (BKT) 集成

用概率模型替代硬阈值置信度。
BKT 追踪"学生是否掌握了某个知识点"的概率，
比简单的置信度更准确。

BKT 核心公式：
P(mastered | correct) = P(correct | mastered) * P(mastered) / P(correct)
P(mastered | incorrect) = P(incorrect | mastered) * P(mastered) / P(incorrect)
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field


@dataclass
class BKTParams:
    """BKT 参数（每个知识点独立）"""
    p_init: float = 0.1       # P(L₀): 初始掌握概率
    p_transit: float = 0.1    # P(T): 学习转移概率（不会→会）
    p_guess: float = 0.2      # P(G): 猜对概率
    p_slip: float = 0.1       # P(S): 失误概率

    def __post_init__(self):
        assert 0 <= self.p_init <= 1
        assert 0 <= self.p_transit <= 1
        assert 0 <= self.p_guess <= 1
        assert 0 <= self.p_slip <= 1
        assert self.p_guess + self.p_slip < 1  # 否则模型无意义


@dataclass
class BKTSkill:
    """BKT 技能状态"""
    skill_id: str
    params: BKTParams
    p_mastered: float = 0.1   # 当前掌握概率
    history: List[Dict[str, Any]] = field(default_factory=list)
    observation_count: int = 0
    correct_count: int = 0

    @property
    def mastery_level(self) -> str:
        if self.p_mastered >= 0.9:
            return "mastered"
        elif self.p_mastered >= 0.6:
            return "learning"
        elif self.p_mastered >= 0.3:
            return "struggling"
        else:
            return "novice"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "p_mastered": self.p_mastered,
            "mastery_level": self.mastery_level,
            "observations": self.observation_count,
            "accuracy": self.correct_count / max(1, self.observation_count),
            "params": {
                "p_init": self.params.p_init,
                "p_transit": self.params.p_transit,
                "p_guess": self.params.p_guess,
                "p_slip": self.params.p_slip,
            }
        }


class BayesianKnowledgeTracer:
    """贝叶斯知识追踪器

    追踪学生对每个知识点的掌握概率，
    比简单置信度更准确地反映"学生会不会"。
    """

    def __init__(self, default_params: Optional[BKTParams] = None):
        self.default_params = default_params or BKTParams()
        self.skills: Dict[str, BKTSkill] = {}

        # 参数自适应历史
        self._param_adaptation_history: List[Dict[str, Any]] = []

    def register_skill(
        self,
        skill_id: str,
        params: Optional[BKTParams] = None,
        initial_mastery: Optional[float] = None
    ):
        """注册一个知识点技能"""
        params = params or self.default_params
        p_init = initial_mastery if initial_mastery is not None else params.p_init

        self.skills[skill_id] = BKTSkill(
            skill_id=skill_id,
            params=params,
            p_mastered=p_init,
        )

    def update(
        self,
        skill_id: str,
        is_correct: bool,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """更新技能掌握概率

        Args:
            skill_id: 技能 ID
            is_correct: 学生回答是否正确
            confidence: 观测的置信度（0-1，用于加权）

        Returns:
            更新后的状态
        """
        skill = self.skills.get(skill_id)
        if skill is None:
            self.register_skill(skill_id)
            skill = self.skills[skill_id]

        params = skill.params
        p_prior = skill.p_mastered

        # BKT 更新公式
        if is_correct:
            # P(mastered | correct) = P(correct|mastered) * P(mastered) / P(correct)
            p_correct_mastered = 1 - params.p_slip  # 掌握了且没失误
            p_correct_not_mastered = params.p_guess  # 没掌握但猜对了

            p_correct = (p_correct_mastered * p_prior +
                        p_correct_not_mastered * (1 - p_prior))

            p_posterior = (p_correct_mastered * p_prior) / max(p_correct, 1e-10)
        else:
            # P(mastered | incorrect) = P(incorrect|mastered) * P(mastered) / P(incorrect)
            p_incorrect_mastered = params.p_slip  # 掌握了但失误
            p_incorrect_not_mastered = 1 - params.p_guess  # 没掌握且没猜对

            p_incorrect = (p_incorrect_mastered * p_prior +
                          p_incorrect_not_mastered * (1 - p_prior))

            p_posterior = (p_incorrect_mastered * p_prior) / max(p_incorrect, 1e-10)

        # 应用学习转移概率
        # 如果之前没掌握，有概率通过这次学习掌握了
        p_mastered_final = p_posterior + (1 - p_posterior) * params.p_transit * confidence

        # 裁剪到 [0, 1]
        p_mastered_final = np.clip(p_mastered_final, 0, 1)

        # 更新状态
        old_mastery = skill.p_mastered
        skill.p_mastered = float(p_mastered_final)
        skill.observation_count += 1
        if is_correct:
            skill.correct_count += 1

        # 记录历史
        skill.history.append({
            "is_correct": is_correct,
            "confidence": confidence,
            "p_prior": float(p_prior),
            "p_posterior": float(p_posterior),
            "p_mastered": float(p_mastered_final),
            "mastery_level": skill.mastery_level,
        })

        return {
            "skill_id": skill_id,
            "p_mastered_before": float(old_mastery),
            "p_mastered_after": float(p_mastered_final),
            "mastery_change": float(p_mastered_final - old_mastery),
            "mastery_level": skill.mastery_level,
            "is_correct": is_correct,
        }

    def predict_correctness(self, skill_id: str) -> float:
        """预测学生下次回答正确的概率

        P(correct) = P(correct|mastered)*P(mastered) + P(correct|not_mastered)*P(not_mastered)
        """
        skill = self.skills.get(skill_id)
        if skill is None:
            return 0.5

        params = skill.params
        p_m = skill.p_mastered

        p_correct = (1 - params.p_slip) * p_m + params.p_guess * (1 - p_m)
        return float(p_correct)

    def get_mastery_probabilities(self) -> Dict[str, float]:
        """获取所有技能的掌握概率"""
        return {sid: s.p_mastered for sid, s in self.skills.items()}

    def get_weak_skills(self, threshold: float = 0.5) -> List[BKTSkill]:
        """获取薄弱技能（掌握概率低于阈值）"""
        return [s for s in self.skills.values() if s.p_mastered < threshold]

    def get_strong_skills(self, threshold: float = 0.8) -> List[BKTSkill]:
        """获取掌握良好的技能"""
        return [s for s in self.skills.values() if s.p_mastered >= threshold]

    def adapt_parameters(
        self,
        skill_id: str,
        window_size: int = 20
    ) -> Dict[str, Any]:
        """自适应调整 BKT 参数

        根据历史观测数据，用 EM 算法的简化版调整参数。
        """
        skill = self.skills.get(skill_id)
        if skill is None or len(skill.history) < window_size:
            return {"status": "insufficient_data"}

        recent = skill.history[-window_size:]
        observations = [(h["is_correct"], h["p_prior"]) for h in recent]

        # 简化版 EM：用观测频率估计参数
        correct_observations = [o for o in observations if o[0]]
        incorrect_observations = [o for o in observations if not o[0]]

        # 估计 guess 和 slip
        if correct_observations:
            # guess ≈ 没掌握但答对的比例
            low_mastery_correct = [o for o in correct_observations if o[1] < 0.5]
            if low_mastery_correct:
                new_guess = len(low_mastery_correct) / max(1, len(correct_observations))
                skill.params.p_guess = np.clip(new_guess, 0.05, 0.4)

        if incorrect_observations:
            # slip ≈ 掌握了但答错的比例
            high_mastery_incorrect = [o for o in incorrect_observations if o[1] > 0.5]
            if high_mastery_incorrect:
                new_slip = len(high_mastery_incorrect) / max(1, len(incorrect_observations))
                skill.params.p_slip = np.clip(new_slip, 0.01, 0.3)

        # 估计 transit
        mastery_increases = [
            h["p_mastered"] - h["p_prior"]
            for h in recent
            if h["p_mastered"] > h["p_prior"]
        ]
        if mastery_increases:
            new_transit = np.mean(mastery_increases)
            skill.params.p_transit = np.clip(new_transit, 0.01, 0.5)

        return {
            "status": "adapted",
            "params": {
                "p_guess": skill.params.p_guess,
                "p_slip": skill.params.p_slip,
                "p_transit": skill.params.p_transit,
            },
            "window_size": window_size,
        }

    def compute_knowledge_state_vector(self, skill_order: List[str]) -> np.ndarray:
        """将所有技能的掌握概率转换为向量

        用于与 CPTE 的能量景观结合。
        """
        vec = np.zeros(len(skill_order))
        for i, skill_id in enumerate(skill_order):
            skill = self.skills.get(skill_id)
            if skill:
                # 将 [0, 1] 映射到 [-1, 1]
                vec[i] = skill.p_mastered * 2 - 1
        return vec

    def get_summary(self) -> Dict[str, Any]:
        """获取总结"""
        if not self.skills:
            return {"total_skills": 0}

        masteries = [s.p_mastered for s in self.skills.values()]
        return {
            "total_skills": len(self.skills),
            "mean_mastery": float(np.mean(masteries)),
            "mastered_count": sum(1 for m in masteries if m >= 0.9),
            "learning_count": sum(1 for m in masteries if 0.3 <= m < 0.9),
            "struggling_count": sum(1 for m in masteries if m < 0.3),
        }
