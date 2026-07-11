"""Typed recommendation model entrypoints."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from algorithm.recommend.contracts import RecommendationInput, RecommendationOutput, RouteFeature, ScoredRoute
from algorithm.recommend.reason_builder import build_reason_factors
from algorithm.recommend.scoring import (
    NEUTRAL_SCORE,
    ScoreWeights,
    calculate_experience_score,
    congestion_score_to_comfort,
    eta_score_from_minutes,
    flow_score_from_context,
    frequency_score_from_minutes,
    reliability_score_from_value,
    transfer_score_from_count,
    walk_score_from_minutes,
)
from algorithm.recommend.selector import select_route_ids


MODEL_VERSION = "recommend_ranker_v1"
MODEL_DIR = Path(__file__).resolve().parents[1] / "model_files"
MODEL_PATH = MODEL_DIR / f"{MODEL_VERSION}.json"
STATS_PATH = MODEL_DIR / "recommend_feature_stats_v1.json"

DEFAULT_LOAD_SCORES = {
    "SEA": 95.0,
    "SDA": 70.0,
    "LSD": 35.0,
}

FEATURE_NAMES = (
    "time_score",
    "comfort_score",
    "walk_score",
    "transfer_score",
    "frequency_score",
    "flow_score",
    "congestion_score",
    "reliability_score",
)

RULE_WEIGHTS = {
    "balanced": ScoreWeights(0.24, 0.18, 0.12, 0.09, 0.12, 0.10, 0.08, 0.07),
    "fastest": ScoreWeights(0.42, 0.10, 0.10, 0.08, 0.10, 0.06, 0.08, 0.06),
    "low_load": ScoreWeights(0.16, 0.34, 0.10, 0.08, 0.10, 0.10, 0.07, 0.05),
    "less_walking": ScoreWeights(0.22, 0.12, 0.30, 0.12, 0.08, 0.06, 0.05, 0.05),
    "less_transfer": ScoreWeights(0.24, 0.12, 0.10, 0.30, 0.08, 0.06, 0.05, 0.05),
}


def _round_score(value: float) -> float:
    return round(float(value), 1)


def _comfort_score(route: RouteFeature) -> float:
    if route.load_score is not None:
        return _round_score(max(0.0, min(100.0, route.load_score)))
    if route.load_code:
        return DEFAULT_LOAD_SCORES.get(route.load_code.upper(), NEUTRAL_SCORE)
    return NEUTRAL_SCORE


def _effective_reliability(route: RouteFeature) -> float:
    values: list[float] = []
    if route.reliability_score is not None:
        values.append(route.reliability_score)
    if route.confidence is not None:
        values.append(route.confidence * 100.0)
    if not values:
        return NEUTRAL_SCORE
    return sum(values) / len(values)


def _component_scores(route: RouteFeature) -> dict[str, float]:
    total_time = route.total_time_minutes if route.total_time_minutes > 0 else route.eta_minutes
    time_score = eta_score_from_minutes(total_time)
    comfort_score = _comfort_score(route)
    walk_score = walk_score_from_minutes(route.walk_time_minutes)
    transfer_score = transfer_score_from_count(route.transfer_count)
    frequency_score = frequency_score_from_minutes(route.avg_service_frequency)
    flow_score = flow_score_from_context(route.station_flow_mean, route.station_flow_level)
    congestion_score = congestion_score_to_comfort(route.normalized_congestion_pressure)
    reliability_score = reliability_score_from_value(_effective_reliability(route))
    return {
        "time_score": _round_score(time_score),
        "comfort_score": _round_score(comfort_score),
        "walk_score": _round_score(walk_score),
        "transfer_score": _round_score(transfer_score),
        "frequency_score": _round_score(frequency_score),
        "flow_score": _round_score(flow_score),
        "congestion_score": _round_score(congestion_score),
        "reliability_score": _round_score(reliability_score),
    }


def _rule_score(component_scores: dict[str, float], preference: str) -> float:
    weights = RULE_WEIGHTS[preference]
    return calculate_experience_score(
        eta_score=component_scores["time_score"],
        load_score=component_scores["comfort_score"],
        walk_score=component_scores["walk_score"],
        transfer_score=component_scores["transfer_score"],
        frequency_score=component_scores["frequency_score"],
        flow_score=component_scores["flow_score"],
        congestion_score=component_scores["congestion_score"],
        reliability_score=component_scores["reliability_score"],
        weights=weights,
    )


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _load_ranker_artifacts() -> tuple[dict[str, Any], dict[str, Any]] | None:
    if not MODEL_PATH.exists() or not STATS_PATH.exists():
        return None
    try:
        with MODEL_PATH.open("r", encoding="utf-8") as model_file:
            model_payload = json.load(model_file)
        with STATS_PATH.open("r", encoding="utf-8") as stats_file:
            stats_payload = json.load(stats_file)
    except (OSError, json.JSONDecodeError):
        return None
    if model_payload.get("feature_names") != list(FEATURE_NAMES):
        return None
    if stats_payload.get("feature_names") != list(FEATURE_NAMES):
        return None
    return model_payload, stats_payload


def _vectorize(component_scores: dict[str, float], stats_payload: dict[str, Any]) -> np.ndarray:
    means = stats_payload.get("mean", {})
    stds = stats_payload.get("std", {})
    values = []
    for feature_name in FEATURE_NAMES:
        mean_value = float(means.get(feature_name, 0.0))
        std_value = float(stds.get(feature_name, 1.0)) or 1.0
        values.append((component_scores[feature_name] - mean_value) / std_value)
    return np.array(values, dtype=float)


def _model_score(
    component_scores: dict[str, float],
    *,
    preference: str,
    artifacts: tuple[dict[str, Any], dict[str, Any]] | None,
) -> float | None:
    if artifacts is None:
        return None
    model_payload, stats_payload = artifacts
    preference_payload = model_payload.get("preferences", {}).get(preference)
    if not preference_payload:
        return None
    weights = np.array(preference_payload.get("weights", []), dtype=float)
    if weights.shape != (len(FEATURE_NAMES),):
        return None
    bias = float(preference_payload.get("bias", 0.0))
    vector = _vectorize(component_scores, stats_payload)
    probability = _sigmoid(float(np.dot(weights, vector) + bias))
    return _round_score(probability * 100.0)


def _build_scored_route(
    route: RouteFeature,
    *,
    preference: str,
    artifacts: tuple[dict[str, Any], dict[str, Any]] | None,
) -> tuple[ScoredRoute, float]:
    component_scores = _component_scores(route)
    rule_score = _rule_score(component_scores, preference)
    learned_score = _model_score(component_scores, preference=preference, artifacts=artifacts)
    recommend_score = learned_score if learned_score is not None else rule_score
    reason_factors = build_reason_factors(route, **component_scores)
    scored = ScoredRoute(
        route_id=route.route_id,
        time_score=component_scores["time_score"],
        comfort_score=component_scores["comfort_score"],
        walk_score=component_scores["walk_score"],
        transfer_score=component_scores["transfer_score"],
        frequency_score=component_scores["frequency_score"],
        flow_score=component_scores["flow_score"],
        congestion_score=component_scores["congestion_score"],
        reliability_score=component_scores["reliability_score"],
        recommend_score=_round_score(recommend_score),
        recommend_types=(),
        reason_factors=reason_factors,
    )
    return scored, rule_score


def predict_recommendation_typed(input_data: RecommendationInput) -> RecommendationOutput:
    artifacts = _load_ranker_artifacts()
    scored_pairs = [
        _build_scored_route(route, preference=input_data.preference, artifacts=artifacts)
        for route in input_data.routes
    ]
    items = [pair[0] for pair in scored_pairs]
    selected_ids = select_route_ids(items)
    type_map = {
        selected_ids["best_experience"]: ["best_experience"],
        selected_ids["fastest"]: ["fastest"],
        selected_ids["least_crowded"]: ["least_crowded"],
        selected_ids["least_walking"]: ["least_walking"],
        selected_ids["least_transfer"]: ["least_transfer"],
    }
    for route_id, recommend_type in list(type_map.items()):
        duplicates = [item for item in items if item.route_id == route_id]
        if not duplicates:
            continue
        merged_types: list[str] = []
        for key, value in selected_ids.items():
            if value == route_id:
                merged_types.append(key)
        type_map[route_id] = merged_types

    final_items = []
    for item in sorted(items, key=lambda current: (-current.recommend_score, -current.time_score, current.route_id)):
        final_items.append(replace(item, recommend_types=tuple(type_map.get(item.route_id, ()))))

    return RecommendationOutput(
        best_experience_route_id=selected_ids["best_experience"],
        fastest_route_id=selected_ids["fastest"],
        least_crowded_route_id=selected_ids["least_crowded"],
        least_walking_route_id=selected_ids["least_walking"],
        least_transfer_route_id=selected_ids["least_transfer"],
        items=tuple(final_items),
    )
