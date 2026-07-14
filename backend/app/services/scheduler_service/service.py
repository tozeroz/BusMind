from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time_utils import now_local
from app.db.session import SessionLocal
from app.models.bus_line import BusLine, BusStation, LineStation
from app.services.collector_service.service import LtaCollectorService
from app.services.lta_service import LtaDataMallClient, LtaDataMallConfig
from app.services.sync_service.service import CacheSyncService


logger = logging.getLogger(__name__)
server_logger = logging.getLogger("uvicorn.error")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("invalid %s=%r, fallback to %d", name, raw, default)
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("invalid %s=%r, fallback to %f", name, raw, default)
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


def select_line_anchors(
    db: Session,
    *,
    max_lines: int,
    stops_per_line: int,
) -> list[tuple[str, str, str, str]]:
    """Pick real (service_no, line_name, bus_stop_code, station_name) anchors.

    For each of the first ``max_lines`` lines (ordered by ``line_id``), pick the
    first ``stops_per_line`` stops along ``line_station``. This yields real
    (line, stop) pairs from the database — exactly the inputs the LTA Bus
    Arrival API requires — instead of the Cartesian product of two unrelated
    hot lists, which used to return "no such service" from LTA.
    """

    rows = db.execute(
        select(
            LineStation.service_no,
            BusLine.line_name,
            LineStation.station_code,
            BusStation.station_name,
            LineStation.order_index,
        )
        .join(BusLine, LineStation.line_id == BusLine.line_id)
        .join(BusStation, LineStation.station_id == BusStation.station_id)
        .where(LineStation.service_no.is_not(None))
        .where(LineStation.station_code.is_not(None))
        .order_by(BusLine.line_id.asc(), LineStation.order_index.asc())
    ).all()

    anchors: list[tuple[str, str, str, str]] = []
    seen_lines: set[str] = set()
    per_line_count: dict[str, int] = {}
    for service_no_value, line_name_value, station_code_value, station_name_value, _ in rows:
        service_no = str(service_no_value)
        if service_no not in seen_lines:
            if len(seen_lines) >= max_lines:
                continue
            seen_lines.add(service_no)
            per_line_count[service_no] = 0
        if per_line_count[service_no] >= stops_per_line:
            continue
        anchors.append(
            (
                service_no,
                str(line_name_value or service_no),
                str(station_code_value),
                str(station_name_value or ""),
            )
        )
        per_line_count[service_no] += 1
    return anchors


def build_refresh_jobs(
    db: Session,
    *,
    max_lines: int,
    stops_per_line: int,
) -> list[RefreshJob]:
    """Build jobs from real (line, stop) anchors.

    Each job requests LTA Bus Arrival for a single service at one of its real
    stops, which matches the (BusStopCode, ServiceNo) pair LTA DataMall expects.
    """

    anchors = select_line_anchors(
        db, max_lines=max_lines, stops_per_line=stops_per_line
    )
    return [
        RefreshJob(
            bus_stop_code=stop_code,
            service_no=service_no,
            station_name=station_name,
            line_name=line_name,
        )
        for service_no, line_name, stop_code, station_name in anchors
    ]


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
        max_lines: int | None = None,
        stops_per_line: int | None = None,
        concurrency: int | None = None,
        per_job_deadline_seconds: float | None = None,
        lta_client: LtaDataMallClient | None = None,
    ) -> None:
        self.interval_seconds = (
            interval_seconds
            if interval_seconds is not None
            else _env_int("BUSMIND_REFRESH_BUS_ARRIVAL_INTERVAL_SECONDS", 60)
        )
        self.max_lines = max_lines if max_lines is not None else 2
        self.stops_per_line = stops_per_line if stops_per_line is not None else 3
        self.concurrency = (
            concurrency
            if concurrency is not None
            else max(1, _env_int("BUSMIND_REFRESH_BUS_ARRIVAL_CONCURRENCY", 4))
        )
        self.per_job_deadline_seconds = (
            per_job_deadline_seconds
            if per_job_deadline_seconds is not None
            else _env_float("BUSMIND_REFRESH_BUS_ARRIVAL_DEADLINE_SECONDS", 6.0)
        )
        self.lta_client = lta_client
        self._task: asyncio.Task[None] | None = None
        self._refresh_task: asyncio.Task[None] | None = None
        self._last_triggered_at: float | None = None
        self._stop_event = asyncio.Event()
        self.started_at: str | None = None
        self.last_tick_started_at: str | None = None
        self.last_tick_finished_at: str | None = None
        self.last_tick_jobs: int = 0
        self.last_tick_processed: int = 0
        self.last_tick_skipped: int = 0
        self.last_tick_error: str | None = None
        self.last_tick_failures: list[str] = []

    @property
    def enabled(self) -> bool:
        return self.lta_client is not None and self.interval_seconds > 0

    def status(self) -> dict[str, object]:
        return {
            "enabled": self.enabled,
            "running": self._task is not None and not self._task.done(),
            "refresh_running": self._refresh_task is not None
            and not self._refresh_task.done(),
            "interval_seconds": self.interval_seconds,
            "max_lines": self.max_lines,
            "stops_per_line": self.stops_per_line,
            "concurrency": self.concurrency,
            "per_job_deadline_seconds": self.per_job_deadline_seconds,
            "started_at": self.started_at,
            "last_tick_started_at": self.last_tick_started_at,
            "last_tick_finished_at": self.last_tick_finished_at,
            "last_tick_jobs": self.last_tick_jobs,
            "last_tick_processed": self.last_tick_processed,
            "last_tick_skipped": self.last_tick_skipped,
            "last_tick_error": self.last_tick_error,
            "last_tick_failures": self.last_tick_failures[-10:],
        }

    async def start(self) -> None:
        if not self.enabled:
            logger.info(
                "BusArrivalRefreshScheduler disabled "
                "(lta_client=%s, interval=%ds)",
                self.lta_client is not None,
                self.interval_seconds,
            )
            server_logger.warning(
                "BusArrivalRefreshScheduler disabled "
                "(lta_client=%s, interval=%ds)",
                self.lta_client is not None,
                self.interval_seconds,
            )
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self.started_at = now_local().isoformat()
        self._task = asyncio.create_task(self._run(), name="bus-arrival-refresh")
        logger.info(
            "BusArrivalRefreshScheduler started: interval=%ds, max_lines=%d, stops_per_line=%d",
            self.interval_seconds,
            self.max_lines,
            self.stops_per_line,
        )
        server_logger.info(
            "BusArrivalRefreshScheduler started: interval=%ds, max_lines=%d, stops_per_line=%d",
            self.interval_seconds,
            self.max_lines,
            self.stops_per_line,
        )

    async def stop(self) -> None:
        if self._refresh_task is not None and not self._refresh_task.done():
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            finally:
                self._refresh_task = None
        if self._task is None:
            return
        self._stop_event.set()
        try:
            await asyncio.wait_for(self._task, timeout=max(5, self.interval_seconds))
        except asyncio.CancelledError:
            logger.info("BusArrivalRefreshScheduler cancelled during shutdown")
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        except asyncio.TimeoutError:
            logger.warning("BusArrivalRefreshScheduler stop timed out; cancelling")
            self._task.cancel()
        except Exception:  # pragma: no cover - defensive
            logger.exception("BusArrivalRefreshScheduler raised during shutdown")
        finally:
            self._task = None

    def trigger_once(self, *, cooldown_seconds: float = 60.0) -> str:
        """Schedule one refresh without delaying the caller.

        Returns a small status string so API callers can distinguish a newly
        queued refresh from a disabled, already-running, or rate-limited one.
        """

        if not self.enabled:
            return "disabled"
        if self._refresh_task is not None and not self._refresh_task.done():
            return "already_running"

        now = time.monotonic()
        if (
            self._last_triggered_at is not None
            and now - self._last_triggered_at < cooldown_seconds
        ):
            return "cooldown"

        self._last_triggered_at = now
        self._refresh_task = asyncio.create_task(
            self._run_once(), name="bus-arrival-refresh-on-demand"
        )
        return "started"

    async def _run_once(self) -> None:
        assert self.lta_client is not None
        try:
            await self._tick(
                LtaCollectorService(self.lta_client),
                CacheSyncService(),
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("On-demand bus-arrival refresh failed")

    async def _run(self) -> None:
        assert self.lta_client is not None
        collector = LtaCollectorService(self.lta_client)
        sync = CacheSyncService()
        while not self._stop_event.is_set():
            try:
                await self._tick(collector, sync)
            except asyncio.CancelledError:
                self.last_tick_finished_at = now_local().isoformat()
                break
            except Exception as exc:  # pragma: no cover - keep scheduler alive
                self.last_tick_error = f"{type(exc).__name__}: {exc}"
                self.last_tick_finished_at = now_local().isoformat()
                logger.exception("BusArrivalRefreshScheduler tick failed")
                server_logger.exception("BusArrivalRefreshScheduler tick failed")
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
        tick_started_at = now_local()
        self.last_tick_started_at = tick_started_at.isoformat()
        self.last_tick_finished_at = None
        self.last_tick_jobs = 0
        self.last_tick_processed = 0
        self.last_tick_skipped = 0
        self.last_tick_error = None
        self.last_tick_failures = []

        # SQLAlchemy's synchronous driver can wait on a database connection.
        # Keep it off FastAPI's event loop so one slow refresh cannot freeze
        # login, health checks, or unrelated API requests.
        def _load_jobs() -> list[RefreshJob]:
            with SessionLocal() as db:
                return build_refresh_jobs(
                    db,
                    max_lines=self.max_lines,
                    stops_per_line=self.stops_per_line,
                )

        jobs = await asyncio.to_thread(_load_jobs)
        self.last_tick_jobs = len(jobs)
        if not jobs:
            self.last_tick_error = "no refresh jobs built from line_station"
            self.last_tick_finished_at = now_local().isoformat()
            server_logger.warning(
                "bus_arrival refresh tick %s jobs=0: no line_station anchors found",
                tick_started_at.isoformat(),
            )
            return

        processed = 0
        skipped = 0
        failures: list[str] = []
        semaphore = asyncio.Semaphore(self.concurrency)

        async def _run(job: RefreshJob) -> tuple[str, int, int] | None:
            if self._stop_event.is_set():
                return
            async with semaphore:
                if self._stop_event.is_set():
                    return
                try:
                    await asyncio.wait_for(
                        collector.refresh_bus_arrival(
                            job.bus_stop_code, job.service_no
                        ),
                        timeout=self.per_job_deadline_seconds,
                    )
                    def _sync_result():
                        with SessionLocal() as sync_db:
                            result = sync.sync_bus_arrival(
                                sync_db, job.bus_stop_code, job.service_no
                            )
                            sync_db.commit()
                            return result

                    result = await asyncio.to_thread(_sync_result)
                    return ("ok", result.processed, result.skipped)
                except asyncio.TimeoutError:
                    failure = (
                        f"{job.bus_stop_code}/{job.service_no}: "
                        f"TimeoutError: exceeded {self.per_job_deadline_seconds:.1f}s"
                    )
                    failures.append(failure)
                    logger.warning(
                        "refresh_bus_arrival timed out for %s/%s after %.1fs",
                        job.bus_stop_code,
                        job.service_no,
                        self.per_job_deadline_seconds,
                    )
                    server_logger.warning(
                        "refresh_bus_arrival timed out for %s/%s after %.1fs",
                        job.bus_stop_code,
                        job.service_no,
                        self.per_job_deadline_seconds,
                    )
                    return ("fail", 0, 1)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    failure = (
                        f"{job.bus_stop_code}/{job.service_no}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                    failures.append(failure)
                    logger.warning(
                        "refresh_bus_arrival failed for %s/%s",
                        job.bus_stop_code,
                        job.service_no,
                        exc_info=True,
                    )
                    server_logger.warning(
                        "refresh_bus_arrival failed for %s/%s: %s",
                        job.bus_stop_code,
                        job.service_no,
                        failure,
                    )
                    return ("fail", 0, 1)

        results = await asyncio.gather(
            *(_run(job) for job in jobs), return_exceptions=True
        )
        for entry in results:
            if not entry or isinstance(entry, Exception):
                skipped += 1
                continue
            status, ok, skip = entry
            if status == "ok":
                processed += ok
                skipped += skip
            else:
                skipped += 1
        self.last_tick_processed = processed
        self.last_tick_skipped = skipped
        self.last_tick_failures = failures
        self.last_tick_finished_at = now_local().isoformat()
        if processed <= 0:
            self.last_tick_error = (
                "refresh tick completed but no rows were synced; "
                f"skipped={skipped}, failures={len(failures)}"
            )
        logger.info(
            "bus_arrival refresh tick %s processed=%d skipped=%d jobs=%d concurrency=%d deadline=%.1fs",
            now_local().isoformat(),
            processed,
            skipped,
            len(jobs),
            self.concurrency,
            self.per_job_deadline_seconds,
        )
        server_logger.info(
            "bus_arrival refresh tick %s processed=%d skipped=%d jobs=%d concurrency=%d deadline=%.1fs",
            now_local().isoformat(),
            processed,
            skipped,
            len(jobs),
            self.concurrency,
            self.per_job_deadline_seconds,
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
    # Cover the first 10 lines × first 2 stops so the UI's "top 10 lines"
    # actually have real bus-arrival data within a minute of startup.
    return BusArrivalRefreshScheduler(
        lta_client=client,
        max_lines=10,
        stops_per_line=2,
        per_job_deadline_seconds=max(8.0, settings.lta_timeout_seconds + 1.0),
    )
