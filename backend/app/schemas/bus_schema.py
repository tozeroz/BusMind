from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LINE_STATUS_ALIASES = {"active": "running"}
VALID_LINE_STATUSES = {"running", "suspended", "offline"}


class BusStationDTO(BaseModel):
    station_id: int
    station_name: str
    station_code: str = ""
    bus_stop_code: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    road_name: Optional[str] = None
    zone: Optional[str] = None
    status: str = "active"
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LineStationDTO(BaseModel):
    id: str
    line_station_id: Optional[str] = None
    line_id: int
    station_id: int
    order_index: int
    stop_sequence: Optional[int] = None
    direction: str
    service_no: Optional[str] = None
    line_name: Optional[str] = None
    operator: Optional[str] = None
    route_distance_km: Optional[float] = None
    station: BusStationDTO

    model_config = ConfigDict(from_attributes=True)


class BusLineDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    service_no: Optional[str] = None
    operator: Optional[str] = None
    direction: int = 1
    start_station: str = ""
    end_station: str = ""
    origin_station_id: Optional[int] = None
    destination_station_id: Optional[int] = None
    total_stations: int = 0
    distance_km: float = 0.0
    first_departure_time: Optional[str] = None
    last_departure_time: Optional[str] = None
    interval_minutes: int = 0
    am_peak_freq: Optional[str] = None
    am_offpeak_freq: Optional[str] = None
    pm_peak_freq: Optional[str] = None
    pm_offpeak_freq: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BusLineWithStationsDTO(BusLineDTO):
    stations: List[LineStationDTO] = Field(default_factory=list)


class BusLineCreateRequest(BaseModel):
    line_id: Optional[int] = Field(default=None, gt=0)
    line_name: str
    line_code: Optional[str] = None
    service_no: Optional[str] = None
    operator: Optional[str] = None
    direction: int = Field(default=1, ge=1, le=2)
    category: Optional[str] = None
    origin_station_id: Optional[int] = Field(default=None, gt=0)
    destination_station_id: Optional[int] = Field(default=None, gt=0)
    start_station: Optional[str] = ""
    end_station: Optional[str] = ""
    total_stations: Optional[int] = Field(default=0, ge=0)
    distance_km: Optional[float] = Field(default=0.0, ge=0)
    first_departure_time: Optional[str] = None
    last_departure_time: Optional[str] = None
    interval_minutes: Optional[int] = Field(default=10, ge=0)
    am_peak_freq: Optional[str] = None
    am_offpeak_freq: Optional[str] = None
    pm_peak_freq: Optional[str] = None
    pm_offpeak_freq: Optional[str] = None
    loop_desc: Optional[str] = None
    status: str = "running"

    @model_validator(mode="after")
    def normalize_code(self):
        code = (self.line_code or self.service_no or "").strip()
        if not code:
            raise ValueError("Line code/service_no cannot be empty")
        if len(code) > 30:
            raise ValueError("Line code/service_no cannot exceed 30 characters")
        self.line_code = code
        self.service_no = code
        return self

    @field_validator("line_name")
    @classmethod
    def validate_line_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Line name cannot be empty")
        if len(value) > 100:
            raise ValueError("Line name cannot exceed 100 characters")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str | None) -> str:
        normalized = LINE_STATUS_ALIASES.get(str(value or "running"), str(value or "running"))
        if normalized not in VALID_LINE_STATUSES:
            raise ValueError(f"Status must be one of {sorted(VALID_LINE_STATUSES)}")
        return normalized


class BusLineUpdateRequest(BaseModel):
    line_name: Optional[str] = None
    operator: Optional[str] = None
    direction: Optional[int] = Field(default=None, ge=1, le=2)
    category: Optional[str] = None
    origin_station_id: Optional[int] = Field(default=None, gt=0)
    destination_station_id: Optional[int] = Field(default=None, gt=0)
    start_station: Optional[str] = None
    end_station: Optional[str] = None
    total_stations: Optional[int] = Field(default=None, ge=0)
    distance_km: Optional[float] = Field(default=None, ge=0)
    first_departure_time: Optional[str] = None
    last_departure_time: Optional[str] = None
    interval_minutes: Optional[int] = Field(default=None, ge=0)
    am_peak_freq: Optional[str] = None
    am_offpeak_freq: Optional[str] = None
    pm_peak_freq: Optional[str] = None
    pm_offpeak_freq: Optional[str] = None
    loop_desc: Optional[str] = None
    status: Optional[str] = None

    @field_validator("line_name")
    @classmethod
    def validate_line_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 100:
            raise ValueError("Line name cannot exceed 100 characters")
        return value

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = LINE_STATUS_ALIASES.get(value, value)
        if normalized not in VALID_LINE_STATUSES:
            raise ValueError(f"Status must be one of {sorted(VALID_LINE_STATUSES)}")
        return normalized


class BusStationCreateRequest(BaseModel):
    station_id: Optional[int] = Field(default=None, gt=0)
    station_name: str
    station_code: Optional[str] = None
    bus_stop_code: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    road_name: Optional[str] = None
    zone: Optional[str] = None
    status: str = "active"

    @model_validator(mode="after")
    def normalize_columns(self):
        code = self.station_code if self.station_code is not None else self.bus_stop_code
        if code is not None:
            code = str(code).strip()
            if len(code) > 30:
                raise ValueError("Station code/bus_stop_code cannot exceed 30 characters")
        self.station_code = code
        self.bus_stop_code = code
        if self.address is None:
            self.address = self.road_name
        if self.road_name is None:
            self.road_name = self.address
        return self

    @field_validator("station_name")
    @classmethod
    def validate_station_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Station name cannot be empty")
        if len(value) > 100:
            raise ValueError("Station name cannot exceed 100 characters")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class BusStationUpdateRequest(BaseModel):
    station_name: Optional[str] = None
    station_code: Optional[str] = None
    bus_stop_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    road_name: Optional[str] = None
    zone: Optional[str] = None
    status: Optional[str] = None

    @field_validator("station_name")
    @classmethod
    def validate_station_name(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and len(value) > 100:
            raise ValueError("Station name cannot exceed 100 characters")
        return value

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -90 <= value <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and not -180 <= value <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return value


class LineStationCreateRequest(BaseModel):
    line_id: int = Field(gt=0)
    station_id: int = Field(gt=0)
    order_index: int = Field(gt=0)
    direction: str = "forward"
    route_distance_km: Optional[float] = Field(default=None, ge=0)
    wd_first_bus: Optional[str] = None
    wd_last_bus: Optional[str] = None
    sat_first_bus: Optional[str] = None
    sat_last_bus: Optional[str] = None
    sun_first_bus: Optional[str] = None
    sun_last_bus: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: str) -> str:
        if value not in {"forward", "backward"}:
            raise ValueError("Direction must be forward or backward")
        return value


class LineStationUpdateRequest(BaseModel):
    order_index: Optional[int] = Field(default=None, gt=0)
    direction: Optional[str] = None
    route_distance_km: Optional[float] = Field(default=None, ge=0)

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in {"forward", "backward"}:
            raise ValueError("Direction must be forward or backward")
        return value


class NearbyStationRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = Field(default=1.0, gt=0)


class NearbyStationDTO(BusStationDTO):
    distance_km: float


class NearbyStationResponse(BaseModel):
    stations: List[NearbyStationDTO]
    total: int


class StationLinesResponse(BaseModel):
    station_id: int
    station_name: str
    lines: List[BusLineDTO]
    total_lines: int


class LineListResponse(BaseModel):
    lines: List[BusLineDTO]
    total: int


class StationListResponse(BaseModel):
    stations: List[BusStationDTO]
    total: int
