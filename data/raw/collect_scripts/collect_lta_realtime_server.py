#!/usr/bin/env python3
"""Linux server collector for LTA realtime datasets.

Default server layout:

  script: /root/BusMind/data/raw/collect_lta_realtime_server.py
  output: /root/BusMind/data/raw/lta
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python 3.7 fallback on Baota servers.
    ZoneInfo = None  # type: ignore


LTA_BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"
DEFAULT_WINDOWS = (
    "morning_peak=07:00-09:00",
    "midday=12:00-14:00",
    "evening_peak=17:00-19:00",
    "night=21:00-23:00",
)


@dataclass(frozen=True)
class CollectionWindow:
    name: str
    start_minutes: int
    end_minutes: int


def default_raw_dir() -> Path:
    # 服务器部署时脚本放在 /root/BusMind/data/raw，采集结果默认写入同级 lta 目录。
    return Path(__file__).resolve().parent / "lta"


def get_timezone(name: str):
    if ZoneInfo is not None:
        return ZoneInfo(name)
    if name in {"Asia/Singapore", "Asia/Shanghai"}:
        return timezone(timedelta(hours=8))
    return None


def now_in_timezone(timezone_name: str) -> datetime:
    tz = get_timezone(timezone_name)
    return datetime.now(tz) if tz else datetime.now()


def parse_hhmm(value: str) -> int:
    hour_text, minute_text = value.split(":", 1)
    hour = int(hour_text)
    minute = int(minute_text)
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Invalid time value: {}".format(value))
    return hour * 60 + minute


def parse_windows(values: Iterable[str]) -> List[CollectionWindow]:
    windows: List[CollectionWindow] = []
    for raw_value in values:
        name, span = raw_value.split("=", 1)
        start_text, end_text = span.split("-", 1)
        windows.append(
            CollectionWindow(
                name=name.strip(),
                start_minutes=parse_hhmm(start_text.strip()),
                end_minutes=parse_hhmm(end_text.strip()),
            )
        )
    return windows


def current_window(now: datetime, windows: List[CollectionWindow]) -> Optional[CollectionWindow]:
    minutes = now.hour * 60 + now.minute
    for window in windows:
        if window.start_minutes <= window.end_minutes:
            if window.start_minutes <= minutes < window.end_minutes:
                return window
        else:
            # 支持跨午夜窗口，虽然当前默认窗口都在同一天内。
            if minutes >= window.start_minutes or minutes < window.end_minutes:
                return window
    return None


def require_account_key(value: Optional[str]) -> str:
    account_key = value or os.environ.get("LTA_ACCOUNT_KEY")
    if not account_key:
        raise RuntimeError("Missing AccountKey. Pass --account-key or set LTA_ACCOUNT_KEY.")

    # 宝塔面板里容易把值写成 "xxx"。LTA 需要纯 AccountKey，这里容错去掉两侧引号。
    return account_key.strip().strip('"').strip("'")


def request_json(url: str, account_key: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "AccountKey": account_key,
            "accept": "application/json",
            "User-Agent": "BusMind-LTA-Collector/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            raise RuntimeError(
                "LTA returned 401 UNAUTHORIZED. Check that LTA_ACCOUNT_KEY is configured, "
                "has no quotes/spaces, and is the active AccountKey from DataMall."
            )
        raise
    return json.loads(raw)


def invoke_odata_all(endpoint: str, account_key: str, page_size: int = 500) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    skip = 0
    while True:
        query = urllib.parse.urlencode({"$skip": skip})
        url = "{}/{}?{}".format(LTA_BASE_URL, endpoint, query)
        payload = request_json(url, account_key)
        page_items = payload.get("value") or []
        if not page_items:
            break
        items.extend(page_items)
        if len(page_items) < page_size:
            break
        skip += page_size
    return items


def load_stop_codes(
    raw_dir: Path,
    bus_stop_codes: Optional[str],
    bus_stop_file: Optional[Path],
    max_stops: int,
) -> List[str]:
    if bus_stop_codes:
        codes = [part.strip() for part in bus_stop_codes.replace(",", "\n").splitlines()]
        return [code for code in codes if code][:max_stops]

    if bus_stop_file is None:
        default_hot_file = Path(__file__).resolve().parent / "hot_bus_stops.txt"
        if default_hot_file.exists():
            bus_stop_file = default_hot_file

    if bus_stop_file:
        text = bus_stop_file.read_text(encoding="utf-8")
        codes = [part.strip() for part in text.replace(",", "\n").splitlines()]
        return [code for code in codes if code][:max_stops]

    bus_stops_path = raw_dir / "api_response" / "BusStops_full.json"
    if not bus_stops_path.exists():
        raise FileNotFoundError(
            "Missing {}. Run fetch_lta_static first, or pass --bus-stop-codes/--bus-stop-file.".format(bus_stops_path)
        )

    payload = json.loads(bus_stops_path.read_text(encoding="utf-8-sig"))
    rows = payload.get("value", payload) if isinstance(payload, dict) else payload
    codes = [str(row.get("BusStopCode", "")).strip() for row in rows if isinstance(row, dict)]
    return [code for code in codes if code][:max_stops]


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def save_json(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def collect_bus_arrival_round(
    account_key: str,
    raw_dir: Path,
    stop_codes: List[str],
    window: CollectionWindow,
    timezone_name: str,
    delay_seconds: float,
    round_index: int,
) -> None:
    timestamp = now_in_timezone(timezone_name)
    out_dir = raw_dir / "bus_arrival_samples" / timestamp.strftime("%Y-%m-%d")
    out_file = out_dir / "{}_bus_arrival_sample.jsonl".format(window.name)
    print(
        "[bus-arrival] round={} window={} stops={} file={}".format(
            round_index, window.name, len(stop_codes), out_file
        ),
        flush=True,
    )

    for stop_code in stop_codes:
        query_time = now_in_timezone(timezone_name).isoformat(timespec="seconds")
        params = urllib.parse.urlencode({"BusStopCode": stop_code})
        url = "{}/v3/BusArrival?{}".format(LTA_BASE_URL, params)
        try:
            payload = request_json(url, account_key)
            record = {
                "query_time": query_time,
                "collection_window": window.name,
                "collection_round": round_index,
                "bus_stop_code": stop_code,
                "response": payload,
            }
            append_jsonl(out_file, record)
            print("[bus-arrival] OK stop={}".format(stop_code), flush=True)
        except Exception as exc:  # Collector should continue on partial API failures.
            print("[bus-arrival] FAILED stop={} error={}".format(stop_code, exc), file=sys.stderr, flush=True)
        if delay_seconds > 0:
            time.sleep(delay_seconds)


def collect_traffic_speed_bands_snapshot(account_key: str, raw_dir: Path, timezone_name: str) -> None:
    timestamp = now_in_timezone(timezone_name)
    out_dir = raw_dir / "traffic_speed_bands" / timestamp.strftime("%Y-%m-%d")
    out_file = out_dir / "traffic_speed_bands_{}.json".format(timestamp.strftime("%Y%m%d_%H%M%S"))
    print("[traffic-speed-bands] fetching file={}".format(out_file), flush=True)
    items = invoke_odata_all("v4/TrafficSpeedBands", account_key)
    record = {
        "query_time": now_in_timezone(timezone_name).isoformat(timespec="seconds"),
        "endpoint": "v4/TrafficSpeedBands",
        "official_update_frequency_seconds": 300,
        "value": items,
    }
    save_json(out_file, record)
    print("[traffic-speed-bands] saved rows={} file={}".format(len(items), out_file), flush=True)


def run_collector(args: argparse.Namespace) -> None:
    account_key = require_account_key(args.account_key)
    raw_dir = Path(args.raw_dir).resolve() if args.raw_dir else default_raw_dir()
    windows = parse_windows(args.bus_windows)
    bus_stop_file = Path(args.bus_stop_file) if args.bus_stop_file else None
    stop_codes = load_stop_codes(raw_dir, args.bus_stop_codes, bus_stop_file, args.max_stops)

    if args.bus_poll_seconds < 20:
        raise ValueError("bus-poll-seconds should not be lower than official Bus Arrival update frequency: 20 seconds.")
    if args.traffic_poll_seconds < 300:
        raise ValueError(
            "traffic-poll-seconds should not be lower than official Traffic Speed Bands update frequency: 300 seconds."
        )

    end_at = None
    if args.duration_minutes:
        end_at = now_in_timezone(args.timezone) + timedelta(minutes=args.duration_minutes)

    next_bus_at: Optional[datetime] = None
    next_traffic_at: Optional[datetime] = None
    bus_round = 1

    print("[collector] mode={} raw_dir={}".format(args.mode, raw_dir), flush=True)
    print(
        "[collector] timezone={} duration_minutes={}".format(
            args.timezone, args.duration_minutes or "forever"
        ),
        flush=True,
    )
    print("[collector] bus windows=" + ", ".join(args.bus_windows), flush=True)

    while True:
        now = now_in_timezone(args.timezone)
        if end_at and now >= end_at:
            print("[collector] duration reached, exiting.", flush=True)
            return

        did_work = False

        if args.mode in {"both", "bus-arrival"}:
            window = current_window(now, windows)
            if window:
                if next_bus_at is None or now >= next_bus_at:
                    collect_bus_arrival_round(
                        account_key=account_key,
                        raw_dir=raw_dir,
                        stop_codes=stop_codes,
                        window=window,
                        timezone_name=args.timezone,
                        delay_seconds=args.stop_delay_seconds,
                        round_index=bus_round,
                    )
                    bus_round += 1
                    next_bus_at = now_in_timezone(args.timezone) + timedelta(seconds=args.bus_poll_seconds)
                    did_work = True
            else:
                next_bus_at = None

        if args.mode in {"both", "traffic-speed-bands"}:
            if next_traffic_at is None or now >= next_traffic_at:
                collect_traffic_speed_bands_snapshot(
                    account_key=account_key,
                    raw_dir=raw_dir,
                    timezone_name=args.timezone,
                )
                next_traffic_at = now_in_timezone(args.timezone) + timedelta(seconds=args.traffic_poll_seconds)
                did_work = True

        # 长驻进程用短睡眠检查时间窗，避免错过高峰开始时间。
        time.sleep(1 if did_work else args.idle_sleep_seconds)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect LTA realtime Bus Arrival and Traffic Speed Bands on Linux.")
    parser.add_argument("--mode", choices=("both", "bus-arrival", "traffic-speed-bands"), default="both")
    parser.add_argument("--account-key", help="LTA DataMall AccountKey. Defaults to LTA_ACCOUNT_KEY env var.")
    parser.add_argument("--raw-dir", help="Raw LTA output directory. Defaults to ./lta beside this script.")
    parser.add_argument("--timezone", default="Asia/Singapore")
    parser.add_argument("--duration-minutes", type=int, help="Optional duration for local testing. Omit for server mode.")
    parser.add_argument("--max-stops", type=int, default=100)
    parser.add_argument("--bus-stop-codes", help="Comma or newline separated hot bus stop codes.")
    parser.add_argument("--bus-stop-file", help="Text file containing hot bus stop codes, one per line.")
    parser.add_argument("--bus-poll-seconds", type=int, default=30)
    parser.add_argument("--traffic-poll-seconds", type=int, default=300)
    parser.add_argument("--stop-delay-seconds", type=float, default=0.3)
    parser.add_argument("--idle-sleep-seconds", type=int, default=10)
    parser.add_argument("--bus-windows", nargs="+", default=list(DEFAULT_WINDOWS))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    run_collector(args)


if __name__ == "__main__":
    main()
