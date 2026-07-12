"""Preference-driven route scorer with 12 fixed input features."""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from algorithm.model.contracts import (
    CONTRACT_VERSION,
    MODEL_NAME,
    MODEL_VERSION,
    NUMERIC_FEATURE_NAMES,
    ModelScoringRequest,
    RouteFeatures,
    ScoreResult,
)


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
SUBSCORE_MODEL_PATH = ARTIFACT_DIR / "route_scorer_v1.json"

PREFERENCE_MIX = {
    "balanced": np.array([0.30, 0.25, 0.15, 0.15, 0.15], dtype=float),
    "fastest": np.array([0.60, 0.12, 0.10, 0.08, 0.10], dtype=float),
    "comfort": np.array([0.18, 0.55, 0.08, 0.07, 0.12], dtype=float),
    "less_walking": np.array([0.20, 0.12, 0.50, 0.08, 0.10], dtype=float),
    "less_transfer": np.array([0.22, 0.12, 0.08, 0.48, 0.10], dtype=float),
}

DEFAULT_MEAN = np.array([10.0, 25.0, 8.0, 600.0, 0.6, 70.0, 70.0, 70.0, 120.0, 80.0, 85.0, 10.0])
DEFAULT_STD = np.array([8.0, 18.0, 6.0, 500.0, 0.8, 22.0, 22.0, 22.0, 120.0, 25.0, 20.0, 7.0])

# Rows map 12 normalized features to five scores:
# time, comfort, walk, transfer, reliability.
DEFAULT_SUBSCORE_COEFFICIENTS = np.array(
    [
        [-0.65, -0.45, -0.20, -0.05, -0.05, 0.00, 0.00, 0.08, 0.00, 0.00, 0.00, -0.25],
        [0.00, 0.00, -0.05, -0.02, -0.05, 0.55, 0.28, 0.32, 0.00, 0.04, 0.04, 0.00],
        [-0.05, 0.00, -0.65, -0.55, -0.05, 0.00, 0.00, 0.00, 0.00, 0.00, 0.04, 0.00],
        [0.00, 0.00, -0.05, 0.00, -1.10, 0.00, 0.00, 0.00, 0.00, 0.05, 0.05, 0.00],
        [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.06, 0.06, -0.45, 0.45, 0.50, 0.00],
    ],
    dtype=float,
)
DEFAULT_SUBSCORE_BIAS = np.array([0.25, 0.20, 0.20, 0.30, 0.25], dtype=float)


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(values, -40.0, 40.0)))


def _round_score(value: float) -> float:
    return round(float(max(0.0, min(100.0, value))), 2)


def _load_artifact() -> dict[str, Any] | None:
    if not SUBSCORE_MODEL_PATH.exists():
        return None
    try:
        with SUBSCORE_MODEL_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("feature_names") != list(NUMERIC_FEATURE_NAMES):
        return None
    return payload


def _model_parameters() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    payload = _load_artifact()
    if not payload:
        return DEFAULT_MEAN, DEFAULT_STD, DEFAULT_SUBSCORE_COEFFICIENTS, DEFAULT_SUBSCORE_BIAS
    mean = np.array(payload.get("mean", DEFAULT_MEAN), dtype=float)
    std = np.array(payload.get("std", DEFAULT_STD), dtype=float)
    coefficients = np.array(
        payload.get("subscore_coefficients", DEFAULT_SUBSCORE_COEFFICIENTS),
        dtype=float,
    )
    bias = np.array(payload.get("subscore_bias", DEFAULT_SUBSCORE_BIAS), dtype=float)
    if mean.shape != (12,) or std.shape != (12,) or coefficients.shape != (5, 12) or bias.shape != (5,):
        return DEFAULT_MEAN, DEFAULT_STD, DEFAULT_SUBSCORE_COEFFICIENTS, DEFAULT_SUBSCORE_BIAS
    std = np.where(std == 0, 1.0, std)
    return mean, std, coefficients, bias


def _score_route(route: RouteFeatures, *, preference: str) -> ScoreResult:
    mean, std, subscore_coefficients, subscore_bias = _model_parameters()
    vector = np.array(route.numeric_vector(), dtype=float)
    normalized = (vector - mean) / std
    logits = subscore_coefficients @ normalized + subscore_bias
    five_scores = _sigmoid(logits) * 100.0

    degraded_penalty = min(len(route.degraded_fields) * 3.0, 18.0)
    five_scores[4] = max(0.0, five_scores[4] - degraded_penalty)

    preference_mix = PREFERENCE_MIX[preference]
    recommend_score = float(np.dot(preference_mix, five_scores))
    contribution_coefficients = preference_mix @ subscore_coefficients
    contributions = {
        feature: round(float(normalized[index] * contribution_coefficients[index]), 4)
        for index, feature in enumerate(NUMERIC_FEATURE_NAMES)
    }

    return ScoreResult(
        route_id=route.route_id,
        time_score=_round_score(five_scores[0]),
        comfort_score=_round_score(five_scores[1]),
        walk_score=_round_score(five_scores[2]),
        transfer_score=_round_score(five_scores[3]),
        reliability_score=_round_score(five_scores[4]),
        recommend_score=_round_score(recommend_score),
        feature_contributions=contributions,
    )


def score_routes_typed(request: ModelScoringRequest) -> dict[str, Any]:
    started = time.perf_counter()
    results = [_score_route(route, preference=request.preference) for route in request.routes]
    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": request.request_id,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "results": [result.to_dict() for result in results],
        "warnings": [],
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def score_routes(payload: dict[str, Any], *, strict_backend: bool = False) -> dict[str, Any]:
    request = ModelScoringRequest.from_dict(payload, strict_backend=strict_backend)
    return score_routes_typed(request)
