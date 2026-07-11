from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
IMPORT_SCRIPT = PROJECT_ROOT / "database" / "import" / "import_processed_to_mysql.py"


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    name: str
    csv_name: str
    columns: tuple[str, ...]
    required: tuple[str, ...]
    unique_keys: tuple[tuple[str, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class Issue:
    severity: str
    dataset: str
    message: str


def load_import_table_specs() -> list[DatasetSpec]:
    spec = importlib.util.spec_from_file_location("busmind_import_processed", IMPORT_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load import script: {IMPORT_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    required_by_table: dict[str, tuple[str, ...]] = {
        "bus_station": ("station_id", "bus_stop_code", "station_name", "latitude", "longitude"),
        "bus_line": ("line_id", "service_no", "line_name", "direction"),
        "line_station": ("line_station_id", "line_id", "stop_sequence", "station_id"),
        "bus_vehicle": ("vehicle_id", "line_id"),
        "bus_eta_status": ("query_time", "vehicle_id", "line_id", "target_station_id", "eta_minutes"),
        "bus_load_status": ("query_time", "vehicle_id", "line_id", "load_level"),
        "passenger_flow_trend": (
            "target_type",
            "target_id",
            "record_time",
            "tap_in_volume",
            "tap_out_volume",
            "total_flow",
        ),
        "map_road_segment": (
            "segment_id",
            "line_id",
            "start_station_id",
            "end_station_id",
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lon",
        ),
        "lta_bus_arrival": ("query_time", "station_id", "service_no", "line_id", "estimated_arrival", "eta_minutes"),
        "traffic_speed_bands": (
            "query_time",
            "speed_band",
            "start_lon",
            "start_lat",
            "end_lon",
            "end_lat",
        ),
    }
    unique_by_table: dict[str, tuple[tuple[str, ...], ...]] = {
        "bus_station": (("station_id",), ("bus_stop_code",)),
        "bus_line": (("line_id",), ("service_no", "direction")),
        "line_station": (("line_station_id",), ("line_id", "stop_sequence")),
        "bus_vehicle": (("vehicle_id",),),
        "bus_eta_status": (("vehicle_id", "target_station_id", "query_time"),),
        "bus_load_status": (("vehicle_id", "station_id", "query_time"),),
        "passenger_flow_trend": (("target_type", "target_id", "record_time", "day_type"),),
        "map_road_segment": (("segment_id",),),
        "lta_bus_arrival": (("vehicle_id", "station_id", "line_id", "query_time", "visit_order"),),
        "traffic_speed_bands": (("link_id", "query_time"),),
    }

    specs = [
        DatasetSpec(
            name=item.name,
            csv_name=item.csv_name,
            columns=tuple(item.columns),
            required=required_by_table[item.name],
            unique_keys=unique_by_table.get(item.name, ()),
        )
        for item in module.TABLES
    ]
    specs.append(
        DatasetSpec(
            name="map_station",
            csv_name="map_station.csv",
            columns=(
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
            ),
            required=("station_id", "bus_stop_code", "station_name", "latitude", "longitude"),
            unique_keys=(("station_id",), ("bus_stop_code",)),
        )
    )
    return specs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate BusMind processed CSV contracts and relationships.")
    parser.add_argument("--processed-dir", type=Path, default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--report", type=Path, help="Optional Markdown report output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    processed_dir = args.processed_dir.resolve()
    specs = load_import_table_specs()

    rows_by_dataset: dict[str, list[dict[str, str | None]]] = {}
    row_counts: dict[str, int] = {}
    issues: list[Issue] = []

    expected_csv_names = {spec.csv_name for spec in specs} | {"processing_summary.csv"}
    for path in sorted(processed_dir.glob("*.csv")):
        if path.name not in expected_csv_names:
            issues.append(
                Issue(
                    "WARN",
                    path.stem,
                    f"Unexpected CSV in processed dir: {path.name}. Keep only if it is a deliberate local artifact.",
                )
            )

    for spec in specs:
        path = processed_dir / spec.csv_name
        if not path.exists():
            issues.append(Issue("ERROR", spec.name, f"Missing file: {path}"))
            rows_by_dataset[spec.name] = []
            row_counts[spec.name] = 0
            continue
        rows, file_issues = load_csv(path, spec)
        rows_by_dataset[spec.name] = rows
        row_counts[spec.name] = len(rows)
        issues.extend(file_issues)

    issues.extend(validate_summary(processed_dir, row_counts))
    issues.extend(validate_foreign_keys(rows_by_dataset))
    issues.extend(validate_value_ranges(rows_by_dataset))

    output = render_report(row_counts, issues)
    print(output)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")

    return 1 if any(issue.severity == "ERROR" for issue in issues) else 0


def load_csv(path: Path, spec: DatasetSpec) -> tuple[list[dict[str, str | None]], list[Issue]]:
    issues: list[Issue] = []
    rows: list[dict[str, str | None]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in spec.columns if column not in fieldnames]
        if missing:
            issues.append(Issue("ERROR", spec.name, f"Missing required columns: {', '.join(missing)}"))
        extra = [column for column in fieldnames if column not in spec.columns]
        if extra:
            issues.append(Issue("WARN", spec.name, f"Extra columns not imported by MySQL script: {', '.join(extra)}"))

        null_counter: Counter[str] = Counter()
        unique_values: dict[tuple[str, ...], set[tuple[str | None, ...]]] = {
            key: set() for key in spec.unique_keys
        }
        duplicate_counter: Counter[tuple[str, ...]] = Counter()

        for raw in reader:
            row = {column: clean_value(raw.get(column)) for column in fieldnames}
            rows.append(row)
            for column in spec.required:
                if row.get(column) is None:
                    null_counter[column] += 1
            for key in spec.unique_keys:
                value = tuple(row.get(column) for column in key)
                if any(item is None for item in value):
                    continue
                if value in unique_values[key]:
                    duplicate_counter[key] += 1
                else:
                    unique_values[key].add(value)

    for column, count in null_counter.items():
        issues.append(Issue("ERROR", spec.name, f"{count} rows have empty required column `{column}`"))
    for key, count in duplicate_counter.items():
        issues.append(Issue("ERROR", spec.name, f"{count} duplicate key rows for ({', '.join(key)})"))
    return rows, issues


def clean_value(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if text == "" or text == "-" or text.lower() in {"nan", "nat", "<na>", "none", "null"}:
        return None
    return text


def validate_summary(processed_dir: Path, row_counts: dict[str, int]) -> list[Issue]:
    path = processed_dir / "processing_summary.csv"
    if not path.exists():
        return [Issue("WARN", "processing_summary", "Missing processing_summary.csv")]

    issues: list[Issue] = []
    summary: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            dataset = clean_value(row.get("dataset"))
            rows = clean_value(row.get("rows"))
            if dataset and rows is not None:
                try:
                    summary[dataset] = int(float(rows))
                except ValueError:
                    issues.append(Issue("ERROR", "processing_summary", f"Invalid row count for {dataset}: {rows}"))

    for dataset, count in sorted(row_counts.items()):
        if dataset not in summary:
            issues.append(Issue("WARN", "processing_summary", f"{dataset} is not listed in processing_summary.csv"))
        elif summary[dataset] != count:
            issues.append(
                Issue(
                    "ERROR",
                    "processing_summary",
                    f"{dataset} count mismatch: summary={summary[dataset]}, actual={count}",
                )
            )
    return issues


def validate_foreign_keys(rows: dict[str, list[dict[str, str | None]]]) -> list[Issue]:
    issues: list[Issue] = []
    station_ids = values(rows, "bus_station", "station_id")
    line_ids = values(rows, "bus_line", "line_id")
    vehicle_ids = values(rows, "bus_vehicle", "vehicle_id")

    fk_checks = [
        ("bus_line", "origin_station_id", station_ids, True),
        ("bus_line", "destination_station_id", station_ids, True),
        ("line_station", "line_id", line_ids, False),
        ("line_station", "station_id", station_ids, False),
        ("bus_vehicle", "line_id", line_ids, False),
        ("bus_vehicle", "current_station_id", station_ids, True),
        ("bus_vehicle", "next_station_id", station_ids, True),
        ("bus_eta_status", "vehicle_id", vehicle_ids, False),
        ("bus_eta_status", "line_id", line_ids, False),
        ("bus_eta_status", "target_station_id", station_ids, False),
        ("bus_load_status", "vehicle_id", vehicle_ids, False),
        ("bus_load_status", "line_id", line_ids, False),
        ("bus_load_status", "station_id", station_ids, True),
        ("passenger_flow_trend", "target_id", station_ids, False),
        ("map_road_segment", "line_id", line_ids, False),
        ("map_road_segment", "start_station_id", station_ids, False),
        ("map_road_segment", "end_station_id", station_ids, False),
        ("map_station", "station_id", station_ids, False),
    ]
    for dataset, column, reference, nullable in fk_checks:
        missing = count_missing_references(rows.get(dataset, []), column, reference, nullable=nullable)
        if missing:
            issues.append(Issue("ERROR", dataset, f"{missing} rows reference missing `{column}` values"))
    return issues


def values(rows: dict[str, list[dict[str, str | None]]], dataset: str, column: str) -> set[str]:
    return {row[column] for row in rows.get(dataset, []) if row.get(column) is not None}


def count_missing_references(
    rows: Iterable[dict[str, str | None]],
    column: str,
    reference: set[str],
    *,
    nullable: bool,
) -> int:
    count = 0
    for row in rows:
        value = row.get(column)
        if value is None and nullable:
            continue
        if value not in reference:
            count += 1
    return count


def validate_value_ranges(rows: dict[str, list[dict[str, str | None]]]) -> list[Issue]:
    issues: list[Issue] = []
    load_scores = {"SEA": 100.0, "SDA": 70.0, "LSD": 35.0}
    load_levels = {"SEA": "seats_available", "SDA": "standing_available", "LSD": "limited_standing"}

    for dataset in ("lta_bus_arrival", "bus_load_status", "bus_vehicle"):
        invalid_load_code = 0
        invalid_load_mapping = 0
        for row in rows.get(dataset, []):
            code = row.get("load_code")
            if code is None:
                continue
            if code not in load_scores:
                invalid_load_code += 1
                continue
            if row.get("load_level") and row.get("load_level") != load_levels[code]:
                invalid_load_mapping += 1
            if row.get("load_score") and abs(as_float(row.get("load_score")) - load_scores[code]) > 0.01:
                invalid_load_mapping += 1
        if invalid_load_code:
            issues.append(Issue("ERROR", dataset, f"{invalid_load_code} rows have unknown LTA Load code"))
        if invalid_load_mapping:
            issues.append(Issue("ERROR", dataset, f"{invalid_load_mapping} rows have inconsistent Load mapping"))

    for dataset, column in (("lta_bus_arrival", "eta_minutes"), ("bus_eta_status", "eta_minutes")):
        invalid = sum(1 for row in rows.get(dataset, []) if as_float(row.get(column)) < 0)
        if invalid:
            issues.append(Issue("ERROR", dataset, f"{invalid} rows have negative `{column}`"))

    invalid_station_coords = sum(
        1
        for row in rows.get("bus_station", [])
        if not in_range(as_float(row.get("latitude")), 1.0, 1.7)
        or not in_range(as_float(row.get("longitude")), 103.0, 104.5)
    )
    if invalid_station_coords:
        issues.append(Issue("ERROR", "bus_station", f"{invalid_station_coords} station coordinates are outside Singapore bounds"))

    invalid_distance = sum(
        1 for row in rows.get("map_road_segment", []) if as_float(row.get("segment_distance_km")) <= 0
    )
    if invalid_distance:
        issues.append(Issue("ERROR", "map_road_segment", f"{invalid_distance} rows have non-positive segment distance"))

    invalid_speed_band = 0
    invalid_congestion = 0
    unknown_speed_band = 0
    missing_link_id = 0
    for row in rows.get("traffic_speed_bands", []):
        speed_band = as_float(row.get("speed_band"))
        if speed_band == 0:
            unknown_speed_band += 1
            if row.get("congestion_score") is not None:
                invalid_congestion += 1
            continue
        if not in_range(speed_band, 1, 8):
            invalid_speed_band += 1
            continue
        expected = round((8 - speed_band) / 7, 4)
        actual = as_float(row.get("congestion_score"))
        if abs(actual - expected) > 0.0001:
            invalid_congestion += 1
        if row.get("link_id") is None:
            missing_link_id += 1
    if invalid_speed_band:
        issues.append(Issue("ERROR", "traffic_speed_bands", f"{invalid_speed_band} rows have speed_band outside 1..8"))
    if invalid_congestion:
        issues.append(Issue("ERROR", "traffic_speed_bands", f"{invalid_congestion} rows have wrong congestion_score formula"))
    if unknown_speed_band:
        issues.append(Issue("WARN", "traffic_speed_bands", f"{unknown_speed_band} rows have speed_band=0, treated as unknown"))
    if missing_link_id:
        issues.append(Issue("WARN", "traffic_speed_bands", f"{missing_link_id} rows have empty link_id"))

    return issues


def as_float(value: str | None) -> float:
    if value is None:
        return float("nan")
    try:
        return float(value)
    except ValueError:
        return float("nan")


def in_range(value: float, low: float, high: float) -> bool:
    return low <= value <= high


def render_report(row_counts: dict[str, int], issues: list[Issue]) -> str:
    lines = [
        "# BusMind processed data validation",
        "",
        "## Row counts",
        "",
        "| **Dataset** | **Rows** |",
        "|---|---:|",
    ]
    for dataset, count in sorted(row_counts.items()):
        lines.append(f"| `{dataset}` | {count} |")

    lines.extend(["", "## Findings", ""])
    if not issues:
        lines.append("No issues found.")
    else:
        lines.extend(["| **Severity** | **Dataset** | **Message** |", "|---|---|---|"])
        for issue in sorted(issues, key=lambda item: (item.severity != "ERROR", item.dataset, item.message)):
            lines.append(f"| {issue.severity} | `{issue.dataset}` | {issue.message} |")

    error_count = sum(1 for issue in issues if issue.severity == "ERROR")
    warn_count = sum(1 for issue in issues if issue.severity == "WARN")
    lines.extend(["", f"Result: {error_count} error(s), {warn_count} warning(s)."])
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
