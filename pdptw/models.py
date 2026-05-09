from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PDPTWReadConfig:
    """控制数据读取范围的配置。

    - 不传 `size` / `case_name`：读取全部实例
    - 只传 `size`：读取某个规模目录下的全部实例
    - 同时传 `size` 和 `case_name`：读取该规模下的单个实例
    - 只传 `case_name`：跨规模搜索该实例名
    """

    dataset_dir: Path = Path("data/PDPTW")
    size: int | None = None
    case_name: str | None = None
    include_solution: bool = True


@dataclass(frozen=True)
class PDPTWNode:
    """单个节点的数据结构。

    这里的节点既可能是仓库，也可能是 pickup / delivery 点。
    读取阶段已经把一些常用判断结果预先算好，方便后续算法直接使用。
    """

    node_id: int
    x: int
    y: int
    demand: int
    ready_time: int
    due_time: int
    service_time: int
    pickup_id: int
    delivery_id: int
    is_depot: bool
    is_pickup: bool
    is_delivery: bool
    pair_id: int | None


@dataclass(frozen=True)
class PDPTWSolution:
    """`.sol` 文件中的参考解。

    这里只保留原始路线序列和少量元信息，不在这一层做可行性或距离评估。
    """

    instance_name: str
    authors: str | None
    date: str | None
    reference: str | None
    routes: list[list[int]]


@dataclass(frozen=True)
class PDPTWInstance:
    """单个 PDPTW 实例。

    这个对象聚合了：
    - 基础实例参数
    - 节点列表
    - 节点索引字典
    - 可选的参考解
    """

    name: str
    size: int
    vehicle_count: int
    vehicle_capacity: int
    vehicle_speed: int
    txt_path: Path
    sol_path: Path | None
    nodes: list[PDPTWNode]
    nodes_by_id: dict[int, PDPTWNode]
    solution: PDPTWSolution | None

    @property
    def request_count(self) -> int:
        """请求数等于 pickup 点数量。"""
        return sum(1 for node in self.nodes if node.is_pickup)

    @property
    def depot(self) -> PDPTWNode:
        """返回仓库节点，默认编号为 0。"""
        return self.nodes_by_id[0]


@dataclass(frozen=True)
class PDPTWDataset:
    """读取结果集合。

    即便只读取一个 case，也统一返回列表形式，方便后续批处理实验复用同一接口。
    """

    dataset_dir: Path
    config: PDPTWReadConfig
    instances: list[PDPTWInstance] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.instances)

    def is_empty(self) -> bool:
        return not self.instances
