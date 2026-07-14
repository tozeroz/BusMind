"""BusMind 模型包。

这里保持包初始化尽量轻量，避免 dataset 工具导入 contracts 时触发 predictor，
从而形成 `dataset.scripts.feature_contract -> model -> predictor -> dataset.scripts.feature_contract` 的循环导入。
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
    if name == "PREFERENCE_MIX":
        from algorithm.model.utils.score_mixing import PREFERENCE_MIX

        return PREFERENCE_MIX
    if name in {"score_routes", "score_routes_typed"}:
        from algorithm.model import register

        return getattr(register, name)
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
