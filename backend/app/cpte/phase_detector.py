"""
CPTE 认知相变引擎 — 相变检测器

检测学生认知状态中的相变信号：
- 序参数 φ(t) 的突变
- 认知磁化率 χ(t) 的峰值
- 能量景观中的鞍点穿越
- 信念向量的旋转（方向突变）
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
from .config import CPTEConfig, DEFAULT_CONFIG


class PhaseDetector:
    """相变检测器

    实时监测学生的认知状态，识别即将发生相变的临界点。
    这是追问的最佳时机——学生处于"一推就通"的状态。
    """

    def __init__(self, config: Optional[CPTEConfig] = None):
        self.config = config or DEFAULT_CONFIG

        # 历史状态窗口
        self._state_history: deque = deque(maxlen=self.config.order_param_window * 3)
        self._energy_history: deque = deque(maxlen=self.config.order_param_window * 3)
        self._order_param_history: deque = deque(maxlen=self.config.order_param_window * 3)

        # 相变事件记录
        self.phase_transitions: List[Dict[str, Any]] = []

        # 冷却计数器
        self._cooldown_counter = 0

    def update(self, state: np.ndarray, energy: float) -> Dict[str, Any]:
        """更新检测器状态，返回当前分析结果

        每次学生输入后调用此方法。

        Args:
            state: 当前信念向量
            energy: 当前能量值

        Returns:
            分析结果，包含是否处于临界点等信息
        """
        self._state_history.append(state.copy())
        self._energy_history.append(energy)

        # 计算序参数
        order_param = float(np.mean(state))
        self._order_param_history.append(order_param)

        # 冷却计数
        if self._cooldown_counter > 0:
            self._cooldown_counter -= 1

        # 各项检测
        result = {
            "order_parameter": order_param,
            "susceptibility": 0.0,
            "energy_trend": 0.0,
            "state_velocity": 0.0,
            "state_acceleration": 0.0,
            "is_critical": False,
            "critical_type": None,
            "confidence": 0.0,
        }

        if len(self._state_history) < 3:
            return result

        # 计算认知磁化率 χ
        result["susceptibility"] = self._compute_susceptibility()

        # 计算能量趋势
        result["energy_trend"] = self._compute_energy_trend()

        # 计算状态速度和加速度
        result["state_velocity"] = self._compute_state_velocity()
        result["state_acceleration"] = self._compute_state_acceleration()

        # 综合判断是否处于临界点
        critical, critical_type, confidence = self._detect_criticality(result)
        result["is_critical"] = critical
        result["critical_type"] = critical_type
        result["confidence"] = confidence

        # 记录相变事件
        if critical and self._cooldown_counter == 0:
            self.phase_transitions.append({
                "step": len(self._state_history),
                "type": critical_type,
                "confidence": confidence,
                "order_parameter": order_param,
                "susceptibility": result["susceptibility"],
                "energy": energy,
            })
            self._cooldown_counter = self.config.critical_cooldown

        return result

    def _compute_susceptibility(self) -> float:
        """计算认知磁化率 χ = (1/T)·[⟨φ²⟩ - ⟨φ⟩²]

        磁化率高表示系统对扰动敏感——处于临界点附近。
        """
        window = list(self._order_param_history)[-self.config.order_param_window:]
        if len(window) < 3:
            return 0.0

        phi_array = np.array(window)
        chi = float(np.var(phi_array))

        # 归一化到 [0, 10] 范围
        return min(10.0, chi * 100)

    def _compute_energy_trend(self) -> float:
        """计算能量变化趋势（负值表示能量在下降，即学习在发生）"""
        window = list(self._energy_history)[-self.config.order_param_window:]
        if len(window) < 3:
            return 0.0

        energies = np.array(window)
        # 线性回归斜率
        x = np.arange(len(energies))
        slope = float(np.polyfit(x, energies, 1)[0])
        return slope

    def _compute_state_velocity(self) -> float:
        """计算状态变化速度 ||db/dt||"""
        states = list(self._state_history)
        if len(states) < 2:
            return 0.0
        return float(np.linalg.norm(states[-1] - states[-2]))

    def _compute_state_acceleration(self) -> float:
        """计算状态变化加速度 ||d²b/dt²||"""
        states = list(self._state_history)
        if len(states) < 3:
            return 0.0

        v1 = states[-1] - states[-2]
        v2 = states[-2] - states[-3]
        return float(np.linalg.norm(v1 - v2))

    def _detect_criticality(
        self,
        metrics: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], float]:
        """综合判断是否处于相变临界点

        返回 (is_critical, type, confidence)
        """
        signals = []

        # 信号1：磁化率突增
        if metrics["susceptibility"] > self.config.susceptibility_threshold:
            signals.append(("susceptibility_spike", metrics["susceptibility"] / 10.0))

        # 信号2：能量趋势突然转向（从上升变为下降）
        if len(self._energy_history) >= 6:
            recent = list(self._energy_history)[-6:]
            first_half_trend = np.mean(np.diff(recent[:3]))
            second_half_trend = np.mean(np.diff(recent[3:]))
            if first_half_trend > 0 and second_half_trend < 0:
                signals.append(("energy_reversal", 0.7))
            elif first_half_trend < 0 and abs(second_half_trend) > abs(first_half_trend) * 2:
                signals.append(("accelerated_descent", 0.6))

        # 信号3：状态速度突增（认知跃迁）
        if metrics["state_velocity"] > 0.15:
            signals.append(("velocity_spike", min(1.0, metrics["state_velocity"])))

        # 信号4：状态加速度突增（变化在加速）
        if metrics["state_acceleration"] > 0.1:
            signals.append(("acceleration_spike", min(1.0, metrics["state_acceleration"])))

        if not signals:
            return False, None, 0.0

        # 选择最强信号
        signals.sort(key=lambda x: x[1], reverse=True)
        best_type, best_confidence = signals[0]

        # 如果有多个信号同时出现，提高置信度
        if len(signals) >= 2:
            best_confidence = min(1.0, best_confidence * 1.3)

        is_critical = best_confidence > 0.5

        return is_critical, best_type, best_confidence

    def get_phase_summary(self) -> Dict[str, Any]:
        """获取相变检测的总结"""
        return {
            "total_transitions": len(self.phase_transitions),
            "transitions": self.phase_transitions,
            "current_susceptibility": self._compute_susceptibility() if self._order_param_history else 0.0,
            "state_history_length": len(self._state_history),
        }

    def reset(self):
        """重置检测器"""
        self._state_history.clear()
        self._energy_history.clear()
        self._order_param_history.clear()
        self.phase_transitions.clear()
        self._cooldown_counter = 0
