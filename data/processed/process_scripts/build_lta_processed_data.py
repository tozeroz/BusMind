"""
Build interface-ready CSV files from raw LTA DataMall data.

The current backend needs database tables for station/line lookup, vehicle
state, real-time ETA/load values, map layers, and passenger-flow trends. This
script intentionally skips model-training sample outputs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import zipfile
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


BUS_PROPS = ("NextBus", "NextBus2", "NextBus3")

LOAD_SCORE = {
    "SEA": 100.0,
    "SDA": 70.0,
    "LSD": 35.0,
}

LOAD_LEVEL = {
    "SEA": "seats_available",
    "SDA": "standing_available",
    "LSD": "limited_standing",
}

LOAD_RATE = {
    "SEA": 0.35,
    "SDA": 0.70,
    "LSD": 0.90,
}

BUS_CAPACITY = {
    "SD": 80,
    "DD": 120,
    "BD": 110,
}

SPEED_BAND_COLOR = {
    1: "#8b0000",
    2: "#c62828",
    3: "#ef5350",
    4: "#fb8c00",
    5: "#fdd835",
    6: "#9ccc65",
    7: "#43a047",
    8: "#1b5e20",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_lta_json_list(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("value"), list):
        return data["value"]
    raise ValueError(f"Unsupported JSON shape: {path}")


def write_csv(df: pd.DataFrame, path: Path) -> None:
    ensure_dir(path.parent)
    df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
    print(f"wrote {len(df):>8} rows -> {path}")


def normalize_stop_code(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5)


def stop_code_to_station_id(value: Any) -> int | None:
    code = normalize_stop_code(value)
    if not code:
        return None
    try:
        return int(code)
    except ValueError:
        return None


def stable_positive_int(value: str) -> int:
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 900_000_000 + 100_000


def latest_month_dir(parent: Path) -> Path:
    candidates = [p for p in parent.iterdir() if p.is_dir() and p.name.isdigit()]
    if not candidates:
        raise FileNotFoundError(f"No month directories found under {parent}")
    return sorted(candidates, key=lambda p: p.name)[-1]


def first_zip_csv(zip_path: Path) -> pd.DataFrame:
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
        if not csv_names:
            raise ValueError(f"No CSV file found inside {zip_path}")
        with zf.open(csv_names[0]) as f:
            return pd.read_csv(f, dtype=str)


def parse_frequency_range(value: Any) -> tuple[float | None, float | None, float | None]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None, None, None
    text = str(value).strip()
    if not text or text == "-":
        return None, None, None
    try:
        if "-" in text:
            left, right = text.split("-", 1)
            min_value = float(left)
            max_value = float(right)
            return min_value, max_value, (min_value + max_value) / 2
        value_float = float(text)
        return value_float, value_float, value_float
    except ValueError:
        return None, None, None


def add_frequency_columns(df: pd.DataFrame, source_col: str, prefix: str) -> None:
    parsed = df[source_col].map(parse_frequency_range)
    df[f"{prefix}_freq_min"] = parsed.map(lambda item: item[0])
    df[f"{prefix}_freq_max"] = parsed.map(lambda item: item[1])
    df[f"{prefix}_freq_avg"] = parsed.map(lambda item: item[2])


def haversine_km(
    lat1: pd.Series,
    lon1: pd.Series,
    lat2: pd.Series,
    lon2: pd.Series,
) -> pd.Series:
    radius_km = 6371.0
    lat1_rad = lat1.map(math.radians)
    lon1_rad = lon1.map(math.radians)
    lat2_rad = lat2.map(math.radians)
    lon2_rad = lon2.map(math.radians)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    a = (dlat / 2).map(math.sin) ** 2 + lat1_rad.map(math.cos) * lat2_rad.map(math.cos) * (dlon / 2).map(math.sin) ** 2
    return 2 * radius_km * a.clip(lower=0, upper=1).map(math.sqrt).map(math.asin)


def flow_level_from_series(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0)
    if values.empty:
        return pd.Series(dtype=str)
    high = values.quantile(0.75)
    medium = values.quantile(0.40)
    return values.map(lambda v: "high" if v >= high else ("medium" if v >= medium else "low"))


def build_bus_station(raw_dir: Path, processed_dir: Path) -> pd.DataFrame:
    stops = pd.DataFrame(read_lta_json_list(raw_dir / "api_response" / "BusStops_full.json"))
    df = stops.rename(
        columns={
            "BusStopCode": "bus_stop_code",
            "RoadName": "road_name",
            "Description": "station_name",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )
    df["bus_stop_code"] = df["bus_stop_code"].map(normalize_stop_code)
    df["station_id"] = df["bus_stop_code"].map(stop_code_to_station_id)
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df[
        [
            "station_id",
            "bus_stop_code",
            "station_name",
            "road_name",
            "latitude",
            "longitude",
        ]
    ].dropna(subset=["station_id", "latitude", "longitude"])
    df["station_id"] = df["station_id"].astype(int)
    df = df.sort_values("station_id")
    write_csv(df, processed_dir / "bus_station.csv")
    return df


def build_bus_line(raw_dir: Path, processed_dir: Path) -> pd.DataFrame:
    services = pd.DataFrame(read_lta_json_list(raw_dir / "api_response" / "BusServices_full.json"))
    df = services.rename(
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
            "LoopDesc": "loop_desc",
        }
    )
    df["service_no"] = df["service_no"].astype(str)
    df["direction"] = pd.to_numeric(df["direction"], errors="coerce").astype("Int64")
    df["origin_stop_code"] = df["origin_stop_code"].map(normalize_stop_code)
    df["destination_stop_code"] = df["destination_stop_code"].map(normalize_stop_code)
    df["origin_station_id"] = df["origin_stop_code"].map(stop_code_to_station_id)
    df["destination_station_id"] = df["destination_stop_code"].map(stop_code_to_station_id)
    df["origin_station_id"] = pd.to_numeric(df["origin_station_id"], errors="coerce").astype("Int64")
    df["destination_station_id"] = pd.to_numeric(df["destination_station_id"], errors="coerce").astype("Int64")
    df = df.sort_values(["service_no", "direction"]).reset_index(drop=True)
    df["line_id"] = range(1, len(df) + 1)
    df["line_name"] = "Bus " + df["service_no"].astype(str)

    add_frequency_columns(df, "am_peak_freq", "am_peak")
    add_frequency_columns(df, "am_offpeak_freq", "am_offpeak")
    add_frequency_columns(df, "pm_peak_freq", "pm_peak")
    add_frequency_columns(df, "pm_offpeak_freq", "pm_offpeak")
    df["avg_service_frequency"] = df[
        [
            "am_peak_freq_avg",
            "am_offpeak_freq_avg",
            "pm_peak_freq_avg",
            "pm_offpeak_freq_avg",
        ]
    ].mean(axis=1, skipna=True)

    columns = [
        "line_id",
        "service_no",
        "line_name",
        "operator",
        "direction",
        "category",
        "origin_station_id",
        "origin_stop_code",
        "destination_station_id",
        "destination_stop_code",
        "am_peak_freq",
        "am_offpeak_freq",
        "pm_peak_freq",
        "pm_offpeak_freq",
        "avg_service_frequency",
        "loop_desc",
    ]
    df = df[columns]
    write_csv(df, processed_dir / "bus_line.csv")
    return df


def build_line_station(
    raw_dir: Path,
    processed_dir: Path,
    lines: pd.DataFrame,
) -> pd.DataFrame:
    routes = pd.DataFrame(read_lta_json_list(raw_dir / "api_response" / "BusRoutes_full.json"))
    df = routes.rename(
        columns={
            "ServiceNo": "service_no",
            "Operator": "operator",
            "Direction": "direction",
            "StopSequence": "stop_sequence",
            "BusStopCode": "bus_stop_code",
            "Distance": "route_distance_km",
            "WD_FirstBus": "wd_first_bus",
            "WD_LastBus": "wd_last_bus",
            "SAT_FirstBus": "sat_first_bus",
            "SAT_LastBus": "sat_last_bus",
            "SUN_FirstBus": "sun_first_bus",
            "SUN_LastBus": "sun_last_bus",
        }
    )
    df["service_no"] = df["service_no"].astype(str)
    df["direction"] = pd.to_numeric(df["direction"], errors="coerce").astype("Int64")
    df["stop_sequence"] = pd.to_numeric(df["stop_sequence"], errors="coerce").astype("Int64")
    df["bus_stop_code"] = df["bus_stop_code"].map(normalize_stop_code)
    df["station_id"] = df["bus_stop_code"].map(stop_code_to_station_id)
    df["route_distance_km"] = pd.to_numeric(df["route_distance_km"], errors="coerce")

    lookup = lines[["line_id", "service_no", "line_name", "direction"]].copy()
    df = df.merge(lookup, on=["service_no", "direction"], how="left", validate="many_to_one")
    df = df.dropna(subset=["line_id", "station_id", "stop_sequence"]).copy()
    df["line_id"] = df["line_id"].astype(int)
    df["station_id"] = df["station_id"].astype(int)
    df["line_station_id"] = (
        df["line_id"].astype(str) + "_" + df["stop_sequence"].astype(str).str.zfill(3)
    )

    columns = [
        "line_station_id",
        "line_id",
        "service_no",
        "line_name",
        "operator",
        "direction",
        "stop_sequence",
        "station_id",
        "bus_stop_code",
        "route_distance_km",
        "wd_first_bus",
        "wd_last_bus",
        "sat_first_bus",
        "sat_last_bus",
        "sun_first_bus",
        "sun_last_bus",
    ]
    df = df[columns].sort_values(["line_id", "stop_sequence"])
    write_csv(df, processed_dir / "line_station.csv")
    return df


def build_passenger_flow_trend(
    raw_dir: Path,
    processed_dir: Path,
    month: str | None,
) -> pd.DataFrame:
    stop_parent = raw_dir / "passenger_volume_stop"
    stop_month_dir = stop_parent / month if month else latest_month_dir(stop_parent)
    stop = first_zip_csv(stop_month_dir / "original.zip").rename(
        columns={
            "YEAR_MONTH": "year_month",
            "DAY_TYPE": "day_type",
            "TIME_PER_HOUR": "hour",
            "PT_TYPE": "pt_type",
            "PT_CODE": "bus_stop_code",
            "TOTAL_TAP_IN_VOLUME": "tap_in_volume",
            "TOTAL_TAP_OUT_VOLUME": "tap_out_volume",
        }
    )
    stop["bus_stop_code"] = stop["bus_stop_code"].map(normalize_stop_code)
    stop["station_id"] = stop["bus_stop_code"].map(stop_code_to_station_id)
    stop["hour"] = pd.to_numeric(stop["hour"], errors="coerce")
    stop["tap_in_volume"] = pd.to_numeric(stop["tap_in_volume"], errors="coerce").fillna(0)
    stop["tap_out_volume"] = pd.to_numeric(stop["tap_out_volume"], errors="coerce").fillna(0)
    stop["total_flow"] = stop["tap_in_volume"] + stop["tap_out_volume"]
    stop["flow_level"] = flow_level_from_series(stop["total_flow"])
    stop = stop.dropna(subset=["station_id", "hour"]).copy()
    stop["station_id"] = stop["station_id"].astype(int)
    stop["hour"] = stop["hour"].astype(int)
    stop["target_type"] = "station"
    stop["target_id"] = stop["station_id"]
    year_month_digits = stop["year_month"].astype(str).str.replace(r"\D", "", regex=True).str[:6]
    base_date = pd.to_datetime(year_month_digits + "01", format="%Y%m%d", errors="coerce")
    stop["record_time"] = base_date + pd.to_timedelta(stop["hour"], unit="h")
    stop["day_type"] = stop["day_type"].map(
        lambda value: "weekend" if "WEEKEND" in str(value).upper() or "HOLIDAY" in str(value).upper() else "weekday"
    )
    stop["data_source"] = "LTA Passenger Volume by Bus Stops"
    columns = [
        "target_type",
        "target_id",
        "bus_stop_code",
        "record_time",
        "day_type",
        "tap_in_volume",
        "tap_out_volume",
        "total_flow",
        "flow_level",
        "data_source",
    ]
    stop = stop[columns].sort_values(["target_id", "day_type", "record_time"])
    write_csv(stop, processed_dir / "passenger_flow_trend.csv")
    return stop


def iter_arrival_records(arrival_root: Path) -> Iterable[dict[str, Any]]:
    files = sorted(arrival_root.glob("*/*.jsonl"))
    if not files:
        raise FileNotFoundError(f"No Bus Arrival jsonl files found under {arrival_root}")
    for path in files:
        with path.open("r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)


def flatten_bus_arrival(
    raw_dir: Path,
    processed_dir: Path,
    lines: pd.DataFrame,
    stations: pd.DataFrame,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for record in iter_arrival_records(raw_dir / "bus_arrival_samples"):
        response = record.get("response") or {}
        query_time = record.get("query_time")
        bus_stop_code = normalize_stop_code(record.get("bus_stop_code") or response.get("BusStopCode"))
        for service in response.get("Services") or []:
            service_no = str(service.get("ServiceNo"))
            operator = service.get("Operator")
            for bus_prop in BUS_PROPS:
                bus = service.get(bus_prop) or {}
                estimated_arrival = bus.get("EstimatedArrival")
                if not estimated_arrival:
                    continue
                origin_stop_code = normalize_stop_code(bus.get("OriginCode"))
                destination_stop_code = normalize_stop_code(bus.get("DestinationCode"))
                visit_order = {"NextBus": 1, "NextBus2": 2, "NextBus3": 3}[bus_prop]
                visit_number = bus.get("VisitNumber") or "1"
                bus_type = str(bus.get("Type") or "").upper()
                feature = bus.get("Feature")
                vehicle_key = "|".join(
                    [
                        service_no,
                        origin_stop_code,
                        destination_stop_code,
                        str(visit_order),
                        str(visit_number),
                        bus_type,
                    ]
                )
                rows.append(
                    {
                        "query_time": query_time,
                        "station_id": stop_code_to_station_id(bus_stop_code),
                        "bus_stop_code": bus_stop_code,
                        "service_no": service_no,
                        "operator": operator,
                        "visit_order": visit_order,
                        "origin_stop_code": origin_stop_code,
                        "destination_stop_code": destination_stop_code,
                        "estimated_arrival": estimated_arrival,
                        "monitored": bus.get("Monitored"),
                        "vehicle_latitude": bus.get("Latitude"),
                        "vehicle_longitude": bus.get("Longitude"),
                        "visit_number": visit_number,
                        "load_code": bus.get("Load"),
                        "feature": feature,
                        "bus_type": bus_type,
                        "vehicle_id": stable_positive_int(vehicle_key),
                    }
                )

    df = pd.DataFrame(rows)
    if df.empty:
        raise ValueError("No usable Bus Arrival rows found.")

    df["query_time"] = pd.to_datetime(df["query_time"], errors="coerce")
    estimated_arrival = pd.to_datetime(df["estimated_arrival"], errors="coerce", utc=True)
    df["estimated_arrival"] = estimated_arrival.dt.tz_convert("Asia/Singapore").dt.tz_localize(None)
    df["predicted_eta_minutes"] = (
        (df["estimated_arrival"] - df["query_time"]).dt.total_seconds() / 60
    ).round(2)
    df = df[df["predicted_eta_minutes"].notna() & (df["predicted_eta_minutes"] >= 0)].copy()
    df["duration_ms"] = (df["predicted_eta_minutes"] * 60 * 1000).round().astype("Int64")
    df["station_id"] = df["station_id"].astype(int)
    df["vehicle_latitude"] = pd.to_numeric(df["vehicle_latitude"], errors="coerce")
    df["vehicle_longitude"] = pd.to_numeric(df["vehicle_longitude"], errors="coerce")
    df["monitored"] = pd.to_numeric(df["monitored"], errors="coerce").fillna(0).astype(int)
    df["predicted_load"] = df["load_code"]
    df["predicted_load_level"] = df["load_code"].map(LOAD_LEVEL)
    df["load_score"] = df["load_code"].map(LOAD_SCORE)

    line_lookup = lines[
        [
            "line_id",
            "service_no",
            "line_name",
            "direction",
            "origin_stop_code",
            "destination_stop_code",
        ]
    ].copy().sort_values(["service_no", "direction", "line_id"])
    line_lookup_unique = line_lookup.drop_duplicates(
        ["service_no", "origin_stop_code", "destination_stop_code"],
        keep="first",
    )
    df = df.merge(
        line_lookup_unique,
        on=["service_no", "origin_stop_code", "destination_stop_code"],
        how="left",
        validate="many_to_one",
    )
    fallback = line_lookup.drop_duplicates("service_no").set_index("service_no")
    missing = df["line_id"].isna()
    for col in ["line_id", "line_name", "direction"]:
        df.loc[missing, col] = df.loc[missing, "service_no"].map(fallback[col])
    df = df.dropna(subset=["line_id"]).copy()
    df["line_id"] = df["line_id"].astype(int)
    df["direction"] = pd.to_numeric(df["direction"], errors="coerce").astype("Int64")

    station_coords = stations[["station_id", "latitude", "longitude"]].rename(
        columns={"latitude": "station_latitude", "longitude": "station_longitude"}
    )
    df = df.merge(station_coords, on="station_id", how="left", validate="many_to_one")
    valid_vehicle_coords = (df["vehicle_latitude"] > 0) & (df["vehicle_longitude"] > 0)
    df["vehicle_to_stop_distance_m"] = pd.NA
    df.loc[valid_vehicle_coords, "vehicle_to_stop_distance_m"] = (
        haversine_km(
            df.loc[valid_vehicle_coords, "vehicle_latitude"],
            df.loc[valid_vehicle_coords, "vehicle_longitude"],
            df.loc[valid_vehicle_coords, "station_latitude"],
            df.loc[valid_vehicle_coords, "station_longitude"],
        )
        * 1000
    ).round(1)
    df["capacity"] = df["bus_type"].map(BUS_CAPACITY).fillna(80).astype(int)
    df["predicted_load_rate"] = df["predicted_load"].map(LOAD_RATE).fillna(0.45)
    df["onboard_count"] = (df["capacity"] * df["predicted_load_rate"]).round().astype(int)
    eta_hours = df["predicted_eta_minutes"] / 60
    distance_km = pd.to_numeric(df["vehicle_to_stop_distance_m"], errors="coerce") / 1000
    speed = distance_km / eta_hours.replace(0, pd.NA)
    df["speed_kph"] = speed.fillna(24).clip(lower=8, upper=60).round(1)

    columns = [
        "query_time",
        "station_id",
        "bus_stop_code",
        "service_no",
        "line_id",
        "line_name",
        "operator",
        "visit_order",
        "origin_stop_code",
        "destination_stop_code",
        "estimated_arrival",
        "predicted_eta_minutes",
        "duration_ms",
        "monitored",
        "vehicle_id",
        "vehicle_latitude",
        "vehicle_longitude",
        "visit_number",
        "predicted_load",
        "predicted_load_level",
        "load_score",
        "predicted_load_rate",
        "onboard_count",
        "capacity",
        "bus_type",
        "feature",
        "vehicle_to_stop_distance_m",
        "speed_kph",
    ]
    output = df[columns].sort_values(["query_time", "station_id", "service_no", "visit_order"])
    output = output.rename(
        columns={
            "predicted_eta_minutes": "eta_minutes",
            "predicted_load": "load_code",
            "predicted_load_level": "load_level",
            "predicted_load_rate": "load_rate",
        }
    )
    write_csv(output, processed_dir / "lta_bus_arrival.csv")
    return df


def build_bus_vehicle(arrival: pd.DataFrame, stations: pd.DataFrame, processed_dir: Path) -> pd.DataFrame:
    df = arrival.copy()
    df = df[(df["vehicle_latitude"] > 0) & (df["vehicle_longitude"] > 0)].copy()
    if df.empty:
        vehicle = pd.DataFrame(
            columns=[
                "vehicle_id",
                "vehicle_code",
                "line_id",
                "service_no",
                "line_name",
                "current_station_id",
                "next_station_id",
                "next_station_name",
                "longitude",
                "latitude",
                "speed_kph",
                "onboard_count",
                "capacity",
                "load_level",
                "load_code",
                "load_score",
                "operation_status",
                "data_status",
                "last_reported_at",
            ]
        )
        write_csv(vehicle, processed_dir / "bus_vehicle.csv")
        return vehicle

    latest = (
        df.sort_values(["query_time", "visit_order"], ascending=[False, True])
        .drop_duplicates("vehicle_id")
        .copy()
    )
    latest["line_id"] = latest["line_id"].astype(int)
    latest["capacity"] = latest["capacity"].astype(int)
    latest["onboard_count"] = latest["onboard_count"].astype(int)
    latest["vehicle_code"] = "V" + latest["vehicle_id"].astype(str)
    latest["operation_status"] = "normal"
    latest["data_status"] = latest["monitored"].map(lambda v: "realtime" if int(v) == 1 else "estimated")

    station_names = stations[["station_id", "station_name"]].copy()
    latest = latest.merge(station_names, on="station_id", how="left", validate="many_to_one")
    latest = latest.rename(
        columns={
            "station_id": "next_station_id",
            "station_name": "next_station_name",
            "vehicle_longitude": "longitude",
            "vehicle_latitude": "latitude",
            "predicted_load": "load_code",
            "predicted_load_level": "load_level",
            "query_time": "last_reported_at",
        }
    )
    latest["current_station_id"] = latest["next_station_id"]
    latest["current_station_id"] = latest["current_station_id"].astype(int)
    latest["next_station_id"] = latest["next_station_id"].astype(int)
    columns = [
        "vehicle_id",
        "vehicle_code",
        "line_id",
        "service_no",
        "line_name",
        "current_station_id",
        "next_station_id",
        "next_station_name",
        "longitude",
        "latitude",
        "speed_kph",
        "onboard_count",
        "capacity",
        "load_level",
        "load_code",
        "load_score",
        "operation_status",
        "data_status",
        "last_reported_at",
    ]
    vehicle = latest[columns].sort_values(["line_id", "vehicle_id"])
    write_csv(vehicle, processed_dir / "bus_vehicle.csv")
    return vehicle


def build_direct_status_tables(arrival: pd.DataFrame, processed_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = arrival.copy()
    base["vehicle_id"] = base["vehicle_id"].astype(int)
    base["line_id"] = base["line_id"].astype(int)
    base["station_id"] = base["station_id"].astype(int)
    base["capacity"] = base["capacity"].astype(int)
    base["onboard_count"] = base["onboard_count"].astype(int)

    eta = base[
        [
            "query_time",
            "vehicle_id",
            "line_id",
            "station_id",
            "bus_stop_code",
            "predicted_eta_minutes",
            "estimated_arrival",
            "vehicle_to_stop_distance_m",
            "speed_kph",
        ]
    ].rename(
        columns={
            "station_id": "target_station_id",
            "predicted_eta_minutes": "eta_minutes",
            "estimated_arrival": "arrival_time",
        }
    )
    eta["data_source"] = "lta_bus_arrival"
    write_csv(eta, processed_dir / "bus_eta_status.csv")

    load = base[
        [
            "query_time",
            "vehicle_id",
            "line_id",
            "station_id",
            "bus_stop_code",
            "predicted_load",
            "predicted_load_level",
            "load_score",
            "predicted_load_rate",
            "capacity",
            "onboard_count",
            "monitored",
        ]
    ].copy()
    load["confidence"] = load["monitored"].map(lambda value: 1.0 if int(value) == 1 else 0.8)
    load["data_source"] = "lta_bus_arrival"
    columns = [
        "query_time",
        "vehicle_id",
        "line_id",
        "station_id",
        "bus_stop_code",
        "predicted_load",
        "predicted_load_level",
        "load_score",
        "predicted_load_rate",
        "onboard_count",
        "capacity",
        "confidence",
        "data_source",
    ]
    load = load[columns]
    load = load.rename(
        columns={
            "predicted_load": "load_code",
            "predicted_load_level": "load_level",
            "predicted_load_rate": "load_rate",
        }
    )
    write_csv(load, processed_dir / "bus_load_status.csv")
    return eta, load


def build_map_station(
    stations: pd.DataFrame,
    line_station: pd.DataFrame,
    processed_dir: Path,
) -> pd.DataFrame:
    grouped = (
        line_station.groupby("station_id")
        .agg(
            line_count=("line_id", "nunique"),
            service_count=("service_no", "nunique"),
            line_ids=("line_id", lambda values: "|".join(map(str, sorted(set(values))))),
            service_nos=("service_no", lambda values: "|".join(map(str, sorted(set(values))))),
        )
        .reset_index()
    )
    df = stations.merge(grouped, on="station_id", how="left")
    df[["line_count", "service_count"]] = df[["line_count", "service_count"]].fillna(0).astype(int)
    df[["line_ids", "service_nos"]] = df[["line_ids", "service_nos"]].fillna("")
    columns = [
        "station_id",
        "bus_stop_code",
        "station_name",
        "road_name",
        "latitude",
        "longitude",
        "line_count",
        "service_count",
        "line_ids",
        "service_nos",
    ]
    df = df[columns].sort_values("station_id")
    write_csv(df, processed_dir / "map_station.csv")
    return df


def build_map_road_segment(
    line_station: pd.DataFrame,
    stations: pd.DataFrame,
    flow_trend: pd.DataFrame,
    processed_dir: Path,
) -> pd.DataFrame:
    station_coords = stations[["station_id", "station_name", "latitude", "longitude"]].copy()
    current = line_station.sort_values(["line_id", "stop_sequence"]).copy()
    current["end_station_id"] = current.groupby("line_id")["station_id"].shift(-1)
    current["end_stop_sequence"] = current.groupby("line_id")["stop_sequence"].shift(-1)
    current["end_route_distance_km"] = current.groupby("line_id")["route_distance_km"].shift(-1)
    current = current.dropna(subset=["end_station_id", "end_stop_sequence"]).copy()
    current["end_station_id"] = current["end_station_id"].astype(int)
    current = current.rename(columns={"station_id": "start_station_id"})
    current = current.merge(
        station_coords.rename(
            columns={
                "station_id": "start_station_id",
                "station_name": "start_station_name",
                "latitude": "start_lat",
                "longitude": "start_lon",
            }
        ),
        on="start_station_id",
        how="left",
        validate="many_to_one",
    )
    current = current.merge(
        station_coords.rename(
            columns={
                "station_id": "end_station_id",
                "station_name": "end_station_name",
                "latitude": "end_lat",
                "longitude": "end_lon",
            }
        ),
        on="end_station_id",
        how="left",
        validate="many_to_one",
    )
    current["segment_distance_km"] = (
        pd.to_numeric(current["end_route_distance_km"], errors="coerce")
        - pd.to_numeric(current["route_distance_km"], errors="coerce")
    )
    invalid_distance = current["segment_distance_km"].isna() | (current["segment_distance_km"] <= 0)
    current.loc[invalid_distance, "segment_distance_km"] = haversine_km(
        current.loc[invalid_distance, "start_lat"],
        current.loc[invalid_distance, "start_lon"],
        current.loc[invalid_distance, "end_lat"],
        current.loc[invalid_distance, "end_lon"],
    )
    station_flow = flow_trend[flow_trend["target_type"] == "station"].copy()
    flow_summary = (
        station_flow.groupby("target_id", as_index=False)["total_flow"]
        .mean()
        .rename(columns={"target_id": "start_station_id", "total_flow": "avg_passenger_flow"})
    )
    current = current.merge(flow_summary, on="start_station_id", how="left")
    current["avg_passenger_flow"] = current["avg_passenger_flow"].fillna(0).round(2)
    current["flow_level"] = flow_level_from_series(current["avg_passenger_flow"])
    current["ride_time_minutes"] = (current["segment_distance_km"] / 18 * 60).clip(lower=1).round(1)
    current["avg_speed_kph"] = (
        current["segment_distance_km"] / (current["ride_time_minutes"] / 60)
    ).replace([math.inf, -math.inf], pd.NA).fillna(18).round(1)
    current["delay_minutes"] = 0
    current["segment_id"] = (
        current["line_id"].astype(str) + "_" + current["stop_sequence"].astype(str).str.zfill(3)
    )
    current["segment_name"] = current["start_station_name"].astype(str) + " - " + current["end_station_name"].astype(str)
    current["path_coordinates"] = current.apply(
        lambda row: json.dumps(
            [[row["start_lon"], row["start_lat"]], [row["end_lon"], row["end_lat"]]],
            ensure_ascii=True,
        ),
        axis=1,
    )
    columns = [
        "segment_id",
        "segment_name",
        "line_id",
        "service_no",
        "line_name",
        "direction",
        "stop_sequence",
        "start_station_id",
        "start_station_name",
        "end_station_id",
        "end_station_name",
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
        "segment_distance_km",
        "ride_time_minutes",
        "avg_speed_kph",
        "delay_minutes",
        "avg_passenger_flow",
        "flow_level",
        "path_coordinates",
    ]
    df = current[columns].sort_values(["line_id", "stop_sequence"])
    write_csv(df, processed_dir / "map_road_segment.csv")
    return df


def iter_traffic_speed_band_snapshots(traffic_root: Path) -> Iterable[dict[str, Any]]:
    if not traffic_root.exists():
        return
    files = sorted(list(traffic_root.glob("*/*.json")) + list(traffic_root.glob("*/*.jsonl")))
    for path in files:
        if path.suffix.lower() == ".jsonl":
            with path.open("r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        yield json.loads(line)
        else:
            yield read_json(path)


def traffic_items_from_snapshot(snapshot: Any) -> tuple[Any, list[dict[str, Any]]]:
    if isinstance(snapshot, list):
        return None, snapshot
    if not isinstance(snapshot, dict):
        return None, []
    query_time = snapshot.get("query_time")
    value = snapshot.get("value")
    if value is None and isinstance(snapshot.get("response"), dict):
        value = snapshot["response"].get("value")
    return query_time, value or []


def build_traffic_speed_bands(raw_dir: Path, processed_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for snapshot in iter_traffic_speed_band_snapshots(raw_dir / "traffic_speed_bands"):
        query_time, items = traffic_items_from_snapshot(snapshot)
        for item in items:
            rows.append(
                {
                    "query_time": query_time,
                    "link_id": item.get("LinkID"),
                    "road_name": item.get("RoadName"),
                    "road_category": item.get("RoadCategory"),
                    "speed_band": item.get("SpeedBand"),
                    "minimum_speed_kmh": item.get("MinimumSpeed"),
                    "maximum_speed_kmh": item.get("MaximumSpeed"),
                    "start_lon": item.get("StartLon"),
                    "start_lat": item.get("StartLat"),
                    "end_lon": item.get("EndLon"),
                    "end_lat": item.get("EndLat"),
                }
            )

    columns = [
        "query_time",
        "link_id",
        "road_name",
        "road_category",
        "speed_band",
        "minimum_speed_kmh",
        "maximum_speed_kmh",
        "congestion_score",
        "heat_color",
        "start_lon",
        "start_lat",
        "end_lon",
        "end_lat",
        "line_coordinates",
    ]
    if not rows:
        print("skipped traffic_speed_bands.csv: no Traffic Speed Bands snapshots found")
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df["query_time"] = pd.to_datetime(df["query_time"], errors="coerce")
    for col in [
        "speed_band",
        "minimum_speed_kmh",
        "maximum_speed_kmh",
        "start_lon",
        "start_lat",
        "end_lon",
        "end_lat",
    ]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["speed_band", "start_lon", "start_lat", "end_lon", "end_lat"]).copy()
    df["speed_band"] = df["speed_band"].astype(int)
    df["congestion_score"] = ((8 - df["speed_band"]) / 7).clip(lower=0, upper=1).round(4)
    df["heat_color"] = df["speed_band"].map(SPEED_BAND_COLOR)
    df["line_coordinates"] = df.apply(
        lambda row: json.dumps(
            [[row["start_lon"], row["start_lat"]], [row["end_lon"], row["end_lat"]]],
            ensure_ascii=True,
        ),
        axis=1,
    )
    df = df[columns].sort_values(["query_time", "link_id"])
    write_csv(df, processed_dir / "traffic_speed_bands.csv")
    return df


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=root / "data" / "raw" / "lta")
    parser.add_argument("--processed-dir", type=Path, default=root / "data" / "processed")
    parser.add_argument("--month", default=None, help="Passenger Volume month such as 202605. Defaults to latest folder.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_dir = args.raw_dir.resolve()
    processed_dir = args.processed_dir.resolve()
    ensure_dir(processed_dir)

    stations = build_bus_station(raw_dir, processed_dir)
    lines = build_bus_line(raw_dir, processed_dir)
    line_station = build_line_station(raw_dir, processed_dir, lines)
    flow_trend = build_passenger_flow_trend(raw_dir, processed_dir, args.month)
    arrival = flatten_bus_arrival(raw_dir, processed_dir, lines, stations)
    vehicles = build_bus_vehicle(arrival, stations, processed_dir)
    eta, load = build_direct_status_tables(arrival, processed_dir)
    map_station = build_map_station(stations, line_station, processed_dir)
    map_road_segment = build_map_road_segment(line_station, stations, flow_trend, processed_dir)
    traffic_speed_bands = build_traffic_speed_bands(raw_dir, processed_dir)

    summary = pd.DataFrame(
        [
            {"dataset": "bus_station", "rows": len(stations)},
            {"dataset": "bus_line", "rows": len(lines)},
            {"dataset": "line_station", "rows": len(line_station)},
            {"dataset": "bus_vehicle", "rows": len(vehicles)},
            {"dataset": "lta_bus_arrival", "rows": len(arrival)},
            {"dataset": "bus_eta_status", "rows": len(eta)},
            {"dataset": "bus_load_status", "rows": len(load)},
            {"dataset": "map_station", "rows": len(map_station)},
            {"dataset": "map_road_segment", "rows": len(map_road_segment)},
            {"dataset": "passenger_flow_trend", "rows": len(flow_trend)},
            {"dataset": "traffic_speed_bands", "rows": len(traffic_speed_bands)},
        ]
    )
    write_csv(summary, processed_dir / "processing_summary.csv")


if __name__ == "__main__":
    main()
