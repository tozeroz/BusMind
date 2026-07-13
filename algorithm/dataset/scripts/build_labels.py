"""Generate pseudo labels from frozen backend-style route features."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_routes_from_feature_group,
    read_frozen_features,
)
from algorithm.model.contracts import CONTRACT_VERSION, PREFERENCE_NAMES
from algorithm.model.scorer import score_routes


SCORE_NAMES = (
    "time_score",
    "comfort_score",
    "walk_score",
    "transfer_score",
    "reliability_score",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--output", type=Path, default=default_dataset_dir() / "pseudo_labels.csv")
    return parser.parse_args()


def _bool_value(value: object) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def main() -> None:
    args = parse_args()
    dataset = read_frozen_features(args.input)
    rows: list[dict[str, object]] = []
    for candidate_group_id, group in dataset.groupby("candidate_group_id"):
        group = group.sort_values(["eta_minutes", "route_id"]).head(10).copy()
        routes = model_input_routes_from_feature_group(group)
        for preference in PREFERENCE_NAMES:
            response = score_routes(
                {
                    "contract_version": CONTRACT_VERSION,
                    "request_id": str(candidate_group_id),
                    "preference": preference,
                    "routes": routes,
                },
                strict_backend=True,
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
                        **{name: scored[name] for name in SCORE_NAMES},
                        "recommend_score": scored["recommend_score"],
                        "is_synthetic": _bool_value(original.get("is_synthetic", False)),
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
