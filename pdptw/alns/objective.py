from __future__ import annotations

from pdptw.alns.config import ALNSConfig
from pdptw.alns.state import SolutionState


def is_better(lhs: tuple[int, float], rhs: tuple[int, float]) -> bool:
    """按 Li & Lim 常见层级目标比较两个解。

    Python 元组按字典序比较，因此 `(车辆数, 距离)` 正好能表达：
    1. 优先少车
    2. 同车数下再比总距离
    """

    return lhs < rhs


def scalar_cost(solution: SolutionState, config: ALNSConfig) -> float:
    """把层级目标压成一个标量，用于模拟退火接受准则。

    注意：真正判断“谁更优”仍建议用 `is_better`。
    这个标量主要用于在 SA 中计算差值和接受概率。
    """

    return solution.vehicle_count * config.vehicle_penalty + solution.total_distance
