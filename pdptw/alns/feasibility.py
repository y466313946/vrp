from __future__ import annotations

from pdptw.alns.instance import PreparedInstance
from pdptw.alns.state import RouteEvaluation, RouteState, SolutionState


def evaluate_route(prepared: PreparedInstance, node_ids: list[int]) -> RouteEvaluation:
    """评估单条路径是否可行，并返回派生信息。

    这里统一检查：
    - 路径是否以仓库开始并回到仓库
    - 时间窗
    - pickup 必须先于 delivery
    - 容量约束
    """

    instance = prepared.instance
    if len(node_ids) < 2 or node_ids[0] != 0 or node_ids[-1] != 0:
        return RouteEvaluation(False, 0.0, [], [], [])

    visited_pickups: set[int] = set()
    loads: list[int] = []
    arrival_times: list[float] = []
    start_times: list[float] = []
    total_distance = 0.0
    current_time = 0.0
    current_load = 0

    for idx, node_id in enumerate(node_ids):
        node = instance.nodes_by_id[node_id]

        if idx == 0:
            arrival = 0.0
        else:
            prev_id = node_ids[idx - 1]
            travel = prepared.distance_matrix[prev_id][node_id]
            total_distance += travel
            arrival = current_time + travel

        start = max(arrival, float(node.ready_time))
        if start > node.due_time:
            return RouteEvaluation(False, 0.0, [], [], [])

        # delivery 点出现时，其对应 pickup 必须已经在当前路径前缀中访问过。
        if node.is_delivery and node.pickup_id not in visited_pickups:
            return RouteEvaluation(False, 0.0, [], [], [])

        current_load += node.demand
        if current_load < 0 or current_load > prepared.vehicle_capacity:
            return RouteEvaluation(False, 0.0, [], [], [])

        if node.is_pickup:
            visited_pickups.add(node.node_id)

        current_time = start + node.service_time
        loads.append(current_load)
        arrival_times.append(arrival)
        start_times.append(start)

    return RouteEvaluation(True, total_distance, loads, arrival_times, start_times)


def finalize_route(prepared: PreparedInstance, route: RouteState) -> bool:
    """把评估结果回填到 `RouteState`。"""

    evaluation = evaluate_route(prepared, route.node_ids)
    if not evaluation.feasible:
        return False

    route.distance = evaluation.distance
    route.loads = evaluation.loads
    route.arrival_times = evaluation.arrival_times
    route.start_times = evaluation.start_times
    return True


def is_solution_feasible(prepared: PreparedInstance, solution: SolutionState) -> bool:
    """检查整个解的全局可行性。"""

    assigned_requests: set[int] = set()
    instance = prepared.instance

    for route in solution.routes:
        evaluation = evaluate_route(prepared, route.node_ids)
        if not evaluation.feasible:
            return False

        route_pickups: set[int] = set()
        route_deliveries: set[int] = set()
        for node_id in route.node_ids:
            if node_id == 0:
                continue
            node = instance.nodes_by_id[node_id]
            if node.is_pickup:
                route_pickups.add(node_id)
            if node.is_delivery:
                route_deliveries.add(node.pickup_id)

        # 同一路径中，pickup 集和 delivery 对应的 pickup 集必须完全一致，
        # 这等价于“同一请求的 pickup / delivery 在同一路径中都出现且都只出现一次”。
        if route_pickups != route_deliveries:
            return False

        overlap = assigned_requests.intersection(route_pickups)
        if overlap:
            return False
        assigned_requests.update(route_pickups)

    all_requests = set(prepared.requests)
    return assigned_requests.union(solution.unserved_requests) == all_requests
