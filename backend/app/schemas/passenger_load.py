from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from backend.app.schemas.common import StrictModel


class LoadLevel(StrEnum):
    SEATS_AVAILABLE = "seats_available"
    STANDING_AVAILABLE = "standing_available"
    LIMITED_STANDING = "limited_standing"


class PassengerLoadPredictionRequest(StrictModel):
    line_id: int = Field(gt=0)
    station_id: int = Field(gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    target_time: datetime | None = None
    current_onboard_count: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, gt=0)
    weather: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def check_onboard_not_overly_unreasonable(self) -> "PassengerLoadPredictionRequest":
        if (
            self.current_onboard_count is not None
            and self.capacity is not None
            and self.current_onboard_count > self.capacity * 2
        ):
            raise ValueError("current_onboard_count 不应超过 capacity 的 2 倍")
        return self


class PassengerLoadPredictionResult(StrictModel):
    line_id: int
    station_id: int
    vehicle_id: int | None
    predicted_onboard_count: int | None
    capacity: int | None
    predicted_load_rate: float | None = Field(default=None, ge=0, le=1)
    predicted_load_level: LoadLevel
    load_score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    predict_time: datetime
    feature_summary: dict[str, Any]
    model_version: str
