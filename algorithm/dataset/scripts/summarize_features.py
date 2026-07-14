"""汇总候选路线冻结特征的数据质量。"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import pandas as pd

from algorithm.dataset.scripts.feature_contract import (
    FROZEN_FEATURE_COLUMNS,
    numeric_feature_frame,
    parse_json_list,
    parse_json_object,
    read_frozen_features,
)
from algorithm.dataset.scripts.paths import feature_summary_path, features_path
from algorithm.model.contracts import NUMERIC_FEATURE_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=features_path())
    parser.add_argument("--output", type=Path, default=feature_summary_path(), help="Markdown 摘要输出路径")
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
        "# 候选路线特征数据摘要",
        "",
        f"输入文件：`{input_path}`",
        "",
        f"- 行数：{len(dataset)}",
        f"- 候选路线组数：{int(dataset['candidate_group_id'].nunique()) if 'candidate_group_id' in dataset else 0}",
        f"- 平均每组路线数：{round(float(group_sizes.mean()), 2) if not group_sizes.empty else 0}",
        f"- 合成样本行数：{synthetic_count}",
        f"- 缺失冻结字段：{', '.join(missing_columns) if missing_columns else '无'}",
        f"- 缺失特征来源字段：{', '.join(missing_source_keys) if missing_source_keys else '无'}",
        "",
        "## 预处理后的数值特征范围",
        "",
        *_markdown_table(numeric_rows, ("特征", "非空数", "最小值", "中位数", "最大值")),
        "",
        "## 降级字段统计",
        "",
        *_markdown_table([(field, count) for field, count in degraded_rows], ("字段", "次数")),
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
        print(f"已写入特征摘要 -> {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    main()
