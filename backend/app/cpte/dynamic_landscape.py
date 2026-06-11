"""
优化3: 能量景观动态更新

每轮对话后，根据学生的实际行为更新能量景观：
- 学生逃离了吸引子 → 降低势阱深度
- 学生陷得更深 → 加深势阱
- 学生向目标移动 → 增强外部场
- 发现新的认知模式 → 创建新吸引子
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape, Attractor


class DynamicLandscapeUpdater:
    """能量景观动态更新器

    核心思想：能量景观不是固定的，而是随着学生的认知演化而变化。
    就像一个弹性的床——学生躺过的地方会留下凹痕。
    """

    def __init__(self, config: Optional[CPTEConfig] = None):
        self.config = config or DEFAULT_CONFIG

        # 更新历史
        self.update_history: List[Dict[str, Any]] = []

        # 学习率（景观变化的速度）
        self.attractor_learning_rate = 0.1
        self.field_learning_rate = 0.05
        self.coupling_learning_rate = 0.03

    def update_after_conversation(
        self,
        landscape: EnergyLandscape,
        state_before: np.ndarray,
        state_after: np.ndarray,
        energy_before: float,
        energy_after: float,
        question_force: Optional[np.ndarray] = None,
        effectiveness: float = 0.0
    ) -> Dict[str, Any]:
        """对话后更新能量景观

        Args:
            landscape: 当前能量景观
            state_before: 追问前的信念状态
            state_after: 追问后的信念状态
            energy_before: 追问前能量
            energy_after: 追问后能量
            question_force: 施加的追问力
            effectiveness: 追问效果评分

        Returns:
            更新记录
        """
        update_record = {
            "timestamp": datetime.now().isoformat(),
            "attractor_updates": [],
            "field_update_magnitude": 0.0,
            "coupling_update_magnitude": 0.0,
        }

        # 1. 更新吸引子
        att_updates = self._update_attractors(
            landscape, state_before, state_after, effectiveness
        )
        update_record["attractor_updates"] = att_updates

        # 2. 更新外部场
        field_mag = self._update_external_field(
            landscape, state_before, state_after, effectiveness
        )
        update_record["field_update_magnitude"] = field_mag

        # 3. 更新交互矩阵
        coupling_mag = self._update_coupling_matrix(
            landscape, state_before, state_after, effectiveness
        )
        update_record["coupling_update_magnitude"] = coupling_mag

        # 4. 更新目标状态（如果学生展示了更好的理解）
        if landscape.target_state is not None:
            self._update_target(landscape, state_after, energy_after)

        self.update_history.append(update_record)
        return update_record

    def _update_attractors(
        self,
        landscape: EnergyLandscape,
        state_before: np.ndarray,
        state_after: np.ndarray,
        effectiveness: float
    ) -> List[Dict[str, Any]]:
        """更新吸引子参数

        规则：
        - 学生从吸引子附近离开 → 势阱变浅（学生正在克服这个误解）
        - 学生停留在吸引子附近 → 势阱变深（学生被误解困住了）
        - 学生从未知区域移动到吸引子附近 → 发现新误解
        """
        updates = []

        for att in landscape.attractors:
            dist_before = np.linalg.norm(state_before - att.center)
            dist_after = np.linalg.norm(state_after - att.center)

            update = {"id": att.id, "changes": {}}

            # 情况1：学生从吸引子中逃出
            if dist_before < att.width * 1.5 and dist_after > att.width * 2:
                # 势阱变浅
                depth_change = -self.attractor_learning_rate * effectiveness * att.depth
                att.depth = max(0.5, att.depth + depth_change)
                update["changes"]["depth"] = {
                    "old": att.depth - depth_change,
                    "new": att.depth,
                    "reason": "学生正在逃离此误解"
                }

                # 同时缩小宽度
                width_change = -self.attractor_learning_rate * 0.5 * att.width
                att.width = max(0.2, att.width + width_change)
                update["changes"]["width"] = {
                    "old": att.width - width_change,
                    "new": att.width,
                    "reason": "误解的影响范围缩小"
                }

            # 情况2：学生被吸引子困住
            elif dist_before < att.width and dist_after < att.width:
                # 势阱变深
                depth_change = self.attractor_learning_rate * 0.5 * att.depth
                att.depth = min(10.0, att.depth + depth_change)
                update["changes"]["depth"] = {
                    "old": att.depth - depth_change,
                    "new": att.depth,
                    "reason": "学生深陷此误解"
                }

            # 情况3：学生被拉向吸引子（新发现的误解倾向）
            elif dist_before > att.width * 2 and dist_after < att.width * 1.5:
                # 轻微加深
                depth_change = self.attractor_learning_rate * 0.3 * att.depth
                att.depth = min(10.0, att.depth + depth_change)
                update["changes"]["depth"] = {
                    "old": att.depth - depth_change,
                    "new": att.depth,
                    "reason": "学生表现出向此误解靠拢的倾向"
                }

            if update["changes"]:
                updates.append(update)

        return updates

    def _update_external_field(
        self,
        landscape: EnergyLandscape,
        state_before: np.ndarray,
        state_after: np.ndarray,
        effectiveness: float
    ) -> float:
        """更新外部场

        如果学生向正确方向移动，增强该方向的场。
        如果学生远离正确方向，减弱该方向的场。
        """
        if landscape.target_state is None:
            return 0.0

        # 学生移动方向
        move_direction = state_after - state_before
        move_norm = np.linalg.norm(move_direction)
        if move_norm < 1e-10:
            return 0.0

        # 指向目标的方向
        to_target = landscape.target_state - state_before
        target_norm = np.linalg.norm(to_target)
        if target_norm < 1e-10:
            return 0.0

        # 方向一致性
        alignment = np.dot(move_direction, to_target) / (move_norm * target_norm)

        # 更新场
        update = self.field_learning_rate * alignment * effectiveness * move_direction
        landscape.external_field += update

        return float(np.linalg.norm(update))

    def _update_coupling_matrix(
        self,
        landscape: EnergyLandscape,
        state_before: np.ndarray,
        state_after: np.ndarray,
        effectiveness: float
    ) -> float:
        """更新交互矩阵

        如果两个维度同时变化，增强它们之间的耦合。
        """
        delta = state_after - state_before
        n = len(delta)

        # 找出变化最大的维度
        active_dims = np.where(np.abs(delta) > 0.05)[0]
        if len(active_dims) < 2:
            return 0.0

        update = np.zeros((n, n))
        for i in active_dims:
            for j in active_dims:
                if i != j:
                    # 同向变化 → 正耦合
                    # 反向变化 → 负耦合
                    coupling_change = self.coupling_learning_rate * delta[i] * delta[j] * effectiveness
                    update[i, j] = coupling_change

        landscape.coupling_matrix += update

        # 对称化
        landscape.coupling_matrix = (landscape.coupling_matrix + landscape.coupling_matrix.T) / 2

        return float(np.linalg.norm(update))

    def _update_target(
        self,
        landscape: EnergyLandscape,
        state_after: np.ndarray,
        energy_after: float
    ):
        """更新目标状态

        如果学生展示了比当前目标更好的理解（能量更低），
        轻微调整目标状态。
        """
        target_energy = landscape.energy(landscape.target_state)

        if energy_after < target_energy:
            # 学生到达了比目标更好的状态！
            # 轻微向学生的方向调整目标
            adjustment = 0.01 * (state_after - landscape.target_state)
            landscape.target_state += adjustment
            landscape.target_state = np.clip(landscape.target_state, -1, 1)

    def detect_new_attractor_candidates(
        self,
        landscape: EnergyLandscape,
        recent_states: List[np.ndarray],
        recent_effectiveness: List[float]
    ) -> List[Dict[str, Any]]:
        """检测潜在的新吸引子位置

        如果学生在某个区域反复卡住（效果差），
        但该区域没有已有吸引子，可能是新的误解模式。
        """
        if len(recent_states) < 3:
            return []

        candidates = []
        for i, (state, eff) in enumerate(zip(recent_states, recent_effectiveness)):
            if eff < 0.3:  # 效果差
                # 检查是否靠近已有吸引子
                is_near_existing = False
                for att in landscape.attractors:
                    if np.linalg.norm(state - att.center) < att.width * 2:
                        is_near_existing = True
                        break

                if not is_near_existing:
                    candidates.append({
                        "position": state.tolist(),
                        "effectiveness": eff,
                        "index": i,
                    })

        return candidates

    def get_update_summary(self) -> Dict[str, Any]:
        """获取更新总结"""
        if not self.update_history:
            return {"updates": 0}

        total_att_updates = sum(len(r.get("attractor_updates", [])) for r in self.update_history)
        total_field_mag = sum(r.get("field_update_magnitude", 0) for r in self.update_history)
        total_coupling_mag = sum(r.get("coupling_update_magnitude", 0) for r in self.update_history)

        return {
            "updates": len(self.update_history),
            "attractor_updates": total_att_updates,
            "cumulative_field_change": total_field_mag,
            "cumulative_coupling_change": total_coupling_mag,
        }
