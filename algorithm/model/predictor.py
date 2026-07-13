"""Public model entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_routes_from_feature_group,
    read_frozen_features,
)
from algorithm.model.contracts import CONTRACT_VERSION
from algorithm.model.register import score_routes


def predict_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
    return score_routes(payload, strict_backend=True)


def predict(payload: dict[str, Any]) -> dict[str, Any]:
    return predict_recommendation(payload)


def _parse_args() -> argparse.Namespace:
    from algorithm.dataset.scripts.recommendation_data import default_dataset_dir

    parser = argparse.ArgumentParser(description="Run a small recommendation-model smoke test.")
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--preference", default="balanced")
    parser.add_argument("--group-id", default=None)
    parser.add_argument("--top-routes", type=int, default=5)
    return parser.parse_args()


def _build_payload_from_features(args: argparse.Namespace) -> dict[str, Any]:
    features = read_frozen_features(args.features)
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
        "routes": model_input_routes_from_feature_group(group),
    }


def main() -> None:
    args = _parse_args()
    payload = _build_payload_from_features(args)
    result = score_routes(payload, strict_backend=True)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
