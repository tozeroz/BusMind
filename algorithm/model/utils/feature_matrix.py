"""Build model-ready feature matrices from frozen route datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from algorithm.dataset.scripts.recommendation_feature_contract import numeric_feature_frame, read_frozen_features
from algorithm.model.contracts import NUMERIC_FEATURE_NAMES


def load_numeric_feature_matrix(features_path: Path) -> pd.DataFrame:
    features = read_frozen_features(features_path)
    return numeric_feature_frame(features)


def feature_columns() -> list[str]:
    return list(NUMERIC_FEATURE_NAMES)

