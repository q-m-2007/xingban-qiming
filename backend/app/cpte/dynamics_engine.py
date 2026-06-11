"""
CPTE 认知相变引擎 — 动力学仿真引擎

用随机微分方程（Langevin 方程）模拟学生认知状态的演化：

    db/dt = -γ·∇E(b) + η(t) + F(t)

其中：
    - γ·∇E(b): 梯度下降力（自然趋向低能量态）
    - η(t): 认知噪声（随机探索），⟨η(t)η(t')⟩ = 2T·δ(t-t')
    - F(t): 追问驱动力（外部干预）
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from .config import CPTEConfig, DEFAULT_CONFIG
from .energy_landscape import EnergyLandscape, Attractor


@dataclass
class SimulationStep:
    """仿真单步记录"""
    step: int
    position: np.ndarray
    energy: float
    gradient: np.ndarray
    force: np.ndarray
    noise: np.ndarray
    velocity: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "position": self.position.tolist(),
            "energy": self.energy,
            "gradient_norm": float(np.linalg.norm(self.gradient)),
            "force_norm": float(np.linalg.norm(self.force)),
            "noise_norm": float(np.linalg.norm(self.noise)),
            "velocity_norm": float(np.linalg.norm(self.velocity)),
        }


@dataclass
class SimulationResult:
    """仿真结果"""
    trajectory: List[SimulationStep]
    initial_position: np.ndarray
    final_position: np.ndarray
    initial_energy: float
    final_energy: float
    energy_change: float
    distance_traveled: float
    steps_taken: int
    converged: bool
    phase_transitions: List[int]  # 发生相变的步数

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initial_position": self.initial_position.tolist(),
            "final_position": self.final_position.tolist(),
            "initial_energy": self.initial_energy,
            "final_energy": self.final_energy,
            "energy_change": self.energy_change,
            "distance_traveled": self.distance_traveled,
            "steps_taken": self.steps_taken,
            "converged": self.converged,
            "phase_transitions": self.phase_transitions,
            "trajectory_length": len(self.trajectory),
        }


class DynamicsEngine:
    """动力学仿真引擎

    用 Euler-Maruyama 方法求解 Langevin 方程，
    模拟学生认知状态在能量景观中的演化。
    """

    def __init__(self, landscape: EnergyLandscape, config: Optional[CPTEConfig] = None):
        self.landscape = landscape
        self.config = config or DEFAULT_CONFIG
        self.N = landscape.N

    def simulate(
        self,
        initial_state: np.ndarray,
        external_force: Optional[np.ndarray] = None,
        n_steps: Optional[int] = None,
        temperature: Optional[float] = None,
        damping: Optional[float] = None,
        record_trajectory: bool = True
    ) -> SimulationResult:
        """运行单次仿真

        Args:
            initial_state: 初始认知状态
            external_force: 外部追问力 F(t)（可以是时变的，这里简化为常力）
            n_steps: 仿真步数
            temperature: 认知温度（覆盖配置值）
            damping: 阻尼系数（覆盖配置值）
            record_trajectory: 是否记录完整轨迹

        Returns:
            SimulationResult
        """
        n_steps = n_steps or self.config.max_steps
        T = temperature if temperature is not None else self.config.temperature
        gamma = damping if damping is not None else self.config.damping
        dt = self.config.dt

        # 初始化
        b = initial_state.copy()
        trajectory = []

        initial_energy = self.landscape.energy(b)
        prev_energy = initial_energy

        for step in range(n_steps):
            # 计算能量梯度
            grad = self.landscape.gradient(b)

            # 计算外部力
            F = external_force if external_force is not None else np.zeros(self.N)

            # 计算认知噪声 η(t) ~ N(0, 2T·dt)
            noise = np.random.randn(self.N) * np.sqrt(2 * T * dt) if T > 0 else np.zeros(self.N)

            # Euler-Maruyama 更新
            # db = -γ·∇E·dt + F·dt + η
            velocity = -gamma * grad * dt + F * dt + noise
            b_new = b + velocity

            # 裁剪到合法范围
            b_new = np.clip(b_new, -1, 1)

            # 计算新能量
            new_energy = self.landscape.energy(b_new)

            # 记录轨迹
            if record_trajectory:
                trajectory.append(SimulationStep(
                    step=step,
                    position=b.copy(),
                    energy=prev_energy,
                    gradient=grad.copy(),
                    force=F.copy(),
                    noise=noise.copy(),
                    velocity=velocity.copy()
                ))

            # 更新状态
            b = b_new
            prev_energy = new_energy

        # 检测相变点
        phase_transitions = self._detect_phase_transitions_in_trajectory(trajectory)

        # 检查是否收敛（能量变化小于阈值）
        converged = abs(new_energy - initial_energy) < 0.01

        return SimulationResult(
            trajectory=trajectory,
            initial_position=initial_state,
            final_position=b,
            initial_energy=initial_energy,
            final_energy=new_energy,
            energy_change=new_energy - initial_energy,
            distance_traveled=float(np.linalg.norm(b - initial_state)),
            steps_taken=n_steps,
            converged=converged,
            phase_transitions=phase_transitions
        )

    def simulate_with_question_force(
        self,
        initial_state: np.ndarray,
        question_force: np.ndarray,
        n_steps: Optional[int] = None
    ) -> SimulationResult:
        """模拟追问力作用下的认知演化

        前半段无外力（自然状态），后半段施加追问力。
        """
        n_steps = n_steps or self.config.max_steps
        half = n_steps // 2

        # 前半段：自然演化
        result1 = self.simulate(
            initial_state,
            external_force=np.zeros(self.N),
            n_steps=half,
            record_trajectory=True
        )

        # 后半段：施加追问力
        result2 = self.simulate(
            result1.final_position,
            external_force=question_force,
            n_steps=n_steps - half,
            record_trajectory=True
        )

        # 合并轨迹
        all_trajectory = result1.trajectory + result2.trajectory

        return SimulationResult(
            trajectory=all_trajectory,
            initial_position=initial_state,
            final_position=result2.final_position,
            initial_energy=result1.initial_energy,
            final_energy=result2.final_energy,
            energy_change=result2.final_energy - result1.initial_energy,
            distance_traveled=float(np.linalg.norm(result2.final_position - initial_state)),
            steps_taken=n_steps,
            converged=result2.converged,
            phase_transitions=result1.phase_transitions + [p + half for p in result2.phase_transitions]
        )

    def monte_carlo_simulate(
        self,
        initial_state: np.ndarray,
        external_force: Optional[np.ndarray] = None,
        n_runs: Optional[int] = None
    ) -> Dict[str, Any]:
        """蒙特卡洛仿真：多次运行取统计平均

        消除随机噪声的影响，得到稳定的预测。
        """
        n_runs = n_runs or self.config.simulation_runs

        final_positions = []
        final_energies = []
        distances = []
        phase_transition_counts = []

        for _ in range(n_runs):
            result = self.simulate(initial_state, external_force)
            final_positions.append(result.final_position)
            final_energies.append(result.final_energy)
            distances.append(result.distance_traveled)
            phase_transition_counts.append(len(result.phase_transitions))

        final_positions = np.array(final_positions)
        final_energies = np.array(final_energies)
        distances = np.array(distances)

        return {
            "mean_final_position": np.mean(final_positions, axis=0).tolist(),
            "std_final_position": np.std(final_positions, axis=0).tolist(),
            "mean_final_energy": float(np.mean(final_energies)),
            "std_final_energy": float(np.std(final_energies)),
            "mean_distance": float(np.mean(distances)),
            "mean_phase_transitions": float(np.mean(phase_transition_counts)),
            "convergence_rate": float(np.mean(np.abs(np.diff(final_energies)) < 0.01)),
        }

    def predict_trajectory(
        self,
        current_state: np.ndarray,
        horizon: Optional[int] = None
    ) -> Dict[str, Any]:
        """预测学生未来的认知轨迹（无外力情况）

        用于判断学生自然演化会走向哪里。
        """
        horizon = horizon or self.config.prediction_horizon
        result = self.simulate(current_state, n_steps=horizon)

        return {
            "predicted_final_position": result.final_position.tolist(),
            "predicted_energy_change": result.energy_change,
            "predicted_distance": result.distance_traveled,
            "likely_attractor": self.landscape._find_nearest_attractor(result.final_position),
            "trajectory_preview": [s.to_dict() for s in result.trajectory[::10]],  # 每10步采样
        }

    def _detect_phase_transitions_in_trajectory(
        self,
        trajectory: List[SimulationStep]
    ) -> List[int]:
        """从轨迹中检测相变点

        相变特征：能量突降 + 位置大幅移动
        """
        if len(trajectory) < 3:
            return []

        transitions = []
        energies = [s.energy for s in trajectory]
        positions = np.array([s.position for s in trajectory])

        for i in range(1, len(trajectory) - 1):
            # 能量变化率
            de = abs(energies[i + 1] - energies[i])

            # 位置变化率
            dp = np.linalg.norm(positions[i + 1] - positions[i])

            # 相变判定：能量突降且位置大幅移动
            if de > 0.1 and dp > 0.05:
                # 确认不是噪声（前后趋势一致）
                if i > 0 and i < len(trajectory) - 2:
                    prev_de = energies[i] - energies[i - 1]
                    next_de = energies[i + 1] - energies[i]
                    if prev_de * next_de < 0:  # 能量先升后降或先降后升
                        transitions.append(i)

        # 去除过近的相变点
        filtered = []
        for t in transitions:
            if not filtered or t - filtered[-1] > self.config.critical_cooldown:
                filtered.append(t)

        return filtered

    def compute_escape_probability(
        self,
        current_state: np.ndarray,
        target_state: np.ndarray,
        barrier_height: float
    ) -> float:
        """计算从当前状态逃逸到目标状态的概率

        使用 Arrhenius 公式：P = exp(-ΔE / T)
        """
        T = self.config.escape_temperature
        if T <= 0:
            return 0.0
        return float(np.exp(-barrier_height / T))
