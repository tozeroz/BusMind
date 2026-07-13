from __future__ import annotations

from app.services.scheduler_service.service import (
    BusArrivalRefreshScheduler,
    RefreshJob,
    build_default_scheduler,
    build_refresh_jobs,
    select_hot_service_nos,
    select_hot_stop_codes,
    select_line_anchors,
)


_default_scheduler: BusArrivalRefreshScheduler | None = None


def get_default_scheduler() -> BusArrivalRefreshScheduler:
    """Return the process-wide on-demand arrival refresher."""

    global _default_scheduler
    if _default_scheduler is None:
        _default_scheduler = build_default_scheduler()
    return _default_scheduler

__all__ = [
    "BusArrivalRefreshScheduler",
    "RefreshJob",
    "build_default_scheduler",
    "get_default_scheduler",
    "build_refresh_jobs",
    "select_hot_service_nos",
    "select_hot_stop_codes",
    "select_line_anchors",
]
