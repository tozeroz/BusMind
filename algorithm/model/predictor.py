"""Public model entrypoints."""

from __future__ import annotations

from typing import Any

from algorithm.model.scorer import score_routes


def predict_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    return score_routes(payload)


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    return predict_recommendation(payload)
