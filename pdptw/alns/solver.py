from __future__ import annotations

import math
import random

from pdptw.models import PDPTWInstance
from pdptw.alns.acceptance import accept_solution
from pdptw.alns.config import ALNSConfig
from pdptw.alns.feasibility import is_solution_feasible
from pdptw.alns.initial_solution import build_initial_solution
from pdptw.alns.instance import prepare_instance
from pdptw.alns.objective import is_better
from pdptw.alns.operators_destroy import RandomRequestRemoval, WorstRequestRemoval
from pdptw.alns.operators_repair import GreedyInsertionRepair, Regret2InsertionRepair
from pdptw.alns.selection import AdaptiveOperatorSelector
from pdptw.alns.state import ALNSResult, SolutionState


class PDPTWALNS:
    """PDPTW 的 ALNS 基线求解器。

    当前版本采用：
    - destroy: random / worst
    - repair: greedy / regret-2
    - acceptance: simulated annealing
    - operator selection: adaptive roulette wheel
    """

    def __init__(self, config: ALNSConfig | None = None) -> None:
        self.config = config or ALNSConfig()
        self.rng = random.Random(self.config.random_seed)
        self.destroy_operators = [
            RandomRequestRemoval(),
            WorstRequestRemoval(),
        ]
        self.repair_operators = [
            GreedyInsertionRepair(),
            Regret2InsertionRepair(),
        ]
        self.selector = AdaptiveOperatorSelector(self.destroy_operators, self.repair_operators, self.config)

    def solve(self, instance: PDPTWInstance) -> ALNSResult:
        """运行主搜索循环。"""

        prepared = prepare_instance(instance)
        current = build_initial_solution(prepared)
        best = current.copy()
        best_iteration = 0
        no_improve_counter = 0

        temperature = self._initial_temperature(current)

        for iteration in range(1, self.config.max_iterations + 1):
            # 1) 选择 destroy / repair 算子
            destroy = self.selector.select_destroy(self.rng)
            repair = self.selector.select_repair(self.rng)
            num_remove = self._sample_num_remove(len(prepared.requests))

            # 2) 先破坏，再修复
            destroyed = destroy.apply(prepared, current, num_remove, self.rng)
            candidate = repair.apply(prepared, destroyed.partial_solution, destroyed.removed_requests, self.rng)

            # 3) repair 后如果还有未插回的请求，或整体不可行，则直接判为 rejected
            if candidate.unserved_requests or not is_solution_feasible(prepared, candidate):
                self.selector.reward(destroy.name, repair.name, "rejected")
            else:
                # 4) 用模拟退火决定是否接受候选解
                accepted = accept_solution(current, candidate, self.config, temperature, self.rng)
                outcome = "rejected"
                if accepted:
                    previous_objective = current.objective
                    current = candidate
                    outcome = "accepted"
                    if is_better(candidate.objective, previous_objective):
                        outcome = "improved"
                    if is_better(candidate.objective, best.objective):
                        best = candidate.copy()
                        best_iteration = iteration
                        no_improve_counter = 0
                        outcome = "global_best"
                    else:
                        no_improve_counter += 1
                else:
                    no_improve_counter += 1
                self.selector.reward(destroy.name, repair.name, outcome)

            # 5) 每个 segment 更新一次算子权重
            if iteration % self.config.segment_length == 0:
                self.selector.update_weights()

            temperature = max(self.config.min_temperature, temperature * self.config.cooling_rate)
            if no_improve_counter >= self.config.no_improve_limit:
                return ALNSResult(best_solution=best, best_iteration=best_iteration, iterations=iteration)

        return ALNSResult(
            best_solution=best,
            best_iteration=best_iteration,
            iterations=self.config.max_iterations,
        )

    def _initial_temperature(self, solution: SolutionState) -> float:
        """如果用户没有显式设置温度，则按初始解规模给一个经验值。"""

        if self.config.initial_temperature is not None:
            return self.config.initial_temperature
        return max(1.0, solution.total_distance * 0.05 + solution.vehicle_count * math.sqrt(self.config.vehicle_penalty))

    def _sample_num_remove(self, request_count: int) -> int:
        """按配置的移除比例随机采样本轮 destroy 的请求数。"""

        lower = max(1, int(request_count * self.config.destroy_fraction_min))
        upper = max(lower, int(request_count * self.config.destroy_fraction_max))
        return self.rng.randint(lower, upper)
