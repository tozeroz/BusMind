"""Typed contracts for BusMind recommendation inference."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from algorithm.recommend.source import FeatureSource


PREFERENCE_NAMES = (
    "balanced",
    "fastest",
    "low_load",
    "less_walking",
    "less_transfer",
)

OUTPUT_RECOMMEND_TYPES = (
    "best_experience",
    "fastest",
    "least_crowded",
    "least_walking",
    "least_transfer",
)

ALLOWED_LOAD_CODES = {"SEA", "SDA", "LSD"}
ALLOWED_FLOW_LEVELS = {"low", "medium", "high"}


class RecommendationValidationError(ValueError):
    """Raised when an incoming recommendation payload is invalid."""


def _error(field_name: str, message: str) -> RecommendationValidationError:
    return RecommendationValidationError(f"{field_name}: {message}")


def _coerce_str(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if value is None:
        raise _error(field_name, "is required")
    text = str(value).strip()
    if not text and not allow_empty:
        raise _error(field_name, "must not be empty")
    return text


def _coerce_optional_str(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_float(value: Any, field_name: str, *, minimum: float | None = None) -> float:
    if value is None:
        raise _error(field_name, "is required")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise _error(field_name, "must be numeric") from exc
    if minimum is not None and result < minimum:
        raise _error(field_name, f"must be >= {minimum}")
    return result


def _coerce_optional_float(value: Any, field_name: str, *, minimum: float | None = None) -> float | None:
    if value is None or value == "":
        return None
    return _coerce_float(value, field_name, minimum=minimum)


def _coerce_int(value: Any, field_name: str, *, minimum: int | None = None) -> int:
    if value is None:
        raise _error(field_name, "is required")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise _error(field_name, "must be an integer") from exc
    if minimum is not None and result < minimum:
        raise _error(field_name, f"must be >= {minimum}")
    return result


def _coerce_optional_list_of_str(value: Any, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise _error(field_name, "must be a list")
    items = [str(item).strip() for item in value if str(item).strip()]
    return tuple(items)


def _coerce_preference(value: Any) -> str:
    text = _coerce_str(value, "preference")
    if text not in PREFERENCE_NAMES:
        raise _error("preference", f"must be one of {', '.join(PREFERENCE_NAMES)}")
    return text


def _coerce_load_code(value: Any) -> str | None:
    text = _coerce_optional_str(value, "load_code")
    if text is None:
        return None
    text = text.upper()
    if text not in ALLOWED_LOAD_CODES:
        raise _error("load_code", f"must be one of {', '.join(sorted(ALLOWED_LOAD_CODES))}")
    return text


def _coerce_flow_level(value: Any) -> str | None:
    text = _coerce_optional_str(value, "station_flow_level")
    if text is None:
        return None
    lowered = text.lower()
    if lowered not in ALLOWED_FLOW_LEVELS:
        raise _error("station_flow_level", f"must be one of {', '.join(sorted(ALLOWED_FLOW_LEVELS))}")
    return lowered


def _coerce_confidence(value: Any) -> float | None:
    score = _coerce_optional_float(value, "confidence", minimum=0.0)
    if score is None:
        return None
    if score > 1.0:
        return min(score / 100.0, 1.0)
    return min(score, 1.0)


@dataclass(frozen=True, slots=True)
class ReasonFactors:
    eta_reason: str
    comfort_reason: str
    walk_reason: str
    transfer_reason: str
    frequency_reason: str
    flow_reason: str
    congestion_reason: str
    reliability_reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "eta_reason": self.eta_reason,
            "comfort_reason": self.comfort_reason,
            "walk_reason": self.walk_reason,
            "transfer_reason": self.transfer_reason,
            "frequency_reason": self.frequency_reason,
            "flow_reason": self.flow_reason,
            "congestion_reason": self.congestion_reason,
            "reliability_reason": self.reliability_reason,
        }


@dataclass(frozen=True, slots=True)
class RouteFeature:
    route_id: str
    service_no: str | None = None
    line_ids: tuple[str, ...] = field(default_factory=tuple)
    eta_minutes: float | None = None
    load_code: str | None = None
    load_score: float | None = None
    walk_time_minutes: float = 0.0
    ride_time_minutes: float = 0.0
    transfer_count: int = 0
    avg_service_frequency: float | None = None
    station_flow_mean: float | None = None
    station_flow_level: str | None = None
    congestion_score: float | None = None
    reliability_score: float | None = None
    confidence: float | None = None
    data_source: str = "unknown"

    def __post_init__(self) -> None:
        if not self.service_no and not self.line_ids:
            raise _error("service_no", "either service_no or line_ids must be provided")

    @property
    def total_time_minutes(self) -> float:
        return round((self.eta_minutes or 0.0) + self.ride_time_minutes, 2)

    @property
    def normalized_congestion_pressure(self) -> float:
        if self.congestion_score is None:
            return 0.5
        if self.congestion_score <= 1.0:
            return max(0.0, min(1.0, self.congestion_score))
        return max(0.0, min(1.0, self.congestion_score / 100.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "service_no": self.service_no,
            "line_ids": list(self.line_ids),
            "eta_minutes": self.eta_minutes,
            "load_code": self.load_code,
            "load_score": self.load_score,
            "walk_time_minutes": self.walk_time_minutes,
            "ride_time_minutes": self.ride_time_minutes,
            "transfer_count": self.transfer_count,
            "avg_service_frequency": self.avg_service_frequency,
            "station_flow_mean": self.station_flow_mean,
            "station_flow_level": self.station_flow_level,
            "congestion_score": self.congestion_score,
            "reliability_score": self.reliability_score,
            "confidence": self.confidence,
            "data_source": self.data_source,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RouteFeature":
        if not isinstance(payload, dict):
            raise _error("routes[]", "each route must be a dict")
        return cls(
            route_id=_coerce_str(payload.get("route_id"), "route_id"),
            service_no=_coerce_optional_str(payload.get("service_no"), "service_no"),
            line_ids=_coerce_optional_list_of_str(payload.get("line_ids"), "line_ids"),
            eta_minutes=_coerce_optional_float(payload.get("eta_minutes"), "eta_minutes", minimum=0.0),
            load_code=_coerce_load_code(payload.get("load_code")),
            load_score=_coerce_optional_float(payload.get("load_score"), "load_score", minimum=0.0),
            walk_time_minutes=_coerce_float(payload.get("walk_time_minutes", 0.0), "walk_time_minutes", minimum=0.0),
            ride_time_minutes=_coerce_float(payload.get("ride_time_minutes", 0.0), "ride_time_minutes", minimum=0.0),
            transfer_count=_coerce_int(payload.get("transfer_count", 0), "transfer_count", minimum=0),
            avg_service_frequency=_coerce_optional_float(
                payload.get("avg_service_frequency"),
                "avg_service_frequency",
                minimum=0.0,
            ),
            station_flow_mean=_coerce_optional_float(payload.get("station_flow_mean"), "station_flow_mean", minimum=0.0),
            station_flow_level=_coerce_flow_level(payload.get("station_flow_level")),
            congestion_score=_coerce_optional_float(payload.get("congestion_score"), "congestion_score", minimum=0.0),
            reliability_score=_coerce_optional_float(
                payload.get("reliability_score"),
                "reliability_score",
                minimum=0.0,
            ),
            confidence=_coerce_confidence(payload.get("confidence")),
            data_source=_coerce_str(payload.get("data_source", "unknown"), "data_source", allow_empty=False),
        )


@dataclass(frozen=True, slots=True)
class RecommendationInput:
    preference: str
    routes: tuple[RouteFeature, ...]
    feature_source: FeatureSource = FeatureSource.ONLINE_BACKEND

    def to_dict(self) -> dict[str, Any]:
        return {
            "preference": self.preference,
            "feature_source": self.feature_source.value,
            "routes": [route.to_dict() for route in self.routes],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RecommendationInput":
        if not isinstance(payload, dict):
            raise RecommendationValidationError("payload must be a dict")
        routes_raw = payload.get("routes")
        if not isinstance(routes_raw, list) or not routes_raw:
            raise _error("routes", "must be a non-empty list")
        routes = tuple(RouteFeature.from_dict(item) for item in routes_raw)
        return cls(
            preference=_coerce_preference(payload.get("preference", "balanced")),
            routes=routes,
            feature_source=FeatureSource.coerce(payload.get("feature_source")),
        )


@dataclass(frozen=True, slots=True)
class ScoredRoute:
    route_id: str
    time_score: float
    comfort_score: float
    walk_score: float
    transfer_score: float
    frequency_score: float
    flow_score: float
    congestion_score: float
    reliability_score: float
    recommend_score: float
    recommend_types: tuple[str, ...]
    reason_factors: ReasonFactors

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "time_score": self.time_score,
            "comfort_score": self.comfort_score,
            "walk_score": self.walk_score,
            "transfer_score": self.transfer_score,
            "frequency_score": self.frequency_score,
            "flow_score": self.flow_score,
            "congestion_score": self.congestion_score,
            "reliability_score": self.reliability_score,
            "recommend_score": self.recommend_score,
            "recommend_types": list(self.recommend_types),
            "reason_factors": self.reason_factors.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RecommendationOutput:
    best_experience_route_id: str
    fastest_route_id: str
    least_crowded_route_id: str
    least_walking_route_id: str
    least_transfer_route_id: str
    items: tuple[ScoredRoute, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_experience_route_id": self.best_experience_route_id,
            "fastest_route_id": self.fastest_route_id,
            "least_crowded_route_id": self.least_crowded_route_id,
            "least_walking_route_id": self.least_walking_route_id,
            "least_transfer_route_id": self.least_transfer_route_id,
            "items": [item.to_dict() for item in self.items],
        }
