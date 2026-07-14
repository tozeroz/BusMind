"""Generate rule-based pseudo labels from frozen backend-style route features."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_route_from_feature_row,
    read_frozen_features,
)
from algorithm.model.contracts import PREFERENCE_NAMES, RouteFeatures


SCORE_NAMES = (
    "time_score",
    "comfort_score",
    "walk_score",
    "transfer_score",
    "reliability_score",
)

PREFERENCE_WEIGHTS = {
    "balanced": {
        "time_score": 0.32,
        "comfort_score": 0.23,
        "walk_score": 0.15,
        "transfer_score": 0.15,
        "reliability_score": 0.15,
    },
    "fastest": {
        "time_score": 0.62,
        "comfort_score": 0.10,
        "walk_score": 0.10,
        "transfer_score": 0.08,
        "reliability_score": 0.10,
    },
    "comfort": {
        "time_score": 0.16,
        "comfort_score": 0.56,
        "walk_score": 0.08,
        "transfer_score": 0.07,
        "reliability_score": 0.13,
    },
    "less_walking": {
        "time_score": 0.18,
        "comfort_score": 0.10,
        "walk_score": 0.54,
        "transfer_score": 0.08,
        "reliability_score": 0.10,
    },
    "less_transfer": {
        "time_score": 0.20,
        "comfort_score": 0.10,
        "walk_score": 0.08,
        "transfer_score": 0.52,
        "reliability_score": 0.10,
    },
}

SOURCE_CONFIDENCE = {
    "lta_realtime": 100.0,
    "traffic_speed_bands": 95.0,
    "database": 92.0,
    "historical": 88.0,
    "cache": 86.0,
    "processed_csv": 84.0,
    "backend_graph": 82.0,
    "lta_line_fallback": 72.0,
    "backend_graph_estimate": 70.0,
    "rule_estimate": 66.0,
    "default": 52.0,
    "model": 50.0,
}

TRANSFER_BASE_SCORE = {
    0: 100.0,
    1: 68.0,
    2: 36.0,
    3: 15.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--output", type=Path, default=default_dataset_dir() / "rule_pseudo_labels.csv")
    parser.add_argument("--max-routes-per-group", type=int, default=10)
    return parser.parse_args()


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return round(max(lower, min(upper, float(value))), 2)


def _bool_value(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _relative_low_score(values: list[float], value: float, *, neutral: float = 82.0) -> float:
    if not values:
        return neutral
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return neutral
    return _clip(100.0 - (float(value) - low) / (high - low) * 55.0)


def _relative_high_score(values: list[float], value: float, *, neutral: float = 78.0) -> float:
    if not values:
        return neutral
    low = min(values)
    high = max(values)
    if math.isclose(low, high):
        return neutral
    return _clip(45.0 + (float(value) - low) / (high - low) * 55.0)


def _freshness_score(seconds: float) -> float:
    if seconds <= 120:
        return 100.0
    if seconds <= 600:
        return 88.0
    if seconds <= 1800:
        return 74.0
    if seconds <= 3600:
        return 62.0
    if seconds <= 21600:
        return 52.0
    return 45.0


def _source_confidence(feature_sources: dict[str, str]) -> float:
    if not feature_sources:
        return 60.0
    scores = [SOURCE_CONFIDENCE.get(str(source), 60.0) for source in feature_sources.values()]
    return round(sum(scores) / len(scores), 2)


def _as_route_feature(row: dict[str, Any]) -> RouteFeatures:
    payload = model_input_route_from_feature_row(row)
    return RouteFeatures.from_dict(payload, strict_backend=True)


def _route_records(group: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in group.to_dict("records"):
        route = _as_route_feature(row)
        walk_burden = max(route.walk_time_minutes, route.walk_distance_meters / 80.0)
        effective_time = (
            route.eta_minutes
            + route.ride_time_minutes
            + 0.35 * route.avg_service_frequency_minutes
            + 3.0 * route.transfer_count
        )
        comfort_raw = (
            0.45 * route.load_score
            + 0.25 * route.history_flow_score
            + 0.25 * route.congestion_score
            + 0.05 * route.monitored_score
        )
        records.append(
            {
                "row": row,
                "route": route,
                "effective_time": effective_time,
                "walk_burden": walk_burden,
                "comfort_raw": comfort_raw,
                "source_confidence": _source_confidence(route.feature_sources),
                "is_synthetic": _bool_value(row.get("is_synthetic", False)),
            }
        )
    return records


def _subscores(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    time_values = [item["effective_time"] for item in records]
    walk_values = [item["walk_burden"] for item in records]
    comfort_values = [item["comfort_raw"] for item in records]
    transfer_values = [float(item["route"].transfer_count) for item in records]

    output: dict[str, dict[str, float]] = {}
    for item in records:
        route: RouteFeatures = item["route"]
        relative_time = _relative_low_score(time_values, item["effective_time"])
        absolute_time = _clip(
            108.0
            - route.eta_minutes * 1.45
            - route.ride_time_minutes * 0.70
            - route.avg_service_frequency_minutes * 0.35
            - route.transfer_count * 4.0
        )
        time_score = _clip(0.62 * relative_time + 0.38 * absolute_time)

        relative_comfort = _relative_high_score(comfort_values, item["comfort_raw"])
        absolute_comfort = _clip(
            item["comfort_raw"]
            - route.transfer_count * 2.5
            - max(0.0, route.walk_time_minutes - 8.0) * 0.8
        )
        comfort_score = _clip(0.55 * absolute_comfort + 0.45 * relative_comfort)

        relative_walk = _relative_low_score(walk_values, item["walk_burden"], neutral=88.0)
        absolute_walk = _clip(
            104.0
            - route.walk_time_minutes * 3.4
            - route.walk_distance_meters / 28.0
            - route.transfer_count * 3.0
        )
        walk_score = _clip(0.58 * relative_walk + 0.42 * absolute_walk)

        relative_transfer = _relative_low_score(transfer_values, float(route.transfer_count), neutral=90.0)
        base_transfer = TRANSFER_BASE_SCORE.get(route.transfer_count, 8.0)
        transfer_score = _clip(0.78 * base_transfer + 0.22 * relative_transfer)

        freshness = _freshness_score(route.data_freshness_seconds)
        reliability_score = _clip(
            0.38 * route.completeness_score
            + 0.24 * route.monitored_score
            + 0.20 * freshness
            + 0.18 * item["source_confidence"]
        )

        output[route.route_id] = {
            "time_score": time_score,
            "comfort_score": comfort_score,
            "walk_score": walk_score,
            "transfer_score": transfer_score,
            "reliability_score": reliability_score,
        }
    return output


def _recommend_score(subscore: dict[str, float], preference: str) -> float:
    weights = PREFERENCE_WEIGHTS[preference]
    return _clip(sum(subscore[name] * weight for name, weight in weights.items()))


def _label_gain(scores: list[float], score: float, rank_position: int) -> float:
    low = min(scores)
    high = max(scores)
    if math.isclose(low, high):
        return round(max(0.0, 3.0 - (rank_position - 1) * 0.5), 4)
    normalized = (score - low) / (high - low)
    return round(3.0 * max(0.0, normalized) ** 1.15, 4)


def _soft_label(scores: list[float], score: float) -> float:
    if not scores:
        return 0.0
    best = max(scores)
    exp_values = [math.exp((value - best) / 6.0) for value in scores]
    current = math.exp((score - best) / 6.0)
    return round(current / sum(exp_values), 6)


def _label_confidence(
    *,
    route_reliability: float,
    best_score: float,
    second_score: float,
    route_count: int,
    is_synthetic: bool,
) -> float:
    margin = max(0.0, best_score - second_score)
    confidence = (
        0.42
        + 0.28 * min(margin / 12.0, 1.0)
        + 0.22 * (route_reliability / 100.0)
        + 0.08 * min(max(route_count - 1, 0) / 5.0, 1.0)
    )
    if is_synthetic:
        confidence -= 0.04
    return round(max(0.30, min(0.98, confidence)), 4)


def _label_rows(candidate_group_id: str, group: pd.DataFrame) -> list[dict[str, object]]:
    records = _route_records(group)
    subscores = _subscores(records)
    output: list[dict[str, object]] = []

    for preference in PREFERENCE_NAMES:
        scored = []
        for item in records:
            route: RouteFeatures = item["route"]
            subscore = subscores[route.route_id]
            recommend_score = _recommend_score(subscore, preference)
            scored.append((item, route, subscore, recommend_score))

        scored.sort(key=lambda item: (-item[3], item[1].route_id))
        score_values = [item[3] for item in scored]
        best_score = score_values[0]
        second_score = score_values[1] if len(score_values) > 1 else best_score
        best_route_id = scored[0][1].route_id

        for rank_index, (item, route, subscore, recommend_score) in enumerate(scored, start=1):
            score_margin = round(best_score - recommend_score, 4)
            output.append(
                {
                    "candidate_group_id": candidate_group_id,
                    "preference": preference,
                    "route_id": route.route_id,
                    "rank_position": rank_index,
                    "label": 1 if route.route_id == best_route_id else 0,
                    "label_gain": _label_gain(score_values, recommend_score, rank_index),
                    "soft_label": _soft_label(score_values, recommend_score),
                    "score_margin": score_margin,
                    "label_confidence": _label_confidence(
                        route_reliability=subscore["reliability_score"],
                        best_score=best_score,
                        second_score=second_score,
                        route_count=len(scored),
                        is_synthetic=item["is_synthetic"],
                    ),
                    **subscore,
                    "recommend_score": recommend_score,
                    "is_synthetic": item["is_synthetic"],
                }
            )
    return output


def main() -> None:
    args = parse_args()
    dataset = read_frozen_features(args.input)
    rows: list[dict[str, object]] = []
    for candidate_group_id, group in dataset.groupby("candidate_group_id"):
        group = group.sort_values(["eta_minutes", "route_id"]).head(args.max_routes_per_group).copy()
        rows.extend(_label_rows(str(candidate_group_id), group))

    output = pd.DataFrame(rows).sort_values(
        ["candidate_group_id", "preference", "rank_position", "route_id"],
        ascending=[True, True, True, True],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"built {len(output)} rule-based pseudo-labeled rows -> {args.output}")


if __name__ == "__main__":
    main()
