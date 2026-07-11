"""One-shot inspector for the bus-arrival refresh scheduler.

Prints the (bus_stop_code, service_no) pairs the scheduler would actually
build from the current MySQL/SQLite database, so we can confirm whether
those IDs match the LTA DataMall catalogue before changing the strategy.

Run with cwd set to the backend directory (same as ``uvicorn app.main:app``):

    cd backend
    python scripts/inspect_refresh_jobs.py
"""

from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.bus_line import BusLine, BusStation, LineStation


def main() -> None:
    with SessionLocal() as db:
        lines = db.execute(
            select(BusLine.line_code, BusLine.line_name)
            .order_by(BusLine.line_id.asc())
            .limit(10)
        ).all()
        print(f"-- lines (showing {len(lines)}) --")
        for row in lines:
            print(f"  service_no={row.line_code}  name={row.line_name}")

        stations = db.execute(
            select(BusStation.station_code, BusStation.station_name)
            .where(BusStation.station_code.is_not(None))
            .order_by(BusStation.station_id.asc())
            .limit(5)
        ).all()
        print(f"\n-- stations (showing {len(stations)}) --")
        for row in stations:
            print(f"  bus_stop_code={row.station_code}  name={row.station_name}")

        sample_line = lines[0] if lines else None
        if sample_line:
            rows = db.execute(
                select(
                    LineStation.order_index,
                    LineStation.station_code,
                    BusStation.station_name,
                )
                .join(BusStation, LineStation.station_id == BusStation.station_id)
                .where(LineStation.line_code == sample_line.line_code)
                .order_by(LineStation.order_index.asc())
                .limit(5)
            ).all()
            print(f"\n-- first 5 stops for service_no={sample_line.line_code} --")
            for row in rows:
                print(
                    f"  seq={row.order_index}  bus_stop_code={row.station_code}  "
                    f"name={row.station_name}"
                )

        cartesian = db.execute(
            select(LineStation.line_code, LineStation.station_code)
            .where(LineStation.station_code.is_not(None))
            .where(LineStation.order_index == 1)
            .order_by(LineStation.line_id.asc())
            .limit(10)
        ).all()
        print("\n-- first stop per line (line_id ASC, limit 10) --")
        for row in cartesian:
            print(f"  service_no={row.line_code}  bus_stop_code={row.station_code}")


if __name__ == "__main__":
    main()