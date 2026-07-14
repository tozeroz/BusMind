"""Shared metrics for comparing route scoring models."""

from __future__ import annotations

import numpy as np


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.mean(np.abs(y_true - y_pred)))


def root_mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def _average_ranks(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    sorted_values = values[order]
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and sorted_values[end] == sorted_values[start]:
            end += 1
        average_rank = (start + end - 1) / 2.0 + 1.0
        ranks[order[start:end]] = average_rank
        start = end
    return ranks


def pearson_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return float("nan")
    true_std = float(np.std(y_true))
    pred_std = float(np.std(y_pred))
    if true_std == 0.0 or pred_std == 0.0:
        return float("nan")
    return float(np.corrcoef(y_true, y_pred)[0, 1])


def spearman_correlation(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) < 2:
        return float("nan")
    return pearson_correlation(_average_ranks(y_true), _average_ranks(y_pred))


def top1_agreement(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if len(y_true) == 0:
        return float("nan")
    true_best = np.flatnonzero(y_true == np.max(y_true))
    pred_best = int(np.argmax(y_pred))
    return float(pred_best in set(int(index) for index in true_best))


def ndcg_at_k(y_true: np.ndarray, y_pred: np.ndarray, *, k: int = 5) -> float:
    if len(y_true) == 0:
        return float("nan")
    limit = min(max(int(k), 1), len(y_true))
    predicted_order = np.argsort(-y_pred, kind="mergesort")[:limit]
    ideal_order = np.argsort(-y_true, kind="mergesort")[:limit]
    discounts = 1.0 / np.log2(np.arange(2, limit + 2, dtype=float))
    dcg = float(np.sum(np.maximum(y_true[predicted_order], 0.0) * discounts))
    ideal = float(np.sum(np.maximum(y_true[ideal_order], 0.0) * discounts))
    if ideal == 0.0:
        return 1.0
    return dcg / ideal

