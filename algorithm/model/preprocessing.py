"""Feature preprocessing for model-facing route payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


LOAD_SCORE_BY_CODE = {
    "SEA": 100.0,
    "SDA": 70.0,
    "LSD": 35.0,
    "UNKNOWN": 60.0,
}

FLOW_SCORE_BY_LEVEL = {
    "low": 90.0,
    "medium": 70.0,
    "high": 45.0,
}

MODEL_SCORE_FIELDS = {
    "load_score",
    "history_flow_score",
    "congestion_score",
    "data_freshness_seconds",
    "monitored_score",
    "completeness_score",
}

REQUIRED_BACKEND_FIELDS = {
    "load_code",
    "station_flow_level",
    "route_speed_band",
    "monitored",
    "source_updated_at",
    "degraded_fields",
}


class PreprocessingError(ValueError):
    """Raised when backend-facing payload preprocessing fails."""


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    return False


def _to_float(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number in (float("inf"), float("-inf")) or number != number:
        return None
    return number


def _clip_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def load_score_from_code(load_code: Any) -> float:
    code = str(load_code or "UNKNOWN").strip().upper()
    return LOAD_SCORE_BY_CODE.get(code, LOAD_SCORE_BY_CODE["UNKNOWN"])


def congestion_score_from_speed_band(speed_band: Any) -> float | None:
    number = _to_float(speed_band)
    if number is None:
        return None
    band = int(number)
    if band <= 0:
        return None
    # LTA SpeedBand: 1 is slowest, 8 is fastest. Model uses a 0-100 smoothness score.
    return _clip_score(30.0 + (max(1, min(8, band)) - 1) * 10.0)


def congestion_score_from_pressure(pressure: Any) -> float | None:
    number = _to_float(pressure)
    if number is None:
        return None
    if number <= 1.0:
        return _clip_score(100.0 - number * 70.0)
    return _clip_score(number)


def history_flow_score_from_level(level: Any) -> float | None:
    text = str(level or "").strip().lower()
    if not text:
        return None
    return FLOW_SCORE_BY_LEVEL.get(text, 60.0)


def monitored_score_from_flag(monitored: Any) -> float | None:
    number = _to_float(monitored)
    if number is None:
        return None
    return 100.0 if number >= 1 else 75.0


def _parse_datetime(value: Any) -> datetime | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def data_freshness_seconds_from_timestamp(value: Any, *, now: datetime | None = None) -> float | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return round(max(0.0, (current - parsed.astimezone(timezone.utc)).total_seconds()), 2)


def completeness_score_from_degraded_fields(value: Any) -> float:
    if isinstance(value, list):
        fields = [str(item).strip() for item in value if str(item).strip()]
    else:
        fields = [item for item in str(value or "").split("|") if item]
    return round(max(55.0, 100.0 - len(dict.fromkeys(fields)) * 6.0), 2)


def _append_degraded(route: dict[str, Any], field: str) -> None:
    degraded = route.get("degraded_fields")
    if degraded is None:
        items: list[str] = []
    elif isinstance(degraded, list):
        items = [str(item).strip() for item in degraded if str(item).strip()]
    else:
        items = [item for item in str(degraded).split("|") if item]
    if field not in items:
        items.append(field)
    route["degraded_fields"] = items


def _source_map(route: dict[str, Any]) -> dict[str, str]:
    sources = route.get("feature_sources")
    if isinstance(sources, dict):
        return {str(key): str(value) for key, value in sources.items()}
    return {}


def _set_source(route: dict[str, Any], field: str, source: str) -> None:
    sources = _source_map(route)
    sources.setdefault(field, source)
    route["feature_sources"] = sources


def _validate_backend_payload(route: dict[str, Any]) -> None:
    forbidden = sorted(field for field in MODEL_SCORE_FIELDS if field in route)
    if forbidden:
        raise PreprocessingError(
            "backend payload must not include model score fields: " + ", ".join(forbidden)
        )

    missing = sorted(field for field in REQUIRED_BACKEND_FIELDS if _is_missing(route.get(field)))
    if missing:
        raise PreprocessingError("backend payload missing required raw fields: " + ", ".join(missing))

    if not isinstance(route.get("degraded_fields"), list):
        raise PreprocessingError("degraded_fields must be a list")


def preprocess_route_payload(route_payload: dict[str, Any], *, strict_backend: bool = False) -> dict[str, Any]:
    """Normalize a backend route payload into model-ready 12-feature payload.

    后端负责生成候选路线和聚合原始业务字段；这里统一做轻量映射，避免后端散落
    `SEA -> 100`、`SpeedBand -> 通畅分` 这类模型特征规则。
    """

    route = dict(route_payload)
    if strict_backend:
        _validate_backend_payload(route)

    route.setdefault("load_code", "UNKNOWN")

    if _is_missing(route.get("load_score")):
        route["load_score"] = load_score_from_code(route.get("load_code"))
        _set_source(route, "load_score", "lta_realtime")

    if _is_missing(route.get("congestion_score")):
        score = None
        speed_keys = ("route_speed_band",) if strict_backend else ("speed_band", "route_speed_band", "SpeedBand")
        for key in speed_keys:
            score = congestion_score_from_speed_band(route.get(key))
            if score is not None:
                break
        if score is None:
            score = congestion_score_from_pressure(route.get("congestion_pressure"))
        if score is not None:
            route["congestion_score"] = score
            _set_source(route, "congestion_score", "cache")

    if _is_missing(route.get("history_flow_score")):
        score = None
        flow_keys = ("station_flow_level",) if strict_backend else ("station_flow_level", "history_flow_level", "flow_level")
        for key in flow_keys:
            score = history_flow_score_from_level(route.get(key))
            if score is not None:
                break
        if score is not None:
            route["history_flow_score"] = score
            _set_source(route, "history_flow_score", "historical")

    if _is_missing(route.get("monitored_score")):
        score = monitored_score_from_flag(route.get("monitored"))
        if score is not None:
            route["monitored_score"] = score
            _set_source(route, "monitored_score", "lta_realtime")

    if _is_missing(route.get("data_freshness_seconds")):
        freshness = None
        time_keys = ("source_updated_at",) if strict_backend else ("source_updated_at", "cache_updated_at", "query_time")
        for key in time_keys:
            freshness = data_freshness_seconds_from_timestamp(route.get(key))
            if freshness is not None:
                break
        if freshness is not None:
            route["data_freshness_seconds"] = freshness
            _set_source(route, "data_freshness_seconds", "cache")

    if _is_missing(route.get("completeness_score")):
        route["completeness_score"] = completeness_score_from_degraded_fields(route.get("degraded_fields"))
        _set_source(route, "completeness_score", "rule_estimate")

    if "feature_sources" not in route or not isinstance(route["feature_sources"], dict):
        route["feature_sources"] = {}

    return route
