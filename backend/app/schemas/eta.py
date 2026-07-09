from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import StrictModel


class EtaResult(StrictModel):
    vehicle_id: int = Field(gt=0)
    target_station_id: int = Field(gt=0)
    predicted_eta_minutes: float = Field(ge=0)
    arrival_time: datetime
    factors: dict[str, Any]
    model_version: str
