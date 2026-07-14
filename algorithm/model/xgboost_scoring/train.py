"""Train the XGBoost candidate route scoring model."""

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
from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES
from algorithm.model.xgboost_scoring.model import METADATA_PATH


def _import_xgboost():
    try:
        import xgboost as xgb
    except ImportError as exc:
        raise RuntimeError("xgboost is not installed. Install it with `uv add xgboost` or `uv sync`.") from exc
    return xgb


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=METADATA_PATH)
    parser.add_argument("--n-estimators", type=int, default=320)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.04)
    parser.add_argument("--subsample", type=float, default=0.90)
    parser.add_argument("--colsample-bytree", type=float, default=0.90)
    parser.add_argument("--reg-lambda", type=float, default=2.0)
    parser.add_argument("--min-child-weight", type=float, default=2.0)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--n-jobs", type=int, default=-1)
    return parser.parse_args()


def _default_labels_path() -> Path:
    dataset_dir = default_dataset_dir()
    fused = dataset_dir / "rule_llm_fused_pseudo_labels.csv"
    if fused.is_file():
        return fused
    return dataset_dir / "rule_pseudo_labels.csv"


def _load_training_frame(features_path: Path, labels_path: Path) -> pd.DataFrame:
    features = read_frozen_features(features_path)
    labels = pd.read_csv(labels_path)

    join_keys = ["candidate_group_id", "route_id"]
    numeric_features = numeric_feature_frame(features.drop_duplicates(join_keys).copy())
    target_columns = [*join_keys, *SCORE_NAMES]
    if "sample_weight" in labels.columns:
        target_columns.append("sample_weight")
    score_targets = labels.drop_duplicates(join_keys)[target_columns]
    dataset = numeric_features.merge(score_targets, on=join_keys, how="inner", validate="one_to_one")
    if dataset.empty:
        raise ValueError("No route rows matched between features and pseudo labels")
    return dataset


def _group_train_eval_mask(dataset: pd.DataFrame, test_size: float, random_state: int) -> np.ndarray:
    groups = np.array(sorted(dataset["candidate_group_id"].astype(str).unique()))
    if len(groups) < 5 or test_size <= 0:
        return np.ones(len(dataset), dtype=bool)
    rng = np.random.default_rng(random_state)
    shuffled = groups.copy()
    rng.shuffle(shuffled)
    eval_count = max(1, int(round(len(shuffled) * min(max(test_size, 0.0), 0.5))))
    eval_groups = set(shuffled[:eval_count])
    return ~dataset["candidate_group_id"].astype(str).isin(eval_groups).to_numpy()


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


def _fit_score_model(
    xgb,
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    sample_weight: np.ndarray | None,
    args: argparse.Namespace,
):
    model = xgb.XGBRegressor(
        objective="reg:squarederror",
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        subsample=args.subsample,
        colsample_bytree=args.colsample_bytree,
        reg_lambda=args.reg_lambda,
        min_child_weight=args.min_child_weight,
        tree_method="hist",
        random_state=args.random_state,
        n_jobs=args.n_jobs,
    )
    fit_kwargs = {}
    if sample_weight is not None:
        fit_kwargs["sample_weight"] = sample_weight
    model.fit(x_train, y_train, **fit_kwargs)
    return model


def main() -> None:
    args = parse_args()
    labels_path = args.labels or _default_labels_path()
    xgb = _import_xgboost()
    dataset = _load_training_frame(args.features, labels_path)

    feature_names = list(NUMERIC_FEATURE_NAMES)
    x = dataset[feature_names].astype(float)
    y = dataset[list(SCORE_NAMES)].to_numpy(dtype=float)
    train_mask = _group_train_eval_mask(dataset, args.test_size, args.random_state)
    x_train = x.loc[train_mask]
    y_train = y[train_mask]
    x_eval = x.loc[~train_mask]
    y_eval = y[~train_mask]

    sample_weight = None
    if "sample_weight" in dataset.columns:
        weights = np.clip(dataset["sample_weight"].to_numpy(dtype=float), 0.05, 1.5)
        sample_weight = weights[train_mask] / max(float(weights[train_mask].mean()), 1e-8)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    model_files: dict[str, str] = {}
    train_predictions = np.zeros_like(y_train, dtype=float)
    eval_predictions = np.zeros_like(y_eval, dtype=float) if len(y_eval) else np.empty((0, len(SCORE_NAMES)))
    score_metrics: dict[str, dict[str, dict[str, float] | None]] = {}

    for index, score_name in enumerate(SCORE_NAMES):
        model = _fit_score_model(xgb, x_train, y_train[:, index], sample_weight, args)
        train_predictions[:, index] = model.predict(x_train)
        if len(y_eval):
            eval_predictions[:, index] = model.predict(x_eval)
        model_path = args.output.parent / f"xgboost_{score_name}.json"
        model.get_booster().save_model(model_path)
        model_files[score_name] = model_path.name
        score_metrics[score_name] = {
            "train": _metrics(y_train[:, index], train_predictions[:, index]),
            "eval": _metrics(y_eval[:, index], eval_predictions[:, index]) if len(y_eval) else None,
        }

    metadata = {
        "model_version": MODEL_VERSION,
        "architecture": "12_feature_xgboost_5_regression_heads",
        "feature_names": feature_names,
        "score_names": list(SCORE_NAMES),
        "model_files": model_files,
        "training_rows": int(len(x_train)),
        "validation_rows": int(len(x_eval)),
        "features_path": str(args.features),
        "labels_path": str(labels_path),
        "sample_weight_column": "sample_weight" if sample_weight is not None else None,
        "params": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "learning_rate": args.learning_rate,
            "subsample": args.subsample,
            "colsample_bytree": args.colsample_bytree,
            "reg_lambda": args.reg_lambda,
            "min_child_weight": args.min_child_weight,
            "tree_method": "hist",
            "random_state": args.random_state,
        },
        "metrics": {
            "scores": score_metrics,
            "recommend_score": {
                "train": _recommend_metrics(y_train, train_predictions),
                "eval": _recommend_metrics(y_eval, eval_predictions) if len(y_eval) else None,
            },
        },
    }
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False, indent=2)

    print(f"saved XGBoost route scorer -> {args.output}")
    print(f"training rows={len(x_train)} validation rows={len(x_eval)}")
    for score_name in SCORE_NAMES:
        train_rmse = score_metrics[score_name]["train"]["rmse"]
        eval_metrics = score_metrics[score_name]["eval"]
        eval_text = f" eval_rmse={eval_metrics['rmse']:.6f}" if eval_metrics else ""
        print(f"{score_name}: train_rmse={train_rmse:.6f}{eval_text}")


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
