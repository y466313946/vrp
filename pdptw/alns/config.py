from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ALNSConfig:
    """ALNS 求解器配置。

    第一版实现主要保留了最常用的参数：
    - 迭代与提前停止
    - 每轮移除比例
    - 算子自适应权重更新
    - 模拟退火接受准则
    - 把“车辆数优先”编码进标量成本的惩罚系数
    """

    max_iterations: int = 500
    no_improve_limit: int = 150
    segment_length: int = 25
    destroy_fraction_min: float = 0.1
    destroy_fraction_max: float = 0.3
    reaction_factor: float = 0.2
    score_global_best: float = 8.0
    score_improved: float = 4.0
    score_accepted: float = 1.5
    score_rejected: float = 0.5
    initial_temperature: float | None = None
    cooling_rate: float = 0.995
    min_temperature: float = 1e-4
    vehicle_penalty: float = 1_000_000.0
    random_seed: int | None = None
