from __future__ import annotations

import json
from typing import Any

from backend.app.schemas.recommendation import RouteRecommendation


def routes_to_context(routes: list[RouteRecommendation]) -> str:
    payload = [
        {
            "route_id": route.route_id,
            "line_names": [segment.line_name for segment in route.segments],
            "boarding_station": route.boarding_station.station_name,
            "alighting_station": route.alighting_station.station_name,
            "predicted_eta_minutes": route.predicted_eta_minutes,
            "predicted_load_level": route.predicted_load.predicted_load_level.value,
            "predicted_load_rate": route.predicted_load.predicted_load_rate,
            "walk_time_minutes": route.walk_time_minutes,
            "transfer_count": route.transfer_count,
            "total_time_minutes": route.total_time_minutes,
            "experience_score": route.experience_score,
            "recommend_types": [item.value for item in route.recommend_types],
            "reason": route.reason,
        }
        for route in routes
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def extract_routes_from_context(context: dict[str, Any] | None) -> list[RouteRecommendation]:
    if not context:
        return []
    candidate: Any = context
    if isinstance(candidate.get("data"), dict):
        candidate = candidate["data"]
    items = candidate.get("items") if isinstance(candidate, dict) else None
    if not isinstance(items, list):
        return []
    routes: list[RouteRecommendation] = []
    for item in items[:10]:
        try:
            routes.append(RouteRecommendation.model_validate(item))
        except Exception:
            continue
    return routes
