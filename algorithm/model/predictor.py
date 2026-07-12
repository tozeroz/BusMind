"""Public model entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from algorithm.model.contracts import CONTRACT_VERSION
from algorithm.model.scorer import score_routes


def predict_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    return score_routes(payload, strict_backend=True)


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    return predict_recommendation(payload)


def _parse_args() -> argparse.Namespace:
    from algorithm.dataset.recommendation_data import default_dataset_dir

    parser = argparse.ArgumentParser(description="Run a small recommendation-model smoke test.")
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--preference", default="balanced")
    parser.add_argument("--group-id", default=None)
    parser.add_argument("--top-routes", type=int, default=5)
    return parser.parse_args()


def _sources(value: object) -> dict[str, str]:
    output: dict[str, str] = {}
    for part in str(value or "").split("|"):
        if ":" not in part:
            continue
        key, source = part.split(":", 1)
        output[key] = source
    return output


def _route_payload(group: Any) -> list[dict[str, object]]:
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


def _build_payload_from_features(args: argparse.Namespace) -> dict[str, Any]:
    import pandas as pd

    features = pd.read_csv(args.features)
    if features.empty:
        raise ValueError(f"No feature rows found in {args.features}")

    if args.group_id is None:
        candidate_group_id = str(features["candidate_group_id"].iloc[0])
    else:
        candidate_group_id = str(args.group_id)

    group = features[features["candidate_group_id"].astype(str) == candidate_group_id].copy()
    if group.empty:
        raise ValueError(f"No routes found for candidate_group_id={candidate_group_id}")

    group = group.sort_values(["eta_minutes", "route_id"]).head(args.top_routes)
    return {
        "contract_version": CONTRACT_VERSION,
        "request_id": f"smoke-test:{candidate_group_id}",
        "preference": args.preference,
        "routes": _route_payload(group),
    }


def main() -> None:
    args = _parse_args()
    payload = _build_payload_from_features(args)
    result = score_routes(payload, strict_backend=False)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
