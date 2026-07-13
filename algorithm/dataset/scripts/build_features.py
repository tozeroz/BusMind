"""Build frozen recommendation features from local processed transit data.

This is the single offline dataset entrypoint for the recommendation model.
It reads processed CSV files, builds backend-style candidate route payloads,
and writes the frozen `features.csv` contract used by labeling and training.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[3]))

from algorithm.dataset.scripts.recommendation_data import (
    default_dataset_dir,
    default_processed_dir,
    default_raw_dir,
    line_congestion_lookup,
    load_bundle,
    stop_code_to_station_id,
    station_flow_hourly_lookup,
)
from algorithm.dataset.scripts.recommendation_feature_contract import FROZEN_FEATURE_COLUMNS, dump_json
from algorithm.routing.transit_graph import GraphNode, RideEdge, TransitGraphSearch, TransitGraphSnapshot


def _default_hot_stops_file() -> Path:
    return default_raw_dir().parent / "collect_scripts" / "hot_bus_stops.txt"


def parse_args() -> argparse.Namespace:
    """
    groups 20
    生成 20 个候选路线组。一个 group 大致对应一个 OD，也就是一组“起点站 -> 终点站”的候选路线。训练排序模型时，同一 group 里的路线互相比较。

    max-attempts 1000
    最多尝试 1000 个 OD。如果找到 20 个满足条件的 group 就提前结束；如果尝试 1000 次还不够，也会停止。这个防止脚本一直搜下去。

    max-transfer 1
    候选路线最多允许 1 次换乘。
    设成 1 比默认 2 快很多，因为搜索空间小很多。后面正式数据可以再考虑是否放回 2。

    max-candidates 5
    每个 OD 最多保留 5 条候选路线。
    比如同一个起终点找到 10 条路线，也只取前 5 条。

    min-candidates 2
    一个 OD 至少要找到 2 条候选路线，才会成为一个 group。因为排序训练需要“同组内可比较”，只有 1 条路线没法排序。
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=default_raw_dir())
    parser.add_argument("--processed-dir", type=Path, default=default_processed_dir())
    parser.add_argument("--output", type=Path, default=default_dataset_dir() / "features.csv")
    parser.add_argument("--month", default=None, help="Passenger volume month such as 202605")
    parser.add_argument("--groups", type=int, default=1000, help="Target candidate OD groups")
    parser.add_argument("--max-attempts", type=int, default=20000)
    parser.add_argument("--max-transfer", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--candidate-search-multiplier", type=int, default=10)
    parser.add_argument("--min-candidates", type=int, default=2)
    parser.add_argument("--pair-pool-size", type=int, default=5000)
    parser.add_argument(
        "--transfer-pair-ratio",
        type=float,
        default=0.35,
        help="Approximate share of OD pairs that should require a transfer when a hot-stop filter is available.",
    )
    parser.add_argument("--progress-every", type=int, default=50)
    parser.add_argument("--attempt-progress-every", type=int, default=50)
    parser.add_argument(
        "--hot-stops-file",
        type=Path,
        default=_default_hot_stops_file(),
        help="Bus stop code file used to restrict OD generation. Existing default is used automatically.",
    )
    parser.add_argument("--ignore-hot-stops", action="store_true", help="Build OD pairs from all processed stations.")
    parser.add_argument("--slow-search-seconds", type=float, default=5.0)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def _order_column(line_station: pd.DataFrame) -> str:
    return "stop_sequence" if "stop_sequence" in line_station.columns else "order_index"


def _clean_line_station(line_station: pd.DataFrame) -> pd.DataFrame:
    frame = line_station.copy()
    order_col = _order_column(frame)
    frame["line_id"] = pd.to_numeric(frame["line_id"], errors="coerce")
    frame["station_id"] = pd.to_numeric(frame["station_id"], errors="coerce")
    frame[order_col] = pd.to_numeric(frame[order_col], errors="coerce")
    frame = frame.dropna(subset=["line_id", "station_id", order_col]).copy()
    frame["line_id"] = frame["line_id"].astype(int)
    frame["station_id"] = frame["station_id"].astype(int)
    frame[order_col] = frame[order_col].astype(int)
    return frame


def _load_hot_station_ids(path: Path | None) -> set[int]:
    if path is None or not path.exists():
        return set()
    station_ids: set[int] = set()
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        text = raw_line.strip()
        if not text or text.startswith("#"):
            continue
        station_id = stop_code_to_station_id(text.split()[0])
        if station_id is not None:
            station_ids.add(station_id)
    return station_ids


def _candidate_od_pairs_from_processed(
    bundle: Any,
    rng: random.Random,
    pair_pool_size: int,
    station_filter: set[int] | None = None,
    transfer_pair_ratio: float = 0.35,
) -> list[tuple[int, int]]:
    line_station = _clean_line_station(bundle.line_station)
    order_col = _order_column(line_station)
    pair_lines: dict[tuple[int, int], set[int]] = defaultdict(set)
    fallback_pair_counts: dict[tuple[int, int], int] = {}
    allowed_stations = station_filter or set()
    line_sequences: dict[int, list[int]] = {}
    station_to_lines: dict[int, set[int]] = defaultdict(set)
    hot_positions_by_line: dict[int, list[tuple[int, int]]] = {}

    for line_id, group in line_station.groupby("line_id"):
        line_id = int(line_id)
        stations = [int(station_id) for station_id in group.sort_values(order_col)["station_id"].drop_duplicates().to_list()]
        if len(stations) < 2:
            continue
        line_sequences[line_id] = stations
        for station_id in stations:
            station_to_lines[station_id].add(line_id)
        if allowed_stations:
            eligible = [
                (index, int(station_id))
                for index, station_id in enumerate(stations)
                if int(station_id) in allowed_stations
            ]
        else:
            eligible = [(index, int(station_id)) for index, station_id in enumerate(stations)]
        if len(eligible) < 2:
            continue
        hot_positions_by_line[line_id] = eligible

        # 优先采样同一个 OD 被多条线路覆盖的情况，天然更容易形成多候选路线组。
        for left in range(len(eligible) - 1):
            for right in range(left + 1, len(eligible)):
                pair_lines[(eligible[left][1], eligible[right][1])].add(line_id)

        # 兜底保留一些单线路 OD，避免多线路 OD 不足时完全没有样本。
        sample_count = min(40, max(8, len(eligible) // 3))
        for _ in range(sample_count):
            left, right = sorted(rng.sample(range(len(eligible)), 2))
            pair = (eligible[left][1], eligible[right][1])
            fallback_pair_counts[pair] = fallback_pair_counts.get(pair, 0) + 1

    transfer_pairs: set[tuple[int, int]] = set()
    if allowed_stations and transfer_pair_ratio > 0:
        for first_line_id, stations in line_sequences.items():
            hot_starts = hot_positions_by_line.get(first_line_id, ())
            if not hot_starts:
                continue
            for start_index, start_station_id in hot_starts:
                downstream_stations = stations[start_index + 1 :]
                for transfer_station_id in downstream_stations:
                    for second_line_id in station_to_lines.get(transfer_station_id, ()):
                        if second_line_id == first_line_id:
                            continue
                        second_hot_positions = hot_positions_by_line.get(second_line_id, ())
                        if not second_hot_positions:
                            continue
                        try:
                            transfer_index = line_sequences[second_line_id].index(transfer_station_id)
                        except ValueError:
                            continue
                        for end_index, end_station_id in second_hot_positions:
                            if end_index <= transfer_index or end_station_id == start_station_id:
                                continue
                            pair = (start_station_id, end_station_id)
                            if pair not in pair_lines:
                                transfer_pairs.add(pair)

    multi_line_pairs = [(pair, len(lines)) for pair, lines in pair_lines.items() if len(lines) >= 2]
    rng.shuffle(multi_line_pairs)
    multi_line_pairs.sort(key=lambda item: item[1], reverse=True)
    transfer_pair_list = list(transfer_pairs)
    rng.shuffle(transfer_pair_list)

    output: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    transfer_count = 0
    direct_index = 0
    transfer_index = 0
    transfer_pair_ratio = max(0.0, min(1.0, float(transfer_pair_ratio)))

    while len(output) < pair_pool_size and (
        direct_index < len(multi_line_pairs) or transfer_index < len(transfer_pair_list)
    ):
        target_transfer_count = round((len(output) + 1) * transfer_pair_ratio)
        take_transfer = (
            transfer_index < len(transfer_pair_list)
            and transfer_count < target_transfer_count
        )
        if take_transfer:
            pair = transfer_pair_list[transfer_index]
            transfer_index += 1
            transfer_count += 1
        elif direct_index < len(multi_line_pairs):
            pair, _line_count = multi_line_pairs[direct_index]
            direct_index += 1
        else:
            pair = transfer_pair_list[transfer_index]
            transfer_index += 1
            transfer_count += 1
        if pair in seen:
            continue
        output.append(pair)
        seen.add(pair)
        if len(output) >= pair_pool_size:
            return output

    fallback_pairs = list(fallback_pair_counts.items())
    rng.shuffle(fallback_pairs)
    fallback_pairs.sort(key=lambda item: item[1], reverse=True)
    for pair, _count in fallback_pairs:
        if pair in seen:
            continue
        output.append(pair)
        seen.add(pair)
        if len(output) >= pair_pool_size:
            break
    return output


def _build_processed_graph_snapshot(bundle: Any) -> Any:
    line_station = _clean_line_station(bundle.line_station)
    order_col = _order_column(line_station)
    line_names: dict[int, str] = {}
    for row in bundle.bus_line.to_dict("records"):
        line_id = int(row["line_id"])
        line_names[line_id] = str(row.get("line_name") or row.get("service_no") or f"line-{line_id}")

    ride_edges: dict[Any, list[Any]] = defaultdict(list)
    station_to_nodes: dict[int, set[Any]] = defaultdict(set)
    node_station: dict[Any, int] = {}

    for line_id, group in line_station.groupby("line_id"):
        entries = (
            group.sort_values(order_col)[[order_col, "station_id"]]
            .drop_duplicates()
            .to_records(index=False)
            .tolist()
        )
        if len(entries) < 2:
            continue
        for order_index, station_id in entries:
            node = GraphNode(line_id=int(line_id), stop_sequence=int(order_index))
            node_station[node] = int(station_id)
            station_to_nodes[int(station_id)].add(node)
        for (order_index, _station_id), (next_order, next_station_id) in zip(entries, entries[1:]):
            from_node = GraphNode(line_id=int(line_id), stop_sequence=int(order_index))
            to_node = GraphNode(line_id=int(line_id), stop_sequence=int(next_order))
            ride_edges[from_node].append(RideEdge(to_node=to_node, to_station_id=int(next_station_id)))

    return TransitGraphSnapshot(
        ride_edges={node: tuple(edges) for node, edges in ride_edges.items()},
        transfer_links={
            station_id: tuple(sorted(nodes, key=lambda node: (node.line_id, node.stop_sequence)))
            for station_id, nodes in station_to_nodes.items()
        },
        line_names=line_names,
        node_station=node_station,
        station_lookup={},
    )


def _latest_arrival_tables(arrival: pd.DataFrame) -> tuple[dict[tuple[int, int], Any], dict[int, Any], Any | None]:
    if arrival.empty:
        return {}, {}, None
    frame = arrival.copy()
    frame["station_id"] = pd.to_numeric(frame["station_id"], errors="coerce")
    frame["line_id"] = pd.to_numeric(frame["line_id"], errors="coerce")
    frame["query_time"] = pd.to_datetime(frame["query_time"], errors="coerce")
    frame = frame.dropna(subset=["station_id", "line_id"]).copy()
    frame["station_id"] = frame["station_id"].astype(int)
    frame["line_id"] = frame["line_id"].astype(int)
    frame = frame.sort_values("query_time")
    by_station_line = {
        (int(row.station_id), int(row.line_id)): row
        for row in frame.drop_duplicates(["station_id", "line_id"], keep="last").itertuples(index=False)
    }
    by_line = {
        int(row.line_id): row
        for row in frame.drop_duplicates(["line_id"], keep="last").itertuples(index=False)
    }
    return by_station_line, by_line, frame.iloc[-1] if not frame.empty else None


def _row_get(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    return getattr(row, key, default)


def _arrival_for_candidate(candidate: Any, by_station_line: dict[tuple[int, int], Any], by_line: dict[int, Any], latest: Any) -> tuple[Any, list[str]]:
    first_line_id = int(candidate.line_ids[0])
    row = by_station_line.get((int(candidate.boarding_station_id), first_line_id))
    degraded: list[str] = []
    if row is None:
        row = by_line.get(first_line_id)
        degraded.extend(["eta_minutes", "load_code"])
    if row is None:
        row = latest
        degraded.extend(["eta_minutes", "load_code", "source_updated_at"])
    return row, list(dict.fromkeys(degraded))


def _iso_timestamp(value: Any) -> str:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return datetime.now(timezone.utc).isoformat()
    if parsed.tzinfo is None:
        parsed = parsed.tz_localize(timezone.utc)
    return parsed.isoformat()


def _route_speed_band_from_pressure(value: Any) -> int:
    try:
        pressure = float(value)
    except (TypeError, ValueError):
        return 5
    if pressure > 1.0:
        pressure = max(0.0, min(1.0, pressure / 100.0))
    band = int(round(8 - max(0.0, min(1.0, pressure)) * 7))
    return max(1, min(8, band))


def _build_lookup_frames(bundle: Any) -> dict[str, Any]:
    line = bundle.bus_line.copy()
    line["line_id"] = pd.to_numeric(line["line_id"], errors="coerce").astype("Int64")
    line_by_id = line.set_index("line_id").to_dict("index")

    flow = station_flow_hourly_lookup(bundle.passenger_flow_trend)
    flow_by_station = flow.groupby("station_id", as_index=False)["station_flow_mean"].mean()
    flow_by_station["station_flow_level"] = pd.qcut(
        flow_by_station["station_flow_mean"].rank(method="first"),
        q=3,
        labels=["low", "medium", "high"],
    ).astype(str)
    flow_lookup = flow_by_station.set_index("station_id").to_dict("index")

    line_congestion = line_congestion_lookup(bundle.bus_station, bundle.line_station, bundle.traffic_speed_bands)
    congestion_lookup = line_congestion.set_index("line_id")["congestion_score"].to_dict()
    global_congestion = float(line_congestion["congestion_score"].mean()) if not line_congestion.empty else 0.45

    return {
        "line_by_id": line_by_id,
        "flow_lookup": flow_lookup,
        "global_flow_level": "medium",
        "congestion_lookup": congestion_lookup,
        "global_congestion": global_congestion,
    }


def _mean_existing(values: list[float | None], fallback: float) -> tuple[float, bool]:
    existing = [float(value) for value in values if value is not None and not pd.isna(value)]
    if not existing:
        return fallback, True
    return round(sum(existing) / len(existing), 3), False


def _candidate_to_feature_row(
    *,
    group_index: int,
    start_station_id: int,
    end_station_id: int,
    candidate: Any,
    lookups: dict[str, Any],
    arrival_row: Any,
    arrival_degraded: list[str],
) -> dict[str, Any]:
    line_ids = [int(line_id) for line_id in candidate.line_ids]
    line_by_id = lookups["line_by_id"]
    service_nos = [str(line_by_id.get(line_id, {}).get("service_no", line_id)) for line_id in line_ids]

    avg_frequency, missing_frequency = _mean_existing(
        [line_by_id.get(line_id, {}).get("avg_service_frequency") for line_id in line_ids],
        fallback=12.0,
    )
    congestion_pressure, missing_congestion = _mean_existing(
        [lookups["congestion_lookup"].get(line_id) for line_id in line_ids],
        fallback=lookups["global_congestion"],
    )

    flow_item = lookups["flow_lookup"].get(int(candidate.boarding_station_id))
    station_flow_level = str((flow_item or {}).get("station_flow_level") or lookups["global_flow_level"])
    missing_flow = flow_item is None

    eta_minutes = _row_get(arrival_row, "eta_minutes", 12.0)
    eta_minutes = float(eta_minutes) if not pd.isna(eta_minutes) else 12.0
    load_code = str(_row_get(arrival_row, "load_code", "UNKNOWN") or "UNKNOWN").upper()
    monitored = 1 if float(_row_get(arrival_row, "monitored", 0) or 0) >= 1 else 0

    degraded_fields = list(arrival_degraded)
    degraded_fields.extend(["ride_time_minutes", "walk_time_minutes", "walk_distance_meters"])
    if missing_frequency:
        degraded_fields.append("avg_service_frequency_minutes")
    if missing_congestion:
        degraded_fields.append("route_speed_band")
    if missing_flow:
        degraded_fields.append("station_flow_level")
    degraded_fields = list(dict.fromkeys(degraded_fields))

    feature_sources = {
        "eta_minutes": "lta_realtime" if "eta_minutes" not in arrival_degraded else "lta_line_fallback",
        "ride_time_minutes": "backend_graph_estimate",
        "walk_time_minutes": "backend_graph_estimate",
        "walk_distance_meters": "rule_estimate",
        "transfer_count": "backend_graph",
        "avg_service_frequency_minutes": "database" if not missing_frequency else "default",
        "load_code": "lta_realtime" if "load_code" not in arrival_degraded else "lta_line_fallback",
        "station_flow_level": "historical" if not missing_flow else "default",
        "route_speed_band": "traffic_speed_bands" if not missing_congestion else "default",
        "source_updated_at": "lta_realtime" if arrival_row is not None else "default",
        "monitored": "lta_realtime" if arrival_row is not None else "default",
        "degraded_fields": "rule_estimate",
    }

    return {
        "candidate_group_id": f"backend_graph_od_{group_index:05d}_{start_station_id}_{end_station_id}",
        "route_id": str(candidate.route_id),
        "service_nos": dump_json(service_nos),
        "eta_minutes": round(eta_minutes, 3),
        "ride_time_minutes": round(float(candidate.ride_time_minutes), 3),
        "walk_time_minutes": round(float(candidate.walk_time_minutes), 3),
        "walk_distance_meters": round(float(candidate.walk_time_minutes) * 80.0, 1),
        "transfer_count": int(candidate.transfer_count),
        "avg_service_frequency_minutes": avg_frequency,
        "load_code": load_code if load_code in {"SEA", "SDA", "LSD", "UNKNOWN"} else "UNKNOWN",
        "station_flow_level": station_flow_level if station_flow_level in {"low", "medium", "high"} else "medium",
        "route_speed_band": _route_speed_band_from_pressure(congestion_pressure),
        "source_updated_at": _iso_timestamp(_row_get(arrival_row, "query_time")),
        "monitored": monitored,
        "degraded_fields": dump_json(degraded_fields),
        "feature_sources": dump_json(feature_sources),
        "is_synthetic": True,
    }


def _select_diverse_candidates(candidates: list[Any], max_candidates: int) -> list[Any]:
    if len(candidates) <= max_candidates:
        return candidates

    selected: list[Any] = []
    selected_route_ids: set[str] = set()

    def add(candidate: Any) -> None:
        route_id = str(candidate.route_id)
        if route_id in selected_route_ids or len(selected) >= max_candidates:
            return
        selected.append(candidate)
        selected_route_ids.add(route_id)

    for transfer_count in sorted({int(candidate.transfer_count) for candidate in candidates}):
        for candidate in candidates:
            if int(candidate.transfer_count) == transfer_count:
                add(candidate)
                break

    for candidate in candidates:
        add(candidate)

    return selected


def build_route_feature_frame(args: argparse.Namespace) -> pd.DataFrame:
    started_at = datetime.now()
    print("[dataset] loading processed feature tables...", flush=True)
    bundle = load_bundle(processed_dir=args.processed_dir, raw_dir=args.raw_dir, month=args.month)
    lookups = _build_lookup_frames(bundle)
    by_station_line, by_line, latest_arrival = _latest_arrival_tables(bundle.lta_bus_arrival)

    rng = random.Random(args.seed)
    station_filter: set[int] | None = None
    if not args.ignore_hot_stops:
        raw_hot_station_ids = _load_hot_station_ids(args.hot_stops_file)
        if raw_hot_station_ids:
            processed_station_ids = set(_clean_line_station(bundle.line_station)["station_id"].unique())
            station_filter = raw_hot_station_ids & processed_station_ids
            print(
                f"[dataset] hot station filter file={args.hot_stops_file} "
                f"loaded={len(raw_hot_station_ids)} matched={len(station_filter)}",
                flush=True,
            )
        elif args.hot_stops_file.exists():
            print(f"[dataset] hot station filter file is empty: {args.hot_stops_file}", flush=True)
        else:
            print(f"[dataset] hot station filter file not found: {args.hot_stops_file}", flush=True)

    scope = "hot stations" if station_filter else "all processed stations"
    print(f"[dataset] building OD pair pool from {scope}...", flush=True)
    od_pairs = _candidate_od_pairs_from_processed(
        bundle,
        rng,
        args.pair_pool_size,
        station_filter=station_filter,
        transfer_pair_ratio=args.transfer_pair_ratio,
    )
    if not od_pairs and station_filter:
        print("[dataset] no OD pairs found in hot station filter; falling back to all processed stations", flush=True)
        station_filter = None
        od_pairs = _candidate_od_pairs_from_processed(
            bundle,
            rng,
            args.pair_pool_size,
            transfer_pair_ratio=0.0,
        )
    print(f"[dataset] OD pair pool size={len(od_pairs)}", flush=True)

    print("[dataset] building transit graph from local processed CSV...", flush=True)
    snapshot = _build_processed_graph_snapshot(bundle)
    search = TransitGraphSearch(snapshot)
    station_ids = sorted(int(item) for item in snapshot.transfer_links.keys())
    print(f"[dataset] graph stations={len(station_ids)}", flush=True)
    fallback_station_ids = [station_id for station_id in station_ids if not station_filter or station_id in station_filter]
    if len(fallback_station_ids) < 2:
        fallback_station_ids = station_ids

    rows: list[dict[str, Any]] = []
    seen_groups: set[tuple[int, int]] = set()
    attempts = 0
    candidate_search_limit = max(
        args.max_candidates,
        min(50, args.max_candidates * max(1, args.candidate_search_multiplier)),
    )
    while len(seen_groups) < args.groups and attempts < args.max_attempts:
        attempts += 1
        if attempts <= len(od_pairs):
            start_station_id, end_station_id = od_pairs[attempts - 1]
        else:
            start_station_id, end_station_id = rng.sample(fallback_station_ids, 2)
        group_key = (start_station_id, end_station_id)
        if group_key in seen_groups:
            continue

        search_started = datetime.now()
        searched_candidates = search.find_candidates(
            start_station_id=start_station_id,
            end_station_id=end_station_id,
            max_transfer=args.max_transfer,
            max_candidates=candidate_search_limit,
        )
        candidates = _select_diverse_candidates(searched_candidates, args.max_candidates)
        search_elapsed = (datetime.now() - search_started).total_seconds()
        if args.slow_search_seconds > 0 and search_elapsed >= args.slow_search_seconds:
            print(
                f"[dataset] slow OD search start={start_station_id} end={end_station_id} "
                f"seconds={search_elapsed:.1f} candidates={len(candidates)}/{len(searched_candidates)}",
                flush=True,
            )
        if len(candidates) < args.min_candidates:
            if args.attempt_progress_every > 0 and attempts % args.attempt_progress_every == 0:
                elapsed = (datetime.now() - started_at).total_seconds()
                hit_rate = len(seen_groups) / attempts if attempts else 0.0
                print(
                    f"[dataset] searching groups={len(seen_groups)}/{args.groups} "
                    f"attempts={attempts}/{args.max_attempts} rows={len(rows)} "
                    f"hit_rate={hit_rate:.3f} elapsed={elapsed:.1f}s",
                    flush=True,
                )
            continue

        seen_groups.add(group_key)
        group_index = len(seen_groups)
        for candidate in candidates:
            arrival_row, arrival_degraded = _arrival_for_candidate(candidate, by_station_line, by_line, latest_arrival)
            rows.append(
                _candidate_to_feature_row(
                    group_index=group_index,
                    start_station_id=start_station_id,
                    end_station_id=end_station_id,
                    candidate=candidate,
                    lookups=lookups,
                    arrival_row=arrival_row,
                    arrival_degraded=arrival_degraded,
                )
            )

        if group_index == 1 or (args.progress_every > 0 and group_index % args.progress_every == 0):
            elapsed = (datetime.now() - started_at).total_seconds()
            hit_rate = group_index / attempts if attempts else 0.0
            print(
                f"[dataset] found groups={group_index}/{args.groups} "
                f"attempts={attempts}/{args.max_attempts} rows={len(rows)} "
                f"hit_rate={hit_rate:.3f} elapsed={elapsed:.1f}s",
                flush=True,
            )

    if not rows:
        raise ValueError("No backend graph candidate groups were generated")
    frame = pd.DataFrame(rows)[list(FROZEN_FEATURE_COLUMNS)]
    return frame.sort_values(["candidate_group_id", "route_id"]).reset_index(drop=True)


def main() -> None:
    args = parse_args()
    started_at = datetime.now()
    frame = build_route_feature_frame(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False, encoding="utf-8-sig")
    group_count = frame["candidate_group_id"].nunique()
    elapsed = (datetime.now() - started_at).total_seconds()
    print(f"built {len(frame)} frozen route rows across {group_count} groups -> {args.output}")
    print(f"avg routes per group={len(frame) / group_count:.2f} elapsed_seconds={elapsed:.1f}")


if __name__ == "__main__":
    main()
