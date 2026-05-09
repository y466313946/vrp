from __future__ import annotations

from dataclasses import dataclass

from pdptw.models import PDPTWInstance, PDPTWSolution
from pdptw.alns.feasibility import finalize_route, is_solution_feasible
from pdptw.alns.initial_solution import _refresh_solution_metrics
from pdptw.alns.instance import prepare_instance
from pdptw.alns.state import RouteState, SolutionState


@dataclass(frozen=True)
class SolutionMetrics:
    """用于展示和对比的解指标。"""

    vehicle_count: int
    total_distance: float
    feasible: bool

    @property
    def objective(self) -> tuple[int, float]:
        return self.vehicle_count, self.total_distance


def evaluate_solution_state(instance: PDPTWInstance, solution: SolutionState) -> SolutionMetrics:
    """评估算法产生的解。"""

    prepared = prepare_instance(instance)
    candidate = solution.copy()
    _refresh_solution_metrics(prepared, candidate)
    feasible = is_solution_feasible(prepared, candidate) and not candidate.unserved_requests
    return SolutionMetrics(
        vehicle_count=candidate.vehicle_count,
        total_distance=candidate.total_distance,
        feasible=feasible,
    )


def evaluate_reference_solution(instance: PDPTWInstance) -> SolutionMetrics | None:
    """评估实例自带 `.sol` 参考解。"""

    if instance.solution is None:
        return None

    prepared = prepare_instance(instance)
    reference_state = solution_file_to_state(instance, instance.solution)
    _refresh_solution_metrics(prepared, reference_state)
    feasible = is_solution_feasible(prepared, reference_state) and not reference_state.unserved_requests
    return SolutionMetrics(
        vehicle_count=reference_state.vehicle_count,
        total_distance=reference_state.total_distance,
        feasible=feasible,
    )


def solution_file_to_state(instance: PDPTWInstance, solution_file: PDPTWSolution) -> SolutionState:
    """把 `.sol` 文件中的路径序列转换成统一解结构。"""

    prepared = prepare_instance(instance)
    routes: list[RouteState] = []
    served_requests: set[int] = set()

    for route_nodes in solution_file.routes:
        # `.sol` 中通常不显式写仓库，这里补上起终点仓库 0。
        route = RouteState(node_ids=[0, *route_nodes, 0])
        if not finalize_route(prepared, route):
            routes.append(route)
            continue
        routes.append(route)
        for node_id in route_nodes:
            node = instance.nodes_by_id[node_id]
            if node.is_pickup:
                served_requests.add(node_id)

    unserved = set(prepared.requests) - served_requests
    return SolutionState(routes=routes, unserved_requests=unserved)
