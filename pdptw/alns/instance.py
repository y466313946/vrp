from __future__ import annotations

import math
from dataclasses import dataclass

from pdptw.models import PDPTWInstance
from pdptw.alns.state import Request


@dataclass(frozen=True)
class PreparedInstance:
    """供 ALNS 反复访问的实例预处理结果。

    把节点级原始实例转换成两类更适合启发式算法的结构：
    - `requests`：以 pickup-delivery 对为中心的请求表示
    - `distance_matrix`：任意两点间欧氏距离
    """

    instance: PDPTWInstance
    requests: dict[int, Request]
    distance_matrix: dict[int, dict[int, float]]

    @property
    def vehicle_capacity(self) -> int:
        return self.instance.vehicle_capacity

    @property
    def depot_id(self) -> int:
        return 0


def prepare_instance(instance: PDPTWInstance) -> PreparedInstance:
    """从原始实例构建 ALNS 需要的预处理信息。"""

    requests: dict[int, Request] = {}
    for node in instance.nodes:
        if not node.is_pickup:
            continue
        # 这里把每个请求用 pickup 节点编号作为 request_id。
        requests[node.node_id] = Request(
            request_id=node.node_id,
            pickup_id=node.node_id,
            delivery_id=node.delivery_id,
            demand=node.demand,
        )

    distance_matrix: dict[int, dict[int, float]] = {}
    for node_i in instance.nodes:
        distance_matrix[node_i.node_id] = {}
        for node_j in instance.nodes:
            # Li & Lim 的标准做法是使用欧氏距离，并令旅行时间等于距离。
            dx = node_i.x - node_j.x
            dy = node_i.y - node_j.y
            distance_matrix[node_i.node_id][node_j.node_id] = math.hypot(dx, dy)

    return PreparedInstance(
        instance=instance,
        requests=requests,
        distance_matrix=distance_matrix,
    )
