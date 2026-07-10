from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.schemas.common import StrictModel


class LtaBusArrivalAdminRefreshRequest(StrictModel):
    bus_stop_code: str = Field(pattern=r"^\d{5}$")
    service_no: str | None = Field(default=None, min_length=1, max_length=12)
    sync_to_db: bool = True


class LtaTrafficSpeedBandsAdminRefreshRequest(StrictModel):
    sync_to_db: bool = True


class LtaRefreshAdminResult(StrictModel):
    dataset: str
    collected: int
    synced: int
    skipped: int
    cache_keys: list[str]
    refreshed_at: datetime
