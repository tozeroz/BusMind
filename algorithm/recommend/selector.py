from __future__ import annotations

from typing import Any


def select_route_ids(items: list[Any]) -> dict[str, str]:
    if not items:
        raise ValueError("候选路线不能为空")

    def load_score(item: Any) -> float:
        return float(item.predicted_load.load_score)

    best = max(items, key=lambda item: (item.experience_score, -item.total_time_minutes))
    fastest = min(items, key=lambda item: (item.total_time_minutes, -item.experience_score))
    least_crowded = max(items, key=lambda item: (load_score(item), -item.total_time_minutes))
    least_walking = min(items, key=lambda item: (item.walk_time_minutes, -item.experience_score))
    least_transfer = min(items, key=lambda item: (item.transfer_count, -item.experience_score))
    return {
        "best_experience": best.route_id,
        "fastest": fastest.route_id,
        "least_crowded": least_crowded.route_id,
        "least_walking": least_walking.route_id,
        "least_transfer": least_transfer.route_id,
    }
