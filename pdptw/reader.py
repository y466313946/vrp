from __future__ import annotations

from pathlib import Path

from pdptw.models import (
    PDPTWInstance,
    PDPTWNode,
    PDPTWReadConfig,
    PDPTWDataset,
    PDPTWSolution,
)


def read_pdptw(config: PDPTWReadConfig | None = None) -> PDPTWDataset:
    """按配置读取 PDPTW 数据集。

    这是对外的统一入口，会根据配置收集目标 `.txt` 文件，
    然后逐个解析为 `PDPTWInstance`。
    """

    config = config or PDPTWReadConfig()
    dataset_dir = Path(config.dataset_dir)

    if not dataset_dir.exists():
        raise FileNotFoundError(f"PDPTW dataset directory not found: {dataset_dir}")

    candidate_txt_files = _collect_txt_files(dataset_dir, config)
    instances = [_read_instance(txt_path, config.include_solution) for txt_path in candidate_txt_files]
    instances.sort(key=lambda instance: (instance.size, instance.name))

    return PDPTWDataset(
        dataset_dir=dataset_dir,
        config=config,
        instances=instances,
    )


def _collect_txt_files(dataset_dir: Path, config: PDPTWReadConfig) -> list[Path]:
    """根据读取配置收集目标实例文件。"""

    if config.case_name and config.size is None:
        # 允许只给实例名，跨规模目录搜索。
        matches = sorted(dataset_dir.glob(f"*/{config.case_name}.txt"))
        if not matches:
            raise FileNotFoundError(f"Case not found under any size directory: {config.case_name}")
        return matches

    target_dirs = [dataset_dir / str(config.size)] if config.size is not None else sorted(
        path for path in dataset_dir.iterdir() if path.is_dir() and path.name.isdigit()
    )

    missing_dirs = [path for path in target_dirs if not path.exists()]
    if missing_dirs:
        missing = ", ".join(str(path) for path in missing_dirs)
        raise FileNotFoundError(f"PDPTW size directory not found: {missing}")

    txt_files: list[Path] = []
    for target_dir in target_dirs:
        if config.case_name:
            case_path = target_dir / f"{config.case_name}.txt"
            if not case_path.exists():
                raise FileNotFoundError(f"Case not found: {case_path}")
            txt_files.append(case_path)
            continue

        txt_files.extend(sorted(target_dir.glob("*.txt")))

    return txt_files


def _read_instance(txt_path: Path, include_solution: bool) -> PDPTWInstance:
    """把单个 `.txt` 实例文件解析为统一数据结构。"""

    lines = [line.strip() for line in txt_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    header = [int(value) for value in lines[0].split()]
    vehicle_count, vehicle_capacity, vehicle_speed = header

    nodes: list[PDPTWNode] = []
    for raw_line in lines[1:]:
        values = [int(value) for value in raw_line.split()]
        node_id, x, y, demand, ready_time, due_time, service_time, pickup_id, delivery_id = values

        # Li & Lim 数据中：
        # - delivery_id != 0 表示当前点是 pickup
        # - pickup_id != 0 表示当前点是 delivery
        is_depot = node_id == 0
        is_pickup = delivery_id != 0
        is_delivery = pickup_id != 0
        pair_id = delivery_id or pickup_id or None

        nodes.append(
            PDPTWNode(
                node_id=node_id,
                x=x,
                y=y,
                demand=demand,
                ready_time=ready_time,
                due_time=due_time,
                service_time=service_time,
                pickup_id=pickup_id,
                delivery_id=delivery_id,
                is_depot=is_depot,
                is_pickup=is_pickup,
                is_delivery=is_delivery,
                pair_id=pair_id,
            )
        )

    nodes_by_id = {node.node_id: node for node in nodes}
    sol_path = txt_path.with_suffix(".sol")
    solution = _read_solution(sol_path) if include_solution and sol_path.exists() else None

    return PDPTWInstance(
        name=txt_path.stem,
        size=int(txt_path.parent.name),
        vehicle_count=vehicle_count,
        vehicle_capacity=vehicle_capacity,
        vehicle_speed=vehicle_speed,
        txt_path=txt_path,
        sol_path=sol_path if sol_path.exists() else None,
        nodes=nodes,
        nodes_by_id=nodes_by_id,
        solution=solution,
    )


def _read_solution(sol_path: Path) -> PDPTWSolution:
    """解析 `.sol` 参考解文件。"""

    authors: str | None = None
    date: str | None = None
    reference: str | None = None
    instance_name: str | None = None
    routes: list[list[int]] = []

    for raw_line in sol_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("Instance name"):
            instance_name = line.split(":", maxsplit=1)[1].strip()
        elif line.startswith("Authors"):
            authors = line.split(":", maxsplit=1)[1].strip()
        elif line.startswith("Date"):
            date = line.split(":", maxsplit=1)[1].strip()
        elif line.startswith("Reference"):
            reference = line.split(":", maxsplit=1)[1].strip()
        elif line.startswith("Route"):
            route_text = line.split(":", maxsplit=1)[1].strip()
            routes.append([int(value) for value in route_text.split()])

    if instance_name is None:
        raise ValueError(f"Invalid solution file, missing instance name: {sol_path}")

    return PDPTWSolution(
        instance_name=instance_name,
        authors=authors,
        date=date,
        reference=reference,
        routes=routes,
    )
