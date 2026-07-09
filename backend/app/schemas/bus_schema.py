from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class BusStationDTO(BaseModel):
    station_id: int
    station_name: str
    station_code: str
    latitude: float
    longitude: float
    address: Optional[str]
    zone: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class LineStationDTO(BaseModel):
    id: int
    line_id: int
    station_id: int
    order_index: int
    direction: str
    station: BusStationDTO

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BusLineDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    start_station: str
    end_station: str
    total_stations: int
    distance_km: float
    first_departure_time: Optional[str]
    last_departure_time: Optional[str]
    interval_minutes: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BusLineWithStationsDTO(BusLineDTO):
    stations: List[LineStationDTO] = []

class BusLineCreateRequest(BaseModel):
    line_name: str
    line_code: str
    start_station: str
    end_station: str
    total_stations: Optional[int] = 0
    distance_km: Optional[float] = 0.0
    first_departure_time: Optional[str] = None
    last_departure_time: Optional[str] = None
    interval_minutes: Optional[int] = 10
    status: Optional[str] = "active"

    @field_validator('line_name')
    def validate_line_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Line name cannot be empty')
        if len(v) > 100:
            raise ValueError('Line name cannot exceed 100 characters')
        return v

    @field_validator('line_code')
    def validate_line_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Line code cannot be empty')
        if len(v) > 20:
            raise ValueError('Line code cannot exceed 20 characters')
        return v

class BusLineUpdateRequest(BaseModel):
    line_name: Optional[str] = None
    start_station: Optional[str] = None
    end_station: Optional[str] = None
    total_stations: Optional[int] = None
    distance_km: Optional[float] = None
    first_departure_time: Optional[str] = None
    last_departure_time: Optional[str] = None
    interval_minutes: Optional[int] = None
    status: Optional[str] = None

    @field_validator('line_name')
    def validate_line_name(cls, v):
        if v and len(v) > 100:
            raise ValueError('Line name cannot exceed 100 characters')
        return v

class BusStationCreateRequest(BaseModel):
    station_name: str
    station_code: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    zone: Optional[str] = None

    @field_validator('station_name')
    def validate_station_name(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Station name cannot be empty')
        if len(v) > 100:
            raise ValueError('Station name cannot exceed 100 characters')
        return v

    @field_validator('station_code')
    def validate_station_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Station code cannot be empty')
        if len(v) > 20:
            raise ValueError('Station code cannot exceed 20 characters')
        return v

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

class BusStationUpdateRequest(BaseModel):
    station_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    zone: Optional[str] = None

    @field_validator('station_name')
    def validate_station_name(cls, v):
        if v and len(v) > 100:
            raise ValueError('Station name cannot exceed 100 characters')
        return v

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

class LineStationCreateRequest(BaseModel):
    line_id: int
    station_id: int
    order_index: int
    direction: str = "forward"

    @field_validator('direction')
    def validate_direction(cls, v):
        if v not in ['forward', 'backward']:
            raise ValueError('Direction must be forward or backward')
        return v

class LineStationUpdateRequest(BaseModel):
    order_index: Optional[int] = None
    direction: Optional[str] = None

    @field_validator('direction')
    def validate_direction(cls, v):
        if v and v not in ['forward', 'backward']:
            raise ValueError('Direction must be forward or backward')
        return v

class NearbyStationRequest(BaseModel):
    latitude: float
    longitude: float
    radius_km: float = 1.0

    @field_validator('latitude')
    def validate_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    def validate_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

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