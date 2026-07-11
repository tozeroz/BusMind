"""Generate pseudo labels from the rule-based recommendation baseline."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import pandas as pd

from algorithm.data_processing.recommendation_data_utils import default_model_dir
from algorithm.recommend.contracts import PREFERENCE_NAMES
from algorithm.recommend.predictor import predict_recommendation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=default_model_dir() / "recommend_feature_dataset_v1.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=default_model_dir() / "recommend_pseudo_labels_v1.csv",
    )
    return parser.parse_args()


def _line_ids(value: object) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    return [item for item in text.split("|") if item]


def _route_payload(group: pd.DataFrame) -> list[dict[str, object]]:
    payload = []
    for row in group.to_dict("records"):
        payload.append(
            {
                "route_id": row["route_id"],
                "service_no": row.get("service_no"),
                "line_ids": _line_ids(row.get("line_ids")),
                "eta_minutes": row.get("eta_minutes"),
                "load_code": row.get("load_code"),
                "load_score": row.get("load_score"),
                "walk_time_minutes": row.get("walk_time_minutes"),
                "ride_time_minutes": row.get("ride_time_minutes"),
                "transfer_count": row.get("transfer_count"),
                "avg_service_frequency": row.get("avg_service_frequency"),
                "station_flow_mean": row.get("station_flow_mean"),
                "station_flow_level": row.get("station_flow_level"),
                "congestion_score": row.get("congestion_score"),
                "reliability_score": row.get("reliability_score"),
                "confidence": row.get("confidence"),
                "data_source": row.get("data_source", "offline_data"),
            }
        )
    return payload


def main() -> None:
    args = parse_args()
    dataset = pd.read_csv(args.input)
    rows: list[dict[str, object]] = []
    for candidate_group_id, group in dataset.groupby("candidate_group_id"):
        route_payload = _route_payload(group)
        for preference in PREFERENCE_NAMES:
            prediction = predict_recommendation(
                {
                    "feature_source": "offline_data",
                    "preference": preference,
                    "routes": route_payload,
                }
            )
            best_route_id = prediction["best_experience_route_id"]
            item_lookup = {item["route_id"]: item for item in prediction["items"]}
            for original in group.to_dict("records"):
                scored = item_lookup[original["route_id"]]
                rows.append(
                    {
                        "candidate_group_id": candidate_group_id,
                        "preference": preference,
                        "route_id": original["route_id"],
                        "label": 1 if original["route_id"] == best_route_id else 0,
                        "recommend_score": scored["recommend_score"],
                        "recommend_types": "|".join(scored["recommend_types"]),
                        "time_score": scored["time_score"],
                        "comfort_score": scored["comfort_score"],
                        "walk_score": scored["walk_score"],
                        "transfer_score": scored["transfer_score"],
                        "frequency_score": scored["frequency_score"],
                        "flow_score": scored["flow_score"],
                        "congestion_score": scored["congestion_score"],
                        "reliability_score": scored["reliability_score"],
                        "is_synthetic": bool(original.get("is_synthetic", False)),
                    }
                )
    output = pd.DataFrame(rows).sort_values(["candidate_group_id", "preference", "label", "route_id"], ascending=[True, True, False, True])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"built {len(output)} pseudo-labeled rows -> {args.output}")


if __name__ == "__main__":
    main()
