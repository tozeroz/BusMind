"""Train the 12-feature to 5-score route scoring layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd

from algorithm.dataset.recommendation_data import default_dataset_dir
from algorithm.model.contracts import MODEL_VERSION, NUMERIC_FEATURE_NAMES
from algorithm.model.scorer import ARTIFACT_DIR


SCORE_NAMES = (
    "time_score",
    "comfort_score",
    "walk_score",
    "transfer_score",
    "reliability_score",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--labels", type=Path, default=default_dataset_dir() / "pseudo_labels.csv")
    parser.add_argument("--output", type=Path, default=ARTIFACT_DIR / "route_scorer_v1.json")
    parser.add_argument("--ridge", type=float, default=0.03)
    return parser.parse_args()


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-4, 1.0 - 1e-4)
    return np.log(clipped / (1.0 - clipped))


def _fit_linear_heads(x: np.ndarray, y_scores: np.ndarray, ridge: float) -> tuple[np.ndarray, np.ndarray, float]:
    y = _logit(y_scores / 100.0)
    x_aug = np.hstack([x, np.ones((len(x), 1), dtype=float)])
    penalty = np.eye(x_aug.shape[1], dtype=float) * ridge
    penalty[-1, -1] = 0.0
    solution = np.linalg.solve(x_aug.T @ x_aug + penalty, x_aug.T @ y)
    coefficients = solution[:-1, :].T
    bias = solution[-1, :]
    prediction = 1.0 / (1.0 + np.exp(-np.clip(x_aug @ solution, -40.0, 40.0))) * 100.0
    mse = float(np.mean((prediction - y_scores) ** 2))
    return coefficients, bias, mse


def main() -> None:
    args = parse_args()
    features = pd.read_csv(args.features)
    labels = pd.read_csv(args.labels)
    score_targets = labels.drop_duplicates("route_id")[["route_id", *SCORE_NAMES]]
    dataset = features.merge(score_targets, on="route_id", how="inner", validate="one_to_one")
    if dataset.empty:
        raise ValueError("No route rows matched between features and pseudo labels")

    feature_names = list(NUMERIC_FEATURE_NAMES)
    mean = dataset[feature_names].mean()
    std = dataset[feature_names].std(ddof=0).replace(0, 1.0)
    x = ((dataset[feature_names] - mean) / std).to_numpy(dtype=float)
    y_scores = dataset[list(SCORE_NAMES)].to_numpy(dtype=float)
    coefficients, bias, mse = _fit_linear_heads(x, y_scores, args.ridge)

    payload = {
        "model_version": MODEL_VERSION,
        "architecture": "12_feature_normalizer_plus_5_linear_sigmoid_heads",
        "feature_names": feature_names,
        "score_names": list(SCORE_NAMES),
        "mean": [round(float(value), 8) for value in mean.to_list()],
        "std": [round(float(value), 8) for value in std.to_list()],
        "subscore_coefficients": [[round(float(value), 8) for value in row] for row in coefficients],
        "subscore_bias": [round(float(value), 8) for value in bias],
        "training_rows": int(len(dataset)),
        "loss": {
            "name": "mse_on_pseudo_score_logits",
            "value": round(float(mse), 8),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    print(f"saved route scorer -> {args.output}")
    print(f"training rows={len(dataset)} mse={mse:.6f}")


if __name__ == "__main__":
    main()
