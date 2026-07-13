"""BusMind model package.

这里保持包初始化尽量轻量，避免 dataset 工具导入 contracts 时触发 predictor，
从而形成 `dataset.scripts.recommendation_feature_contract -> model -> predictor -> dataset.scripts.recommendation_feature_contract` 的循环导入。
"""

from algorithm.model.contracts import (
    CONTRACT_VERSION,
    MODEL_NAME,
    MODEL_VERSION,
    NUMERIC_FEATURE_NAMES,
    PREFERENCE_NAMES,
    ModelContractError,
    ModelScoringRequest,
    RouteFeatures,
    ScoreResult,
)


def __getattr__(name: str):
    if name == "predict_recommendation":
        from algorithm.model.predictor import predict_recommendation

        return predict_recommendation
    if name == "preprocess_route_payload":
        from algorithm.model.preprocessing import preprocess_route_payload

        return preprocess_route_payload
    if name in {"PREFERENCE_MIX", "score_routes", "score_routes_typed"}:
        from algorithm.model import scorer

        return getattr(scorer, name)
    raise AttributeError(f"module 'algorithm.model' has no attribute {name!r}")

__all__ = [
    "CONTRACT_VERSION",
    "MODEL_NAME",
    "MODEL_VERSION",
    "NUMERIC_FEATURE_NAMES",
    "PREFERENCE_NAMES",
    "ModelContractError",
    "ModelScoringRequest",
    "RouteFeatures",
    "ScoreResult",
    "PREFERENCE_MIX",
    "preprocess_route_payload",
    "predict_recommendation",
    "score_routes",
    "score_routes_typed",
]
