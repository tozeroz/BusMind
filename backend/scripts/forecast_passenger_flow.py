from __future__ import annotations

import argparse
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (BACKEND_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.db.session import SessionLocal  # noqa: E402
from app.services.passenger_flow_forecast_service import (  # noqa: E402
    DEFAULT_HORIZON_DAYS,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MIN_HISTORY_POINTS,
    generate_station_predictions,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate passenger flow predictions for stations.")
    parser.add_argument(
        "--station-id",
        action="append",
        type=int,
        dest="station_ids",
        help="Generate only the given station id. Repeat the option to pass multiple ids.",
    )
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS)
    parser.add_argument("--min-history-points", type=int, default=DEFAULT_MIN_HISTORY_POINTS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    with SessionLocal() as db:
        results = generate_station_predictions(
            db,
            station_ids=args.station_ids,
            lookback_days=args.lookback_days,
            horizon_days=args.horizon_days,
            min_history_points=args.min_history_points,
        )

    created = sum(item.created for item in results)
    deleted = sum(item.deleted for item in results)
    reused = sum(item.reused for item in results)
    skipped = [item for item in results if item.skipped]

    print(
        "passenger_flow_forecast "
        f"stations={len(results)} created={created} deleted={deleted} reused={reused} skipped={len(skipped)}"
    )
    if skipped:
        preview = ", ".join(f"{item.station_id}:{item.reason}" for item in skipped[:10])
        print(f"skipped_preview={preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
