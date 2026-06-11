"""
CPTE 认知相变引擎 — 超参数配置
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CPTEConfig:
    """CPTE 算法超参数"""

    # ── 信念空间维度 ──────────────────────────────────────
    belief_dimensions: int = 16          # 信念向量维度 N
    belief_range: tuple = (-1.0, 1.0)    # 信念值范围

    # ── 能量景观参数 ──────────────────────────────────────
    coupling_strength: float = 0.5       # J: 信念间耦合强度
    field_strength: float = 1.0          # h: 外部场强度
    attractor_depth: float = 3.0         # D: 误解吸引子默认深度
    attractor_width: float = 0.5         # σ: 误解吸引子默认宽度

    # ── 动力学参数 ──────────────────────────────────────
    damping: float = 0.8                 # γ: 阻尼系数（趋向低能量态的速度）
    temperature: float = 0.3             # T: 认知温度（探索性噪声强度）
    dt: float = 0.05                     # 仿真时间步长
    max_steps: int = 200                 # 单次仿真最大步数

    # ── 相变检测参数 ──────────────────────────────────────
    susceptibility_threshold: float = 2.0   # χ 阈值：超过此值判定为临界点
    order_param_window: int = 10             # 序参数滑动窗口大小
    critical_cooldown: int = 5               # 两次相变检测之间的最小间隔步数

    # ── 能量壁垒参数 ──────────────────────────────────────
    barrier_path_samples: int = 20       # 路径采样点数（找鞍点）
    escape_temperature: float = 1.0      # 逃逸概率计算的等效温度

    # ── 追问力场参数 ──────────────────────────────────────
    force_gradient_weight: float = 0.6   # λ_grad: 能量下降方向权重
    force_target_weight: float = 0.4     # λ_target: 指向正确理解方向权重
    force_magnitude_limit: float = 2.0   # 力的大小上限

    # ── 自优化参数 ──────────────────────────────────────
    adaptation_rate: float = 0.1         # α: 参数自适应学习率
    min_adaptation_samples: int = 5      # 最少多少轮对话后才开始自适应
    attractor_discovery_eps: float = 0.3 # DBSCAN 聚类半径
    attractor_discovery_min: int = 3     # DBSCAN 最小样本数
    exploration_decay: float = 0.995     # 探索权重衰减因子

    # ── LLM 参数 ──────────────────────────────────────
    llm_temperature_belief: float = 0.3  # 信念提取的 LLM 温度
    llm_temperature_question: float = 0.7  # 追问生成的 LLM 温度

    # ── 仿真参数 ──────────────────────────────────────
    simulation_runs: int = 10            # 蒙特卡洛仿真次数（取平均）
    prediction_horizon: int = 50         # 预测学生未来状态的步数


# 全局默认配置
DEFAULT_CONFIG = CPTEConfig()
