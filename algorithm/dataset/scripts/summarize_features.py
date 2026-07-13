"""Summarize frozen recommendation feature data quality."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    FROZEN_FEATURE_COLUMNS,
    numeric_feature_frame,
    parse_json_list,
    parse_json_object,
    read_frozen_features,
)
from algorithm.model.contracts import NUMERIC_FEATURE_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--output", type=Path, help="Optional markdown report path")
    return parser.parse_args()


def _markdown_table(rows: list[tuple[object, ...]], headers: tuple[str, ...]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(str(value) for value in row) + " |" for row in rows)
    return lines


def build_report(dataset: pd.DataFrame, input_path: Path) -> str:
    missing_columns = [column for column in FROZEN_FEATURE_COLUMNS if column not in dataset.columns]
    numeric = numeric_feature_frame(dataset) if not missing_columns else pd.DataFrame()
    group_sizes = dataset.groupby("candidate_group_id")["route_id"].count() if "candidate_group_id" in dataset else pd.Series(dtype=int)
    synthetic_count = int(dataset.get("is_synthetic", pd.Series(dtype=bool)).astype(str).str.lower().isin({"1", "true", "yes"}).sum())

    degraded_counts: dict[str, int] = {}
    for value in dataset.get("degraded_fields", pd.Series(dtype=str)).fillna(""):
        for field in parse_json_list(value):
            degraded_counts[field] = degraded_counts.get(field, 0) + 1

    source_keys: set[str] = set()
    for value in dataset.get("feature_sources", pd.Series(dtype=str)).fillna(""):
        source_keys.update(parse_json_object(value).keys())

    numeric_rows: list[tuple[object, ...]] = []
    for column in NUMERIC_FEATURE_NAMES:
        values = pd.to_numeric(numeric[column], errors="coerce") if column in numeric else pd.Series(dtype=float)
        numeric_rows.append(
            (
                column,
                int(values.notna().sum()),
                round(float(values.min()), 3) if values.notna().any() else "",
                round(float(values.median()), 3) if values.notna().any() else "",
                round(float(values.max()), 3) if values.notna().any() else "",
            )
        )

    degraded_rows = sorted(degraded_counts.items(), key=lambda item: (-item[1], item[0])) or [("none", 0)]
    missing_source_keys = [
        field
        for field in (
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
        )
        if field not in source_keys
    ]

    lines = [
        "# Recommendation Feature Dataset Summary",
        "",
        f"Input: `{input_path}`",
        "",
        f"- Rows: {len(dataset)}",
        f"- Candidate groups: {int(dataset['candidate_group_id'].nunique()) if 'candidate_group_id' in dataset else 0}",
        f"- Average routes per group: {round(float(group_sizes.mean()), 2) if not group_sizes.empty else 0}",
        f"- Synthetic rows: {synthetic_count}",
        f"- Missing frozen columns: {', '.join(missing_columns) if missing_columns else 'none'}",
        f"- Missing feature source keys: {', '.join(missing_source_keys) if missing_source_keys else 'none'}",
        "",
        "## Numeric Feature Ranges After Preprocessing",
        "",
        *_markdown_table(numeric_rows, ("feature", "non_null", "min", "median", "max")),
        "",
        "## Degraded Field Counts",
        "",
        *_markdown_table([(field, count) for field, count in degraded_rows], ("field", "count")),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    dataset = read_frozen_features(args.input)
    report = build_report(dataset, args.input)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
        print(f"wrote feature summary -> {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
