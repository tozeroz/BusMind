"""Train the 12-feature to 5-score route scoring layer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import numeric_feature_frame, read_frozen_features
from algorithm.model.contracts import MODEL_VERSION, NUMERIC_FEATURE_NAMES
from algorithm.model.linear_scoring.model import ARTIFACT_DIR
from algorithm.model.utils.score_mixing import SCORE_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--labels", type=Path, default=default_dataset_dir() / "pseudo_labels.csv")
    parser.add_argument("--output", type=Path, default=ARTIFACT_DIR / "linear_route_scoring.json")
    parser.add_argument("--ridge", type=float, default=0.03)
    return parser.parse_args()


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-4, 1.0 - 1e-4)
    return np.log(clipped / (1.0 - clipped))


def _fit_linear_heads(
    x: np.ndarray,
    y_scores: np.ndarray,
    ridge: float,
    sample_weight: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    y = _logit(y_scores / 100.0)
    x_aug = np.hstack([x, np.ones((len(x), 1), dtype=float)])
    if sample_weight is None:
        weights = np.ones(len(x_aug), dtype=float)
    else:
        weights = np.clip(sample_weight.astype(float), 0.05, 1.5)
        weights = weights / max(float(weights.mean()), 1e-8)
    weighted_x = x_aug * np.sqrt(weights)[:, None]
    weighted_y = y * np.sqrt(weights)[:, None]
    penalty = np.eye(x_aug.shape[1], dtype=float) * ridge
    penalty[-1, -1] = 0.0
    solution = np.linalg.solve(weighted_x.T @ weighted_x + penalty, weighted_x.T @ weighted_y)
    coefficients = solution[:-1, :].T
    bias = solution[-1, :]
    prediction = 1.0 / (1.0 + np.exp(-np.clip(x_aug @ solution, -40.0, 40.0))) * 100.0
    row_mse = np.mean((prediction - y_scores) ** 2, axis=1)
    mse = float(np.average(row_mse, weights=weights))
    return coefficients, bias, mse


def main() -> None:
    args = parse_args()
    features = read_frozen_features(args.features)
    labels = pd.read_csv(args.labels)

    # route_id 在真实采样里可能不是全局唯一；训练分项评分时按候选集合内的线路去重对齐。
    join_keys = ["candidate_group_id", "route_id"]
    numeric_features = numeric_feature_frame(features.drop_duplicates(join_keys).copy())
    target_columns = [*join_keys, *SCORE_NAMES]
    if "sample_weight" in labels.columns:
        target_columns.append("sample_weight")
    score_targets = labels.drop_duplicates(join_keys)[target_columns]
    dataset = numeric_features.merge(score_targets, on=join_keys, how="inner", validate="one_to_one")
    if dataset.empty:
        raise ValueError("No route rows matched between features and pseudo labels")

    feature_names = list(NUMERIC_FEATURE_NAMES)
    mean = dataset[feature_names].mean()
    std = dataset[feature_names].std(ddof=0).replace(0, 1.0)
    x = ((dataset[feature_names] - mean) / std).to_numpy(dtype=float)
    y_scores = dataset[list(SCORE_NAMES)].to_numpy(dtype=float)
    sample_weight = dataset["sample_weight"].to_numpy(dtype=float) if "sample_weight" in dataset.columns else None
    coefficients, bias, mse = _fit_linear_heads(x, y_scores, args.ridge, sample_weight)

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
        "sample_weight_column": "sample_weight" if sample_weight is not None else None,
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
