"""
CPTE — Cognitive Phase Transition Engine (v2.0 Ultra)
认知相变引擎 — 最强版
"""

from .config import CPTEConfig, DEFAULT_CONFIG
from .belief_vector import BeliefVector, BeliefDimensionMapper
from .energy_landscape import EnergyLandscape, Attractor
from .dynamics_engine import DynamicsEngine, SimulationResult
from .phase_detector import PhaseDetector
from .barrier_calculator import BarrierCalculator
from .escape_planner import EscapePlanner
from .force_optimizer import ForceOptimizer
from .self_optimizer import SelfOptimizer, ConversationRecord
from .knowledge_adapter import KnowledgeAdapter
from .manager import CPTEManager

# 七大优化模块
from .embedding import SemanticEmbedder, get_embedder
from .forgetting import ForgettingModel, ForgettableBelief
from .dynamic_landscape import DynamicLandscapeUpdater
from .transfer import CrossTopicTransfer
from .lyapunov import LyapunovAnalyzer
from .bkt import BayesianKnowledgeTracer, BKTParams, BKTSkill
from .multi_student import MultiStudentTransfer, StudentProfile

__version__ = "2.0.0"
__all__ = [
    "CPTEConfig", "DEFAULT_CONFIG",
    "BeliefVector", "BeliefDimensionMapper",
    "EnergyLandscape", "Attractor",
    "DynamicsEngine", "SimulationResult",
    "PhaseDetector", "BarrierCalculator",
    "EscapePlanner", "ForceOptimizer",
    "SelfOptimizer", "ConversationRecord",
    "KnowledgeAdapter", "CPTEManager",
    # 优化模块
    "SemanticEmbedder", "get_embedder",
    "ForgettingModel", "ForgettableBelief",
    "DynamicLandscapeUpdater",
    "CrossTopicTransfer",
    "LyapunovAnalyzer",
    "BayesianKnowledgeTracer", "BKTParams", "BKTSkill",
    "MultiStudentTransfer", "StudentProfile",
]
