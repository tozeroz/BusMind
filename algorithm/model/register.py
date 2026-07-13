"""Register and select candidate route scoring models."""

from __future__ import annotations

import os
from typing import Any

from algorithm.model.contracts import ModelScoringRequest


DEFAULT_SCORING_MODEL = "linear"
SCORING_MODEL_ENV = "BUSMIND_SCORING_MODEL"

MODEL_ALIASES = {
    "linear": "linear",
    "linear_scoring": "linear",
    "xgboost": "xgboost",
    "xgboost_scoring": "xgboost",
    "tabpfn": "tabpfn",
    "tabpfn_scoring": "tabpfn",
}


def normalize_model_key(name: str | None = None) -> str:
    raw_name = (name or os.getenv(SCORING_MODEL_ENV) or DEFAULT_SCORING_MODEL).strip().lower()
    try:
        return MODEL_ALIASES[raw_name]
    except KeyError as exc:
        choices = ", ".join(sorted(MODEL_ALIASES))
        raise ValueError(f"Unsupported scoring model {raw_name!r}; choose one of: {choices}") from exc


def get_route_scoring_model(name: str | None = None):
    model_key = normalize_model_key(name)
    if model_key == "linear":
        from algorithm.model.linear_scoring.model import LinearRouteScoringModel

        return LinearRouteScoringModel()
    if model_key == "xgboost":
        from algorithm.model.xgboost_scoring.model import XGBoostRouteScoringModel

        return XGBoostRouteScoringModel()
    if model_key == "tabpfn":
        from algorithm.model.tabpfn_scoring.model import TabPFNRouteScoringModel

        return TabPFNRouteScoringModel()
    raise AssertionError(f"Unhandled scoring model key: {model_key}")


def score_routes_typed(request: ModelScoringRequest, *, model_name: str | None = None) -> dict[str, Any]:
    model = get_route_scoring_model(model_name)
    return model.score_routes_typed(request)


def score_routes(payload: dict[str, Any], *, strict_backend: bool = False, model_name: str | None = None) -> dict[str, Any]:
    request = ModelScoringRequest.from_dict(payload, strict_backend=strict_backend)
    return score_routes_typed(request, model_name=model_name)

