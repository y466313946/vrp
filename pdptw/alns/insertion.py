from __future__ import annotations

from pdptw.alns.feasibility import evaluate_route, finalize_route
from pdptw.alns.instance import PreparedInstance
from pdptw.alns.state import InsertionMove, RouteState, SolutionState


def build_empty_route() -> RouteState:
    """构造空路径，形式固定为 `[0, 0]`。"""

    return RouteState(node_ids=[0, 0])


def best_insertion_for_request(
    prepared: PreparedInstance,
    solution: SolutionState,
    request_id: int,
) -> InsertionMove | None:
    """返回某个请求的最优插入动作。"""

    moves = enumerate_insertion_moves(prepared, solution, request_id)
    return min(moves, key=lambda move: move.delta_distance) if moves else None


def enumerate_insertion_moves(
    prepared: PreparedInstance,
    solution: SolutionState,
    request_id: int,
) -> list[InsertionMove]:
    """枚举一个请求的全部可行插入位置。

    对每条路径同时枚举：
    - pickup 的插入位置
    - delivery 在 pickup 之后的插入位置
    """

    request = prepared.requests[request_id]
    moves: list[InsertionMove] = []

    candidate_route_count = len(solution.routes) + 1
    for route_index in range(candidate_route_count):
        route = solution.routes[route_index] if route_index < len(solution.routes) else build_empty_route()
        baseline_distance = route.distance if route_index < len(solution.routes) else 0.0
        node_ids = route.node_ids

        for pickup_position in range(1, len(node_ids)):
            pickup_route = node_ids[:pickup_position] + [request.pickup_id] + node_ids[pickup_position:]
            for delivery_position in range(pickup_position + 1, len(pickup_route)):
                trial = pickup_route[:delivery_position] + [request.delivery_id] + pickup_route[delivery_position:]
                evaluation = evaluate_route(prepared, trial)
                if not evaluation.feasible:
                    continue

                # 插入评估采用增量距离作为局部成本。
                delta_distance = evaluation.distance - baseline_distance
                move = InsertionMove(
                    request_id=request_id,
                    route_index=route_index,
                    pickup_position=pickup_position,
                    delivery_position=delivery_position,
                    delta_distance=delta_distance,
                )
                moves.append(move)

    return moves


def apply_insertion_move(
    prepared: PreparedInstance,
    solution: SolutionState,
    move: InsertionMove,
) -> None:
    """把一个插入动作真正应用到解上。"""

    request = prepared.requests[move.request_id]

    if move.route_index == len(solution.routes):
        solution.routes.append(build_empty_route())

    route = solution.routes[move.route_index]
    route.node_ids.insert(move.pickup_position, request.pickup_id)
    route.node_ids.insert(move.delivery_position, request.delivery_id)
    finalize_route(prepared, route)
    solution.unserved_requests.discard(move.request_id)


def remove_request_from_route(route: RouteState, pickup_id: int, delivery_id: int) -> bool:
    """从一条路径里删除某个请求对应的 pickup / delivery 节点。"""

    changed = False
    if pickup_id in route.node_ids:
        route.node_ids.remove(pickup_id)
        changed = True
    if delivery_id in route.node_ids:
        route.node_ids.remove(delivery_id)
        changed = True
    return changed
