from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Request:
    """以请求为中心的表示。

    ALNS 的 destroy / repair 通常按“请求”操作，而不是按单个节点操作。
    对于 PDPTW，一个请求对应一个 pickup 节点和一个 delivery 节点。
    """

    request_id: int
    pickup_id: int
    delivery_id: int
    demand: int


@dataclass
class RouteState:
    """一条车辆路径的当前状态。

    `node_ids` 中显式保留起终点仓库 `0`，例如 `[0, ..., 0]`，
    这样距离、时间窗和容量检查都更统一。
    """

    node_ids: list[int]
    distance: float = 0.0
    loads: list[int] = field(default_factory=list)
    arrival_times: list[float] = field(default_factory=list)
    start_times: list[float] = field(default_factory=list)

    def copy(self) -> "RouteState":
        return RouteState(
            node_ids=list(self.node_ids),
            distance=self.distance,
            loads=list(self.loads),
            arrival_times=list(self.arrival_times),
            start_times=list(self.start_times),
        )


@dataclass
class SolutionState:
    """整个解的状态。

    第一版实现只在可行解空间中搜索，因此 `unserved_requests`
    主要出现在 destroy 之后、repair 完成之前的中间阶段。
    """

    routes: list[RouteState]
    unserved_requests: set[int] = field(default_factory=set)
    total_distance: float = 0.0
    vehicle_count: int = 0

    def copy(self) -> "SolutionState":
        return SolutionState(
            routes=[route.copy() for route in self.routes],
            unserved_requests=set(self.unserved_requests),
            total_distance=self.total_distance,
            vehicle_count=self.vehicle_count,
        )

    @property
    def objective(self) -> tuple[int, float]:
        """层级目标：先比车辆数，再比总距离。"""
        return self.vehicle_count, self.total_distance


@dataclass(frozen=True)
class InsertionMove:
    """把一个请求插入某条路径的候选动作。"""

    request_id: int
    route_index: int
    pickup_position: int
    delivery_position: int
    delta_distance: float


@dataclass(frozen=True)
class RouteEvaluation:
    """单条路径的评估结果。"""

    feasible: bool
    distance: float
    loads: list[int]
    arrival_times: list[float]
    start_times: list[float]


@dataclass(frozen=True)
class ALNSResult:
    """求解器输出。"""

    best_solution: SolutionState
    best_iteration: int
    iterations: int
    runtime_seconds: float
