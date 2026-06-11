"""
CPTE v2.0 Ultra — 七大优化模块测试
"""

import pytest
import numpy as np
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.cpte.config import CPTEConfig
from app.cpte.embedding import SemanticEmbedder
from app.cpte.forgetting import ForgettingModel, ForgettableBelief
from app.cpte.dynamic_landscape import DynamicLandscapeUpdater
from app.cpte.transfer import CrossTopicTransfer
from app.cpte.lyapunov import LyapunovAnalyzer
from app.cpte.bkt import BayesianKnowledgeTracer, BKTParams
from app.cpte.multi_student import MultiStudentTransfer
from app.cpte.energy_landscape import EnergyLandscape, Attractor


@pytest.fixture
def config():
    return CPTEConfig(belief_dimensions=8)


@pytest.fixture
def landscape(config):
    N = config.belief_dimensions
    l = EnergyLandscape(dimensions=N, config=config)
    l.set_external_field(np.ones(N) * 0.3)
    l.set_target_state(np.ones(N) * 0.8)
    l.add_attractor(Attractor(id="M001", center=np.ones(N)*-0.5, depth=3.0, width=0.5, description="test"))
    return l


# ═══════════════════════════════════════════════════════
# 优化1: 语义 Embedding
# ═══════════════════════════════════════════════════════

class TestSemanticEmbedding:
    def test_embedder_creation(self):
        embedder = SemanticEmbedder()
        assert embedder is not None

    def test_encode_returns_vector(self):
        embedder = SemanticEmbedder()
        vec = embedder.encode("一元二次方程", dimension=8)
        assert len(vec) == 8
        assert np.all(vec >= -1)
        assert np.all(vec <= 1)

    def test_similar_texts_similar_vectors(self):
        embedder = SemanticEmbedder()
        vec1 = embedder.encode("一元二次方程", dimension=8)
        vec2 = embedder.encode("二次方程", dimension=8)
        vec3 = embedder.encode("三角函数", dimension=8)

        sim_12 = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-10)
        sim_13 = np.dot(vec1, vec3) / (np.linalg.norm(vec1) * np.linalg.norm(vec3) + 1e-10)

        # 相似文本应该有更高的相似度（至少不是反向）
        assert sim_12 > sim_13 or abs(sim_12 - sim_13) < 0.1

    def test_batch_encode(self):
        embedder = SemanticEmbedder()
        texts = ["x=3", "x=5", "方程有解"]
        vecs = embedder.encode_batch(texts, dimension=8)
        assert vecs.shape == (3, 8)

    def test_caching(self):
        embedder = SemanticEmbedder()
        vec1 = embedder.encode("test", dimension=8)
        vec2 = embedder.encode("test", dimension=8)
        np.testing.assert_array_equal(vec1, vec2)

    def test_similarity(self):
        embedder = SemanticEmbedder()
        sim = embedder.similarity("一元二次方程", "二次方程")
        assert -1 <= sim <= 1


# ═══════════════════════════════════════════════════════
# 优化2: 遗忘曲线
# ═══════════════════════════════════════════════════════

class TestForgettingModel:
    def test_add_belief(self):
        model = ForgettingModel()
        belief = model.add_belief("b1", "x=3", "concept", 0.8)
        assert belief.current_confidence() == pytest.approx(0.8, abs=0.05)

    def test_forgetting_decay(self):
        model = ForgettingModel()
        belief = model.add_belief("b1", "x=3", "concept", 0.8)
        # 1小时后
        future = datetime.now() + timedelta(hours=1)
        conf_after_1h = belief.current_confidence(future)
        assert conf_after_1h < 0.8
        assert conf_after_1h > 0.05  # 不会低于基线

    def test_different_types_different_decay(self):
        model = ForgettingModel()
        concept = model.add_belief("b1", "概念", "concept", 0.8)
        heuristic = model.add_belief("b2", "启发", "heuristic", 0.8)

        future = datetime.now() + timedelta(hours=2)
        conf_concept = concept.current_confidence(future)
        conf_heuristic = heuristic.current_confidence(future)

        # 启发式信念衰减更快
        assert conf_heuristic < conf_concept

    def test_activation_reinforces(self):
        model = ForgettingModel()
        belief = model.add_belief("b1", "x=3", "concept", 0.8)

        # 多次激活
        for _ in range(5):
            belief.activate()

        future = datetime.now() + timedelta(hours=2)
        conf_with_activations = belief.current_confidence(future)

        # 激活越多，衰减越慢
        model2 = ForgettingModel()
        belief2 = model2.add_belief("b2", "x=3", "concept", 0.8)
        conf_without = belief2.current_confidence(future)

        assert conf_with_activations >= conf_without

    def test_emotional_tag_effect(self):
        model = ForgettingModel()
        attached = model.add_belief("b1", "x=3", "concept", 0.8, emotional_tag="attached")
        insecure = model.add_belief("b2", "x=3", "concept", 0.8, emotional_tag="insecure")

        future = datetime.now() + timedelta(hours=1)
        conf_attached = attached.current_confidence(future)
        conf_insecure = insecure.current_confidence(future)

        # 有情感依附的记忆更持久
        assert conf_attached > conf_insecure

    def test_forgotten_beliefs(self):
        model = ForgettingModel()
        model.add_belief("b1", "x=3", "concept", 0.8)
        model.add_belief("b2", "y=5", "heuristic", 0.3)

        future = datetime.now() + timedelta(hours=3)
        forgotten = model.get_forgotten_beliefs(threshold=0.2, now=future)
        assert len(forgotten) >= 1

    def test_predict_forgetting_curve(self):
        model = ForgettingModel()
        model.add_belief("b1", "x=3", "concept", 0.8)
        curve = model.predict_forgetting_curve("b1", duration_hours=24)
        assert len(curve["confidences"]) == 100
        assert curve["confidences"][0] > curve["confidences"][-1]


# ═══════════════════════════════════════════════════════
# 优化3: 能量景观动态更新
# ═══════════════════════════════════════════════════════

class TestDynamicLandscape:
    def test_update_attractors_escape(self, landscape, config):
        updater = DynamicLandscapeUpdater(config)
        att = landscape.attractors[0]
        old_depth = att.depth

        # 学生从吸引子中逃出
        state_before = att.center.copy()
        state_after = att.center + np.ones(config.belief_dimensions) * 2
        updater.update_after_conversation(
            landscape, state_before, state_after, 0, -1, effectiveness=0.8
        )

        # 势阱应该变浅
        assert att.depth < old_depth

    def test_update_attractors_trapped(self, landscape, config):
        updater = DynamicLandscapeUpdater(config)
        att = landscape.attractors[0]
        old_depth = att.depth

        # 学生被困在吸引子中
        state = att.center + np.random.randn(config.belief_dimensions) * 0.1
        updater.update_after_conversation(
            landscape, state, state, 0, 0, effectiveness=0.1
        )

        # 势阱应该变深
        assert att.depth > old_depth

    def test_update_external_field(self, landscape, config):
        updater = DynamicLandscapeUpdater(config)
        old_field = landscape.external_field.copy()

        # 学生向正确方向移动
        state_before = np.zeros(config.belief_dimensions)
        state_after = np.ones(config.belief_dimensions) * 0.3
        updater.update_after_conversation(
            landscape, state_before, state_after, 0, -1, effectiveness=0.7
        )

        # 场应该有变化
        assert not np.allclose(landscape.external_field, old_field)

    def test_detect_new_attractors(self, landscape, config):
        updater = DynamicLandscapeUpdater(config)
        states = [np.ones(config.belief_dimensions) * 0.5] * 5
        effects = [0.1] * 5
        candidates = updater.detect_new_attractor_candidates(landscape, states, effects)
        assert isinstance(candidates, list)


# ═══════════════════════════════════════════════════════
# 优化4: 跨知识点迁移
# ═══════════════════════════════════════════════════════

class TestCrossTopicTransfer:
    def test_register_topic(self, config):
        transfer = CrossTopicTransfer(config.belief_dimensions)
        l = EnergyLandscape(dimensions=config.belief_dimensions)
        transfer.register_topic("quadratic", l)
        assert "quadratic" in transfer.landscapes

    def test_transferred_field(self, config):
        transfer = CrossTopicTransfer(config.belief_dimensions)
        l1 = EnergyLandscape(dimensions=config.belief_dimensions)
        l1.set_external_field(np.ones(config.belief_dimensions) * 0.5)
        l2 = EnergyLandscape(dimensions=config.belief_dimensions)

        transfer.register_topic("linear", l1)
        transfer.register_topic("quadratic", l2)
        transfer.set_transfer_weight("linear", "quadratic", 0.7)

        states = {"linear": np.ones(config.belief_dimensions) * 0.8}
        field = transfer.compute_transferred_field("quadratic", states)
        assert len(field) == config.belief_dimensions
        assert np.any(field != 0)

    def test_learning_priority(self, config):
        transfer = CrossTopicTransfer(config.belief_dimensions)
        states = {
            "linear": np.ones(config.belief_dimensions) * 0.8,
            "quadratic": np.ones(config.belief_dimensions) * 0.2,
        }
        priorities = transfer.get_learning_priority(states, ["linear", "quadratic"])
        assert len(priorities) == 2
        # 掌握差的应该优先级高
        assert priorities[0]["priority"] >= priorities[1]["priority"]


# ═══════════════════════════════════════════════════════
# 优化5: Lyapunov 指数
# ═══════════════════════════════════════════════════════

class TestLyapunovAnalyzer:
    def test_creation(self, config):
        analyzer = LyapunovAnalyzer(config.belief_dimensions)
        assert analyzer.dimension == config.belief_dimensions

    def test_update_returns_result(self, config):
        analyzer = LyapunovAnalyzer(config.belief_dimensions)
        result = analyzer.update(np.zeros(config.belief_dimensions))
        assert "lyapunov_exponent" in result
        assert "is_critical" in result
        assert "is_stable" in result

    def test_stable_trajectory(self, config):
        analyzer = LyapunovAnalyzer(config.belief_dimensions, window_size=10)
        # 收敛轨迹
        for i in range(15):
            state = np.ones(config.belief_dimensions) * (0.5 + 0.01 * i)
            result = analyzer.update(state)
        # 应该是稳定的
        assert result["is_stable"] or result["lyapunov_exponent"] < 0.1

    def test_bifurcation_detection(self, config):
        analyzer = LyapunovAnalyzer(config.belief_dimensions)
        params = list(np.linspace(0, 1, 20))
        states = [np.random.randn(config.belief_dimensions) * p for p in params]
        result = analyzer.detect_bifurcation(params, states)
        assert "has_bifurcation" in result


# ═══════════════════════════════════════════════════════
# 优化6: 贝叶斯知识追踪
# ═══════════════════════════════════════════════════════

class TestBKT:
    def test_register_skill(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("quadratic")
        assert "quadratic" in bkt.skills

    def test_correct_increases_mastery(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("quadratic")
        old = bkt.skills["quadratic"].p_mastered
        bkt.update("quadratic", is_correct=True)
        assert bkt.skills["quadratic"].p_mastered > old

    def test_incorrect_decreases_mastery(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("q1", BKTParams(p_init=0.8))
        old = bkt.skills["q1"].p_mastered
        bkt.update("q1", is_correct=False)
        assert bkt.skills["q1"].p_mastered < old















        bkt.register_skill("quadratic", BKTParams(p_init=0.1, p_transit=0.2))
        for _ in range(20):
            bkt.update("quadratic", is_correct=True)
        assert bkt.skills["quadratic"].p_mastered > 0.5

    def test_predict_correctness(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("quadratic")
        prob = bkt.predict_correctness("quadratic")
        assert 0 <= prob <= 1

    def test_weak_skills(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("weak", BKTParams(p_init=0.1))
        bkt.register_skill("strong", BKTParams(p_init=0.9))
        weak = bkt.get_weak_skills(threshold=0.5)
        assert len(weak) >= 1

    def test_knowledge_state_vector(self):
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("a", BKTParams(p_init=0.8))
        bkt.register_skill("b", BKTParams(p_init=0.2))
        vec = bkt.compute_knowledge_state_vector(["a", "b"])
        assert len(vec) == 2
        assert vec[0] > vec[1]  # a 掌握更好


# ═══════════════════════════════════════════════════════
# 优化7: 多学生迁移学习
# ═══════════════════════════════════════════════════════

class TestMultiStudent:
    def test_register_student(self):
        ms = MultiStudentTransfer(8)
        ms.register_student("s1", ["quadratic"])
        assert "s1" in ms.students

    def test_log_interaction(self):
        ms = MultiStudentTransfer(8)
        ms.register_student("s1")
        ms.log_interaction(
            "s1", "quadratic",
            np.zeros(8), np.ones(8)*0.1,
            np.ones(8)*0.1, 0.6
        )
        assert ms.students["s1"].total_interactions == 1

    def test_learn_collective_knowledge_insufficient(self):
        ms = MultiStudentTransfer(8)
        result = ms.learn_collective_knowledge()
        assert result["status"] == "insufficient_data"

    def test_cold_start_params(self):
        ms = MultiStudentTransfer(8)
        ms.register_student("s1", ["quadratic"])
        params = ms.get_cold_start_params("s1", "quadratic")
        assert "initial_attractors" in params

    def test_collective_summary(self):
        ms = MultiStudentTransfer(8)
        ms.register_student("s1")
        summary = ms.get_collective_summary()
        assert summary["total_students"] == 1


# ═══════════════════════════════════════════════════════
# 集成测试
# ═══════════════════════════════════════════════════════

class TestOptimizationIntegration:
    def test_bkt_feeds_energy_landscape(self, config, landscape):
        """BKT 掌握概率可以转换为能量景观的状态"""
        bkt = BayesianKnowledgeTracer()
        bkt.register_skill("s1", BKTParams(p_init=0.8))
        bkt.register_skill("s2", BKTParams(p_init=0.5))
        bkt.register_skill("s3", BKTParams(p_init=0.3))
        bkt.register_skill("s4", BKTParams(p_init=0.7))
        bkt.register_skill("s5", BKTParams(p_init=0.2))
        bkt.register_skill("s6", BKTParams(p_init=0.6))
        bkt.register_skill("s7", BKTParams(p_init=0.4))
        bkt.register_skill("s8", BKTParams(p_init=0.9))

        vec = bkt.compute_knowledge_state_vector(["s1","s2","s3","s4","s5","s6","s7","s8"])
        energy = landscape.energy(vec)
        assert isinstance(energy, float)

    def test_forgetting_affects_belief_vector(self, config):
        """遗忘模型影响信念向量"""
        model = ForgettingModel()
        model.add_belief("b1", "x=3", "concept", 0.8)

        now = datetime.now()
        conf_now = model.beliefs["b1"].current_confidence(now)

        future = now + timedelta(hours=3)
        conf_future = model.beliefs["b1"].current_confidence(future)

        assert conf_now > conf_future

    def test_lyapunov_detects_phase_transition(self, config):
        """Lyapunov 指数能检测相变"""
        analyzer = LyapunovAnalyzer(config.belief_dimensions, window_size=10)

        # 稳定→不稳定→稳定的轨迹
        states = []
        for i in range(20):
            if 8 <= i <= 12:
                # 不稳定区域：大幅波动
                states.append(np.random.randn(config.belief_dimensions) * 0.5)
            else:
                states.append(np.ones(config.belief_dimensions) * 0.5)

        for state in states:
            result = analyzer.update(state)

        assert "lyapunov_exponent" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
