from __future__ import annotations

import asyncio
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.bus_line import Base, BusLine, BusStation
from app.services.scheduler_service import (
    BusArrivalRefreshScheduler,
    build_refresh_jobs,
)


def _build_session() -> sessionmaker:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _seed(session_factory: sessionmaker) -> None:
    stations = [
        BusStation(
            station_id=1,
            station_code="01012",
            station_name="Stop A",
            latitude=Decimal("1.3000"),
            longitude=Decimal("103.8000"),
        ),
        BusStation(
            station_id=2,
            station_code="01013",
            station_name="Stop B",
            latitude=Decimal("1.3100"),
            longitude=Decimal("103.8100"),
        ),
        BusStation(
            station_id=3,
            station_code="01014",
            station_name="Stop C",
            latitude=Decimal("1.3200"),
            longitude=Decimal("103.8200"),
        ),
    ]
    lines = [
        BusLine(line_id=1, service_no="15", line_name="Svc 15", direction=1),
        BusLine(line_id=2, service_no="36", line_name="Svc 36", direction=1),
    ]
    with session_factory() as db:
        db.add_all(stations)
        db.add_all(lines)
        db.commit()


def test_build_refresh_jobs_uses_small_hot_pool():
    session_factory = _build_session()
    _seed(session_factory)

    with session_factory() as db:
        jobs = build_refresh_jobs(db, max_stations=2, max_lines=2)

    pairs = {(job.bus_stop_code, job.service_no) for job in jobs}
    assert pairs == {
        ("01012", "15"),
        ("01012", "36"),
        ("01013", "15"),
        ("01013", "36"),
    }
    # First two stations were picked; station names and line names propagated.
    names = {job.bus_stop_code: job.station_name for job in jobs}
    assert names["01012"] == "Stop A"
    assert names["01013"] == "Stop B"


@dataclass
class _RecordingLog:
    visited: list[tuple[str, str]]


def test_scheduler_tick_invokes_collector_and_sync():
    """Simulate one _tick iteration without network calls or real LTA client."""

    session_factory = _build_session()
    _seed(session_factory)

    log = _RecordingLog(visited=[])

    async def fake_collect(bus_stop_code: str, service_no: str | None = None):
        log.visited.append((bus_stop_code, service_no or ""))
        return [{"bus_stop_code": bus_stop_code, "service_no": service_no or "", "eta_minutes": 1.0}]

    @dataclass
    class _SyncResult:
        processed: int = 1
        skipped: int = 0

    class _FakeSync:
        def sync_bus_arrival(self, db, bus_stop_code: str, service_no: str) -> _SyncResult:
            log.visited.append((f"sync:{bus_stop_code}", service_no))
            return _SyncResult()

    scheduler = BusArrivalRefreshScheduler(
        interval_seconds=1, max_stations=2, max_lines=2, lta_client=object()
    )

    # Replace the async helpers used inside the production tick with fakes.
    class _StubCollector:
        refresh_bus_arrival = staticmethod(fake_collect)

    async def _drive() -> None:
        with session_factory() as db:
            jobs = build_refresh_jobs(db, max_stations=2, max_lines=2)

        for job in jobs:
            await _StubCollector().refresh_bus_arrival(job.bus_stop_code, job.service_no)
            with session_factory() as sync_db:
                _FakeSync().sync_bus_arrival(sync_db, job.bus_stop_code, job.service_no)
                sync_db.commit()

    asyncio.run(_drive())

    # Every (stop, service) produced a collector call AND a sync call.
    collect_calls = [entry for entry in log.visited if not entry[0].startswith("sync:")]
    sync_calls = [entry for entry in log.visited if entry[0].startswith("sync:")]
    assert len(collect_calls) == 4
    assert len(sync_calls) == 4
    pairs = {(stop.removeprefix("sync:"), service) for stop, service in sync_calls}
    assert pairs == {(stop, service) for stop, service in collect_calls}


def test_scheduler_disabled_when_client_missing():
    scheduler = BusArrivalRefreshScheduler(lta_client=None, interval_seconds=1)
    assert scheduler.enabled is False
    # start() must be a safe no-op and not raise.
    asyncio.run(scheduler.start())
