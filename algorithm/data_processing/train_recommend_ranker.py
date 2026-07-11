"""Train a numpy-only linear ranker from pseudo labels."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from algorithm.data_processing.recommendation_data_utils import default_model_dir
from algorithm.recommend.contracts import PREFERENCE_NAMES
from algorithm.recommend.models import FEATURE_NAMES, MODEL_VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=default_model_dir() / "recommend_pseudo_labels_v1.csv",
    )
    parser.add_argument(
        "--model-output",
        type=Path,
        default=default_model_dir() / f"{MODEL_VERSION}.json",
    )
    parser.add_argument(
        "--stats-output",
        type=Path,
        default=default_model_dir() / "recommend_feature_stats_v1.json",
    )
    parser.add_argument("--epochs", type=int, default=350)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.002)
    return parser.parse_args()


def _sigmoid(values: np.ndarray) -> np.ndarray:
    positive = values >= 0
    negative = ~positive
    output = np.empty_like(values, dtype=float)
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exp_values = np.exp(values[negative])
    output[negative] = exp_values / (1.0 + exp_values)
    return output


def _build_pairwise_diffs(frame: pd.DataFrame, feature_names: list[str]) -> np.ndarray:
    diffs: list[np.ndarray] = []
    for _, group in frame.groupby("candidate_group_id"):
        positive = group[group["label"] == 1]
        negative = group[group["label"] == 0]
        if len(positive) != 1 or negative.empty:
            continue
        positive_vector = positive.iloc[0][feature_names].to_numpy(dtype=float)
        for _, negative_row in negative.iterrows():
            diffs.append(positive_vector - negative_row[feature_names].to_numpy(dtype=float))
    if not diffs:
        raise ValueError("No valid positive-vs-negative pairs were generated for training")
    return np.vstack(diffs)


def _train_pairwise_ranker(
    pairwise_diffs: np.ndarray,
    *,
    epochs: int,
    learning_rate: float,
    l2: float,
) -> tuple[np.ndarray, float, list[float]]:
    weights = np.zeros(pairwise_diffs.shape[1], dtype=float)
    bias = 0.0
    losses: list[float] = []
    for _ in range(epochs):
        logits = pairwise_diffs @ weights + bias
        probabilities = _sigmoid(logits)
        loss = float(np.mean(np.log1p(np.exp(-logits))) + 0.5 * l2 * np.dot(weights, weights))
        losses.append(loss)
        error = probabilities - 1.0
        grad_w = (pairwise_diffs.T @ error) / len(pairwise_diffs) + l2 * weights
        grad_b = float(np.mean(error))
        weights -= learning_rate * grad_w
        bias -= learning_rate * grad_b
    return weights, bias, losses


def main() -> None:
    args = parse_args()
    feature_names = list(FEATURE_NAMES)
    dataset = pd.read_csv(args.input)

    means = dataset[feature_names].mean().to_dict()
    stds = dataset[feature_names].std(ddof=0).replace(0, 1.0).to_dict()
    standardized = dataset.copy()
    for feature_name in feature_names:
        standardized[feature_name] = (standardized[feature_name] - means[feature_name]) / stds[feature_name]

    model_payload: dict[str, object] = {
        "version": MODEL_VERSION,
        "feature_names": feature_names,
        "preferences": {},
        "fallback": "rule_baseline",
    }

    for preference in PREFERENCE_NAMES:
        preference_frame = standardized[standardized["preference"] == preference].copy()
        if preference_frame.empty:
            continue
        pairwise_diffs = _build_pairwise_diffs(preference_frame, feature_names)
        weights, bias, losses = _train_pairwise_ranker(
            pairwise_diffs,
            epochs=args.epochs,
            learning_rate=args.learning_rate,
            l2=args.l2,
        )
        model_payload["preferences"][preference] = {
            "weights": [round(float(value), 8) for value in weights],
            "bias": round(float(bias), 8),
            "pair_count": int(len(pairwise_diffs)),
            "final_loss": round(float(losses[-1]), 8),
        }

    stats_payload = {
        "version": "recommend_feature_stats_v1",
        "feature_names": feature_names,
        "mean": {key: round(float(value), 8) for key, value in means.items()},
        "std": {key: round(float(value), 8) for key, value in stds.items()},
    }

    args.model_output.parent.mkdir(parents=True, exist_ok=True)
    with args.model_output.open("w", encoding="utf-8") as model_file:
        json.dump(model_payload, model_file, ensure_ascii=False, indent=2)
    with args.stats_output.open("w", encoding="utf-8") as stats_file:
        json.dump(stats_payload, stats_file, ensure_ascii=False, indent=2)

    print(f"saved ranker -> {args.model_output}")
    print(f"saved stats  -> {args.stats_output}")


if __name__ == "__main__":
    main()
