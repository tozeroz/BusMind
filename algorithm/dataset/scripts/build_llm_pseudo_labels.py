"""Generate, call, aggregate, and fuse LLM-assisted pseudo labels.

The workflow creates deterministic seed-conditioned request JSONL files,
optionally calls DeepSeek for those requests, aggregates model responses, and
fuses them with the existing rule-based pseudo labels.
"""

from __future__ import annotations

import argparse
import asyncio
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

from algorithm.dataset.scripts.build_rule_pseudo_labels import PREFERENCE_WEIGHTS
from algorithm.dataset.scripts.recommendation_data import default_dataset_dir
from algorithm.dataset.scripts.recommendation_feature_contract import (
    model_input_route_from_feature_row,
    read_frozen_features,
)
from algorithm.model.contracts import PREFERENCE_NAMES, RouteFeatures
from algorithm.model.utils.score_mixing import SCORE_NAMES
from backend.app.core.intelligence_settings import settings
from llm.providers.deepseek import DeepSeekClient, DeepSeekConfig, DeepSeekError


DEFAULT_SEED_COUNT = 3
REQUEST_SCHEMA_VERSION = "llm_pseudo_label_request"
RESPONSE_SCHEMA_VERSION = "llm_pseudo_label_response"
DEFAULT_LABEL_MAX_TOKENS = 1800


class DeepSeekLabelError(DeepSeekError):
    def __init__(self, message: str, raw_content: str | None = None) -> None:
        super().__init__(message)
        self.raw_content = raw_content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prompts = subparsers.add_parser("generate-prompts", help="Build seed-conditioned LLM labeling requests")
    prompts.add_argument("--features", type=Path, default=default_dataset_dir() / "features.csv")
    prompts.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_pseudo_label_requests.jsonl")
    prompts.add_argument("--seed-count", type=int, default=DEFAULT_SEED_COUNT)
    prompts.add_argument("--max-groups", type=int, default=0)
    prompts.add_argument("--max-routes-per-group", type=int, default=10)

    split = subparsers.add_parser("split-requests", help="Split LLM request JSONL for team labeling")
    split.add_argument("--requests", type=Path, default=default_dataset_dir() / "llm_pseudo_label_requests.jsonl")
    split.add_argument("--output-dir", type=Path, default=default_dataset_dir() / "llm_pseudo_label_shards")
    split.add_argument("--shards", type=int, default=5)
    split.add_argument("--prefix", type=str, default="llm_pseudo_label_requests")

    call = subparsers.add_parser("call-deepseek", help="Call DeepSeek for request JSONL")
    call.add_argument("--requests", type=Path, default=default_dataset_dir() / "llm_pseudo_label_requests.jsonl")
    call.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_pseudo_label_responses.jsonl")
    call.add_argument("--errors-output", type=Path, default=None)
    call.add_argument("--limit", type=int, default=0)
    call.add_argument("--retries", type=int, default=2)
    call.add_argument("--temperature", type=float, default=None)
    call.add_argument("--max-tokens", type=int, default=None)
    call.add_argument("--timeout-seconds", type=float, default=None)
    call.add_argument("--sleep-seconds", type=float, default=0.0)
    call.add_argument("--no-json-mode", action="store_false", dest="json_mode")
    call.add_argument("--overwrite", action="store_true")

    aggregate = subparsers.add_parser("aggregate", help="Aggregate JSONL LLM responses across seeds")
    aggregate.add_argument("--responses", type=Path, default=default_dataset_dir() / "llm_pseudo_label_responses.jsonl")
    aggregate.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_pseudo_labels.csv")
    aggregate.add_argument("--expected-seeds", type=int, default=DEFAULT_SEED_COUNT)

    merge = subparsers.add_parser("merge-responses", help="Merge team response JSONL shards")
    merge.add_argument("--input-dir", type=Path, default=default_dataset_dir() / "llm_pseudo_label_shards")
    merge.add_argument("--pattern", type=str, default="llm_pseudo_label_responses_part_*_of_*.jsonl")
    merge.add_argument("--inputs", type=Path, nargs="*", default=None)
    merge.add_argument("--output", type=Path, default=default_dataset_dir() / "llm_pseudo_label_responses.jsonl")
    merge.add_argument("--skip-invalid", action="store_true")

    fuse = subparsers.add_parser("fuse", help="Fuse rule labels and aggregated LLM labels")
    fuse.add_argument("--rule-labels", type=Path, default=default_dataset_dir() / "rule_pseudo_labels.csv")
    fuse.add_argument("--llm-labels", type=Path, default=default_dataset_dir() / "llm_pseudo_labels.csv")
    fuse.add_argument("--output", type=Path, default=default_dataset_dir() / "rule_llm_fused_pseudo_labels.csv")
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
        "Return one JSON object only. The answer must be directly parseable by Python json.loads. "
        "Use double quotes for every key and string. Put commas between every object field and array item. "
        "Do not include markdown, comments, trailing commas, code fences, or extra explanation."
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
                    "reason": "short Chinese reason without quotes or line breaks",
                }
            ],
        },
        "strict_output_requirements": [
            "Return exactly one JSON object.",
            "Return exactly one label for each route_id in routes.",
            "Keep route_id identical to the input route_id.",
            "All score fields must be numbers, not strings.",
            "reason must be short plain text without quotes, braces, or line breaks.",
        ],
        "json_template": {
            "schema_version": RESPONSE_SCHEMA_VERSION,
            "candidate_group_id": candidate_group_id,
            "seed": seed,
            "labels": [
                {
                    "route_id": routes[0]["route_id"] if routes else "route_id_from_input",
                    "time_score": 80,
                    "comfort_score": 75,
                    "walk_score": 90,
                    "transfer_score": 100,
                    "reliability_score": 70,
                    "confidence": 0.75,
                    "reason": "示例",
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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, raw_line in enumerate(file, start=1):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: line {line_number} is not valid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}: line {line_number} must be a JSON object")
            rows.append(row)
    return rows


def _request_group_id(row: dict[str, Any]) -> str:
    group_id = str(row.get("candidate_group_id") or "").strip()
    if group_id:
        return group_id
    request_id = str(row.get("request_id") or "").strip()
    if "::" in request_id:
        return request_id.split("::", 1)[0]
    if request_id:
        return request_id
    raise ValueError("request row missing candidate_group_id/request_id")


def _request_identity(row: dict[str, Any]) -> str:
    request_id = str(row.get("request_id") or "").strip()
    if request_id:
        return request_id
    candidate_group_id = str(row.get("candidate_group_id") or "").strip()
    seed = str(row.get("seed") or "").strip()
    if candidate_group_id and seed:
        return f"{candidate_group_id}::{seed}"
    raise ValueError("response row missing request_id or candidate_group_id+seed")


def _part_name(prefix: str, index: int, count: int) -> str:
    width = max(2, len(str(count)))
    return f"{prefix}_part_{index:0{width}d}_of_{count:0{width}d}.jsonl"


def split_requests(args: argparse.Namespace) -> None:
    if args.shards < 1:
        raise ValueError("--shards must be >= 1")
    requests = _read_jsonl(args.requests)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for request in requests:
        grouped.setdefault(_request_group_id(request), []).append(request)
    if not grouped:
        raise ValueError(f"No LLM requests found in {args.requests}")

    shards: list[list[dict[str, Any]]] = [[] for _ in range(args.shards)]
    for index, group_id in enumerate(sorted(grouped)):
        shards[index % args.shards].extend(grouped[group_id])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    total_written = 0
    for index, rows in enumerate(shards, start=1):
        path = args.output_dir / _part_name(args.prefix, index, args.shards)
        with path.open("w", encoding="utf-8") as file:
            for row in rows:
                file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        total_written += len(rows)
        group_count = len({_request_group_id(row) for row in rows})
        print(f"part {index}/{args.shards}: requests={len(rows)}, groups={group_count} -> {path}")

    print(f"split {total_written} requests across {args.shards} shards -> {args.output_dir}")


def _existing_request_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    completed: set[str] = set()
    for row in _read_jsonl(path):
        request_id = str(row.get("request_id") or "").strip()
        if request_id:
            completed.add(request_id)
    return completed


def _error_output_path(args: argparse.Namespace) -> Path:
    if args.errors_output is not None:
        return args.errors_output
    return args.output.with_suffix(".errors.jsonl")


def _deepseek_config(args: argparse.Namespace) -> DeepSeekConfig:
    if not settings.deepseek_api_key:
        raise ValueError("DEEPSEEK_API_KEY is not configured in the project root .env")
    max_tokens = args.max_tokens if args.max_tokens is not None else max(
        settings.deepseek_max_tokens,
        DEFAULT_LABEL_MAX_TOKENS,
    )
    return DeepSeekConfig(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        timeout_seconds=args.timeout_seconds or settings.deepseek_timeout_seconds,
        max_tokens=max_tokens,
        temperature=args.temperature if args.temperature is not None else settings.deepseek_temperature,
    )


def _request_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    messages = request.get("messages")
    if not isinstance(messages, list) or not messages:
        raise ValueError("request missing messages")
    normalized: list[dict[str, str]] = []
    for message in messages:
        if not isinstance(message, dict):
            raise ValueError("message must be an object")
        role = str(message.get("role") or "").strip()
        content = str(message.get("content") or "").strip()
        if role not in {"system", "user", "assistant"} or not content:
            raise ValueError("message role/content is invalid")
        normalized.append({"role": role, "content": content})
    return normalized


def _validate_deepseek_payload(row: dict[str, Any]) -> None:
    payload = _response_payload(row)
    labels = payload.get("labels")
    if not isinstance(labels, list) or not labels:
        raise ValueError("DeepSeek response contains no labels")
    route_ids = {str(route.get("route_id") or "").strip() for route in row.get("routes", [])}
    for label in labels:
        route_id = str(label.get("route_id") or "").strip()
        if not route_id:
            raise ValueError("DeepSeek response label missing route_id")
        if route_ids and route_id not in route_ids:
            raise ValueError(f"DeepSeek response has unknown route_id: {route_id}")
        for name in SCORE_NAMES:
            _score_value(label.get(name))
        _confidence_value(label.get("confidence"))


async def _call_deepseek_request(
    client: DeepSeekClient,
    request: dict[str, Any],
    retries: int,
    json_mode: bool,
) -> dict[str, Any]:
    messages = _request_messages(request)
    last_error: Exception | None = None
    last_raw_content: str | None = None
    for attempt in range(retries + 1):
        try:
            content = await client.chat(
                messages,
                response_format={"type": "json_object"} if json_mode else None,
            )
            response = {
                "schema_version": RESPONSE_SCHEMA_VERSION,
                "provider": "deepseek",
                "model": settings.deepseek_model,
                "request_id": str(request.get("request_id") or ""),
                "candidate_group_id": str(request.get("candidate_group_id") or ""),
                "seed": str(request.get("seed") or ""),
                "content": content,
            }
            try:
                _validate_deepseek_payload({**response, "routes": request.get("routes", [])})
            except (ValueError, json.JSONDecodeError) as exc:
                raise DeepSeekLabelError(str(exc), raw_content=content) from exc
            return response
        except (DeepSeekError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if isinstance(exc, DeepSeekLabelError):
                last_raw_content = exc.raw_content
            if attempt < retries:
                await asyncio.sleep(min(2.0**attempt, 8.0))
    if last_raw_content is not None:
        raise DeepSeekLabelError(str(last_error or "DeepSeek labeling failed"), raw_content=last_raw_content)
    raise DeepSeekError(str(last_error or "DeepSeek labeling failed"))


async def _call_deepseek(args: argparse.Namespace) -> None:
    requests = _read_jsonl(args.requests)
    completed = set() if args.overwrite else _existing_request_ids(args.output)
    pending = [
        request
        for request in requests
        if str(request.get("request_id") or "").strip() not in completed
    ]
    if args.limit > 0:
        pending = pending[: args.limit]
    if not pending:
        print(f"no pending DeepSeek label requests -> {args.output}")
        return

    config = _deepseek_config(args)
    client = DeepSeekClient(config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    errors_output = _error_output_path(args)
    errors_output.parent.mkdir(parents=True, exist_ok=True)
    output_mode = "w" if args.overwrite else "a"
    error_mode = "w" if args.overwrite else "a"

    succeeded = 0
    failed = 0
    with args.output.open(output_mode, encoding="utf-8") as output_file, errors_output.open(
        error_mode,
        encoding="utf-8",
    ) as error_file:
        for index, request in enumerate(pending, start=1):
            request_id = str(request.get("request_id") or "").strip()
            try:
                response = await _call_deepseek_request(
                    client,
                    request,
                    max(args.retries, 0),
                    bool(args.json_mode),
                )
            except Exception as exc:  # keep the batch resumable
                failed += 1
                error_row = {
                    "request_id": request_id,
                    "candidate_group_id": str(request.get("candidate_group_id") or ""),
                    "seed": str(request.get("seed") or ""),
                    "error": str(exc),
                }
                raw_content = getattr(exc, "raw_content", None)
                if isinstance(raw_content, str) and raw_content:
                    error_row["raw_content_excerpt"] = raw_content[:4000]
                error_file.write(json.dumps(error_row, ensure_ascii=False, separators=(",", ":")) + "\n")
                error_file.flush()
                print(f"[{index}/{len(pending)}] failed {request_id}: {exc}")
            else:
                succeeded += 1
                output_file.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                output_file.flush()
                print(f"[{index}/{len(pending)}] labeled {request_id}")
            if args.sleep_seconds > 0 and index < len(pending):
                await asyncio.sleep(args.sleep_seconds)

    print(f"DeepSeek labeling complete: succeeded={succeeded}, failed={failed}")
    print(f"responses -> {args.output}")
    if failed:
        print(f"errors -> {errors_output}")


def call_deepseek(args: argparse.Namespace) -> None:
    asyncio.run(_call_deepseek(args))


def _merge_input_paths(args: argparse.Namespace) -> list[Path]:
    if args.inputs:
        return [path for path in args.inputs if path.is_file()]
    return sorted(path for path in args.input_dir.glob(args.pattern) if path.is_file())


def merge_responses(args: argparse.Namespace) -> None:
    paths = _merge_input_paths(args)
    if not paths:
        raise ValueError(f"No response shards found in {args.input_dir} with pattern {args.pattern!r}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    written = 0
    skipped_duplicates = 0
    skipped_invalid = 0
    with args.output.open("w", encoding="utf-8") as output_file:
        for path in paths:
            for line_number, row in enumerate(_read_jsonl(path), start=1):
                try:
                    identity = _request_identity(row)
                    _response_payload(row)
                except Exception:
                    if args.skip_invalid:
                        skipped_invalid += 1
                        continue
                    raise ValueError(f"{path}: line {line_number} is not a valid LLM response")
                if identity in seen:
                    skipped_duplicates += 1
                    continue
                seen.add(identity)
                output_file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
                written += 1

    print(f"merged {written} response rows -> {args.output}")
    print(f"input_files={len(paths)}, duplicate_rows={skipped_duplicates}, invalid_rows={skipped_invalid}")


def _extract_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()
    candidate = text
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if not match:
            raise
        candidate = match.group(0)
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            repaired = re.sub(r",(\s*[\]}])", r"\1", candidate)
            repaired = re.sub(r"}\s*(?={)", "},", repaired)
            payload = json.loads(repaired)
    if not isinstance(payload, dict):
        raise ValueError("LLM response JSON must be an object")
    return payload


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
    elif args.command == "split-requests":
        split_requests(args)
    elif args.command == "call-deepseek":
        call_deepseek(args)
    elif args.command == "aggregate":
        aggregate_responses(args)
    elif args.command == "merge-responses":
        merge_responses(args)
    elif args.command == "fuse":
        fuse_labels(args)
    else:
        raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
