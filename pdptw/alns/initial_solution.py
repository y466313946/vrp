from __future__ import annotations

from pdptw.alns.feasibility import finalize_route
from pdptw.alns.insertion import apply_insertion_move, best_insertion_for_request
from pdptw.alns.instance import PreparedInstance
from pdptw.alns.state import RouteState, SolutionState


def build_initial_solution(prepared: PreparedInstance) -> SolutionState:
    """构造一个简单但可行的初始解。

    当前策略是按 pickup 的 ready time 排序，逐个请求做最优插入。
    如果现有路径无法容纳该请求，就新开一条路径。
    """

    snapshots = build_initial_solution_snapshots(prepared)
    return snapshots[-1]


def build_initial_solution_snapshots(prepared: PreparedInstance) -> list[SolutionState]:
    """记录初始解从空解到完整初始解的逐步构造过程。"""

    solution = SolutionState(
        routes=[],
        unserved_requests=set(prepared.requests),
    )
    snapshots = [solution.copy()]

    request_order = sorted(
        prepared.requests.values(),
        key=lambda request: (
            prepared.instance.nodes_by_id[request.pickup_id].ready_time,
            request.pickup_id,
        ),
    )

    for request in request_order:
        move = best_insertion_for_request(prepared, solution, request.request_id)
        if move is None:
            route = RouteState(node_ids=[0, request.pickup_id, request.delivery_id, 0])
            if not finalize_route(prepared, route):
                raise ValueError(f"Cannot build feasible initial route for request {request.request_id}")
            solution.routes.append(route)
            solution.unserved_requests.discard(request.request_id)
            _refresh_solution_metrics(prepared, solution)
            snapshots.append(solution.copy())
            continue

        apply_insertion_move(prepared, solution, move)
        _refresh_solution_metrics(prepared, solution)
        snapshots.append(solution.copy())

    return snapshots


def _refresh_solution_metrics(prepared: PreparedInstance, solution: SolutionState) -> None:
    """刷新解的派生统计量。

    该函数会：
    - 删除空路径
    - 重算每条路径的距离和时序信息
    - 更新解的总距离和车辆数
    """

    active_routes: list[RouteState] = []
    total_distance = 0.0
    for route in solution.routes:
        if route.node_ids == [0, 0]:
            continue
        finalize_route(prepared, route)
        active_routes.append(route)
        total_distance += route.distance

    solution.routes = active_routes
    solution.vehicle_count = len(active_routes)
    solution.total_distance = total_distance
