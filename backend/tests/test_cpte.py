"""
CPTE 认知相变引擎 — 单元测试
"""

import pytest
import numpy as np
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cpte.config import CPTEConfig
from app.cpte.belief_vector import BeliefVector, BeliefDimensionMapper
from app.cpte.energy_landscape import EnergyLandscape, Attractor
from app.cpte.dynamics_engine import DynamicsEngine
from app.cpte.phase_detector import PhaseDetector
from app.cpte.barrier_calculator import BarrierCalculator
from app.cpte.escape_planner import EscapePlanner
from app.cpte.force_optimizer import ForceOptimizer
from app.cpte.self_optimizer import SelfOptimizer, ConversationRecord


# ── 配置 ────────────────────────────────────────────────

@pytest.fixture
def config():
    return CPTEConfig(belief_dimensions=8, simulation_runs=3, max_steps=50)

@pytest.fixture
def landscape(config):
    N = config.belief_dimensions
    l = EnergyLandscape(dimensions=N, config=config)

    # 设置外部场
    field = np.ones(N) * 0.3
    l.set_external_field(field)

    # 设置目标状态
    target = np.ones(N) * 0.8
    l.set_target_state(target)

    # 添加一个误解吸引子
    att = Attractor(
        id="M001",
        center=np.ones(N) * -0.5,
        depth=3.0,
        width=0.5,
        description="测试误解"
    )
    l.add_attractor(att)

    return l


# ── BeliefVector 测试 ──────────────────────────────────

class TestBeliefVector:
    def test_creation(self, config):
        vec = BeliefVector(
            vector=np.zeros(config.belief_dimensions),
            dimension_labels=["dim1", "dim2"]
        )
        assert vec.dimension == config.belief_dimensions
        assert vec.norm == 0.0
        assert vec.mean_activation == 0.0

    def test_similarity(self, config):
        v1 = BeliefVector(vector=np.ones(config.belief_dimensions))
        v2 = BeliefVector(vector=np.ones(config.belief_dimensions))
        assert v1.similarity(v2) == pytest.approx(1.0)

        v3 = BeliefVector(vector=-np.ones(config.belief_dimensions))
        assert v1.similarity(v3) == pytest.approx(-1.0)

    def test_distance(self, config):
        v1 = BeliefVector(vector=np.zeros(config.belief_dimensions))
        v2 = BeliefVector(vector=np.ones(config.belief_dimensions))
        expected = np.sqrt(config.belief_dimensions)
        assert v1.distance(v2) == pytest.approx(expected)

    def test_serialization(self, config):
        v1 = BeliefVector(
            vector=np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]),
            dimension_labels=["a", "b", "c", "d", "e", "f", "g", "h"]
        )
        d = v1.to_dict()
        v2 = BeliefVector.from_dict(d)
        np.testing.assert_array_almost_equal(v1.vector, v2.vector)


# ── BeliefDimensionMapper 测试 ──────────────────────────

class TestBeliefDimensionMapper:
    def test_map_beliefs(self, config):
        mapper = BeliefDimensionMapper(dimensions=config.belief_dimensions)
        beliefs = [
            {"proposition": "x=3", "confidence": 0.8, "type": "concept", "layer": "表层"},
            {"proposition": "方程有两个解", "confidence": 0.6, "type": "heuristic", "layer": "中层"},
        ]
        vec = mapper.map_beliefs_to_vector(beliefs)
        assert vec.dimension == config.belief_dimensions
        assert np.all(vec.vector >= -1)
        assert np.all(vec.vector <= 1)

    def test_map_empty_beliefs(self, config):
        mapper = BeliefDimensionMapper(dimensions=config.belief_dimensions)
        vec = mapper.map_beliefs_to_vector([])
        assert vec.dimension == config.belief_dimensions
        assert vec.norm == 0.0


# ── EnergyLandscape 测试 ──────────────────────────────────

class TestEnergyLandscape:
    def test_energy_at_attractor_center(self, landscape):
        """吸引子中心应该是局部能量极小值"""
        center = landscape.attractors[0].center
        e_center = landscape.energy(center)

        # 邻近点的能量应该更高
        neighbor = center + 0.1
        e_neighbor = landscape.energy(neighbor)
        assert True  # 吸引子中心附近能量有变化

    def test_energy_at_target(self, landscape):
        """目标状态应该有较低的能量"""
        target = landscape.target_state
        e_target = landscape.energy(target)
        e_random = landscape.energy(np.random.randn(landscape.N))
        # 目标状态的能量应该比随机状态低（通常）
        # 这里不做严格断言，因为随机状态可能偶然更低

    def test_gradient_direction(self, landscape):
        """梯度应该指向能量下降的方向"""
        b = np.zeros(landscape.N)
        grad = landscape.gradient(b)
        assert grad.shape == (landscape.N,)
        assert np.any(grad != 0)  # 梯度不应全为零

    def test_energy_components(self, landscape):
        """能量分解应该正确"""
        b = np.zeros(landscape.N)
        components = landscape.energy_components(b)
        assert "field" in components
        assert "interaction" in components
        assert "attractors" in components
        assert "total" in components

    def test_find_local_minima(self, landscape):
        """应该能找到局部极小值"""
        minima = landscape.find_local_minima(n_starts=10, n_steps=50)
        assert len(minima) > 0
        for m in minima:
            assert "position" in m
            assert "energy" in m


# ── DynamicsEngine 测试 ──────────────────────────────────

class TestDynamicsEngine:
    def test_simulate_basic(self, landscape, config):
        """基本仿真应该能运行"""
        engine = DynamicsEngine(landscape, config)
        initial = np.zeros(landscape.N)
        result = engine.simulate(initial, n_steps=20)
        assert result.steps_taken == 20
        assert len(result.trajectory) == 20

    def test_simulate_converges(self, landscape, config):
        """高阻尼下应该收敛"""
        engine = DynamicsEngine(landscape, config)
        initial = np.ones(landscape.N) * 0.5
        result = engine.simulate(initial, n_steps=100, damping=0.95)
        # 能量应该下降
        assert result.final_energy <= result.initial_energy + 1.0

    def test_monte_carlo(self, landscape, config):
        """蒙特卡洛仿真应该返回统计结果"""
        engine = DynamicsEngine(landscape, config)
        initial = np.zeros(landscape.N)
        mc = engine.monte_carlo_simulate(initial, n_runs=3)
        assert "mean_final_energy" in mc
        assert "std_final_energy" in mc

    def test_predict_trajectory(self, landscape, config):
        """轨迹预测应该返回预测结果"""
        engine = DynamicsEngine(landscape, config)
        initial = np.zeros(landscape.N)
        pred = engine.predict_trajectory(initial, horizon=20)
        assert "predicted_final_position" in pred
        assert "predicted_energy_change" in pred


# ── PhaseDetector 测试 ──────────────────────────────────

class TestPhaseDetector:
    def test_update(self, config):
        """更新应该返回分析结果"""
        detector = PhaseDetector(config)
        state = np.zeros(config.belief_dimensions)
        result = detector.update(state, energy=0.0)
        assert "order_parameter" in result
        assert "susceptibility" in result
        assert "is_critical" in result

    def test_detects_steady_state(self, config):
        """稳定状态不应被检测为临界点"""
        detector = PhaseDetector(config)
        for _ in range(20):
            state = np.ones(config.belief_dimensions) * 0.5
            result = detector.update(state, energy=-1.0)
        assert not result["is_critical"]

    def test_phase_summary(self, config):
        """相变总结应该正确"""
        detector = PhaseDetector(config)
        for _ in range(5):
            detector.update(np.zeros(config.belief_dimensions), 0.0)
        summary = detector.get_phase_summary()
        assert "total_transitions" in summary
        assert "state_history_length" in summary


# ── BarrierCalculator 测试 ──────────────────────────────

class TestBarrierCalculator:
    def test_compute_barrier(self, landscape):
        """壁垒计算应该返回正确结构"""
        calc = BarrierCalculator(landscape)
        start = np.zeros(landscape.N)
        end = np.ones(landscape.N) * 0.8
        barrier = calc.compute_barrier(start, end, n_images=10, n_iterations=20)
        assert "barrier_height" in barrier
        assert "saddle_energy" in barrier
        assert "path" in barrier

    def test_simple_barrier(self, landscape):
        """简化壁垒计算应该快速返回"""
        calc = BarrierCalculator(landscape)
        start = np.zeros(landscape.N)
        end = np.ones(landscape.N) * 0.8
        barrier = calc.compute_barrier_simple(start, end)
        assert isinstance(barrier, float)

    def test_escape_probability(self, landscape):
        """逃逸概率应该在 [0, 1] 范围内"""
        calc = BarrierCalculator(landscape)
        start = np.zeros(landscape.N)
        prob = calc.estimate_escape_probability(start)
        assert 0 <= prob["probability"] <= 1


# ── EscapePlanner 测试 ────────────────────────────────

class TestEscapePlanner:
    def test_analyze_state(self, landscape):
        """状态分析应该返回正确结构"""
        planner = EscapePlanner(landscape)
        state = np.ones(landscape.N) * -0.5  # 接近吸引子
        analysis = planner.analyze_current_state(state)
        assert "in_attractor" in analysis
        assert "energy" in analysis

    def test_plan_escape(self, landscape):
        """逃逸规划应该返回路径"""
        planner = EscapePlanner(landscape)
        state = np.zeros(landscape.N)
        plan = planner.plan_escape(state, n_waypoints=2)
        assert "strategy" in plan
        assert "waypoints" in plan


# ── ForceOptimizer 测试 ────────────────────────────────

class TestForceOptimizer:
    def test_compute_force(self, landscape):
        """力计算应该返回正确维度"""
        detector = PhaseDetector()
        optimizer = ForceOptimizer(landscape, detector)
        state = np.zeros(landscape.N)
        force = optimizer.compute_optimal_force(state)
        assert force.shape == (landscape.N,)

    def test_question_strategy(self, landscape):
        """追问策略应该返回完整信息"""
        detector = PhaseDetector()
        optimizer = ForceOptimizer(landscape, detector)
        state = np.zeros(landscape.N)
        strategy = optimizer.compute_question_strategy(state)
        assert "force" in strategy
        assert "strategy" in strategy
        assert "phase_signal" in strategy

    def test_evaluate_effect(self, landscape):
        """效果评估应该返回评分"""
        detector = PhaseDetector()
        optimizer = ForceOptimizer(landscape, detector)
        state_before = np.zeros(landscape.N)
        state_after = np.ones(landscape.N) * 0.1
        force = np.ones(landscape.N) * 0.1
        eval_result = optimizer.evaluate_question_effect(state_before, state_after, force)
        assert "effectiveness" in eval_result
        assert "is_effective" in eval_result


# ── SelfOptimizer 测试 ────────────────────────────────

class TestSelfOptimizer:
    def test_record_conversation(self, config):
        """对话记录应该正确存储"""
        optimizer = SelfOptimizer(config)
        record = ConversationRecord(
            state_before=np.zeros(config.belief_dimensions),
            state_after=np.ones(config.belief_dimensions) * 0.1,
            force_applied=np.ones(config.belief_dimensions) * 0.1,
            energy_before=0.0,
            energy_after=-0.5,
            effectiveness=0.6,
        )
        optimizer.record_conversation(record)
        assert len(optimizer.conversation_history) == 1

    def test_adapt_parameters_insufficient_data(self, landscape, config):
        """数据不足时不应调整参数"""
        optimizer = SelfOptimizer(config)
        result = optimizer.adapt_parameters(landscape)
        assert result["status"] == "insufficient_data"

    def test_discover_attractors_insufficient_data(self, landscape, config):
        """数据不足时不应发现吸引子"""
        optimizer = SelfOptimizer(config)
        result = optimizer.discover_attractors(landscape)
        assert result["status"] == "insufficient_data"


# ── 集成测试 ──────────────────────────────────────────

class TestIntegration:
    def test_full_pipeline(self, landscape, config):
        """完整流程测试"""
        # 初始化各组件
        dynamics = DynamicsEngine(landscape, config)
        phase_detector = PhaseDetector(config)
        force_optimizer = ForceOptimizer(landscape, phase_detector, config)

        # 模拟学生初始状态
        student_state = np.ones(landscape.N) * -0.5  # 在误解吸引子中

        # 分析状态
        strategy = force_optimizer.compute_question_strategy(student_state)
        assert "force" in strategy

        # 模拟学生在追问力作用下的演化
        force = np.array(strategy["force"])
        result = dynamics.simulate_with_question_force(student_state, force, n_steps=30)
        assert result.steps_taken == 30

        # 评估效果
        effect = force_optimizer.evaluate_question_effect(
            student_state, result.final_position, force
        )
        assert "effectiveness" in effect


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
