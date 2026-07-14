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

from algorithm.dataset.scripts.feature_contract import numeric_feature_frame, read_frozen_features
from algorithm.dataset.scripts.paths import features_path, fused_labels_path, rule_labels_path
from algorithm.model.contracts import MODEL_VERSION, NUMERIC_FEATURE_NAMES
from algorithm.model.linear_scoring.model import ARTIFACT_DIR
from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=features_path())
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=ARTIFACT_DIR / "linear_route_scoring.json")
    parser.add_argument("--ridge", type=float, default=0.03)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    return parser.parse_args()


def _default_labels_path() -> Path:
    fused = fused_labels_path()
    if fused.is_file():
        return fused
    return rule_labels_path()


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
    prediction = _predict_linear_heads(x, coefficients, bias)
    row_mse = np.mean((prediction - y_scores) ** 2, axis=1)
    mse = float(np.average(row_mse, weights=weights))
    return coefficients, bias, mse


def _load_training_frame(features_path: Path, labels_path: Path) -> pd.DataFrame:
    features = read_frozen_features(features_path)
    labels = pd.read_csv(labels_path)

    join_keys = ["candidate_group_id", "route_id"]
    numeric_features = numeric_feature_frame(features.drop_duplicates(join_keys).copy())
    target_columns = [*join_keys, *SCORE_NAMES]
    if "sample_weight" in labels.columns:
        target_columns.append("sample_weight")
    # 融合标签按偏好展开，但五个子评分是路线级目标，训练前需要按路线去重。
    score_targets = labels.drop_duplicates(join_keys)[target_columns]
    dataset = numeric_features.merge(score_targets, on=join_keys, how="inner", validate="one_to_one")
    if dataset.empty:
        raise ValueError("No route rows matched between features and pseudo labels")
    return dataset


def _group_train_eval_mask(dataset: pd.DataFrame, test_size: float, random_state: int) -> np.ndarray:
    # 同一个候选路线组必须整体进入训练集或验证集，避免组内比较信息泄漏。
    groups = np.array(sorted(dataset["candidate_group_id"].astype(str).unique()))
    if len(groups) < 5 or test_size <= 0:
        return np.ones(len(dataset), dtype=bool)
    rng = np.random.default_rng(random_state)
    shuffled = groups.copy()
    rng.shuffle(shuffled)
    eval_count = max(1, int(round(len(shuffled) * min(max(test_size, 0.0), 0.5))))
    eval_groups = set(shuffled[:eval_count])
    return ~dataset["candidate_group_id"].astype(str).isin(eval_groups).to_numpy()


def _predict_linear_heads(x: np.ndarray, coefficients: np.ndarray, bias: np.ndarray) -> np.ndarray:
    logits = x @ coefficients.T + bias
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -40.0, 40.0))) * 100.0


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    errors = y_pred - y_true
    return {
        "rmse": round(float(np.sqrt(np.mean(errors**2))), 6),
        "mae": round(float(np.mean(np.abs(errors))), 6),
    }


def _recommend_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, dict[str, float]]:
    output: dict[str, dict[str, float]] = {}
    for preference, weights in PREFERENCE_MIX.items():
        true_score = y_true @ weights
        pred_score = y_pred @ weights
        output[preference] = _metrics(true_score, pred_score)
    return output


def main() -> None:
    args = parse_args()
    labels_path = args.labels or _default_labels_path()
    dataset = _load_training_frame(args.features, labels_path)

    feature_names = list(NUMERIC_FEATURE_NAMES)
    train_mask = _group_train_eval_mask(dataset, args.test_size, args.random_state)
    train_frame = dataset.loc[train_mask].copy()
    eval_frame = dataset.loc[~train_mask].copy()

    # 归一化参数只用训练集拟合，验证集不能参与模型参数估计。
    mean = train_frame[feature_names].mean()
    std = train_frame[feature_names].std(ddof=0).replace(0, 1.0)
    x_train = ((train_frame[feature_names] - mean) / std).to_numpy(dtype=float)
    y_train = train_frame[list(SCORE_NAMES)].to_numpy(dtype=float)
    x_eval = ((eval_frame[feature_names] - mean) / std).to_numpy(dtype=float)
    y_eval = eval_frame[list(SCORE_NAMES)].to_numpy(dtype=float)

    sample_weight = train_frame["sample_weight"].to_numpy(dtype=float) if "sample_weight" in train_frame.columns else None
    coefficients, bias, train_loss = _fit_linear_heads(x_train, y_train, args.ridge, sample_weight)
    train_predictions = _predict_linear_heads(x_train, coefficients, bias)
    eval_predictions = _predict_linear_heads(x_eval, coefficients, bias) if len(x_eval) else np.empty((0, len(SCORE_NAMES)))

    score_metrics: dict[str, dict[str, dict[str, float] | None]] = {}
    for index, score_name in enumerate(SCORE_NAMES):
        score_metrics[score_name] = {
            "train": _metrics(y_train[:, index], train_predictions[:, index]),
            "eval": _metrics(y_eval[:, index], eval_predictions[:, index]) if len(y_eval) else None,
        }

    payload = {
        "model_version": MODEL_VERSION,
        "architecture": "12_feature_normalizer_plus_5_linear_sigmoid_heads",
        "feature_names": feature_names,
        "score_names": list(SCORE_NAMES),
        "mean": [round(float(value), 8) for value in mean.to_list()],
        "std": [round(float(value), 8) for value in std.to_list()],
        "subscore_coefficients": [[round(float(value), 8) for value in row] for row in coefficients],
        "subscore_bias": [round(float(value), 8) for value in bias],
        "training_rows": int(len(train_frame)),
        "validation_rows": int(len(eval_frame)),
        "features_path": str(args.features),
        "labels_path": str(labels_path),
        "sample_weight_column": "sample_weight" if sample_weight is not None else None,
        "params": {
            "ridge": args.ridge,
            "test_size": args.test_size,
            "random_state": args.random_state,
        },
        "loss": {
            "name": "mse_on_pseudo_score_logits",
            "value": round(float(train_loss), 8),
        },
        "metrics": {
            "scores": score_metrics,
            "recommend_score": {
                "train": _recommend_metrics(y_train, train_predictions),
                "eval": _recommend_metrics(y_eval, eval_predictions) if len(y_eval) else None,
            },
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    print(f"saved route scorer -> {args.output}")
    print(f"training rows={len(train_frame)} validation rows={len(eval_frame)}")
    for score_name in SCORE_NAMES:
        train_rmse = score_metrics[score_name]["train"]["rmse"]
        eval_metrics = score_metrics[score_name]["eval"]
        eval_text = f" eval_rmse={eval_metrics['rmse']:.6f}" if eval_metrics else ""
        print(f"{score_name}: train_rmse={train_rmse:.6f}{eval_text}")


if __name__ == "__main__":
    main()
