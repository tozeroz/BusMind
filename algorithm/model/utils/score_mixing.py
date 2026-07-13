"""Shared score names, preference weights, and score helpers."""

from __future__ import annotations

import numpy as np


SCORE_NAMES = (
    "time_score",
    "comfort_score",
    "walk_score",
    "transfer_score",
    "reliability_score",
)

PREFERENCE_MIX = {
    "balanced": np.array([0.30, 0.25, 0.15, 0.15, 0.15], dtype=float),
    "fastest": np.array([0.60, 0.12, 0.10, 0.08, 0.10], dtype=float),
    "comfort": np.array([0.18, 0.55, 0.08, 0.07, 0.12], dtype=float),
    "less_walking": np.array([0.20, 0.12, 0.50, 0.08, 0.10], dtype=float),
    "less_transfer": np.array([0.22, 0.12, 0.08, 0.48, 0.10], dtype=float),
}


def round_score(value: float) -> float:
    return round(float(max(0.0, min(100.0, value))), 2)


def mix_recommend_score(five_scores: np.ndarray, *, preference: str) -> float:
    return float(np.dot(PREFERENCE_MIX[preference], five_scores))

