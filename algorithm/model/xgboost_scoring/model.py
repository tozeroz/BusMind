"""XGBoost candidate route scoring model."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from functools import lru_cache
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
from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES, mix_recommend_score, round_score


ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
METADATA_PATH = ARTIFACT_DIR / "xgboost_route_scoring.json"


class XGBoostArtifactError(RuntimeError):
    """Raised when the XGBoost artifact is unavailable or invalid."""


def _import_xgboost():
    try:
        import xgboost as xgb
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise XGBoostArtifactError(
            "xgboost is not installed. Install it with `uv add xgboost` or `uv sync`."
        ) from exc
    return xgb


def _read_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise XGBoostArtifactError(
            f"XGBoost artifact not found: {path}. "
            "Train it with `python algorithm/model/xgboost_scoring/train.py`."
        )
    try:
        with path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise XGBoostArtifactError(f"Cannot read XGBoost artifact metadata: {path}") from exc
    if metadata.get("feature_names") != list(NUMERIC_FEATURE_NAMES):
        raise XGBoostArtifactError("XGBoost artifact feature_names do not match the current model contract")
    if metadata.get("score_names") != list(SCORE_NAMES):
        raise XGBoostArtifactError("XGBoost artifact score_names do not match the current model contract")
    return metadata


@lru_cache(maxsize=2)
def _load_artifact(metadata_path_text: str = str(METADATA_PATH)) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata_path = Path(metadata_path_text)
    metadata = _read_metadata(metadata_path)
    xgb = _import_xgboost()
    base_dir = metadata_path.parent
    model_files = metadata.get("model_files")
    if not isinstance(model_files, dict):
        raise XGBoostArtifactError("XGBoost artifact metadata missing model_files")

    models: dict[str, Any] = {}
    for score_name in SCORE_NAMES:
        relative_path = model_files.get(score_name)
        if not relative_path:
            raise XGBoostArtifactError(f"XGBoost artifact missing model file for {score_name}")
        model_path = base_dir / str(relative_path)
        if not model_path.is_file():
            raise XGBoostArtifactError(f"XGBoost model file not found: {model_path}")
        booster = xgb.Booster()
        booster.load_model(model_path)
        models[score_name] = booster
    return metadata, models


def _d_matrix(vector: np.ndarray):
    xgb = _import_xgboost()
    return xgb.DMatrix(vector, feature_names=list(NUMERIC_FEATURE_NAMES))


def _predict_contributions(models: dict[str, Any], dmatrix: Any, preference: str) -> dict[str, float]:
    preference_mix = PREFERENCE_MIX[preference]
    total = np.zeros(len(NUMERIC_FEATURE_NAMES), dtype=float)
    for score_index, score_name in enumerate(SCORE_NAMES):
        try:
            contribution = models[score_name].predict(dmatrix, pred_contribs=True)[0]
        except Exception:
            return {feature: 0.0 for feature in NUMERIC_FEATURE_NAMES}
        total += preference_mix[score_index] * np.asarray(contribution[:-1], dtype=float)
    return {
        feature: round(float(total[index]), 4)
        for index, feature in enumerate(NUMERIC_FEATURE_NAMES)
    }


class XGBoostRouteScoringModel:
    model_key = "xgboost"
    model_name = MODEL_NAME
    model_version = MODEL_VERSION

    def __init__(self, artifact_path: Path = METADATA_PATH) -> None:
        self.artifact_path = artifact_path

    def _artifact(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return _load_artifact(str(self.artifact_path))

    def score_route(self, route: RouteFeatures, *, preference: str) -> ScoreResult:
        _metadata, models = self._artifact()
        vector = np.array(route.numeric_vector(), dtype=float).reshape(1, -1)
        dmatrix = _d_matrix(vector)
        five_scores = np.array(
            [float(models[score_name].predict(dmatrix)[0]) for score_name in SCORE_NAMES],
            dtype=float,
        )
        five_scores = np.clip(five_scores, 0.0, 100.0)
        recommend_score = mix_recommend_score(five_scores, preference=preference)

        return ScoreResult(
            route_id=route.route_id,
            time_score=round_score(five_scores[0]),
            comfort_score=round_score(five_scores[1]),
            walk_score=round_score(five_scores[2]),
            transfer_score=round_score(five_scores[3]),
            reliability_score=round_score(five_scores[4]),
            recommend_score=round_score(recommend_score),
            feature_contributions=_predict_contributions(models, dmatrix, preference),
        )

    def score_routes_typed(self, request: ModelScoringRequest) -> dict[str, Any]:
        started = time.perf_counter()
        results = [self.score_route(route, preference=request.preference) for route in request.routes]
        return {
            "contract_version": CONTRACT_VERSION,
            "request_id": request.request_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "scoring_model": self.model_key,
            "results": [result.to_dict() for result in results],
            "warnings": [],
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


def score_routes_typed(request: ModelScoringRequest) -> dict[str, Any]:
    return XGBoostRouteScoringModel().score_routes_typed(request)


def score_routes(payload: dict[str, Any], *, strict_backend: bool = False) -> dict[str, Any]:
    request = ModelScoringRequest.from_dict(payload, strict_backend=strict_backend)
    return score_routes_typed(request)
