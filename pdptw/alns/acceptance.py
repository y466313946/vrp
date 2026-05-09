from __future__ import annotations

import math
import random

from pdptw.alns.config import ALNSConfig
from pdptw.alns.objective import scalar_cost
from pdptw.alns.state import SolutionState


def accept_solution(
    current: SolutionState,
    candidate: SolutionState,
    config: ALNSConfig,
    temperature: float,
    rng: random.Random,
) -> bool:
    """模拟退火接受准则。

    - 候选解更好：直接接受
    - 候选解更差：按温度和成本差计算概率接受
    """

    current_cost = scalar_cost(current, config)
    candidate_cost = scalar_cost(candidate, config)
    if candidate_cost <= current_cost:
        return True

    if temperature <= 0:
        return False

    probability = math.exp((current_cost - candidate_cost) / temperature)
    return rng.random() < probability
