from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    w_load: float
    w_walk: float
    w_transfer: float


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def walk_score_from_minutes(walk_time_minutes: float) -> float:
    # Matches the documented example: 6.5 minutes -> 84.0
    return float(round(_clamp(100.0 - walk_time_minutes * 2.5)))


def transfer_score_from_count(transfer_count: int) -> float:
    return float(round(_clamp(100.0 - transfer_count * 20.0)))


def calculate_experience_score(
    load_score: float,
    walk_score: float,
    transfer_score: float,
    weights: ScoreWeights,
) -> float:
    score = (
        load_score * weights.w_load
        + walk_score * weights.w_walk
        + transfer_score * weights.w_transfer
    )
    return float(round(_clamp(score), 1))


def build_experience_reason(
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
) -> str:
    load_text = {
        "seats_available": "车内较宽松",
        "standing_available": "车内可站立",
        "limited_standing": "车内较拥挤",
        "overcrowded": "车内非常拥挤",
    }.get(load_level, "客流状态一般")
    transfer_text = "无需换乘" if transfer_count == 0 else f"需要换乘 {transfer_count} 次"
    return f"{load_text}，步行约 {walk_time_minutes:.1f} 分钟，{transfer_text}。"


def build_route_reason(
    line_names: list[str],
    eta_minutes: float,
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
    experience_score: float,
) -> str:
    line_text = " -> ".join(name for name in line_names if name) or "候选线路"
    experience_reason = build_experience_reason(
        load_level=load_level,
        walk_time_minutes=walk_time_minutes,
        transfer_count=transfer_count,
    )
    return (
        f"推荐乘坐 {line_text}。预计 {eta_minutes:.1f} 分钟到站，"
        f"{experience_reason} 综合体验分 {experience_score:.1f}。"
    )


def select_route_ids(items: list[Any]) -> dict[str, str]:
    if not items:
        raise ValueError("items must not be empty")

    def experience_key(item: Any) -> tuple[float, float]:
        return (float(getattr(item, "experience_score", 0.0)), -float(getattr(item, "total_time_minutes", 0.0)))

    def fastest_key(item: Any) -> tuple[float, float]:
        return (float(getattr(item, "total_time_minutes", 0.0)), -float(getattr(item, "experience_score", 0.0)))

    def crowd_key(item: Any) -> tuple[float, float]:
        predicted_load = getattr(item, "predicted_load", None)
        load_score = float(getattr(predicted_load, "load_score", 0.0)) if predicted_load is not None else 0.0
        return (load_score, float(getattr(item, "experience_score", 0.0)))

    def walking_key(item: Any) -> tuple[float, float]:
        return (float(getattr(item, "walk_time_minutes", 0.0)), -float(getattr(item, "experience_score", 0.0)))

    def transfer_key(item: Any) -> tuple[int, float]:
        return (int(getattr(item, "transfer_count", 0)), -float(getattr(item, "experience_score", 0.0)))

    return {
        "best_experience": max(items, key=experience_key).route_id,
        "fastest": min(items, key=fastest_key).route_id,
        "least_crowded": max(items, key=crowd_key).route_id,
        "least_walking": min(items, key=walking_key).route_id,
        "least_transfer": min(items, key=transfer_key).route_id,
    }
