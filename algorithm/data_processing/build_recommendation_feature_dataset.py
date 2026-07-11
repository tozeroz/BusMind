"""Build the offline recommendation feature dataset."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from algorithm.data_processing.recommendation_data_utils import (
    build_recommendation_feature_frame,
    default_model_dir,
    default_processed_dir,
    default_raw_dir,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=default_raw_dir())
    parser.add_argument("--processed-dir", type=Path, default=default_processed_dir())
    parser.add_argument(
        "--output",
        type=Path,
        default=default_model_dir() / "recommend_feature_dataset_v1.csv",
    )
    parser.add_argument("--month", default=None, help="Passenger volume month such as 202605")
    parser.add_argument("--max-groups", type=int, default=None, help="Optional cap for quick local verification")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = build_recommendation_feature_frame(
        processed_dir=args.processed_dir,
        raw_dir=args.raw_dir,
        month=args.month,
        max_groups=args.max_groups,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"built {len(dataset)} route rows across {dataset['candidate_group_id'].nunique()} groups -> {args.output}")


if __name__ == "__main__":
    main()
