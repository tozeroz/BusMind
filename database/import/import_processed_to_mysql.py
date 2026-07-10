from __future__ import annotations

import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional for deployment shells
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


@dataclass(frozen=True, slots=True)
class TableSpec:
    name: str
    csv_name: str
    columns: tuple[str, ...]


TABLES: tuple[TableSpec, ...] = (
    TableSpec(
        "bus_station",
        "bus_station.csv",
        ("station_id", "bus_stop_code", "station_name", "road_name", "latitude", "longitude"),
    ),
    TableSpec(
        "bus_line",
        "bus_line.csv",
        (
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
        ),
    ),
    TableSpec(
        "line_station",
        "line_station.csv",
        (
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
        ),
    ),
    TableSpec(
        "bus_vehicle",
        "bus_vehicle.csv",
        (
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
        ),
    ),
    TableSpec(
        "bus_eta_status",
        "bus_eta_status.csv",
        (
            "query_time",
            "vehicle_id",
            "line_id",
            "target_station_id",
            "bus_stop_code",
            "eta_minutes",
            "arrival_time",
            "vehicle_to_stop_distance_m",
            "speed_kph",
            "data_source",
        ),
    ),
    TableSpec(
        "bus_load_status",
        "bus_load_status.csv",
        (
            "query_time",
            "vehicle_id",
            "line_id",
            "station_id",
            "bus_stop_code",
            "load_code",
            "load_level",
            "load_score",
            "load_rate",
            "onboard_count",
            "capacity",
            "confidence",
            "data_source",
        ),
    ),
    TableSpec(
        "passenger_flow_trend",
        "passenger_flow_trend.csv",
        (
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
        ),
    ),
    TableSpec(
        "map_road_segment",
        "map_road_segment.csv",
        (
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
        ),
    ),
    TableSpec(
        "lta_bus_arrival",
        "lta_bus_arrival.csv",
        (
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
            "eta_minutes",
            "duration_ms",
            "monitored",
            "vehicle_id",
            "vehicle_latitude",
            "vehicle_longitude",
            "visit_number",
            "load_code",
            "load_level",
            "load_score",
            "load_rate",
            "onboard_count",
            "capacity",
            "bus_type",
            "feature",
            "vehicle_to_stop_distance_m",
            "speed_kph",
        ),
    ),
    TableSpec(
        "traffic_speed_bands",
        "traffic_speed_bands.csv",
        (
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
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import BusMind processed CSV files into MySQL.")
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument(
        "--tables",
        nargs="*",
        help="Optional table names to import. Defaults to all tables in dependency order.",
    )
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true", help="Validate CSV files without connecting to MySQL.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / ".env", override=False)

    selected = select_tables(args.tables)
    processed_dir = args.processed_dir.resolve()
    if args.dry_run:
        for spec in selected:
            path = processed_dir / spec.csv_name
            print(f"{spec.name}: {count_csv_rows(path)} rows from {path}")
        return

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("Missing DATABASE_URL. Start your SSH tunnel first, then set DATABASE_URL.")

    from sqlalchemy import create_engine

    engine = create_engine(database_url, future=True)
    with engine.begin() as connection:
        for spec in selected:
            imported = import_table(connection, processed_dir, spec, args.batch_size)
            print(f"{spec.name}: imported {imported} rows")


def select_tables(names: list[str] | None) -> list[TableSpec]:
    if not names:
        return list(TABLES)
    by_name = {spec.name: spec for spec in TABLES}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise SystemExit(f"Unknown table(s): {', '.join(missing)}")
    return [by_name[name] for name in names]


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return max(0, sum(1 for _ in f) - 1)


def import_table(connection, processed_dir: Path, spec: TableSpec, batch_size: int) -> int:
    path = processed_dir / spec.csv_name
    if not path.exists():
        print(f"{spec.name}: skipped missing {path}")
        return 0

    statement = build_upsert_statement(spec)
    total = 0
    batch: list[dict[str, object | None]] = []
    for row in iter_csv_rows(path, spec.columns):
        batch.append(row)
        if len(batch) >= batch_size:
            connection.execute(statement, batch)
            total += len(batch)
            batch.clear()
    if batch:
        connection.execute(statement, batch)
        total += len(batch)
    return total


def iter_csv_rows(path: Path, columns: tuple[str, ...]) -> Iterable[dict[str, object | None]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return
        missing = [column for column in columns if column not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")
        for raw in reader:
            yield {column: clean_value(raw.get(column)) for column in columns}


def clean_value(value: str | None) -> object | None:
    if value is None:
        return None
    text_value = value.strip()
    if text_value == "" or text_value == "-" or text_value.lower() in {"nan", "nat", "<na>", "none", "null"}:
        return None
    return text_value


def build_upsert_statement(spec: TableSpec):
    from sqlalchemy import text

    column_sql = ", ".join(f"`{column}`" for column in spec.columns)
    value_sql = ", ".join(f":{column}" for column in spec.columns)
    update_columns = [column for column in spec.columns if not column.endswith("_id") or column not in {"station_id", "line_id", "vehicle_id"}]
    update_sql = ", ".join(f"`{column}` = VALUES(`{column}`)" for column in update_columns)
    sql = f"INSERT INTO `{spec.name}` ({column_sql}) VALUES ({value_sql})"
    if update_sql:
        sql += f" ON DUPLICATE KEY UPDATE {update_sql}"
    return text(sql)


if __name__ == "__main__":
    main()
