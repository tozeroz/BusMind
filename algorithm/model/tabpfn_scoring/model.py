"""TabPFN candidate route scoring model."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

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
METADATA_PATH = ARTIFACT_DIR / "tabpfn_route_scoring.json"


class TabPFNArtifactError(RuntimeError):
    """Raised when the TabPFN artifact is unavailable or invalid."""


def _import_tabpfn_regressor():
    try:
        from tabpfn import TabPFNRegressor
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise TabPFNArtifactError(
            "tabpfn is not installed. Install it with `uv sync --extra algorithm --extra tabpfn`."
        ) from exc
    return TabPFNRegressor


def _read_metadata(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise TabPFNArtifactError(
            f"TabPFN artifact not found: {path}. "
            "Train it with `python algorithm/model/tabpfn_scoring/train.py`."
        )
    try:
        with path.open("r", encoding="utf-8") as file:
            metadata = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise TabPFNArtifactError(f"Cannot read TabPFN artifact metadata: {path}") from exc
    if metadata.get("feature_names") != list(NUMERIC_FEATURE_NAMES):
        raise TabPFNArtifactError("TabPFN artifact feature_names do not match the current model contract")
    if metadata.get("score_names") != list(SCORE_NAMES):
        raise TabPFNArtifactError("TabPFN artifact score_names do not match the current model contract")
    return metadata


def _context_path(metadata_path: Path, metadata: dict[str, Any]) -> Path:
    context_file = metadata.get("context_file")
    if not context_file:
        raise TabPFNArtifactError("TabPFN artifact metadata missing context_file")
    path = metadata_path.parent / str(context_file)
    if not path.is_file():
        raise TabPFNArtifactError(f"TabPFN context file not found: {path}")
    return path


def _fit_regressors(metadata_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    metadata = _read_metadata(metadata_path)
    context = np.load(_context_path(metadata_path, metadata), allow_pickle=False)
    feature_names = list(NUMERIC_FEATURE_NAMES)
    x_train = pd.DataFrame(context["x_train"], columns=feature_names)
    y_train = np.asarray(context["y_train"], dtype=float)
    if y_train.shape[1] != len(SCORE_NAMES):
        raise TabPFNArtifactError("TabPFN context y_train has invalid shape")

    Regressor = _import_tabpfn_regressor()
    models: dict[str, Any] = {}
    for index, score_name in enumerate(SCORE_NAMES):
        model = Regressor()
        model.fit(x_train, y_train[:, index])
        models[score_name] = model
    return metadata, models


@lru_cache(maxsize=2)
def _load_artifact(metadata_path_text: str = str(METADATA_PATH)) -> tuple[dict[str, Any], dict[str, Any]]:
    return _fit_regressors(Path(metadata_path_text))


def _feature_frame(route: RouteFeatures) -> pd.DataFrame:
    return pd.DataFrame([route.numeric_vector()], columns=list(NUMERIC_FEATURE_NAMES))


def _predict_contributions(preference: str) -> dict[str, float]:
    # TabPFN does not expose cheap per-row feature attributions in the core package.
    return {feature: 0.0 for feature in NUMERIC_FEATURE_NAMES}


class TabPFNRouteScoringModel:
    model_key = "tabpfn"
    model_name = MODEL_NAME
    model_version = MODEL_VERSION

    def __init__(self, artifact_path: Path = METADATA_PATH) -> None:
        self.artifact_path = artifact_path

    def _artifact(self) -> tuple[dict[str, Any], dict[str, Any]]:
        return _load_artifact(str(self.artifact_path))

    def score_route(self, route: RouteFeatures, *, preference: str) -> ScoreResult:
        _metadata, models = self._artifact()
        x = _feature_frame(route)
        five_scores = np.array(
            [float(models[score_name].predict(x)[0]) for score_name in SCORE_NAMES],
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
            feature_contributions=_predict_contributions(preference),
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
            "warnings": ["tabpfn_feature_contributions_unavailable"],
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


def score_routes_typed(request: ModelScoringRequest) -> dict[str, Any]:
    return TabPFNRouteScoringModel().score_routes_typed(request)


def score_routes(payload: dict[str, Any], *, strict_backend: bool = False) -> dict[str, Any]:
    request = ModelScoringRequest.from_dict(payload, strict_backend=strict_backend)
    return score_routes_typed(request)
