from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


VEHICLE_STATUS_ALIASES = {
    "running": "normal",
    "stopped": "offline",
    "maintenance": "offline",
}
VALID_VEHICLE_STATUSES = {"normal", "delayed", "offline"}
VALID_DATA_STATUSES = {"realtime", "estimated"}


class BusVehicleDTO(BaseModel):
    vehicle_id: int
    vehicle_code: Optional[str] = None
    line_id: int
    service_no: Optional[str] = None
    line_name: Optional[str] = None
    current_latitude: float = 0.0
    current_longitude: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    current_station_id: Optional[int] = None
    current_station_name: Optional[str] = None
    next_station_id: Optional[int] = None
    next_station_name: Optional[str] = None
    current_position_text: Optional[str] = None
    progress: float = 0.0
    status: str
    operation_status: Optional[str] = None
    speed_kmh: float = 0.0
    speed_kph: float = 0.0
    speed: float = 0.0
    direction_deg: float = 0.0
    onboard_count: int = 0
    capacity: int = 0
    load_level: Optional[str] = None
    load_code: Optional[str] = None
    load_score: Optional[float] = None
    load_rate: float = 0.0
    load_percent: float = 0.0
    delay_minutes: int = 0
    data_status: str = "estimated"
    last_updated_at: Optional[datetime] = None
    last_reported_at: Optional[datetime] = None
    update_time: str = ""
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VehicleListResponse(BaseModel):
    vehicles: List[BusVehicleDTO]
    total: int


class VehicleCreateRequest(BaseModel):
    vehicle_id: Optional[int] = Field(default=None, gt=0)
    vehicle_code: Optional[str] = None
    line_id: int = Field(gt=0)
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_station_id: Optional[int] = Field(default=None, gt=0)
    next_station_id: Optional[int] = Field(default=None, gt=0)
    next_station_name: Optional[str] = None
    current_position_text: Optional[str] = None
    progress: float = 0.0
    status: str = "normal"
    operation_status: Optional[str] = None
    speed_kmh: Optional[float] = Field(default=0.0, ge=0)
    speed_kph: Optional[float] = None
    direction_deg: float = 0.0
    onboard_count: Optional[int] = Field(default=0, ge=0)
    capacity: Optional[int] = Field(default=60, gt=0)
    load_level: Optional[str] = None
    load_code: Optional[str] = None
    load_score: Optional[float] = None
    delay_minutes: int = Field(default=0, ge=0)
    data_status: str = "estimated"

    @model_validator(mode="after")
    def normalize_compatibility_fields(self):
        if self.current_latitude is None:
            self.current_latitude = self.latitude
        if self.current_longitude is None:
            self.current_longitude = self.longitude
        if self.speed_kph is not None:
            self.speed_kmh = self.speed_kph
        raw_status = self.operation_status or self.status
        self.status = VEHICLE_STATUS_ALIASES.get(raw_status, raw_status)
        self.operation_status = self.status
        if self.status not in VALID_VEHICLE_STATUSES:
            raise ValueError(f"Status must be one of {sorted(VALID_VEHICLE_STATUSES)}")
        if self.data_status not in VALID_DATA_STATUSES:
            raise ValueError(f"data_status must be one of {sorted(VALID_DATA_STATUSES)}")
        return self

    @field_validator("vehicle_code")
    @classmethod
    def validate_vehicle_code(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                return None
            if len(value) > 30:
                raise ValueError("Vehicle code cannot exceed 30 characters")
        return value

    @field_validator("current_latitude", "latitude")
    @classmethod
    def validate_latitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("current_longitude", "longitude")
    @classmethod
    def validate_longitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class VehicleUpdateRequest(BaseModel):
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    current_station_id: Optional[int] = Field(default=None, gt=0)
    next_station_id: Optional[int] = Field(default=None, gt=0)
    next_station_name: Optional[str] = None
    current_position_text: Optional[str] = None
    progress: Optional[float] = None
    status: Optional[str] = None
    operation_status: Optional[str] = None
    speed_kmh: Optional[float] = Field(default=None, ge=0)
    speed_kph: Optional[float] = Field(default=None, ge=0)
    direction_deg: Optional[float] = None
    onboard_count: Optional[int] = Field(default=None, ge=0)
    capacity: Optional[int] = Field(default=None, gt=0)
    load_level: Optional[str] = None
    load_code: Optional[str] = None
    load_score: Optional[float] = None
    delay_minutes: Optional[int] = Field(default=None, ge=0)
    data_status: Optional[str] = None

    @model_validator(mode="after")
    def normalize_compatibility_fields(self):
        if self.current_latitude is None:
            self.current_latitude = self.latitude
        if self.current_longitude is None:
            self.current_longitude = self.longitude
        if self.speed_kmh is None:
            self.speed_kmh = self.speed_kph
        raw_status = self.operation_status or self.status
        if raw_status is not None:
            normalized = VEHICLE_STATUS_ALIASES.get(raw_status, raw_status)
            if normalized not in VALID_VEHICLE_STATUSES:
                raise ValueError(f"Status must be one of {sorted(VALID_VEHICLE_STATUSES)}")
            self.status = normalized
            self.operation_status = normalized
        if self.data_status is not None and self.data_status not in VALID_DATA_STATUSES:
            raise ValueError(f"data_status must be one of {sorted(VALID_DATA_STATUSES)}")
        return self

    @field_validator("current_latitude", "latitude")
    @classmethod
    def validate_latitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("current_longitude", "longitude")
    @classmethod
    def validate_longitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value
