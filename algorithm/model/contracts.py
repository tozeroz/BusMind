"""Contracts for the BusMind route scoring model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from algorithm.model.preprocessing import PreprocessingError, preprocess_route_payload


CONTRACT_VERSION = "1.0.0"
MODEL_NAME = "busmind-route-scorer"
MODEL_VERSION = "0.1.0"

PREFERENCE_NAMES = (
    "balanced",
    "fastest",
    "comfort",
    "less_walking",
    "less_transfer",
)

PREFERENCE_ALIASES = {
    "low_load": "comfort",
}

LOAD_CODES = {"SEA", "SDA", "LSD", "UNKNOWN"}
SOURCE_NAMES = {"lta_realtime", "cache", "database", "historical", "rule_estimate", "model", "default"}

NUMERIC_FEATURE_NAMES = (
    "eta_minutes",
    "ride_time_minutes",
    "walk_time_minutes",
    "walk_distance_meters",
    "transfer_count",
    "load_score",
    "history_flow_score",
    "congestion_score",
    "data_freshness_seconds",
    "monitored_score",
    "completeness_score",
    "avg_service_frequency_minutes",
)


class ModelContractError(ValueError):
    """Raised when a model scoring payload violates the contract."""


def _contract_error(field: str, message: str) -> ModelContractError:
    return ModelContractError(f"{field}: {message}")


def _coerce_str(value: Any, field: str) -> str:
    if value is None:
        raise _contract_error(field, "is required")
    text = str(value).strip()
    if not text:
        raise _contract_error(field, "must not be empty")
    return text


def _coerce_float(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if value is None:
        raise _contract_error(field, "is required")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise _contract_error(field, "must be numeric") from exc
    if number < minimum:
        raise _contract_error(field, f"must be >= {minimum}")
    if number in (float("inf"), float("-inf")) or number != number:
        raise _contract_error(field, "must be finite")
    return number


def _coerce_int(value: Any, field: str, *, minimum: int = 0) -> int:
    number = _coerce_float(value, field, minimum=float(minimum))
    if int(number) != number:
        raise _contract_error(field, "must be an integer")
    return int(number)


def normalize_preference(value: Any) -> str:
    preference = _coerce_str(value or "balanced", "preference").lower()
    preference = PREFERENCE_ALIASES.get(preference, preference)
    if preference not in PREFERENCE_NAMES:
        raise _contract_error("preference", f"must be one of {', '.join(PREFERENCE_NAMES)}")
    return preference


def _coerce_service_nos(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _contract_error("service_nos", "must be a non-empty list")
    items = tuple(str(item).strip() for item in value if str(item).strip())
    if not items:
        raise _contract_error("service_nos", "must contain at least one service number")
    return items


def _coerce_load_code(value: Any) -> str:
    code = _coerce_str(value or "UNKNOWN", "load_code").upper()
    if code not in LOAD_CODES:
        raise _contract_error("load_code", f"must be one of {', '.join(sorted(LOAD_CODES))}")
    return code


def _coerce_sources(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise _contract_error("feature_sources", "must be an object")
    output: dict[str, str] = {}
    for key, raw_source in value.items():
        source = str(raw_source).strip()
        if source not in SOURCE_NAMES:
            raise _contract_error(f"feature_sources.{key}", f"must be one of {', '.join(sorted(SOURCE_NAMES))}")
        output[str(key)] = source
    return output


def _coerce_string_list(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise _contract_error(field, "must be a list")
    return tuple(str(item).strip() for item in value if str(item).strip())


@dataclass(frozen=True, slots=True)
class RouteFeatures:
    route_id: str
    service_nos: tuple[str, ...]
    eta_minutes: float
    ride_time_minutes: float
    walk_time_minutes: float
    walk_distance_meters: float
    transfer_count: int
    load_code: str
    load_score: float
    history_flow_score: float
    congestion_score: float
    data_freshness_seconds: float
    monitored_score: float
    completeness_score: float
    avg_service_frequency_minutes: float
    feature_sources: dict[str, str] = field(default_factory=dict)
    degraded_fields: tuple[str, ...] = field(default_factory=tuple)

    def numeric_vector(self) -> list[float]:
        return [
            self.eta_minutes,
            self.ride_time_minutes,
            self.walk_time_minutes,
            self.walk_distance_meters,
            float(self.transfer_count),
            self.load_score,
            self.history_flow_score,
            self.congestion_score,
            self.data_freshness_seconds,
            self.monitored_score,
            self.completeness_score,
            self.avg_service_frequency_minutes,
        ]

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, strict_backend: bool = False) -> "RouteFeatures":
        if not isinstance(payload, dict):
            raise _contract_error("routes[]", "each route must be an object")
        try:
            payload = preprocess_route_payload(payload, strict_backend=strict_backend)
        except PreprocessingError as exc:
            raise _contract_error("routes[]", str(exc)) from exc
        return cls(
            route_id=_coerce_str(payload.get("route_id"), "route_id"),
            service_nos=_coerce_service_nos(payload.get("service_nos")),
            eta_minutes=_coerce_float(payload.get("eta_minutes"), "eta_minutes"),
            ride_time_minutes=_coerce_float(payload.get("ride_time_minutes"), "ride_time_minutes"),
            walk_time_minutes=_coerce_float(payload.get("walk_time_minutes"), "walk_time_minutes"),
            walk_distance_meters=_coerce_float(payload.get("walk_distance_meters"), "walk_distance_meters"),
            transfer_count=_coerce_int(payload.get("transfer_count"), "transfer_count"),
            load_code=_coerce_load_code(payload.get("load_code")),
            load_score=_coerce_float(payload.get("load_score"), "load_score"),
            history_flow_score=_coerce_float(payload.get("history_flow_score"), "history_flow_score"),
            congestion_score=_coerce_float(payload.get("congestion_score"), "congestion_score"),
            data_freshness_seconds=_coerce_float(
                payload.get("data_freshness_seconds"),
                "data_freshness_seconds",
            ),
            monitored_score=_coerce_float(payload.get("monitored_score"), "monitored_score"),
            completeness_score=_coerce_float(payload.get("completeness_score"), "completeness_score"),
            avg_service_frequency_minutes=_coerce_float(
                payload.get("avg_service_frequency_minutes"),
                "avg_service_frequency_minutes",
            ),
            feature_sources=_coerce_sources(payload.get("feature_sources")),
            degraded_fields=_coerce_string_list(payload.get("degraded_fields"), "degraded_fields"),
        )


@dataclass(frozen=True, slots=True)
class ModelScoringRequest:
    contract_version: str
    request_id: str
    preference: str
    routes: tuple[RouteFeatures, ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any], *, strict_backend: bool = False) -> "ModelScoringRequest":
        if not isinstance(payload, dict):
            raise ModelContractError("payload must be an object")
        if "weights" in payload:
            raise _contract_error("weights", "is not supported; use preference")
        contract_version = _coerce_str(payload.get("contract_version", CONTRACT_VERSION), "contract_version")
        if contract_version != CONTRACT_VERSION:
            raise _contract_error("contract_version", f"must be {CONTRACT_VERSION}")
        routes_raw = payload.get("routes")
        if not isinstance(routes_raw, list) or not routes_raw:
            raise _contract_error("routes", "must be a non-empty list")
        if len(routes_raw) > 10:
            raise _contract_error("routes", "must contain at most 10 routes")
        return cls(
            contract_version=contract_version,
            request_id=_coerce_str(payload.get("request_id"), "request_id"),
            preference=normalize_preference(payload.get("preference", "balanced")),
            routes=tuple(RouteFeatures.from_dict(route, strict_backend=strict_backend) for route in routes_raw),
        )


@dataclass(frozen=True, slots=True)
class ScoreResult:
    route_id: str
    time_score: float
    comfort_score: float
    walk_score: float
    transfer_score: float
    reliability_score: float
    recommend_score: float
    feature_contributions: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "time_score": self.time_score,
            "comfort_score": self.comfort_score,
            "walk_score": self.walk_score,
            "transfer_score": self.transfer_score,
            "reliability_score": self.reliability_score,
            "recommend_score": self.recommend_score,
            "feature_contributions": self.feature_contributions,
        }
