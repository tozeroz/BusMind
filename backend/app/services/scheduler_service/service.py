from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time_utils import now_local
from app.db.session import SessionLocal
from app.models.bus_line import BusLine, BusStation
from app.services.collector_service.service import LtaCollectorService
from app.services.lta_service import LtaDataMallClient, LtaDataMallConfig
from app.services.sync_service.service import CacheSyncService


logger = logging.getLogger(__name__)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid %s=%r, fallback to %d", name, raw, default)
        return default


@dataclass(frozen=True, slots=True)
class RefreshJob:
    bus_stop_code: str
    service_no: str
    station_name: str
    line_name: str


def select_hot_stop_codes(
    db: Session,
    *,
    max_stations: int,
) -> list[tuple[str, str]]:
    """Pick a small set of representative bus stops.

    The ORM exposes ``bus_stop_code`` as a @property alias of ``station_code``;
    SQLAlchemy ``select()`` cannot target Python attributes, so we query the
    column directly and re-label the result back to ``bus_stop_code`` for
    callers.
    """

    rows = db.execute(
        select(BusStation.station_code, BusStation.station_name)
        .where(BusStation.station_code.is_not(None))
        .order_by(BusStation.station_id.asc())
        .limit(max_stations)
    ).all()
    return [(str(row.station_code), str(row.station_name)) for row in rows]


def select_hot_service_nos(db: Session, *, max_lines: int) -> list[tuple[str, str]]:
    """Pick a small set of representative bus services.

    ``service_no`` is exposed on the ORM as a @property alias of ``line_code``.
    """

    rows = db.execute(
        select(BusLine.line_code, BusLine.line_name)
        .order_by(BusLine.line_id.asc())
        .limit(max_lines)
    ).all()
    return [(str(row.line_code), str(row.line_name)) for row in rows]


def build_refresh_jobs(
    db: Session,
    *,
    max_stations: int,
    max_lines: int,
) -> list[RefreshJob]:
    stops = select_hot_stop_codes(db, max_stations=max_stations)
    services = select_hot_service_nos(db, max_lines=max_lines)
    if not stops or not services:
        return []
    jobs: list[RefreshJob] = []
    for stop_code, stop_name in stops:
        for service_no, line_name in services:
            jobs.append(
                RefreshJob(
                    bus_stop_code=stop_code,
                    service_no=service_no,
                    station_name=stop_name,
                    line_name=line_name,
                )
            )
    return jobs


class BusArrivalRefreshScheduler:
    """Background loop that keeps the bus-arrival cache + MySQL tables warm.

    Behaviour:

    - On every tick (default 60 s) the scheduler builds a stable hot pool of
      stops × services from ``bus_station`` / ``bus_line`` and asks the LTA
      collector to refresh Bus Arrival once per pair.
    - The collector writes the memory cache; ``CacheSyncService`` then upserts
      ``bus_vehicle / bus_eta_status / bus_load_status / lta_bus_arrival``.
    - When ``LTA_ACCOUNT_KEY`` is missing the scheduler logs once at startup
      and exits silently so dev databases continue to work.

    The class is intentionally dependency-free (no APScheduler) so it can land
    without touching ``backend/requirements.txt``.
    """

    def __init__(
        self,
        *,
        interval_seconds: int | None = None,
        max_stations: int | None = None,
        max_lines: int | None = None,
        lta_client: LtaDataMallClient | None = None,
    ) -> None:
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else _env_int("BUSMIND_REFRESH_BUS_ARRIVAL_INTERVAL_SECONDS", 60)
        )
        self.max_stations = max_stations if max_stations is not None else 3
        self.max_lines = max_lines if max_lines is not None else 2
        self.lta_client = lta_client
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    @property
    def enabled(self) -> bool:
        return self.lta_client is not None and self.interval_seconds > 0

    async def start(self) -> None:
        if not self.enabled:
            logger.info(
                "BusArrivalRefreshScheduler disabled "
                "(lta_client=%s, interval=%ds)",
                self.lta_client is not None,
                self.interval_seconds,
            )
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="bus-arrival-refresh")
        logger.info(
            "BusArrivalRefreshScheduler started: interval=%ds, max_stations=%d, max_lines=%d",
            self.interval_seconds,
            self.max_stations,
            self.max_lines,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=max(5, self.interval_seconds))
        except asyncio.TimeoutError:
            logger.warning("BusArrivalRefreshScheduler stop timed out; cancelling")
            self._task.cancel()
        except Exception:  # pragma: no cover - defensive
            logger.exception("BusArrivalRefreshScheduler raised during shutdown")
        finally:
            self._task = None

    async def _run(self) -> None:
        assert self.lta_client is not None
        collector = LtaCollectorService(self.lta_client)
        sync = CacheSyncService()
        while not self._stop_event.is_set():
            try:
                await self._tick(collector, sync)
            except Exception:  # pragma: no cover - keep scheduler alive
                logger.exception("BusArrivalRefreshScheduler tick failed")
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=self.interval_seconds
                )
            except asyncio.TimeoutError:
                continue

    async def _tick(
        self,
        collector: LtaCollectorService,
        sync: CacheSyncService,
    ) -> None:
        with SessionLocal() as db:
            jobs = build_refresh_jobs(
                db,
                max_stations=self.max_stations,
                max_lines=self.max_lines,
            )
        if not jobs:
            return

        processed = 0
        skipped = 0
        for job in jobs:
            try:
                await collector.refresh_bus_arrival(
                    job.bus_stop_code, job.service_no
                )
                with SessionLocal() as sync_db:
                    result = sync.sync_bus_arrival(
                        sync_db, job.bus_stop_code, job.service_no
                    )
                    sync_db.commit()
                processed += result.processed
                skipped += result.skipped
            except Exception:
                logger.warning(
                    "refresh_bus_arrival failed for %s/%s",
                    job.bus_stop_code,
                    job.service_no,
                )
                skipped += 1
        logger.info(
            "bus_arrival refresh tick %s processed=%d skipped=%d jobs=%d",
            now_local().isoformat(),
            processed,
            skipped,
            len(jobs),
        )


def build_default_scheduler() -> BusArrivalRefreshScheduler:
    """Factory used by ``app.main`` to construct the scheduler for production."""

    from app.core.intelligence_settings import settings

    if not settings.lta_account_key:
        return BusArrivalRefreshScheduler(lta_client=None)
    client = LtaDataMallClient(
        LtaDataMallConfig(
            account_key=settings.lta_account_key,
            base_url=settings.lta_base_url,
            timeout_seconds=settings.lta_timeout_seconds,
        )
    )
    return BusArrivalRefreshScheduler(lta_client=client)
