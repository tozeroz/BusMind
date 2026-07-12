"""Shared data loaders and feature builders for recommendation training."""

from __future__ import annotations

import hashlib
import json
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


BUS_PROPS = ("NextBus", "NextBus2", "NextBus3")
LOAD_SCORE_BY_CODE = {
    "SEA": 100.0,
    "SDA": 70.0,
    "LSD": 35.0,
    "UNKNOWN": 60.0,
}


@dataclass(frozen=True, slots=True)
class DatasetBundle:
    bus_station: pd.DataFrame
    bus_line: pd.DataFrame
    line_station: pd.DataFrame
    passenger_flow_trend: pd.DataFrame
    lta_bus_arrival: pd.DataFrame
    traffic_speed_bands: pd.DataFrame


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_raw_dir() -> Path:
    return project_root() / "data" / "raw" / "lta"


def default_processed_dir() -> Path:
    return project_root() / "data" / "processed"


def default_model_dir() -> Path:
    return project_root() / "algorithm" / "model" / "artifacts"


def default_dataset_dir() -> Path:
    return project_root() / "algorithm" / "dataset" / "recommendation" / "v1"


def normalize_stop_code(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5) if text else ""


def stop_code_to_station_id(value: Any) -> int | None:
    code = normalize_stop_code(value)
    if not code:
        return None
    try:
        return int(code)
    except ValueError:
        return None


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = _read_json(path)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("value"), list):
        return payload["value"]
    raise ValueError(f"Unsupported JSON payload at {path}")


def _first_zip_csv(zip_path: Path) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as archive:
        csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise FileNotFoundError(f"No CSV found inside {zip_path}")
        with archive.open(csv_names[0]) as file:
            return pd.read_csv(file, dtype=str)


def _parse_frequency_range(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    if "-" in text:
        left, right = text.split("-", 1)
        try:
            return (float(left) + float(right)) / 2.0
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _flow_level(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    if numeric.empty:
        return pd.Series(dtype=str)
    high = numeric.quantile(0.75)
    medium = numeric.quantile(0.40)
    return numeric.map(lambda value: "high" if value >= high else ("medium" if value >= medium else "low"))


def traffic_congestion_score(speed_band: Any) -> float | None:
    try:
        band = int(speed_band)
    except (TypeError, ValueError):
        return None
    if band <= 0:
        return None
    return round(min(1.0, max(0.0, (8 - band) / 7.0)), 4)


def _normalize_road_name(value: Any) -> str:
    return " ".join(str(value or "").upper().strip().split())


def _stable_hash(text: str) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)


def _day_type_from_timestamp(timestamp: pd.Timestamp) -> str:
    if timestamp.dayofweek >= 5:
        return "weekend"
    return "weekday"


def load_bus_station(processed_dir: Path, raw_dir: Path) -> pd.DataFrame:
    processed_path = processed_dir / "bus_station.csv"
    if processed_path.exists():
        return pd.read_csv(processed_path)
    stops = pd.DataFrame(_read_json_list(raw_dir / "api_response" / "BusStops_full.json"))
    stops = stops.rename(
        columns={
            "BusStopCode": "bus_stop_code",
            "RoadName": "road_name",
            "Description": "station_name",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )
    stops["bus_stop_code"] = stops["bus_stop_code"].map(normalize_stop_code)
    stops["station_id"] = stops["bus_stop_code"].map(stop_code_to_station_id)
    stops["latitude"] = pd.to_numeric(stops["latitude"], errors="coerce")
    stops["longitude"] = pd.to_numeric(stops["longitude"], errors="coerce")
    stops = stops.dropna(subset=["station_id"]).copy()
    stops["station_id"] = stops["station_id"].astype(int)
    return stops[
        ["station_id", "bus_stop_code", "station_name", "road_name", "latitude", "longitude"]
    ].sort_values("station_id")


def load_bus_line(processed_dir: Path, raw_dir: Path) -> pd.DataFrame:
    processed_path = processed_dir / "bus_line.csv"
    if processed_path.exists():
        return pd.read_csv(processed_path)
    services = pd.DataFrame(_read_json_list(raw_dir / "api_response" / "BusServices_full.json"))
    services = services.rename(
        columns={
            "ServiceNo": "service_no",
            "Operator": "operator",
            "Direction": "direction",
            "Category": "category",
            "OriginCode": "origin_stop_code",
            "DestinationCode": "destination_stop_code",
            "AM_Peak_Freq": "am_peak_freq",
            "AM_Offpeak_Freq": "am_offpeak_freq",
            "PM_Peak_Freq": "pm_peak_freq",
            "PM_Offpeak_Freq": "pm_offpeak_freq",
        }
    )
    services["service_no"] = services["service_no"].astype(str)
    services["direction"] = pd.to_numeric(services["direction"], errors="coerce").astype("Int64")
    services["origin_stop_code"] = services["origin_stop_code"].map(normalize_stop_code)
    services["destination_stop_code"] = services["destination_stop_code"].map(normalize_stop_code)
    services = services.sort_values(["service_no", "direction"]).reset_index(drop=True)
    services["line_id"] = range(1, len(services) + 1)
    frequency_columns = ["am_peak_freq", "am_offpeak_freq", "pm_peak_freq", "pm_offpeak_freq"]
    parsed_frequency = services[frequency_columns].apply(lambda column: column.map(_parse_frequency_range))
    services["avg_service_frequency"] = parsed_frequency.mean(axis=1, skipna=True)
    return services[
        [
            "line_id",
            "service_no",
            "operator",
            "direction",
            "category",
            "origin_stop_code",
            "destination_stop_code",
            "avg_service_frequency",
        ]
    ]


def load_line_station(processed_dir: Path, raw_dir: Path, bus_line: pd.DataFrame) -> pd.DataFrame:
    processed_path = processed_dir / "line_station.csv"
    if processed_path.exists():
        frame = pd.read_csv(processed_path)
        if "line_id" in frame.columns:
            frame["line_id"] = pd.to_numeric(frame["line_id"], errors="coerce").astype("Int64")
        return frame
    routes = pd.DataFrame(_read_json_list(raw_dir / "api_response" / "BusRoutes_full.json"))
    routes = routes.rename(
        columns={
            "ServiceNo": "service_no",
            "Direction": "direction",
            "StopSequence": "stop_sequence",
            "BusStopCode": "bus_stop_code",
            "Distance": "route_distance_km",
        }
    )
    routes["service_no"] = routes["service_no"].astype(str)
    routes["direction"] = pd.to_numeric(routes["direction"], errors="coerce").astype("Int64")
    routes["stop_sequence"] = pd.to_numeric(routes["stop_sequence"], errors="coerce")
    routes["bus_stop_code"] = routes["bus_stop_code"].map(normalize_stop_code)
    routes["station_id"] = routes["bus_stop_code"].map(stop_code_to_station_id)
    routes["route_distance_km"] = pd.to_numeric(routes["route_distance_km"], errors="coerce")
    routes = routes.merge(
        bus_line[["line_id", "service_no", "direction"]],
        on=["service_no", "direction"],
        how="left",
        validate="many_to_one",
    )
    routes = routes.dropna(subset=["line_id", "station_id", "stop_sequence"]).copy()
    routes["line_id"] = routes["line_id"].astype(int)
    routes["station_id"] = routes["station_id"].astype(int)
    return routes[["line_id", "service_no", "stop_sequence", "station_id", "route_distance_km"]]


def load_passenger_flow_trend(processed_dir: Path, raw_dir: Path, month: str | None = None) -> pd.DataFrame:
    processed_path = processed_dir / "passenger_flow_trend.csv"
    if processed_path.exists():
        frame = pd.read_csv(processed_path)
        frame["record_time"] = pd.to_datetime(frame["record_time"], errors="coerce")
        frame["hour"] = frame["record_time"].dt.hour
        frame["station_id"] = pd.to_numeric(frame.get("target_id"), errors="coerce")
        return frame

    month_dir = None
    base_dir = raw_dir / "passenger_volume_stop"
    if month:
        month_dir = base_dir / month
    else:
        month_dirs = [candidate for candidate in base_dir.iterdir() if candidate.is_dir() and candidate.name.isdigit()]
        if not month_dirs:
            raise FileNotFoundError(f"No passenger volume month under {base_dir}")
        month_dir = sorted(month_dirs, key=lambda item: item.name)[-1]
    flow = _first_zip_csv(month_dir / "original.zip").rename(
        columns={
            "YEAR_MONTH": "year_month",
            "DAY_TYPE": "day_type",
            "TIME_PER_HOUR": "hour",
            "PT_CODE": "bus_stop_code",
            "TOTAL_TAP_IN_VOLUME": "tap_in_volume",
            "TOTAL_TAP_OUT_VOLUME": "tap_out_volume",
        }
    )
    flow["bus_stop_code"] = flow["bus_stop_code"].map(normalize_stop_code)
    flow["station_id"] = flow["bus_stop_code"].map(stop_code_to_station_id)
    flow["hour"] = pd.to_numeric(flow["hour"], errors="coerce")
    flow["tap_in_volume"] = pd.to_numeric(flow["tap_in_volume"], errors="coerce").fillna(0.0)
    flow["tap_out_volume"] = pd.to_numeric(flow["tap_out_volume"], errors="coerce").fillna(0.0)
    flow["total_flow"] = flow["tap_in_volume"] + flow["tap_out_volume"]
    flow["day_type"] = flow["day_type"].map(
        lambda value: "weekend" if "WEEKEND" in str(value).upper() or "HOLIDAY" in str(value).upper() else "weekday"
    )
    flow["year_month"] = flow["year_month"].astype(str).str.replace(r"\D", "", regex=True).str[:6]
    flow["record_time"] = pd.to_datetime(flow["year_month"] + "01", format="%Y%m%d", errors="coerce") + pd.to_timedelta(
        flow["hour"], unit="h"
    )
    flow = flow.dropna(subset=["station_id", "hour"]).copy()
    flow["station_id"] = flow["station_id"].astype(int)
    return flow[
        [
            "station_id",
            "bus_stop_code",
            "record_time",
            "day_type",
            "hour",
            "tap_in_volume",
            "tap_out_volume",
            "total_flow",
        ]
    ]


def load_lta_bus_arrival(processed_dir: Path, raw_dir: Path, bus_line: pd.DataFrame) -> pd.DataFrame:
    processed_path = processed_dir / "lta_bus_arrival.csv"
    if processed_path.exists():
        frame = pd.read_csv(processed_path)
        frame["query_time"] = pd.to_datetime(frame["query_time"], errors="coerce")
        return frame

    lookup = bus_line[["line_id", "service_no", "origin_stop_code", "destination_stop_code"]].copy()
    line_by_service = bus_line.drop_duplicates("service_no").set_index("service_no")
    rows: list[dict[str, Any]] = []
    for path in sorted((raw_dir / "bus_arrival_samples").glob("*/*.jsonl")):
        with path.open("r", encoding="utf-8-sig") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                response = record.get("response") or {}
                query_time = pd.to_datetime(record.get("query_time"), errors="coerce")
                bus_stop_code = normalize_stop_code(record.get("bus_stop_code") or response.get("BusStopCode"))
                for service in response.get("Services") or []:
                    service_no = str(service.get("ServiceNo"))
                    for bus_prop in BUS_PROPS:
                        bus = service.get(bus_prop) or {}
                        estimated_arrival = bus.get("EstimatedArrival")
                        if not estimated_arrival:
                            continue
                        rows.append(
                            {
                                "query_time": query_time,
                                "bus_stop_code": bus_stop_code,
                                "station_id": stop_code_to_station_id(bus_stop_code),
                                "service_no": service_no,
                                "visit_order": {"NextBus": 1, "NextBus2": 2, "NextBus3": 3}[bus_prop],
                                "origin_stop_code": normalize_stop_code(bus.get("OriginCode")),
                                "destination_stop_code": normalize_stop_code(bus.get("DestinationCode")),
                                "estimated_arrival": pd.to_datetime(estimated_arrival, errors="coerce", utc=True),
                                "monitored": pd.to_numeric(bus.get("Monitored"), errors="coerce"),
                                "load_code": str(bus.get("Load") or "").upper() or None,
                            }
                        )
    arrival = pd.DataFrame(rows)
    if arrival.empty:
        return arrival
    arrival["estimated_arrival"] = arrival["estimated_arrival"].dt.tz_convert("Asia/Singapore").dt.tz_localize(None)
    arrival["eta_minutes"] = ((arrival["estimated_arrival"] - arrival["query_time"]).dt.total_seconds() / 60.0)
    arrival = arrival[arrival["eta_minutes"].notna() & (arrival["eta_minutes"] >= 0)].copy()
    arrival["load_score"] = arrival["load_code"].map(LOAD_SCORE_BY_CODE)
    arrival = arrival.merge(
        lookup.drop_duplicates(["service_no", "origin_stop_code", "destination_stop_code"]),
        on=["service_no", "origin_stop_code", "destination_stop_code"],
        how="left",
    )
    missing = arrival["line_id"].isna()
    arrival.loc[missing, "line_id"] = arrival.loc[missing, "service_no"].map(line_by_service["line_id"])
    arrival["line_id"] = pd.to_numeric(arrival["line_id"], errors="coerce").astype("Int64")
    return arrival[
        [
            "query_time",
            "station_id",
            "bus_stop_code",
            "service_no",
            "line_id",
            "visit_order",
            "eta_minutes",
            "load_code",
            "load_score",
            "monitored",
        ]
    ]


def load_traffic_speed_bands(processed_dir: Path, raw_dir: Path) -> pd.DataFrame:
    processed_path = processed_dir / "traffic_speed_bands.csv"
    if processed_path.exists():
        frame = pd.read_csv(processed_path)
        frame["query_time"] = pd.to_datetime(frame["query_time"], errors="coerce")
        return frame
    rows: list[dict[str, Any]] = []
    for path in sorted((raw_dir / "traffic_speed_bands").glob("*/*.json")):
        payload = _read_json(path)
        items = payload.get("value") if isinstance(payload, dict) else payload
        query_time = pd.to_datetime((payload or {}).get("query_time"), errors="coerce") if isinstance(payload, dict) else pd.NaT
        for item in items or []:
            rows.append(
                {
                    "query_time": query_time,
                    "link_id": item.get("LinkID"),
                    "road_name": item.get("RoadName"),
                    "speed_band": pd.to_numeric(item.get("SpeedBand"), errors="coerce"),
                    "congestion_score": traffic_congestion_score(item.get("SpeedBand")),
                }
            )
    return pd.DataFrame(rows)


def load_bundle(
    *,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    month: str | None = None,
) -> DatasetBundle:
    processed = (processed_dir or default_processed_dir()).resolve()
    raw = (raw_dir or default_raw_dir()).resolve()
    bus_station = load_bus_station(processed, raw)
    bus_line = load_bus_line(processed, raw)
    line_station = load_line_station(processed, raw, bus_line)
    passenger_flow_trend = load_passenger_flow_trend(processed, raw, month=month)
    lta_bus_arrival = load_lta_bus_arrival(processed, raw, bus_line)
    traffic_speed_bands = load_traffic_speed_bands(processed, raw)
    return DatasetBundle(
        bus_station=bus_station,
        bus_line=bus_line,
        line_station=line_station,
        passenger_flow_trend=passenger_flow_trend,
        lta_bus_arrival=lta_bus_arrival,
        traffic_speed_bands=traffic_speed_bands,
    )


def _remaining_distance_lookup(line_station: pd.DataFrame) -> pd.DataFrame:
    frame = line_station.copy()
    frame["route_distance_km"] = pd.to_numeric(frame["route_distance_km"], errors="coerce")
    max_distance = frame.groupby("line_id", as_index=False)["route_distance_km"].max().rename(
        columns={"route_distance_km": "line_total_distance_km"}
    )
    frame = frame.merge(max_distance, on="line_id", how="left")
    frame["remaining_distance_km"] = (frame["line_total_distance_km"] - frame["route_distance_km"]).clip(lower=1.5)
    return (
        frame.groupby(["line_id", "station_id"], as_index=False)["remaining_distance_km"]
        .median()
        .sort_values(["line_id", "station_id"])
    )


def _station_flow_hourly_lookup(passenger_flow_trend: pd.DataFrame) -> pd.DataFrame:
    frame = passenger_flow_trend.copy()
    if "station_id" not in frame.columns:
        frame["station_id"] = pd.to_numeric(frame.get("target_id"), errors="coerce")
    if "hour" not in frame.columns:
        frame["hour"] = pd.to_datetime(frame["record_time"], errors="coerce").dt.hour
    grouped = (
        frame.groupby(["station_id", "day_type", "hour"], as_index=False)["total_flow"]
        .mean()
        .rename(columns={"total_flow": "station_flow_mean"})
    )
    grouped["station_flow_level"] = _flow_level(grouped["station_flow_mean"])
    return grouped


def _line_congestion_lookup(
    bus_station: pd.DataFrame,
    line_station: pd.DataFrame,
    traffic_speed_bands: pd.DataFrame,
) -> pd.DataFrame:
    traffic = traffic_speed_bands.copy()
    if traffic.empty:
        return pd.DataFrame(columns=["line_id", "congestion_score"])
    traffic["road_key"] = traffic["road_name"].map(_normalize_road_name)
    road_congestion = (
        traffic.dropna(subset=["congestion_score"])
        .groupby("road_key", as_index=False)["congestion_score"]
        .mean()
    )
    station_roads = bus_station[["station_id", "road_name"]].copy()
    station_roads["road_key"] = station_roads["road_name"].map(_normalize_road_name)
    merged = line_station.merge(station_roads[["station_id", "road_key"]], on="station_id", how="left")
    merged = merged.merge(road_congestion, on="road_key", how="left")
    return (
        merged.groupby("line_id", as_index=False)["congestion_score"]
        .mean()
        .sort_values("line_id")
    )


def _build_synthetic_dynamic_features(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["is_synthetic"] = False
    output["walk_time_is_synthetic"] = False
    output["transfer_count_is_synthetic"] = False
    for group_id, group in output.groupby("candidate_group_id"):
        # 离线阶段还没有真实步行路径；同组无差异时生成可比较的步行负担。
        if group["walk_time_minutes"].nunique(dropna=False) <= 1:
            for index in group.index:
                hashed = _stable_hash(f"walk|{group_id}|{output.at[index, 'route_id']}")
                output.at[index, "walk_time_minutes"] = float([0.0, 3.0, 6.0, 9.0][hashed % 4])
                output.at[index, "is_synthetic"] = True
                output.at[index, "walk_time_is_synthetic"] = True
        # 当前候选集多来自同站到站样本，先生成少量换乘差异打通排序训练。
        if group["transfer_count"].nunique(dropna=False) <= 1:
            for index in group.index:
                hashed = _stable_hash(f"transfer|{group_id}|{output.at[index, 'route_id']}")
                output.at[index, "transfer_count"] = int([0, 0, 1, 1, 2][hashed % 5])
                output.at[index, "is_synthetic"] = True
                output.at[index, "transfer_count_is_synthetic"] = True
    return output


def build_recommendation_feature_frame(
    *,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    month: str | None = None,
    max_groups: int | None = None,
) -> pd.DataFrame:
    bundle = load_bundle(processed_dir=processed_dir, raw_dir=raw_dir, month=month)
    arrival = bundle.lta_bus_arrival.copy()
    if arrival.empty:
        raise ValueError("No Bus Arrival samples available for recommendation feature building")

    arrival["line_id"] = pd.to_numeric(arrival["line_id"], errors="coerce")
    arrival = arrival.dropna(subset=["station_id", "line_id", "query_time"]).copy()
    arrival["station_id"] = arrival["station_id"].astype(int)
    arrival["line_id"] = arrival["line_id"].astype(int)
    arrival["query_time"] = pd.to_datetime(arrival["query_time"], errors="coerce")
    arrival["day_type"] = arrival["query_time"].map(_day_type_from_timestamp)
    arrival["hour"] = arrival["query_time"].dt.hour
    arrival["candidate_group_id"] = (
        arrival["query_time"].dt.strftime("%Y-%m-%dT%H:%M:%S")
        + "|"
        + arrival["bus_stop_code"].astype(str)
    )

    if max_groups is not None:
        keep_groups = arrival["candidate_group_id"].drop_duplicates().head(max_groups)
        arrival = arrival[arrival["candidate_group_id"].isin(set(keep_groups))].copy()

    line_lookup = bundle.bus_line[["line_id", "service_no", "avg_service_frequency"]].copy()
    remaining = _remaining_distance_lookup(bundle.line_station)
    station_flow = _station_flow_hourly_lookup(bundle.passenger_flow_trend)
    line_congestion = _line_congestion_lookup(bundle.bus_station, bundle.line_station, bundle.traffic_speed_bands)

    frame = arrival.merge(line_lookup, on=["line_id", "service_no"], how="left")
    frame = frame.merge(remaining, on=["line_id", "station_id"], how="left")
    frame = frame.merge(station_flow, on=["station_id", "day_type", "hour"], how="left")
    frame = frame.merge(line_congestion, on="line_id", how="left")

    global_flow_mean = float(station_flow["station_flow_mean"].mean()) if not station_flow.empty else 800.0
    global_congestion = float(line_congestion["congestion_score"].mean()) if not line_congestion.empty else 0.45
    global_frequency = float(line_lookup["avg_service_frequency"].mean()) if not line_lookup.empty else 10.0
    global_remaining = float(remaining["remaining_distance_km"].median()) if not remaining.empty else 8.0

    missing_congestion = frame["congestion_score"].isna()
    missing_frequency = frame["avg_service_frequency"].isna()
    missing_remaining_distance = frame["remaining_distance_km"].isna()
    missing_load_score = frame["load_score"].isna()
    frame["station_flow_mean"] = frame["station_flow_mean"].fillna(global_flow_mean)
    missing_flow_level = frame["station_flow_level"].isna()
    frame.loc[missing_flow_level, "station_flow_level"] = _flow_level(frame.loc[missing_flow_level, "station_flow_mean"])
    frame["congestion_score"] = frame["congestion_score"].fillna(global_congestion)
    frame["avg_service_frequency"] = frame["avg_service_frequency"].fillna(global_frequency)
    frame["remaining_distance_km"] = frame["remaining_distance_km"].fillna(global_remaining)
    frame["ride_time_minutes"] = (frame["remaining_distance_km"] / 18.0 * 60.0).clip(lower=5.0).round(1)
    frame["walk_time_minutes"] = 0.0
    frame["transfer_count"] = 0
    frame["confidence"] = 1.0

    monitored = pd.to_numeric(frame.get("monitored"), errors="coerce").fillna(0)
    frame["reliability_score"] = np.where(monitored >= 1, 92.0, 76.0)
    frame.loc[missing_flow_level, "reliability_score"] -= 4.0
    frame.loc[missing_congestion, "reliability_score"] -= 6.0
    frame["reliability_score"] = frame["reliability_score"].clip(lower=50.0, upper=98.0)
    frame["missing_congestion"] = missing_congestion.astype(bool)
    frame["missing_frequency"] = missing_frequency.astype(bool)
    frame["missing_remaining_distance"] = missing_remaining_distance.astype(bool)
    frame["missing_load_score"] = missing_load_score.astype(bool)
    frame["missing_flow_level"] = missing_flow_level.astype(bool)

    frame["route_id"] = (
        frame["candidate_group_id"]
        + "|"
        + frame["service_no"].astype(str)
        + "|"
        + frame["visit_order"].astype(str)
    )
    frame["line_ids"] = frame["line_id"].astype(str)
    frame["data_source"] = "offline_data"

    frame = frame[
        [
            "candidate_group_id",
            "query_time",
            "station_id",
            "bus_stop_code",
            "route_id",
            "service_no",
            "line_ids",
            "eta_minutes",
            "load_code",
            "load_score",
            "walk_time_minutes",
            "ride_time_minutes",
            "transfer_count",
            "avg_service_frequency",
            "station_flow_mean",
            "station_flow_level",
            "congestion_score",
            "reliability_score",
            "confidence",
            "monitored",
            "missing_congestion",
            "missing_frequency",
            "missing_remaining_distance",
            "missing_load_score",
            "missing_flow_level",
            "data_source",
        ]
    ].copy()

    frame = _build_synthetic_dynamic_features(frame)
    frame.loc[frame["is_synthetic"], "confidence"] = 0.75
    frame.loc[frame["is_synthetic"], "reliability_score"] = frame.loc[frame["is_synthetic"], "reliability_score"].clip(
        upper=82.0
    )

    counts = frame.groupby("candidate_group_id")["route_id"].transform("count")
    frame = frame[counts >= 2].copy()
    return frame.sort_values(["candidate_group_id", "eta_minutes", "route_id"]).reset_index(drop=True)


def _history_flow_score(level: Any) -> float:
    mapping = {
        "low": 90.0,
        "medium": 70.0,
        "high": 45.0,
    }
    return mapping.get(str(level or "").lower(), 60.0)


def _traffic_score(congestion_pressure: Any) -> float:
    try:
        pressure = float(congestion_pressure)
    except (TypeError, ValueError):
        return 60.0
    if pressure <= 1.0:
        return round(max(0.0, min(100.0, 100.0 - pressure * 70.0)), 2)
    return round(max(0.0, min(100.0, pressure)), 2)


def _is_true(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _degraded_fields(row: pd.Series) -> str:
    # 记录哪些特征不是直接真实来源，后续 completeness_score 和数据审计都依赖它。
    fields: list[str] = []
    if _is_true(row.get("missing_remaining_distance")):
        fields.append("ride_time_minutes")
    if _is_true(row.get("walk_time_is_synthetic")):
        fields.extend(["walk_time_minutes", "walk_distance_meters"])
    if _is_true(row.get("transfer_count_is_synthetic")):
        fields.append("transfer_count")
    if _is_true(row.get("missing_load_score")):
        fields.append("load_score")
    if _is_true(row.get("missing_flow_level")):
        fields.append("history_flow_score")
    if _is_true(row.get("missing_congestion")):
        fields.append("congestion_score")
    if _is_true(row.get("missing_frequency")):
        fields.append("avg_service_frequency_minutes")
    if pd.isna(row.get("monitored")):
        fields.append("monitored_score")
    fields.append("data_freshness_seconds")
    return "|".join(dict.fromkeys(fields))


def _completeness_score(degraded_fields: Any) -> float:
    # 每个降级字段扣 6 分，避免模拟样本和真实样本在可靠性上被同等看待。
    fields = [item for item in str(degraded_fields or "").split("|") if item]
    return round(max(55.0, 100.0 - len(fields) * 6.0), 2)


def _feature_sources(row: pd.Series) -> str:
    # feature_sources 必须覆盖 12 维特征，方便后端以后按同一契约组装 payload。
    sources = {
        "eta_minutes": "lta_realtime",
        "ride_time_minutes": "rule_estimate",
        "walk_time_minutes": "rule_estimate",
        "walk_distance_meters": "rule_estimate",
        "transfer_count": "rule_estimate",
        "load_score": "default" if _is_true(row.get("missing_load_score")) else "lta_realtime",
        "history_flow_score": "default" if _is_true(row.get("missing_flow_level")) else "historical",
        "congestion_score": "default" if _is_true(row.get("missing_congestion")) else "historical",
        "data_freshness_seconds": "default",
        "monitored_score": "default" if pd.isna(row.get("monitored")) else "lta_realtime",
        "completeness_score": "rule_estimate",
        "avg_service_frequency_minutes": "default" if _is_true(row.get("missing_frequency")) else "database",
    }
    return "|".join(f"{field}:{source}" for field, source in sources.items())


def _model_generated_feature_sources() -> str:
    sources = {
        "eta_minutes": "model",
        "ride_time_minutes": "model",
        "walk_time_minutes": "model",
        "walk_distance_meters": "model",
        "transfer_count": "model",
        "load_score": "model",
        "history_flow_score": "model",
        "congestion_score": "model",
        "data_freshness_seconds": "model",
        "monitored_score": "model",
        "completeness_score": "rule_estimate",
        "avg_service_frequency_minutes": "model",
    }
    return "|".join(f"{field}:{source}" for field, source in sources.items())


def _load_code_from_score(score: float) -> str:
    if score >= 90:
        return "SEA"
    if score >= 55:
        return "SDA"
    return "LSD"


def _clip(value: float, lower: float, upper: float) -> float:
    return round(float(max(lower, min(upper, value))), 3)


def expand_feature_frame_to_min_groups(
    frame: pd.DataFrame,
    *,
    min_groups: int | None,
    max_routes_per_group: int = 10,
) -> pd.DataFrame:
    if min_groups is None or min_groups <= 0:
        return frame

    current_groups = frame["candidate_group_id"].nunique()
    if current_groups >= min_groups:
        return frame

    groups = [(group_id, group.copy()) for group_id, group in frame.groupby("candidate_group_id")]
    if not groups:
        return frame

    rows: list[pd.DataFrame] = [frame]
    needed = min_groups - current_groups
    generated_sources = _model_generated_feature_sources()
    generated_degraded = (
        "eta_minutes|ride_time_minutes|walk_time_minutes|walk_distance_meters|"
        "transfer_count|load_score|history_flow_score|congestion_score|"
        "data_freshness_seconds|monitored_score|avg_service_frequency_minutes"
    )

    for offset in range(needed):
        source_group_id, source_group = groups[offset % len(groups)]
        group = source_group.sort_values(["eta_minutes", "route_id"]).head(max_routes_per_group).copy()
        new_group_id = f"synthetic_od_{offset + 1:05d}"
        group["candidate_group_id"] = new_group_id
        group["is_synthetic"] = True
        group["feature_sources"] = generated_sources
        group["degraded_fields"] = generated_degraded
        group["completeness_score"] = _completeness_score(generated_degraded)

        for index in group.index:
            token = f"{source_group_id}|{offset}|{group.at[index, 'route_id']}"
            h = _stable_hash(token)
            eta_factor = 0.75 + (h % 51) / 100.0
            ride_factor = 0.85 + ((h // 7) % 31) / 100.0
            walk_shift = [0.0, 2.0, 4.0, 6.0, 8.0][(h // 11) % 5]
            transfer_shift = [-1, 0, 0, 1][(h // 13) % 4]
            freshness = [60.0, 90.0, 120.0, 180.0, 300.0][(h // 17) % 5]

            group.at[index, "eta_minutes"] = _clip(float(group.at[index, "eta_minutes"]) * eta_factor, 0.0, 60.0)
            group.at[index, "ride_time_minutes"] = _clip(
                float(group.at[index, "ride_time_minutes"]) * ride_factor,
                3.0,
                150.0,
            )
            group.at[index, "walk_time_minutes"] = _clip(
                float(group.at[index, "walk_time_minutes"]) + walk_shift,
                0.0,
                35.0,
            )
            group.at[index, "walk_distance_meters"] = _clip(float(group.at[index, "walk_time_minutes"]) * 80.0, 0.0, 2800.0)
            group.at[index, "transfer_count"] = int(max(0, min(3, int(group.at[index, "transfer_count"]) + transfer_shift)))
            load_score = _clip(float(group.at[index, "load_score"]) + [-20.0, 0.0, 15.0][(h // 19) % 3], 35.0, 100.0)
            group.at[index, "load_score"] = load_score
            group.at[index, "load_code"] = _load_code_from_score(load_score)
            group.at[index, "history_flow_score"] = _clip(
                float(group.at[index, "history_flow_score"]) + [-20.0, -10.0, 0.0, 10.0, 20.0][(h // 23) % 5],
                20.0,
                100.0,
            )
            group.at[index, "congestion_score"] = _clip(
                float(group.at[index, "congestion_score"]) + [-15.0, -7.5, 0.0, 7.5, 15.0][(h // 29) % 5],
                0.0,
                100.0,
            )
            group.at[index, "data_freshness_seconds"] = freshness
            group.at[index, "monitored_score"] = [75.0, 100.0][(h // 31) % 2]
            group.at[index, "avg_service_frequency_minutes"] = _clip(
                float(group.at[index, "avg_service_frequency_minutes"]) * (0.8 + ((h // 37) % 41) / 100.0),
                3.0,
                120.0,
            )
            group.at[index, "route_id"] = f"{new_group_id}|{group.at[index, 'service_nos']}|{index}"

        rows.append(group)

    return pd.concat(rows, ignore_index=True).sort_values(["candidate_group_id", "route_id"]).reset_index(drop=True)


def build_model_feature_frame(
    *,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    month: str | None = None,
    max_groups: int | None = None,
) -> pd.DataFrame:
    frame = build_recommendation_feature_frame(
        processed_dir=processed_dir,
        raw_dir=raw_dir,
        month=month,
        max_groups=max_groups,
    )
    output = frame.copy()
    output["service_nos"] = output["service_no"].astype(str)
    output["walk_distance_meters"] = (pd.to_numeric(output["walk_time_minutes"], errors="coerce").fillna(0.0) * 80.0).round(1)
    output["history_flow_score"] = output["station_flow_level"].map(_history_flow_score)
    output["congestion_score"] = output["congestion_score"].map(_traffic_score)
    # 离线样本没有真实缓存写入时间，统一用默认 freshness，并在 degraded_fields 标记。
    output["data_freshness_seconds"] = 60.0
    output["avg_service_frequency_minutes"] = output["avg_service_frequency"]
    output["load_code"] = output["load_code"].fillna("UNKNOWN")
    output["load_score"] = pd.to_numeric(output["load_score"], errors="coerce")
    output["load_score"] = output["load_score"].fillna(output["load_code"].map(LOAD_SCORE_BY_CODE)).fillna(60.0)
    monitored = pd.to_numeric(output["monitored"], errors="coerce")
    output["monitored_score"] = np.where(monitored >= 1, 100.0, 75.0)
    output["degraded_fields"] = output.apply(_degraded_fields, axis=1)
    output["completeness_score"] = output["degraded_fields"].map(_completeness_score)
    output["feature_sources"] = output.apply(_feature_sources, axis=1)
    columns = [
        "candidate_group_id",
        "route_id",
        "service_nos",
        "eta_minutes",
        "ride_time_minutes",
        "walk_time_minutes",
        "walk_distance_meters",
        "transfer_count",
        "load_code",
        "load_score",
        "history_flow_score",
        "congestion_score",
        "data_freshness_seconds",
        "monitored_score",
        "completeness_score",
        "avg_service_frequency_minutes",
        "feature_sources",
        "degraded_fields",
        "is_synthetic",
    ]
    return output[columns].sort_values(["candidate_group_id", "route_id"]).reset_index(drop=True)
