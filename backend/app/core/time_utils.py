from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.intelligence_settings import settings


def now_local() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.timezone))
    except Exception:
        return datetime.now(timezone.utc)


def ensure_local_datetime(value: datetime | None) -> datetime:
    if value is None:
        return now_local()
    if value.tzinfo is None:
        try:
            return value.replace(tzinfo=ZoneInfo(settings.timezone))
        except Exception:
            return value.replace(tzinfo=timezone.utc)
    return value
