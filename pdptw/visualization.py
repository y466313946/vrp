from __future__ import annotations

from pathlib import Path

from pdptw.alns.state import ALNSResult, SolutionState
from pdptw.models import PDPTWInstance


def plot_solution(
    instance: PDPTWInstance,
    solution: SolutionState,
    output_path: str | None = None,
    show: bool = True,
) -> None:
    """可视化给定解的车辆路径。"""

    try:
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError("Visualization requires matplotlib. Please install it with `pip install matplotlib`.") from exc

    fig, ax = plt.subplots(figsize=(10, 8))
    depot = instance.depot
    pickup_nodes = [node for node in instance.nodes if node.is_pickup]
    delivery_nodes = [node for node in instance.nodes if node.is_delivery]
    route_count = max(1, len(solution.routes))
    cmap = plt.get_cmap("tab20", route_count)

    for index, route in enumerate(solution.routes):
        if len(route.node_ids) < 2:
            continue
        color = cmap(index % cmap.N)
        x_coords = [instance.nodes_by_id[node_id].x for node_id in route.node_ids]
        y_coords = [instance.nodes_by_id[node_id].y for node_id in route.node_ids]
        ax.plot(
            x_coords,
            y_coords,
            marker="o",
            linewidth=1.8,
            markersize=4,
            color=color,
            alpha=0.9,
            label=f"Route {index + 1}",
        )

    ax.scatter(
        [node.x for node in pickup_nodes],
        [node.y for node in pickup_nodes],
        c="tab:blue",
        s=32,
        marker="^",
        label="Pickup",
        zorder=3,
    )
    ax.scatter(
        [node.x for node in delivery_nodes],
        [node.y for node in delivery_nodes],
        c="tab:orange",
        s=32,
        marker="s",
        label="Delivery",
        zorder=3,
    )
    ax.scatter([depot.x], [depot.y], c="red", s=120, marker="*", label="Depot", zorder=4)

    # 小规模实例时标注节点编号，避免图面过于拥挤。
    if instance.size <= 100:
        for node in instance.nodes:
            ax.text(node.x + 0.5, node.y + 0.5, str(node.node_id), fontsize=7, alpha=0.75)

    ax.set_title(f"ALNS Solution Visualization: {instance.name}")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.4)
    ax.legend(loc="best")
    ax.set_aspect("equal", adjustable="box")
    fig.tight_layout()

    if output_path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output, dpi=200, bbox_inches="tight")
        print(f"plot_saved: {output}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def plot_alns_result(
    instance: PDPTWInstance,
    result: ALNSResult,
    output_path: str | None = None,
    show: bool = True,
) -> None:
    """可视化 ALNS 求解结果中的最优解。"""

    plot_solution(instance, result.best_solution, output_path=output_path, show=show)
