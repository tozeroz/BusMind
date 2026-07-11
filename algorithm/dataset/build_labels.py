"""Generate pseudo labels from the route scoring model."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from algorithm.dataset.recommendation_data import default_dataset_dir
from algorithm.model.contracts import CONTRACT_VERSION, PREFERENCE_NAMES
from algorithm.model.scorer import score_routes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--output", type=Path, default=default_dataset_dir() / "pseudo_labels.csv")
    return parser.parse_args()


def _sources(value: object) -> dict[str, str]:
    output: dict[str, str] = {}
    for part in str(value or "").split("|"):
        if ":" not in part:
            continue
        key, source = part.split(":", 1)
        output[key] = source
    return output


def _route_payload(group: pd.DataFrame) -> list[dict[str, object]]:
    routes = []
    for row in group.to_dict("records"):
        routes.append(
            {
                "route_id": row["route_id"],
                "service_nos": [item for item in str(row["service_nos"]).split("|") if item],
                "eta_minutes": row["eta_minutes"],
                "ride_time_minutes": row["ride_time_minutes"],
                "walk_time_minutes": row["walk_time_minutes"],
                "walk_distance_meters": row["walk_distance_meters"],
                "transfer_count": row["transfer_count"],
                "load_code": row["load_code"],
                "load_score": row["load_score"],
                "history_flow_score": row["history_flow_score"],
                "congestion_score": row["congestion_score"],
                "data_freshness_seconds": row["data_freshness_seconds"],
                "monitored_score": row["monitored_score"],
                "completeness_score": row["completeness_score"],
                "avg_service_frequency_minutes": row["avg_service_frequency_minutes"],
                "feature_sources": _sources(row["feature_sources"]),
                "degraded_fields": [item for item in str(row.get("degraded_fields") or "").split("|") if item],
            }
        )
    return routes


def main() -> None:
    args = parse_args()
    dataset = pd.read_csv(args.input)
    rows: list[dict[str, object]] = []
    for candidate_group_id, group in dataset.groupby("candidate_group_id"):
        group = group.sort_values(["eta_minutes", "route_id"]).head(10).copy()
        routes = _route_payload(group)
        for preference in PREFERENCE_NAMES:
            response = score_routes(
                {
                    "contract_version": CONTRACT_VERSION,
                    "request_id": str(candidate_group_id),
                    "preference": preference,
                    "routes": routes,
                }
            )
            results = {item["route_id"]: item for item in response["results"]}
            best_route_id = max(response["results"], key=lambda item: item["recommend_score"])["route_id"]
            for original in group.to_dict("records"):
                scored = results[original["route_id"]]
                rows.append(
                    {
                        "candidate_group_id": candidate_group_id,
                        "preference": preference,
                        "route_id": original["route_id"],
                        "label": 1 if original["route_id"] == best_route_id else 0,
                        "time_score": scored["time_score"],
                        "comfort_score": scored["comfort_score"],
                        "walk_score": scored["walk_score"],
                        "transfer_score": scored["transfer_score"],
                        "reliability_score": scored["reliability_score"],
                        "recommend_score": scored["recommend_score"],
                        "is_synthetic": bool(original.get("is_synthetic", False)),
                    }
                )
    output = pd.DataFrame(rows).sort_values(
        ["candidate_group_id", "preference", "label", "route_id"],
        ascending=[True, True, False, True],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"built {len(output)} pseudo-labeled rows -> {args.output}")


if __name__ == "__main__":
    main()
