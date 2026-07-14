"""Train the TabPFN candidate route scoring model."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import numeric_feature_frame, read_frozen_features
from algorithm.model.contracts import MODEL_VERSION, NUMERIC_FEATURE_NAMES
from algorithm.model.tabpfn_scoring.model import METADATA_PATH
from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _load_project_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        from dotenv import dotenv_values
    except ImportError:
        return
    for key, value in dotenv_values(env_path, encoding="utf-8").items():
        if value is not None and not os.getenv(key):
            os.environ[key] = value


def _import_tabpfn_regressor():
    _load_project_env()
    try:
        from tabpfn import TabPFNRegressor
    except ImportError as exc:
        raise RuntimeError(
            "tabpfn is not installed. Install it with `uv sync --extra algorithm --extra tabpfn`."
        ) from exc
    return TabPFNRegressor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=METADATA_PATH)
    parser.add_argument("--context-output", type=Path, default=None)
    parser.add_argument("--max-train-rows", type=int, default=1000)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
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


def _sample_train_rows(dataset: pd.DataFrame, max_rows: int, random_state: int) -> pd.DataFrame:
    if max_rows <= 0 or len(dataset) <= max_rows:
        return dataset.copy()
    weights = None
    if "sample_weight" in dataset.columns:
        raw = np.clip(dataset["sample_weight"].to_numpy(dtype=float), 0.05, 1.5)
        weights = raw / raw.sum()
    rng = np.random.default_rng(random_state)
    positions = rng.choice(len(dataset), size=max_rows, replace=False, p=weights)
    return dataset.iloc[np.sort(positions)].copy()


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


def _fit_regressors(x_train: pd.DataFrame, y_train: np.ndarray):
    Regressor = _import_tabpfn_regressor()
    models = {}
    for index, score_name in enumerate(SCORE_NAMES):
        model = Regressor()
        model.fit(x_train, y_train[:, index])
        models[score_name] = model
    return models


def _predict_all(models: dict[str, object], x: pd.DataFrame) -> np.ndarray:
    predictions = np.zeros((len(x), len(SCORE_NAMES)), dtype=float)
    for index, score_name in enumerate(SCORE_NAMES):
        predictions[:, index] = np.asarray(models[score_name].predict(x), dtype=float)
    return np.clip(predictions, 0.0, 100.0)


def main() -> None:
    args = parse_args()
    labels_path = args.labels or _default_labels_path()
    dataset = _load_training_frame(args.features, labels_path)
    train_mask = _group_train_eval_mask(dataset, args.test_size, args.random_state)
    train_frame = _sample_train_rows(dataset.loc[train_mask].copy(), args.max_train_rows, args.random_state)
    eval_frame = dataset.loc[~train_mask].copy()

    feature_names = list(NUMERIC_FEATURE_NAMES)
    x_train = train_frame[feature_names].astype(float)
    y_train = train_frame[list(SCORE_NAMES)].to_numpy(dtype=float)
    x_eval = eval_frame[feature_names].astype(float)
    y_eval = eval_frame[list(SCORE_NAMES)].to_numpy(dtype=float)

    models = _fit_regressors(x_train, y_train)
    train_predictions = _predict_all(models, x_train)
    eval_predictions = _predict_all(models, x_eval) if len(x_eval) else np.empty((0, len(SCORE_NAMES)))

    score_metrics: dict[str, dict[str, dict[str, float] | None]] = {}
    for index, score_name in enumerate(SCORE_NAMES):
        score_metrics[score_name] = {
            "train": _metrics(y_train[:, index], train_predictions[:, index]),
            "eval": _metrics(y_eval[:, index], eval_predictions[:, index]) if len(y_eval) else None,
        }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    context_path = args.context_output or (args.output.parent / "tabpfn_training_context.npz")
    np.savez_compressed(
        context_path,
        x_train=x_train.to_numpy(dtype=float),
        y_train=y_train,
        feature_names=np.array(feature_names),
        score_names=np.array(SCORE_NAMES),
    )

    metadata = {
        "model_version": MODEL_VERSION,
        "architecture": "12_feature_tabpfn_5_regression_contexts",
        "feature_names": feature_names,
        "score_names": list(SCORE_NAMES),
        "context_file": context_path.name,
        "training_rows_total": int(train_mask.sum()),
        "training_rows_context": int(len(x_train)),
        "validation_rows": int(len(x_eval)),
        "features_path": str(args.features),
        "labels_path": str(labels_path),
        "sample_weight_column": "sample_weight" if "sample_weight" in dataset.columns else None,
        "params": {
            "max_train_rows": args.max_train_rows,
            "test_size": args.test_size,
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

    print(f"saved TabPFN route scorer -> {args.output}")
    print(f"saved TabPFN context -> {context_path}")
    print(f"context rows={len(x_train)} validation rows={len(x_eval)}")
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
