"""候选线路评分数据集的规范路径。"""

from __future__ import annotations

from pathlib import Path

from algorithm.dataset.scripts.data import default_dataset_dir


def features_dir() -> Path:
    return default_dataset_dir() / "features"


def labels_dir() -> Path:
    return default_dataset_dir() / "labels"


def llm_dir() -> Path:
    return default_dataset_dir() / "llm"


def llm_shards_dir() -> Path:
    return llm_dir() / "shards"


def features_path() -> Path:
    return features_dir() / "features.csv"


def rule_labels_path() -> Path:
    return labels_dir() / "rule_pseudo_labels.csv"


def llm_requests_path() -> Path:
    return llm_dir() / "llm_pseudo_label_requests.jsonl"


def canonical_llm_requests_path() -> Path:
    return llm_requests_path()


def llm_responses_path() -> Path:
    return llm_dir() / "llm_pseudo_label_responses.jsonl"


def canonical_llm_responses_path() -> Path:
    return llm_responses_path()


def llm_labels_path() -> Path:
    return labels_dir() / "llm_pseudo_labels.csv"


def fused_labels_path() -> Path:
    return labels_dir() / "rule_llm_fused_pseudo_labels.csv"


def feature_summary_path() -> Path:
    return features_dir() / "feature-summary.md"
