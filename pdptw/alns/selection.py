from __future__ import annotations

import random
from dataclasses import dataclass

from pdptw.alns.config import ALNSConfig


@dataclass
class OperatorStat:
    """记录单个算子的自适应统计量。"""

    weight: float = 1.0
    score: float = 0.0
    usages: int = 0


class AdaptiveOperatorSelector:
    """管理 destroy / repair 算子的轮盘赌选择与权重更新。"""

    def __init__(self, destroy_operators: list, repair_operators: list, config: ALNSConfig) -> None:
        self.destroy_operators = destroy_operators
        self.repair_operators = repair_operators
        self.config = config
        self.destroy_stats = {operator.name: OperatorStat() for operator in destroy_operators}
        self.repair_stats = {operator.name: OperatorStat() for operator in repair_operators}

    def select_destroy(self, rng: random.Random):
        return self._roulette(self.destroy_operators, self.destroy_stats, rng)

    def select_repair(self, rng: random.Random):
        return self._roulette(self.repair_operators, self.repair_stats, rng)

    def reward(self, destroy_name: str, repair_name: str, outcome: str) -> None:
        """根据一次迭代结果给参与的算子累计奖励分数。"""

        reward = {
            "global_best": self.config.score_global_best,
            "improved": self.config.score_improved,
            "accepted": self.config.score_accepted,
            "rejected": self.config.score_rejected,
        }[outcome]
        self.destroy_stats[destroy_name].score += reward
        self.repair_stats[repair_name].score += reward

    def update_weights(self) -> None:
        self._update_group(self.destroy_stats)
        self._update_group(self.repair_stats)

    def _roulette(self, operators: list, stats: dict[str, OperatorStat], rng: random.Random):
        """按当前权重做轮盘赌抽样。"""

        total = sum(stats[operator.name].weight for operator in operators)
        threshold = rng.random() * total
        cumulative = 0.0
        for operator in operators:
            stat = stats[operator.name]
            cumulative += stat.weight
            if cumulative >= threshold:
                stat.usages += 1
                return operator
        stats[operators[-1].name].usages += 1
        return operators[-1]

    def _update_group(self, stats: dict[str, OperatorStat]) -> None:
        """按段更新权重，避免单次迭代波动过大。"""

        for stat in stats.values():
            if stat.usages == 0:
                continue
            average_score = stat.score / stat.usages
            stat.weight = (1.0 - self.config.reaction_factor) * stat.weight + self.config.reaction_factor * average_score
            stat.score = 0.0
            stat.usages = 0
