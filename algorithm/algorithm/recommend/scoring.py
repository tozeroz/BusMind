"""Pure scoring functions for the latest three-factor experience index."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    w_load: float = 0.50
    w_walk: float = 0.30
    w_transfer: float = 0.20

    def validate(self) -> None:
        if min(self.w_load, self.w_walk, self.w_transfer) < 0:
            raise ValueError("权重不能为负数")
        if abs(self.w_load + self.w_walk + self.w_transfer - 1.0) > 1e-6:
            raise ValueError("三项权重之和必须为 1")


def load_score_from_rate(load_rate: float) -> float:
    if not 0 <= load_rate <= 1:
        raise ValueError("load_rate 必须在 0 到 1 之间")
    return float(round(max(0.0, min(100.0, 100.0 - load_rate * 55.0))))


def walk_score_from_minutes(walk_time_minutes: float) -> float:
    if walk_time_minutes < 0:
        raise ValueError("walk_time_minutes 不能为负数")
    return float(round(max(0.0, 100.0 - walk_time_minutes * 2.5)))


def transfer_score_from_count(transfer_count: int) -> float:
    if transfer_count < 0:
        raise ValueError("transfer_count 不能为负数")
    return float(round(max(0.0, 100.0 - transfer_count * 30.0)))


def calculate_experience_score(
    load_score: float,
    walk_score: float,
    transfer_score: float,
    weights: ScoreWeights,
) -> float:
    weights.validate()
    for score in (load_score, walk_score, transfer_score):
        if not 0 <= score <= 100:
            raise ValueError("各分项得分必须在 0 到 100 之间")
    value = (
        weights.w_load * load_score
        + weights.w_walk * walk_score
        + weights.w_transfer * transfer_score
    )
    return round(value, 1)
