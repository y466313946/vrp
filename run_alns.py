from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import TypedDict

from pdptw import ALNSConfig, ALNSResult, PDPTWALNS, PDPTWReadConfig, plot_alns_result, read_pdptw
from pdptw.alns.evaluation import evaluate_reference_solution, evaluate_solution_state


class ExperimentRow(TypedDict):
    """单个实例实验结果的强类型表示。"""

    instance: str
    size: int
    iterations: int
    best_iteration: int
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
    parser.add_argument("--size", type=int, help="Instance size directory, e.g. 100, 200, 400.")
    parser.add_argument("--case", help="Instance name, e.g. lc101 or lc1_2_1.")
    parser.add_argument("--all", action="store_true", help="Run all instances under data/PDPTW.")
    parser.add_argument("--limit", type=int, help="Limit the number of loaded instances, useful for quick tests.")
    parser.add_argument("--output-csv", help="Optional CSV file path for saving run results.")
    parser.add_argument("--iterations", type=int, default=500, help="Maximum ALNS iterations.")
    parser.add_argument("--no-improve-limit", type=int, default=150, help="Early stop after N non-improving iterations.")
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument("--segment-length", type=int, default=25, help="Operator weight update segment length.")
    parser.add_argument("--plot", action="store_true", help="Visualize the best solution for a single instance.")
    parser.add_argument("--plot-output", help="Optional image path for saving the plotted solution.")
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


def main() -> None:
    """读取实例、运行 ALNS，并打印/导出结果。"""

    parser = build_parser()
    args = parser.parse_args()

    dataset = read_pdptw(resolve_read_config(args))
    if dataset.is_empty():
        raise ValueError("No matching instances found.")

    instances = dataset.instances[: args.limit] if args.limit else dataset.instances
    solver = build_solver(args)

    if len(instances) == 1:
        rows = [
            run_single_instance(
                instances[0],
                solver,
                plot=args.plot,
                plot_output=args.plot_output,
            )
        ]
        print_single_result(rows[0])
    else:
        rows = [run_instance(instance, solver) for instance in instances]
        print_batch_summary(rows)

    if args.output_csv:
        write_csv(rows, args.output_csv)
        print(f"csv_saved: {args.output_csv}")


if __name__ == "__main__":
    main()
