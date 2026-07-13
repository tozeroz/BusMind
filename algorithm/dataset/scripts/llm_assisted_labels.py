"""Generate, aggregate, and fuse LLM-assisted pseudo labels.

This script does not call an LLM directly. It creates deterministic
seed-conditioned request JSONL files, aggregates model responses, and fuses
them with the existing rule-based pseudo labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

import pandas as pd

from algorithm.dataset.scripts.build_labels import PREFERENCE_WEIGHTS
from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_route_from_feature_row,
    read_frozen_features,
)
from algorithm.model.contracts import PREFERENCE_NAMES, RouteFeatures
from algorithm.model.utils.score_mixing import SCORE_NAMES


DEFAULT_SEED_COUNT = 3
REQUEST_SCHEMA_VERSION = "llm_pseudo_label_request"
RESPONSE_SCHEMA_VERSION = "llm_pseudo_label_response"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prompts = subparsers.add_parser("generate-prompts", help="Build seed-conditioned LLM labeling requests")
    prompts.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    prompts.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_label_requests.jsonl")
    prompts.add_argument("--seed-count", type=int, default=DEFAULT_SEED_COUNT)
    prompts.add_argument("--max-groups", type=int, default=0)
    prompts.add_argument("--max-routes-per-group", type=int, default=10)

    aggregate = subparsers.add_parser("aggregate", help="Aggregate JSONL LLM responses across seeds")
    aggregate.add_argument("--responses", type=Path, default=default_dataset_dir() / "llm_label_responses.jsonl")
    aggregate.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_labels_aggregated.csv")
    aggregate.add_argument("--expected-seeds", type=int, default=DEFAULT_SEED_COUNT)

    fuse = subparsers.add_parser("fuse", help="Fuse rule labels and aggregated LLM labels")
    fuse.add_argument("--rule-labels", type=Path, default=default_dataset_dir() / "pseudo_labels.csv")
    fuse.add_argument("--llm-labels", type=Path, default=default_dataset_dir() / "llm_labels_aggregated.csv")
    fuse.add_argument("--output", type=Path, default=default_dataset_dir() / "pseudo_labels_llm_fused.csv")
    fuse.add_argument("--rule-weight", type=float, default=1.0)
    fuse.add_argument("--llm-weight", type=float, default=0.55)
    fuse.add_argument("--conflict-threshold", type=float, default=0.45)

    return parser.parse_args()


def _clip(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return round(max(lower, min(upper, float(value))), 2)


def _clip_unit(value: float) -> float:
    if math.isnan(float(value)):
        return 0.0
    return round(max(0.0, min(1.0, float(value))), 4)


def _bool_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _seed_for(candidate_group_id: str, seed_index: int) -> str:
    digest = hashlib.sha1(f"{candidate_group_id}:{seed_index}".encode("utf-8")).hexdigest()
    return digest[:10].upper()


def _as_route_feature(row: dict[str, Any]) -> RouteFeatures:
    payload = model_input_route_from_feature_row(row)
    return RouteFeatures.from_dict(payload, strict_backend=True)


def _route_for_prompt(row: dict[str, Any]) -> dict[str, Any]:
    route = _as_route_feature(row)
    return {
        "route_id": route.route_id,
        "service_nos": list(route.service_nos),
        "eta_minutes": route.eta_minutes,
        "ride_time_minutes": route.ride_time_minutes,
        "walk_time_minutes": route.walk_time_minutes,
        "walk_distance_meters": route.walk_distance_meters,
        "transfer_count": route.transfer_count,
        "load_score": route.load_score,
        "history_flow_score": route.history_flow_score,
        "congestion_score": route.congestion_score,
        "data_freshness_seconds": route.data_freshness_seconds,
        "monitored_score": route.monitored_score,
        "completeness_score": route.completeness_score,
        "avg_service_frequency_minutes": route.avg_service_frequency_minutes,
        "feature_sources": route.feature_sources,
        "degraded_fields": list(route.degraded_fields),
        "is_synthetic": _bool_value(row.get("is_synthetic", False)),
    }


def _system_prompt() -> str:
    return (
        "You are a public-transit route labeling assistant. "
        "Score each candidate route from 0 to 100 for five dimensions: "
        "time_score, comfort_score, walk_score, transfer_score, reliability_score. "
        "Higher is better. Use the provided numeric route features only. "
        "Return valid JSON only. Do not include markdown."
    )


def _user_prompt(candidate_group_id: str, seed: str, routes: list[dict[str, Any]]) -> str:
    payload = {
        "task": "label_candidate_routes",
        "candidate_group_id": candidate_group_id,
        "seed_condition": seed,
        "scoring_rules": {
            "time_score": "Prefer shorter ETA, shorter ride time, lower service interval, and fewer transfers.",
            "comfort_score": "Prefer lower load, lower historical flow pressure, smoother traffic, and monitored data.",
            "walk_score": "Prefer shorter walking time and distance.",
            "transfer_score": "Prefer fewer transfers; direct routes should usually score highest.",
            "reliability_score": "Prefer fresh, monitored, complete, and high-confidence data sources.",
        },
        "output_schema": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "candidate_group_id": candidate_group_id,
            "seed": seed,
            "labels": [
                {
                    "route_id": "string",
                    "time_score": "0-100 number",
                    "comfort_score": "0-100 number",
                    "walk_score": "0-100 number",
                    "transfer_score": "0-100 number",
                    "reliability_score": "0-100 number",
                    "confidence": "0-1 number",
                    "reason": "short Chinese reason",
                }
            ],
        },
        "routes": routes,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_prompts(args: argparse.Namespace) -> None:
    features = read_frozen_features(args.features)
    groups = list(features.groupby("candidate_group_id", sort=True))
    if args.max_groups > 0:
        groups = groups[: args.max_groups]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with args.output.open("w", encoding="utf-8") as file:
        for candidate_group_id, group in groups:
            group = group.sort_values(["eta_minutes", "route_id"]).head(args.max_routes_per_group).copy()
            routes = [_route_for_prompt(row) for row in group.to_dict("records")]
            if not routes:
                continue
            group_id = str(candidate_group_id)
            for seed_index in range(args.seed_count):
                seed = _seed_for(group_id, seed_index)
                request = {
                    "schema_version": REQUEST_SCHEMA_VERSION,
                    "request_id": f"{group_id}::{seed}",
                    "candidate_group_id": group_id,
                    "seed": seed,
                    "messages": [
                        {"role": "system", "content": _system_prompt()},
                        {"role": "user", "content": _user_prompt(group_id, seed, routes)},
                    ],
                    "routes": routes,
                }
                file.write(json.dumps(request, ensure_ascii=False, separators=(",", ":")) + "\n")
                written += 1

    print(f"wrote {written} LLM label requests -> {args.output}")


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _response_payload(line: dict[str, Any]) -> dict[str, Any]:
    if "labels" in line:
        return line
    for key in ("response", "output", "content"):
        value = line.get(key)
        if isinstance(value, dict) and "labels" in value:
            return value
        if isinstance(value, str):
            return _extract_json_object(value)
    choices = line.get("choices")
    if isinstance(choices, list) and choices:
        content = choices[0].get("message", {}).get("content")
        if isinstance(content, str):
            return _extract_json_object(content)
    raise ValueError("LLM response row does not contain labels or parseable content")


def _score_value(value: Any) -> float:
    try:
        return _clip(float(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid score value: {value!r}") from exc


def _confidence_value(value: Any) -> float:
    if value is None:
        return 0.65
    try:
        return _clip_unit(float(value))
    except (TypeError, ValueError):
        return 0.65


def _read_llm_response_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, raw_line in enumerate(file, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            line = json.loads(raw_line)
            payload = _response_payload(line)
            candidate_group_id = str(payload.get("candidate_group_id") or line.get("candidate_group_id") or "")
            seed = str(payload.get("seed") or line.get("seed") or "")
            if not candidate_group_id:
                raise ValueError(f"line {line_number}: missing candidate_group_id")
            labels = payload.get("labels")
            if not isinstance(labels, list):
                raise ValueError(f"line {line_number}: labels must be a list")
            for label in labels:
                route_id = str(label.get("route_id") or "").strip()
                if not route_id:
                    raise ValueError(f"line {line_number}: label missing route_id")
                rows.append(
                    {
                        "candidate_group_id": candidate_group_id,
                        "route_id": route_id,
                        "seed": seed,
                        **{name: _score_value(label.get(name)) for name in SCORE_NAMES},
                        "confidence": _confidence_value(label.get("confidence")),
                        "reason": str(label.get("reason") or "").strip(),
                    }
                )
    return rows


def aggregate_responses(args: argparse.Namespace) -> None:
    rows = _read_llm_response_rows(args.responses)
    if not rows:
        raise ValueError(f"No LLM response labels found in {args.responses}")

    frame = pd.DataFrame(rows)
    output_rows: list[dict[str, Any]] = []
    for (candidate_group_id, route_id), group in frame.groupby(["candidate_group_id", "route_id"], sort=True):
        score_stds = []
        row: dict[str, Any] = {
            "candidate_group_id": candidate_group_id,
            "route_id": route_id,
            "llm_label_count": int(len(group)),
            "llm_seed_count": int(group["seed"].nunique()),
        }
        for name in SCORE_NAMES:
            values = [float(item) for item in group[name].tolist()]
            median = statistics.median(values)
            std = statistics.pstdev(values) if len(values) > 1 else 0.0
            score_stds.append(std)
            row[f"llm_{name}"] = _clip(median)
            row[f"llm_{name}_std"] = round(float(std), 4)

        mean_confidence = float(group["confidence"].mean())
        std_mean = float(sum(score_stds) / len(score_stds))
        consistency = max(0.0, 1.0 - std_mean / 25.0)
        coverage = min(float(row["llm_seed_count"]) / max(args.expected_seeds, 1), 1.0)
        row["llm_score_std_mean"] = round(std_mean, 4)
        row["llm_label_confidence"] = round(mean_confidence * (0.55 + 0.45 * consistency) * (0.55 + 0.45 * coverage), 4)
        reasons = [reason for reason in group["reason"].tolist() if reason]
        row["llm_reason_sample"] = " | ".join(reasons[:3])
        output_rows.append(row)

    output = pd.DataFrame(output_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"aggregated {len(output)} LLM-labeled routes -> {args.output}")


def _recommend_score(subscore: dict[str, float], preference: str) -> float:
    weights = PREFERENCE_WEIGHTS[preference]
    return _clip(sum(subscore[name] * weight for name, weight in weights.items()))


def _label_gain(scores: list[float], score: float, rank_position: int) -> float:
    low = min(scores)
    high = max(scores)
    if math.isclose(low, high):
        return round(max(0.0, 3.0 - (rank_position - 1) * 0.5), 4)
    normalized = (score - low) / (high - low)
    return round(3.0 * max(0.0, normalized) ** 1.15, 4)


def _soft_label(scores: list[float], score: float) -> float:
    if not scores:
        return 0.0
    best = max(scores)
    exp_values = [math.exp((value - best) / 6.0) for value in scores]
    current = math.exp((score - best) / 6.0)
    return round(current / sum(exp_values), 6)


def _fuse_scores(row: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    has_llm = all(pd.notna(row.get(f"llm_{name}")) for name in SCORE_NAMES)
    if not has_llm:
        return {
            **{name: _clip(float(row[name])) for name in SCORE_NAMES},
            "label_source": "rule",
            "rule_label_confidence": round(float(row.get("label_confidence", 0.65)), 4),
            "llm_label_confidence": 0.0,
            "llm_label_count": 0,
            "rule_llm_agreement": 0.0,
            "sample_weight": round(float(row.get("label_confidence", 0.65)), 4),
        }

    rule_confidence = _clip_unit(float(row.get("label_confidence", 0.65)))
    llm_confidence = _clip_unit(float(row.get("llm_label_confidence", 0.0)))
    diffs = [abs(float(row[name]) - float(row[f"llm_{name}"])) for name in SCORE_NAMES]
    agreement = _clip_unit(1.0 - sum(diffs) / len(diffs) / 35.0)

    rule_weight = max(0.05, rule_confidence * args.rule_weight)
    llm_weight = max(0.0, llm_confidence * args.llm_weight)
    if agreement < args.conflict_threshold:
        llm_weight *= 0.65

    denominator = rule_weight + llm_weight
    scores = {
        name: _clip((float(row[name]) * rule_weight + float(row[f"llm_{name}"]) * llm_weight) / denominator)
        for name in SCORE_NAMES
    }
    fused_confidence = _clip_unit(0.35 * rule_confidence + 0.45 * llm_confidence + 0.20 * agreement)
    if agreement < args.conflict_threshold:
        fused_confidence = _clip_unit(fused_confidence * 0.75)

    return {
        **scores,
        "label_source": "rule_llm_fused",
        "rule_label_confidence": rule_confidence,
        "llm_label_confidence": llm_confidence,
        "llm_label_count": int(row.get("llm_label_count", 0) or 0),
        "rule_llm_agreement": agreement,
        "sample_weight": fused_confidence,
    }


def _rerank_preference_rows(frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for (candidate_group_id, preference), group in frame.groupby(["candidate_group_id", "preference"], sort=True):
        scored = group.copy()
        scored["recommend_score"] = scored.apply(
            lambda row: _recommend_score({name: float(row[name]) for name in SCORE_NAMES}, str(preference)),
            axis=1,
        )
        scored = scored.sort_values(["recommend_score", "route_id"], ascending=[False, True]).reset_index(drop=True)
        score_values = [float(item) for item in scored["recommend_score"].tolist()]
        best_score = score_values[0]
        best_route_id = str(scored.iloc[0]["route_id"])
        for index, row in scored.iterrows():
            item = row.to_dict()
            rank_position = index + 1
            recommend_score = float(item["recommend_score"])
            item["rank_position"] = rank_position
            item["label"] = 1 if str(item["route_id"]) == best_route_id else 0
            item["label_gain"] = _label_gain(score_values, recommend_score, rank_position)
            item["soft_label"] = _soft_label(score_values, recommend_score)
            item["score_margin"] = round(best_score - recommend_score, 4)
            item["label_confidence"] = item["sample_weight"]
            rows.append(item)
    return pd.DataFrame(rows)


def fuse_labels(args: argparse.Namespace) -> None:
    rules = pd.read_csv(args.rule_labels)
    llm = pd.read_csv(args.llm_labels)
    for frame in (rules, llm):
        frame["candidate_group_id"] = frame["candidate_group_id"].astype(str)
        frame["route_id"] = frame["route_id"].astype(str)
    merged = rules.merge(llm, on=["candidate_group_id", "route_id"], how="left")

    fused_rows: list[dict[str, Any]] = []
    for row in merged.to_dict("records"):
        fused = _fuse_scores(row, args)
        output = dict(row)
        output.update(fused)
        fused_rows.append(output)

    fused_frame = pd.DataFrame(fused_rows)
    reranked = _rerank_preference_rows(fused_frame)

    preferred_columns = [
        "candidate_group_id",
        "preference",
        "route_id",
        "rank_position",
        "label",
        "label_gain",
        "soft_label",
        "score_margin",
        "label_confidence",
        *SCORE_NAMES,
        "recommend_score",
        "sample_weight",
        "label_source",
        "rule_label_confidence",
        "llm_label_confidence",
        "llm_label_count",
        "rule_llm_agreement",
        "is_synthetic",
    ]
    columns = [column for column in preferred_columns if column in reranked.columns]
    extra_columns = [column for column in reranked.columns if column not in columns and not column.startswith("llm_")]
    output = reranked[columns + extra_columns].sort_values(
        ["candidate_group_id", "preference", "rank_position", "route_id"],
        ascending=[True, True, True, True],
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    fused_count = int((output["label_source"] == "rule_llm_fused").sum())
    print(f"wrote {len(output)} fused pseudo-label rows -> {args.output}")
    print(f"rule+LLM fused rows={fused_count}; rule-only rows={len(output) - fused_count}")


def main() -> None:
    args = parse_args()
    if args.command == "generate-prompts":
        generate_prompts(args)
    elif args.command == "aggregate":
        aggregate_responses(args)
    elif args.command == "fuse":
        fuse_labels(args)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
