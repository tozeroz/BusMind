"""Dict-compatible predictor entrypoint for backend and offline callers."""

from __future__ import annotations

from typing import Any

from algorithm.recommend.contracts import RecommendationInput
from algorithm.recommend.models import predict_recommendation_typed


def predict_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    typed_input = RecommendationInput.from_dict(payload)
    return predict_recommendation_typed(typed_input).to_dict()
