"""Helpers for selecting top routes from scored recommendation items."""

from __future__ import annotations

from typing import Iterable, Protocol


class _SelectableRoute(Protocol):
    route_id: str
    recommend_score: float
    time_score: float
    comfort_score: float
    walk_score: float
    transfer_score: float


def _legacy_load_score(item: object) -> float:
    predicted_load = getattr(item, "predicted_load", None)
    if predicted_load is not None and hasattr(predicted_load, "load_score"):
        return float(predicted_load.load_score)
    return float(getattr(item, "comfort_score"))


def _ensure_items(items: Iterable[_SelectableRoute]) -> list[_SelectableRoute]:
    selected = list(items)
    if not selected:
        raise ValueError("candidate routes must not be empty")
    return selected


def select_route_ids(items: Iterable[_SelectableRoute]) -> dict[str, str]:
    routes = _ensure_items(items)
    if hasattr(routes[0], "experience_score"):
        best = max(routes, key=lambda item: (float(item.experience_score), -float(item.total_time_minutes)))
        fastest = min(routes, key=lambda item: (float(item.total_time_minutes), -float(item.experience_score)))
        least_crowded = max(routes, key=lambda item: (_legacy_load_score(item), -float(item.total_time_minutes)))
        least_walking = min(routes, key=lambda item: (float(item.walk_time_minutes), -float(item.experience_score)))
        least_transfer = min(routes, key=lambda item: (int(item.transfer_count), -float(item.experience_score)))
        return {
            "best_experience": best.route_id,
            "fastest": fastest.route_id,
            "least_crowded": least_crowded.route_id,
            "least_walking": least_walking.route_id,
            "least_transfer": least_transfer.route_id,
        }
    best = max(routes, key=lambda item: (item.recommend_score, item.time_score))
    fastest = max(routes, key=lambda item: (item.time_score, item.recommend_score))
    least_crowded = max(routes, key=lambda item: (item.comfort_score, item.recommend_score))
    least_walking = max(routes, key=lambda item: (item.walk_score, item.recommend_score))
    least_transfer = max(routes, key=lambda item: (item.transfer_score, item.recommend_score))
    return {
        "best_experience": best.route_id,
        "fastest": fastest.route_id,
        "least_crowded": least_crowded.route_id,
        "least_walking": least_walking.route_id,
        "least_transfer": least_transfer.route_id,
    }
