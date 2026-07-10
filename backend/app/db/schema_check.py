"""Validate that the connected database contains the columns expected by the ORM.

Usage from the project root::

    cd backend
    python -m app.db.schema_check

The checker is read-only. It never creates or alters tables.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, inspect

from app.db.session import engine
from app.models import Base  # imports every model into shared metadata


@dataclass(frozen=True)
class SchemaIssue:
    object_name: str
    issue: str


# The view is intentionally not mapped as an ORM table because Base.create_all()
# must never create a physical table named v_map_station.
EXPECTED_VIEW_COLUMNS = {
    "station_id",
    "bus_stop_code",
    "station_name",
    "road_name",
    "longitude",
    "latitude",
    "line_count",
    "service_count",
    "line_ids",
    "line_names",
    "service_nos",
}


def validate_database_schema(bind: Engine = engine) -> list[SchemaIssue]:
    inspector = inspect(bind)
    table_names = set(inspector.get_table_names())
    view_names = set(inspector.get_view_names())
    issues: list[SchemaIssue] = []

    for table in Base.metadata.sorted_tables:
        if table.name not in table_names:
            issues.append(SchemaIssue(table.name, "missing table"))
            continue

        actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
        expected_columns = {column.name for column in table.columns}
        missing = sorted(expected_columns - actual_columns)
        extra = sorted(actual_columns - expected_columns)
        if missing:
            issues.append(SchemaIssue(table.name, f"missing columns: {', '.join(missing)}"))
        if extra:
            # Extra columns do not break ORM reads, but are reported so schema drift is visible.
            issues.append(SchemaIssue(table.name, f"extra columns: {', '.join(extra)}"))

    if "v_map_station" not in view_names:
        issues.append(SchemaIssue("v_map_station", "missing view"))
    else:
        actual_view_columns = {column["name"] for column in inspector.get_columns("v_map_station")}
        missing_view_columns = sorted(EXPECTED_VIEW_COLUMNS - actual_view_columns)
        if missing_view_columns:
            issues.append(
                SchemaIssue(
                    "v_map_station",
                    f"missing columns: {', '.join(missing_view_columns)}",
                )
            )

    return issues


def main() -> int:
    try:
        issues = validate_database_schema(engine)
    except Exception as exc:  # pragma: no cover - command-line diagnostics
        print(f"[ERROR] Cannot connect to database: {exc}")
        return 2

    if not issues:
        print("[OK] Database tables, fields and v_map_station match backend ORM expectations.")
        return 0

    print("[FAILED] Database schema mismatches found:")
    for issue in issues:
        print(f"  - {issue.object_name}: {issue.issue}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
