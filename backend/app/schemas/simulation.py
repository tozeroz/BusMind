from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import StrictModel
from app.schemas.passenger_load import LoadLevel


class VehicleRunStatus(StrEnum):
    NORMAL = "normal"
    DELAYED = "delayed"
    OFFLINE = "offline"


class VehicleStatusUpdateRequest(StrictModel):
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    current_station_id: int | None = Field(default=None, gt=0)
    next_station_id: int | None = Field(default=None, gt=0)
    speed_kph: float | None = Field(default=None, ge=0, le=160)
    onboard_count: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, gt=0, le=300)
    status: VehicleRunStatus | None = None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "VehicleStatusUpdateRequest":
        if not self.model_dump(exclude_none=True):
            raise ValueError("至少提供一个需要更新的车辆状态字段")
        if (
            self.onboard_count is not None
            and self.capacity is not None
            and self.onboard_count > self.capacity * 2
        ):
            raise ValueError("onboard_count 不应超过 capacity 的 2 倍")
        return self


class VehicleStatusUpdateResult(StrictModel):
    vehicle_id: int
    line_id: int
    longitude: float
    latitude: float
    current_station_id: int
    next_station_id: int
    speed_kph: float
    onboard_count: int
    capacity: int
    status: VehicleRunStatus
    source: str
    updated_at: datetime


class PredictionType(StrEnum):
    ETA = "eta"
    PASSENGER_LOAD = "passenger_load"


class PredictionResultUpdateRequest(StrictModel):
    prediction_type: PredictionType
    vehicle_id: int | None = Field(default=None, gt=0)
    line_id: int | None = Field(default=None, gt=0)
    station_id: int | None = Field(default=None, gt=0)
    target_station_id: int | None = Field(default=None, gt=0)

    predicted_eta_minutes: float | None = Field(default=None, ge=0, le=240)
    arrival_time: datetime | None = None

    predicted_load_rate: float | None = Field(default=None, ge=0, le=2)
    predicted_load_level: LoadLevel | None = None
    predicted_onboard_count: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, gt=0, le=300)
    load_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float = Field(default=0.9, ge=0, le=1)
    prediction_time: datetime | None = None

    model_version: str = Field(default="manual_update_v1", min_length=1, max_length=80)
    source: str = Field(default="simulation", min_length=1, max_length=40)
    expires_in_seconds: int = Field(default=300, ge=20, le=86400)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_by_prediction_type(self) -> "PredictionResultUpdateRequest":
        if self.prediction_type == PredictionType.ETA:
            if self.vehicle_id is None or self.line_id is None or self.target_station_id is None:
                raise ValueError("ETA 更新必须提供 vehicle_id、line_id 和 target_station_id")
            if self.predicted_eta_minutes is None and self.arrival_time is None:
                raise ValueError("ETA 更新必须提供 predicted_eta_minutes 或 arrival_time")
        else:
            if self.vehicle_id is None or self.line_id is None:
                raise ValueError("客载预测更新必须提供 vehicle_id 和 line_id")
            if self.predicted_load_rate is None and self.predicted_load_level is None:
                raise ValueError(
                    "客载预测更新必须提供 predicted_load_rate 或 predicted_load_level"
                )
            if (
                self.predicted_onboard_count is not None
                and self.capacity is not None
                and self.predicted_onboard_count > self.capacity * 2
            ):
                raise ValueError("predicted_onboard_count 不应超过 capacity 的 2 倍")
        return self


class PredictionResultUpdateResult(StrictModel):
    prediction_type: PredictionType
    storage_key: str
    source: str
    model_version: str
    payload: dict[str, Any]
    updated_at: datetime
    expires_at: datetime


class LtaBusArrivalRefreshRequest(StrictModel):
    bus_stop_code: str = Field(pattern=r"^\d{5}$")
    service_no: str = Field(min_length=1, max_length=12)
    vehicle_id: int = Field(gt=0)
    line_id: int = Field(gt=0)
    station_id: int = Field(gt=0)
    capacity: int = Field(default=60, gt=0, le=300)
    expires_in_seconds: int = Field(default=60, ge=20, le=600)


class LtaBusArrivalRefreshResult(StrictModel):
    bus_stop_code: str
    service_no: str
    operator: str
    vehicle_id: int
    line_id: int
    station_id: int
    predicted_eta_minutes: float
    estimated_arrival: datetime
    predicted_load_level: LoadLevel
    predicted_load_rate: float
    monitored: bool
    latitude: float | None
    longitude: float | None
    feature: str
    bus_type: str
    source: str
    refreshed_at: datetime
    expires_at: datetime