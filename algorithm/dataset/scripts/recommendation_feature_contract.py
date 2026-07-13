"""Contract utilities for the frozen recommendation feature dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from algorithm.model.contracts import NUMERIC_FEATURE_NAMES, RouteFeatures


FROZEN_FEATURE_COLUMNS = (
    "candidate_group_id",
    "route_id",
    "service_nos",
    "eta_minutes",
    "ride_time_minutes",
    "walk_time_minutes",
    "walk_distance_meters",
    "transfer_count",
    "avg_service_frequency_minutes",
    "load_code",
    "station_flow_level",
    "route_speed_band",
    "source_updated_at",
    "monitored",
    "degraded_fields",
    "feature_sources",
    "is_synthetic",
)

MODEL_INTERNAL_COLUMNS = {
    "load_score",
    "history_flow_score",
    "congestion_score",
    "data_freshness_seconds",
    "monitored_score",
    "completeness_score",
}


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _load_json(value: Any, *, default: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    if isinstance(value, (list, dict)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def parse_json_list(value: Any) -> list[str]:
    parsed = _load_json(value, default=[])
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    # Compatibility for old pipe-delimited temporary files.
    return [item for item in str(value or "").split("|") if item]


def parse_json_object(value: Any) -> dict[str, str]:
    parsed = _load_json(value, default={})
    if isinstance(parsed, dict):
        return {str(key): str(item) for key, item in parsed.items()}
    output: dict[str, str] = {}
    for part in str(value or "").split("|"):
        if ":" not in part:
            continue
        key, source = part.split(":", 1)
        output[key] = source
    return output


def validate_frozen_feature_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in FROZEN_FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError("features.csv missing frozen columns: " + ", ".join(missing))
    forbidden = sorted(column for column in MODEL_INTERNAL_COLUMNS if column in frame.columns)
    if forbidden:
        raise ValueError("features.csv contains model-internal columns: " + ", ".join(forbidden))


def model_input_route_from_feature_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "route_id": row["route_id"],
        "service_nos": parse_json_list(row["service_nos"]),
        "eta_minutes": row["eta_minutes"],
        "ride_time_minutes": row["ride_time_minutes"],
        "walk_time_minutes": row["walk_time_minutes"],
        "walk_distance_meters": row["walk_distance_meters"],
        "transfer_count": row["transfer_count"],
        "avg_service_frequency_minutes": row["avg_service_frequency_minutes"],
        "load_code": row["load_code"],
        "station_flow_level": row["station_flow_level"],
        "route_speed_band": row["route_speed_band"],
        "source_updated_at": row["source_updated_at"],
        "monitored": row["monitored"],
        "degraded_fields": parse_json_list(row["degraded_fields"]),
        "feature_sources": parse_json_object(row["feature_sources"]),
    }


def model_input_routes_from_feature_group(group: pd.DataFrame) -> list[dict[str, Any]]:
    return [model_input_route_from_feature_row(row) for row in group.to_dict("records")]


def numeric_feature_frame(features: pd.DataFrame) -> pd.DataFrame:
    validate_frozen_feature_columns(features)
    rows: list[dict[str, Any]] = []
    for row in features.to_dict("records"):
        payload = model_input_route_from_feature_row(row)
        route = RouteFeatures.from_dict(payload, strict_backend=True)
        numeric = dict(zip(NUMERIC_FEATURE_NAMES, route.numeric_vector(), strict=True))
        numeric["candidate_group_id"] = row["candidate_group_id"]
        numeric["route_id"] = row["route_id"]
        rows.append(numeric)
    return pd.DataFrame(rows)


def read_frozen_features(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    validate_frozen_feature_columns(frame)
    return frame
