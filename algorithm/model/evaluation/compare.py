"""Compare Linear, XGBoost, and TabPFN route scoring models."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import numpy as np
import pandas as pd

from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_route_from_feature_row,
    numeric_feature_frame,
    read_frozen_features,
)
from algorithm.model.contracts import NUMERIC_FEATURE_NAMES, RouteFeatures
from algorithm.model.evaluation.metrics import (
    mean_absolute_error,
    ndcg_at_k,
    pearson_correlation,
    root_mean_squared_error,
    spearman_correlation,
    top1_agreement,
)
from algorithm.model.evaluation.plots import build_score_curve_frames, write_score_curve_png, write_score_curve_svg
from algorithm.model.register import get_route_scoring_model, normalize_model_key
from algorithm.model.utils.score_mixing import PREFERENCE_MIX, SCORE_NAMES


JOIN_KEYS = ["candidate_group_id", "route_id"]
DEFAULT_MODELS = ("linear", "xgboost", "tabpfn")
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "artifacts"


def _default_labels_path() -> Path:
    dataset_dir = default_dataset_dir()
    fused = dataset_dir / "rule_llm_fused_pseudo_labels.csv"
    if fused.is_file():
        return fused
    return dataset_dir / "rule_pseudo_labels.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--labels", type=Path, default=None)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--max-groups", type=int, default=0)
    parser.add_argument("--ranking-k", type=int, default=5)
    parser.add_argument(
        "--ranking-target",
        choices=("recommend_score", "label_gain", "soft_label"),
        default="recommend_score",
    )
    parser.add_argument("--save-predictions", action="store_true")
    parser.add_argument("--plot-curves", action="store_true")
    parser.add_argument("--plot-preference", choices=sorted(PREFERENCE_MIX), default="balanced")
    parser.add_argument("--plot-format", choices=("png", "svg", "both"), default="png")
    parser.add_argument("--plot-max-points", type=int, default=400)
    parser.add_argument("--fail-on-unavailable", action="store_true")
    return parser.parse_args()


def _normalize_models(raw_models: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in raw_models:
        for name in str(item).split(","):
            name = name.strip()
            if not name:
                continue
            model_key = normalize_model_key(name)
            if model_key not in normalized:
                normalized.append(model_key)
    if not normalized:
        raise ValueError("No models selected")
    return normalized


def _load_route_frame(features_path: Path, labels_path: Path) -> pd.DataFrame:
    features = read_frozen_features(features_path).drop_duplicates(JOIN_KEYS).copy()
    labels = pd.read_csv(labels_path)
    missing_scores = [name for name in SCORE_NAMES if name not in labels.columns]
    if missing_scores:
        raise ValueError("labels file missing score columns: " + ", ".join(missing_scores))
    route_targets = labels.drop_duplicates(JOIN_KEYS)[[*JOIN_KEYS, *SCORE_NAMES]].copy()
    route_frame = features.merge(route_targets, on=JOIN_KEYS, how="inner", validate="one_to_one")
    if route_frame.empty:
        raise ValueError("No route rows matched between features and labels")
    return route_frame


def _load_ranking_frame(labels_path: Path) -> pd.DataFrame:
    labels = pd.read_csv(labels_path)
    required = [*JOIN_KEYS, "preference", "recommend_score"]
    missing = [column for column in required if column not in labels.columns]
    if missing:
        raise ValueError("labels file missing ranking columns: " + ", ".join(missing))
    columns = [column for column in [*required, "label_gain", "soft_label"] if column in labels.columns]
    return labels.drop_duplicates([*JOIN_KEYS, "preference"])[columns].copy()


def _select_groups(route_frame: pd.DataFrame, max_groups: int, random_state: int) -> np.ndarray:
    groups = np.array(sorted(route_frame["candidate_group_id"].astype(str).unique()))
    if max_groups <= 0 or len(groups) <= max_groups:
        return groups
    rng = np.random.default_rng(random_state)
    sampled = rng.choice(groups, size=max_groups, replace=False)
    return np.array(sorted(sampled))


def _eval_groups(groups: np.ndarray, test_size: float, random_state: int) -> np.ndarray:
    if len(groups) == 0:
        return groups
    if test_size <= 0:
        return groups
    rng = np.random.default_rng(random_state)
    shuffled = groups.copy()
    rng.shuffle(shuffled)
    ratio = min(max(test_size, 0.0), 1.0)
    eval_count = max(1, int(round(len(shuffled) * ratio)))
    return np.array(sorted(shuffled[:eval_count]))


def _route_from_row(row: dict[str, Any]) -> RouteFeatures:
    payload = model_input_route_from_feature_row(row)
    return RouteFeatures.from_dict(payload, strict_backend=True)


def _predict_route_scores(model_key: str, route_frame: pd.DataFrame) -> pd.DataFrame:
    if model_key == "tabpfn":
        return _predict_tabpfn_route_scores(route_frame)

    model = get_route_scoring_model(model_key)
    rows: list[dict[str, Any]] = []
    for row in route_frame.to_dict("records"):
        route = _route_from_row(row)
        result = model.score_route(route, preference="balanced")
        rows.append(
            {
                "candidate_group_id": row["candidate_group_id"],
                "route_id": row["route_id"],
                **{f"pred_{name}": getattr(result, name) for name in SCORE_NAMES},
            }
        )
    return pd.DataFrame(rows)


def _predict_tabpfn_route_scores(route_frame: pd.DataFrame) -> pd.DataFrame:
    from algorithm.model.tabpfn_scoring.model import TabPFNRouteScoringModel

    numeric_features = numeric_feature_frame(route_frame.drop_duplicates(JOIN_KEYS).copy())
    predictions = TabPFNRouteScoringModel().predict_feature_frame(numeric_features[list(NUMERIC_FEATURE_NAMES)])
    output = numeric_features[JOIN_KEYS].copy()
    for index, score_name in enumerate(SCORE_NAMES):
        output[f"pred_{score_name}"] = np.round(predictions[:, index], 2)
    return output


def _score_regression_metrics(route_eval: pd.DataFrame, predictions: pd.DataFrame) -> dict[str, float]:
    merged = route_eval[[*JOIN_KEYS, *SCORE_NAMES]].merge(predictions, on=JOIN_KEYS, how="inner", validate="one_to_one")
    output: dict[str, float] = {}
    rmse_values: list[float] = []
    for name in SCORE_NAMES:
        y_true = merged[name].to_numpy(dtype=float)
        y_pred = merged[f"pred_{name}"].to_numpy(dtype=float)
        rmse = root_mean_squared_error(y_true, y_pred)
        rmse_values.append(rmse)
        output[f"{name}_rmse"] = rmse
        output[f"{name}_mae"] = mean_absolute_error(y_true, y_pred)
        output[f"{name}_pearson"] = pearson_correlation(y_true, y_pred)
        output[f"{name}_spearman"] = spearman_correlation(y_true, y_pred)
    output["macro_rmse"] = float(np.mean(rmse_values))
    return output


def _attach_recommend_predictions(ranking_eval: pd.DataFrame, predictions: pd.DataFrame) -> pd.DataFrame:
    merged = ranking_eval.merge(predictions, on=JOIN_KEYS, how="inner", validate="many_to_one")
    if merged.empty:
        return merged
    pred_scores = merged[[f"pred_{name}" for name in SCORE_NAMES]].to_numpy(dtype=float)
    weights = np.vstack([PREFERENCE_MIX[str(preference)] for preference in merged["preference"]])
    merged["pred_recommend_score"] = np.sum(pred_scores * weights, axis=1)
    return merged


def _ranking_metrics(ranking_eval: pd.DataFrame, predictions: pd.DataFrame, target: str, k: int) -> dict[str, float]:
    merged = _attach_recommend_predictions(ranking_eval, predictions)
    if merged.empty:
        return {
            "recommend_score_rmse": float("nan"),
            "recommend_score_mae": float("nan"),
            "top1_agreement": float("nan"),
            f"ndcg_at_{k}": float("nan"),
        }
    if target not in merged.columns:
        raise ValueError(f"Ranking target {target!r} is not available in labels")

    output: dict[str, float] = {
        "recommend_score_rmse": root_mean_squared_error(
            merged["recommend_score"].to_numpy(dtype=float),
            merged["pred_recommend_score"].to_numpy(dtype=float),
        ),
        "recommend_score_mae": mean_absolute_error(
            merged["recommend_score"].to_numpy(dtype=float),
            merged["pred_recommend_score"].to_numpy(dtype=float),
        ),
    }
    top1_values: list[float] = []
    ndcg_values: list[float] = []
    for _group_key, group in merged.groupby(["candidate_group_id", "preference"], sort=False):
        if len(group) < 2:
            continue
        y_true = group[target].to_numpy(dtype=float)
        y_pred = group["pred_recommend_score"].to_numpy(dtype=float)
        top1_values.append(top1_agreement(y_true, y_pred))
        ndcg_values.append(ndcg_at_k(y_true, y_pred, k=k))
    output["top1_agreement"] = float(np.mean(top1_values)) if top1_values else float("nan")
    output[f"ndcg_at_{k}"] = float(np.mean(ndcg_values)) if ndcg_values else float("nan")

    for preference, group in merged.groupby("preference", sort=True):
        y_true = group["recommend_score"].to_numpy(dtype=float)
        y_pred = group["pred_recommend_score"].to_numpy(dtype=float)
        output[f"{preference}_recommend_score_rmse"] = root_mean_squared_error(y_true, y_pred)
    return output


def _round_metric(value: Any) -> Any:
    if isinstance(value, float):
        if np.isnan(value):
            return None
        return round(value, 6)
    return value


def _evaluate_model(
    model_key: str,
    route_eval: pd.DataFrame,
    ranking_eval: pd.DataFrame,
    *,
    ranking_target: str,
    ranking_k: int,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    predictions = _predict_route_scores(model_key, route_eval)
    metrics = {
        "model": model_key,
        "status": "ok",
        "evaluation_routes": int(len(route_eval)),
        "evaluation_groups": int(route_eval["candidate_group_id"].nunique()),
        **_score_regression_metrics(route_eval, predictions),
        **_ranking_metrics(ranking_eval, predictions, ranking_target, ranking_k),
    }
    return {key: _round_metric(value) for key, value in metrics.items()}, predictions


def _print_summary(metrics_frame: pd.DataFrame, ranking_k: int) -> None:
    columns = [
        "model",
        "status",
        "macro_rmse",
        "recommend_score_rmse",
        "top1_agreement",
        f"ndcg_at_{ranking_k}",
    ]
    existing = [column for column in columns if column in metrics_frame.columns]
    print(metrics_frame[existing].to_string(index=False))


def main() -> None:
    args = parse_args()
    labels_path = args.labels or _default_labels_path()
    models = _normalize_models(args.models)

    route_frame = _load_route_frame(args.features, labels_path)
    selected_groups = _select_groups(route_frame, args.max_groups, args.random_state)
    route_frame = route_frame[route_frame["candidate_group_id"].astype(str).isin(selected_groups)].copy()
    eval_groups = _eval_groups(selected_groups, args.test_size, args.random_state)
    route_eval = route_frame[route_frame["candidate_group_id"].astype(str).isin(eval_groups)].copy()
    if route_eval.empty:
        raise ValueError("Evaluation split is empty")

    ranking_frame = _load_ranking_frame(labels_path)
    ranking_eval = ranking_frame[ranking_frame["candidate_group_id"].astype(str).isin(eval_groups)].copy()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    plot_paths: dict[str, str] = {}
    skipped: dict[str, str] = {}

    for model_key in models:
        try:
            metrics, predictions = _evaluate_model(
                model_key,
                route_eval,
                ranking_eval,
                ranking_target=args.ranking_target,
                ranking_k=args.ranking_k,
            )
        except Exception as exc:
            if args.fail_on_unavailable:
                raise
            skipped[model_key] = str(exc)
            metrics = {
                "model": model_key,
                "status": "skipped",
                "error": str(exc),
                "evaluation_routes": int(len(route_eval)),
                "evaluation_groups": int(route_eval["candidate_group_id"].nunique()),
            }
            predictions = None
        metrics_rows.append(metrics)
        if predictions is not None:
            prediction_frames.append(predictions.assign(model=model_key))
            if args.plot_curves:
                curves = build_score_curve_frames(
                    route_eval,
                    ranking_eval,
                    predictions,
                    preference=args.plot_preference,
                )
                model_plot_paths: list[str] = []
                if args.plot_format in {"png", "both"}:
                    png_path = args.output_dir / f"{model_key}_score_curves_{args.plot_preference}.png"
                    write_score_curve_png(
                        curves,
                        png_path,
                        title=f"{model_key} label vs prediction curves",
                        max_points=args.plot_max_points,
                    )
                    model_plot_paths.append(str(png_path))
                if args.plot_format in {"svg", "both"}:
                    svg_path = args.output_dir / f"{model_key}_score_curves_{args.plot_preference}.svg"
                    write_score_curve_svg(
                        curves,
                        svg_path,
                        title=f"{model_key} label vs prediction curves",
                        max_points=args.plot_max_points,
                    )
                    model_plot_paths.append(str(svg_path))
                plot_paths[model_key] = model_plot_paths[0] if len(model_plot_paths) == 1 else model_plot_paths

    metrics_frame = pd.DataFrame(metrics_rows)
    metrics_path = args.output_dir / "comparison_metrics.csv"
    json_path = args.output_dir / "comparison_metrics.json"
    split_path = args.output_dir / "comparison_test_groups.csv"
    metrics_frame.to_csv(metrics_path, index=False)
    pd.DataFrame({"candidate_group_id": eval_groups}).to_csv(split_path, index=False)

    payload = {
        "features_path": str(args.features),
        "labels_path": str(labels_path),
        "models": models,
        "test_size": args.test_size,
        "random_state": args.random_state,
        "max_groups": args.max_groups,
        "ranking_target": args.ranking_target,
        "ranking_k": args.ranking_k,
        "plot_format": args.plot_format,
        "evaluation_routes": int(len(route_eval)),
        "evaluation_groups": int(route_eval["candidate_group_id"].nunique()),
        "skipped": skipped,
        "plots": plot_paths,
        "metrics": metrics_rows,
    }
    with json_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    if args.save_predictions and prediction_frames:
        predictions_path = args.output_dir / "comparison_predictions.csv"
        pd.concat(prediction_frames, ignore_index=True).to_csv(predictions_path, index=False)

    print(f"saved metrics -> {metrics_path}")
    print(f"saved details -> {json_path}")
    print(f"saved test groups -> {split_path}")
    for model_key, plot_path in plot_paths.items():
        print(f"saved {model_key} plot -> {plot_path}")
    _print_summary(metrics_frame, args.ranking_k)


if __name__ == "__main__":
    main()
