from __future__ import annotations

import random
from dataclasses import dataclass

from pdptw.alns.feasibility import finalize_route
from pdptw.alns.initial_solution import _refresh_solution_metrics
from pdptw.alns.insertion import remove_request_from_route
from pdptw.alns.instance import PreparedInstance
from pdptw.alns.state import SolutionState


@dataclass(frozen=True)
class DestroyOutcome:
    """destroy 算子的输出。"""

    partial_solution: SolutionState
    removed_requests: list[int]


class DestroyOperator:
    """destroy 算子基类。"""

    name: str

    def apply(
        self,
        prepared: PreparedInstance,
        solution: SolutionState,
        num_remove: int,
        rng: random.Random,
    ) -> DestroyOutcome:
        raise NotImplementedError


class RandomRequestRemoval(DestroyOperator):
    """随机移除若干请求。"""

    name = "random_request_removal"

    def apply(
        self,
        prepared: PreparedInstance,
        solution: SolutionState,
        num_remove: int,
        rng: random.Random,
    ) -> DestroyOutcome:
        partial = solution.copy()
        removable = _collect_served_requests(prepared, partial)
        removed = rng.sample(removable, k=min(num_remove, len(removable)))
        _remove_requests(prepared, partial, removed)
        return DestroyOutcome(partial_solution=partial, removed_requests=removed)


class WorstRequestRemoval(DestroyOperator):
    """移除“删掉后最省距离”的请求。"""

    name = "worst_request_removal"

    def apply(
        self,
        prepared: PreparedInstance,
        solution: SolutionState,
        num_remove: int,
        rng: random.Random,
    ) -> DestroyOutcome:
        partial = solution.copy()
        scored_requests: list[tuple[float, int]] = []
        for request_id in _collect_served_requests(prepared, partial):
            saving = _estimate_removal_saving(prepared, partial, request_id)
            scored_requests.append((saving, request_id))

        scored_requests.sort(reverse=True)
        removed = [request_id for _, request_id in scored_requests[:num_remove]]
        _remove_requests(prepared, partial, removed)
        return DestroyOutcome(partial_solution=partial, removed_requests=removed)


def _collect_served_requests(prepared: PreparedInstance, solution: SolutionState) -> list[int]:
    """收集当前已被服务的请求。"""

    served = set(prepared.requests) - solution.unserved_requests
    return sorted(served)


def _estimate_removal_saving(prepared: PreparedInstance, solution: SolutionState, request_id: int) -> float:
    """估计移除一个请求后带来的距离节省。"""

    request = prepared.requests[request_id]
    best_saving = 0.0
    for route in solution.routes:
        if request.pickup_id not in route.node_ids:
            continue

        before = route.distance
        route_copy = route.copy()
        remove_request_from_route(route_copy, request.pickup_id, request.delivery_id)
        if route_copy.node_ids == [0, 0]:
            after = 0.0
        else:
            feasible = finalize_route(prepared, route_copy)
            after = route_copy.distance if feasible else before
        best_saving = max(best_saving, before - after)
        break
    return best_saving


def _remove_requests(prepared: PreparedInstance, solution: SolutionState, request_ids: list[int]) -> None:
    """真正从解里移除若干请求，并刷新解统计量。"""

    for request_id in request_ids:
        request = prepared.requests[request_id]
        for route in solution.routes:
            if remove_request_from_route(route, request.pickup_id, request.delivery_id):
                if route.node_ids != [0, 0]:
                    finalize_route(prepared, route)
                break
        solution.unserved_requests.add(request_id)

    _refresh_solution_metrics(prepared, solution)
