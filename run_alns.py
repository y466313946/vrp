from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import TypedDict

from pdptw import (
    ALNSConfig,
    ALNSResult,
    PDPTWALNS,
    PDPTWReadConfig,
    animate_solution_snapshots,
    build_initial_solution_snapshots,
    plot_alns_result,
    plot_solution,
    read_pdptw,
)
from pdptw.alns.evaluation import evaluate_reference_solution, evaluate_solution_state, solution_file_to_state
from pdptw.alns.instance import prepare_instance


class ExperimentRow(TypedDict):
    """单个实例实验结果的强类型表示。"""

    instance: str
    size: int
    iterations: int
    best_iteration: int
    runtime_seconds: float
    alns_feasible: bool
    alns_vehicles: int
    alns_distance: float
    reference_available: bool
    reference_feasible: bool | None
    reference_vehicles: int | None
    reference_distance: float | None
    vehicle_gap: int | None
    distance_gap: float | None
    distance_gap_pct: float | None


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数。

    当前脚本同时支持：
    - 单实例运行
    - 单个规模目录下的批量运行
    - 全数据集批量运行
    """

    parser = argparse.ArgumentParser(description="Run ALNS on a PDPTW instance.")
    # 实例规模目录；默认不限定规模，配合 --case 时会跨规模搜索实例。
    parser.add_argument("--size", type=int, default=None, help="Instance size directory, e.g. 100, 200, 400.")
    # 实例名称；默认不指定单个实例。
    parser.add_argument("--case", default=None, help="Instance name, e.g. lc101 or lc1_2_1.")
    # 是否读取 data/PDPTW 下的全部实例；默认关闭。
    parser.add_argument("--all", action="store_true", default=False, help="Run all instances under data/PDPTW.")
    # 限制读取实例数量；默认不限制，常用于快速测试。
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of loaded instances, useful for quick tests.")
    # 结果 CSV 输出路径；默认不导出 CSV。
    parser.add_argument("--output-csv", default=None, help="Optional CSV file path for saving run results.")
    # ALNS 最大迭代次数；默认 500 次。
    parser.add_argument("--iterations", type=int, default=500, help="Maximum ALNS iterations.")
    # 连续无改进提前停止阈值；默认 150 次。
    parser.add_argument("--no-improve-limit", type=int, default=150, help="Early stop after N non-improving iterations.")
    # 随机种子；默认 0，便于复现实验。
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    # 算子权重更新分段长度；默认每 25 次迭代更新一次。
    parser.add_argument("--segment-length", type=int, default=25, help="Operator weight update segment length.")
    # 是否显示单实例最终最优解图；默认关闭。
    parser.add_argument("--plot", action="store_true", default=False, help="Visualize the best solution for a single instance.")
    # 最终最优解图片输出路径；默认不保存图片。
    parser.add_argument("--plot-output", default=None, help="Optional image path for saving the plotted solution.")
    # 是否显示 reference 解图；默认关闭。
    parser.add_argument("--plot-reference", action="store_true", default=False, help="Visualize the reference solution for a single instance.")
    # reference 解图片输出路径；默认不保存图片。
    parser.add_argument("--reference-plot-output", default=None, help="Optional image path for saving the reference solution plot.")
    # 是否播放初始解构造动画；默认关闭。
    parser.add_argument("--animate-initial", action="store_true", default=False, help="Animate initial solution construction.")
    # 初始解构造动画输出路径；默认不保存动画。
    parser.add_argument("--animation-output", default=None, help="Optional GIF/MP4 path for saving the initial solution animation.")
    # 动画帧间隔，单位毫秒；默认 500 ms。
    parser.add_argument("--animation-interval", type=int, default=500, help="Animation frame interval in milliseconds.")
    return parser


def resolve_read_config(args: argparse.Namespace) -> PDPTWReadConfig:
    """根据命令行参数推断读取模式。"""

    if args.all:
        return PDPTWReadConfig()

    if args.case:
        return PDPTWReadConfig(size=args.size, case_name=args.case)

    if args.size is not None:
        # 只给 size 时，表示批量读取该规模目录下的所有实例。
        return PDPTWReadConfig(size=args.size)

    raise ValueError("Please provide --case, or provide --size for batch mode, or use --all.")


def build_solver(args: argparse.Namespace) -> PDPTWALNS:
    """按命令行参数构造求解器。"""

    return PDPTWALNS(
        ALNSConfig(
            max_iterations=args.iterations,
            no_improve_limit=args.no_improve_limit,
            segment_length=args.segment_length,
            random_seed=args.seed,
        )
    )


def build_experiment_row(instance, result: ALNSResult) -> ExperimentRow:
    """把一次求解结果整理成统一结果字典。"""

    alns_metrics = evaluate_solution_state(instance, result.best_solution)
    reference_metrics = evaluate_reference_solution(instance)

    row: ExperimentRow = {
        "instance": instance.name,
        "size": instance.size,
        "iterations": result.iterations,
        "best_iteration": result.best_iteration,
        "runtime_seconds": round(result.runtime_seconds, 3),
        "alns_feasible": alns_metrics.feasible,
        "alns_vehicles": alns_metrics.vehicle_count,
        "alns_distance": round(alns_metrics.total_distance, 2),
        "reference_available": reference_metrics is not None,
    }

    if reference_metrics is None:
        row.update(
            {
                "reference_feasible": None,
                "reference_vehicles": None,
                "reference_distance": None,
                "vehicle_gap": None,
                "distance_gap": None,
                "distance_gap_pct": None,
            }
        )
        return row

    vehicle_gap = alns_metrics.vehicle_count - reference_metrics.vehicle_count
    distance_gap = alns_metrics.total_distance - reference_metrics.total_distance
    distance_gap_pct = (
        0.0
        if reference_metrics.total_distance == 0
        else distance_gap / reference_metrics.total_distance * 100.0
    )
    row.update(
        {
            "reference_feasible": reference_metrics.feasible,
            "reference_vehicles": reference_metrics.vehicle_count,
            "reference_distance": round(reference_metrics.total_distance, 2),
            "vehicle_gap": vehicle_gap,
            "distance_gap": round(distance_gap, 2),
            "distance_gap_pct": round(distance_gap_pct, 2),
        }
    )
    return row


def run_instance(instance, solver: PDPTWALNS) -> ExperimentRow:
    """运行单个实例并整理成统一结果字典。"""

    result = solver.solve(instance)
    print(instance.name, 'solved')
    return build_experiment_row(instance, result)


def write_csv(rows: list[ExperimentRow], output_csv: str) -> None:
    """把实验结果写入 CSV。"""

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "instance",
        "size",
        "iterations",
        "best_iteration",
        "runtime_seconds",
        "alns_feasible",
        "alns_vehicles",
        "alns_distance",
        "reference_available",
        "reference_feasible",
        "reference_vehicles",
        "reference_distance",
        "vehicle_gap",
        "distance_gap",
        "distance_gap_pct",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def print_single_result(row: ExperimentRow) -> None:
    """打印单实例结果，保持原有的易读文本格式。"""

    print(f"instance: {row['instance']}")
    print(f"size: {row['size']}")
    print(f"iterations: {row['iterations']}")
    print(f"best_iteration: {row['best_iteration']}")
    print(f"runtime_seconds: {row['runtime_seconds']:.3f}")
    print("alns:")
    print(f"  feasible: {row['alns_feasible']}")
    print(f"  vehicles: {row['alns_vehicles']}")
    print(f"  distance: {row['alns_distance']:.2f}")

    if not row["reference_available"]:
        print("reference:")
        print("  available: False")
        return

    print("reference:")
    print("  available: True")
    print(f"  feasible: {row['reference_feasible']}")
    print(f"  vehicles: {row['reference_vehicles']}")
    print(f"  distance: {row['reference_distance']:.2f}")
    print("gap:")
    print(f"  vehicles: {row['vehicle_gap']:+d}")
    print(f"  distance: {row['distance_gap']:+.2f}")
    print(f"  distance_pct: {row['distance_gap_pct']:+.2f}%")


def print_batch_summary(rows: list[ExperimentRow]) -> None:
    """打印批量运行的摘要信息。"""

    print(f"instances: {len(rows)}")
    feasible_count = sum(1 for row in rows if row["alns_feasible"])
    print(f"alns_feasible_count: {feasible_count}")
    total_runtime = sum(row["runtime_seconds"] for row in rows)
    avg_runtime = total_runtime / len(rows) if rows else 0.0
    print(f"total_runtime_seconds: {total_runtime:.3f}")
    print(f"avg_runtime_seconds: {avg_runtime:.3f}")

    rows_with_reference = [row for row in rows if row["reference_available"]]
    print(f"reference_count: {len(rows_with_reference)}")
    if not rows_with_reference:
        return

    matched_vehicle_count = sum(1 for row in rows_with_reference if row["vehicle_gap"] == 0)
    avg_gap_pct = sum(row["distance_gap_pct"] or 0.0 for row in rows_with_reference) / len(rows_with_reference)
    print(f"matched_vehicle_count: {matched_vehicle_count}")
    print(f"avg_distance_gap_pct: {avg_gap_pct:+.2f}%")


def run_single_instance(instance, solver: PDPTWALNS, plot: bool = False, plot_output: str | None = None) -> ExperimentRow:
    """运行单实例；按需可视化最优解。"""

    result = solver.solve(instance)
    if plot or plot_output:
        plot_alns_result(instance, result, output_path=plot_output, show=plot)
    return build_experiment_row(instance, result)


def plot_reference_solution(
    instance,
    output_path: str | None = None,
    show: bool = True,
) -> None:
    """可视化实例自带的 reference 解。"""

    if instance.solution is None:
        print(f"reference_plot_skipped: {instance.name} has no reference solution")
        return

    reference_state = solution_file_to_state(instance, instance.solution)
    plot_solution(
        instance,
        reference_state,
        output_path=output_path,
        show=show,
        title=f"Reference Solution Visualization: {instance.name}",
    )


def animate_initial_solution(
    instance,
    output_path: str | None = None,
    show: bool = True,
    interval: int = 500,
) -> None:
    """把初始解从空解到完整初始解的构造过程做成动画。"""

    prepared = prepare_instance(instance)
    snapshots = build_initial_solution_snapshots(prepared)
    animate_solution_snapshots(instance, snapshots, output_path=output_path, show=show, interval=interval)


def main() -> None:
    """读取实例、运行 ALNS，并打印/导出结果。"""

    parser = build_parser()
    args = parser.parse_args()

    args.case = 'lc204'
    args.size = 100
    args.iterations = 500
    args.plot = True
    args.plot_reference = True
    # args.plot_reference = True
    # if args.case:
    #     args.plot_output = 'outputs/' + args.case + '_solution.png'
    #     args.reference_plot_output = 'outputs/' + args.case + '_reference_solution.png'
    args.limit = 1000
    # args.output_csv = 'outputs/' + str(args.size) + '.csv'

    dataset = read_pdptw(resolve_read_config(args))
    if dataset.is_empty():
        raise ValueError("No matching instances found.")

    instances = dataset.instances[: args.limit] if args.limit else dataset.instances
    solver = build_solver(args)

    if len(instances) == 1:
        if args.animate_initial or args.animation_output:
            animate_initial_solution(
                instances[0],
                output_path=args.animation_output,
                show=args.animate_initial,
                interval=args.animation_interval,
            )

        rows = [
            run_single_instance(
                instances[0],
                solver,
                plot=args.plot,
                plot_output=args.plot_output,
            )
        ]
        if args.plot_reference or args.reference_plot_output:
            plot_reference_solution(
                instances[0],
                output_path=args.reference_plot_output,
                show=args.plot_reference,
            )
        print_single_result(rows[0])
    else:
        rows = [run_instance(instance, solver) for instance in instances]
        print_batch_summary(rows)

    if args.output_csv:
        write_csv(rows, args.output_csv)
        print(f"csv_saved: {args.output_csv}")


if __name__ == "__main__":
    main()
