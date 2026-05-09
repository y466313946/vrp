from __future__ import annotations

import random

from pdptw.alns.initial_solution import _refresh_solution_metrics
from pdptw.alns.insertion import apply_insertion_move, best_insertion_for_request, enumerate_insertion_moves
from pdptw.alns.instance import PreparedInstance
from pdptw.alns.state import InsertionMove, SolutionState


class RepairOperator:
    """repair 算子基类。"""

    name: str

    def apply(
        self,
        prepared: PreparedInstance,
        partial_solution: SolutionState,
        removed_requests: list[int],
        rng: random.Random,
    ) -> SolutionState:
        raise NotImplementedError


class GreedyInsertionRepair(RepairOperator):
    """每次选择当前全局最便宜的插入动作。"""

    name = "greedy_insertion"

    def apply(
        self,
        prepared: PreparedInstance,
        partial_solution: SolutionState,
        removed_requests: list[int],
        rng: random.Random,
    ) -> SolutionState:
        solution = partial_solution.copy()
        pending = list(dict.fromkeys(removed_requests))

        while pending:
            # 在所有“待插入请求”中找当前最小增量的那一个。
            best_move: InsertionMove | None = None
            best_request: int | None = None
            for request_id in pending:
                move = best_insertion_for_request(prepared, solution, request_id)
                if move is None:
                    continue
                if best_move is None or move.delta_distance < best_move.delta_distance:
                    best_move = move
                    best_request = request_id

            if best_move is None or best_request is None:
                break

            apply_insertion_move(prepared, solution, best_move)
            pending.remove(best_request)

        _refresh_solution_metrics(prepared, solution)
        return solution


class Regret2InsertionRepair(RepairOperator):
    """Regret-2 插入。

    如果某个请求的“最好插入位置”和“第二好插入位置”差距很大，
    说明它更紧迫，应该优先插入。
    """

    name = "regret2_insertion"

    def apply(
        self,
        prepared: PreparedInstance,
        partial_solution: SolutionState,
        removed_requests: list[int],
        rng: random.Random,
    ) -> SolutionState:
        solution = partial_solution.copy()
        pending = list(dict.fromkeys(removed_requests))

        while pending:
            selected_request: int | None = None
            selected_move: InsertionMove | None = None
            best_regret = float("-inf")

            for request_id in pending:
                moves = _enumerate_moves(prepared, solution, request_id)
                if not moves:
                    continue

                moves.sort(key=lambda move: move.delta_distance)
                best = moves[0]
                second = moves[1] if len(moves) > 1 else None
                regret = (second.delta_distance - best.delta_distance) if second else 1_000_000.0

                if regret > best_regret:
                    best_regret = regret
                    selected_request = request_id
                    selected_move = best

            if selected_request is None or selected_move is None:
                break

            apply_insertion_move(prepared, solution, selected_move)
            pending.remove(selected_request)

        _refresh_solution_metrics(prepared, solution)
        return solution


def _enumerate_moves(
    prepared: PreparedInstance,
    solution: SolutionState,
    request_id: int,
) -> list[InsertionMove]:
    """单独抽出一层，便于后续扩展更复杂的候选筛选逻辑。"""

    return enumerate_insertion_moves(prepared, solution, request_id)
