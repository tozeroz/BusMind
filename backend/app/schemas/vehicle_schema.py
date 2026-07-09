from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class BusVehicleDTO(BaseModel):
    vehicle_id: int
    vehicle_code: str
    line_id: int
    line_name: Optional[str] = None
    current_latitude: float
    current_longitude: float
    next_station_id: Optional[int] = None
    next_station_name: Optional[str] = None
    status: str
    speed_kmh: float
    direction_deg: float
    onboard_count: int
    capacity: int
    load_rate: float
    last_updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class VehicleListResponse(BaseModel):
    vehicles: List[BusVehicleDTO]
    total: int

class VehicleCreateRequest(BaseModel):
    vehicle_code: str
    line_id: int
    current_latitude: float
    current_longitude: float
    next_station_id: Optional[int] = None
    status: Optional[str] = "running"
    speed_kmh: Optional[float] = 0.0
    direction_deg: Optional[float] = 0.0
    onboard_count: Optional[int] = 0
    capacity: Optional[int] = 60

    @field_validator('vehicle_code')
    def validate_vehicle_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Vehicle code cannot be empty')
        if len(v) > 20:
            raise ValueError('Vehicle code cannot exceed 20 characters')
        return v

    @field_validator('current_latitude')
    def validate_current_latitude(cls, v):
        if v < -90 or v > 90:
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('current_longitude')
    def validate_current_longitude(cls, v):
        if v < -180 or v > 180:
            raise ValueError('Longitude must be between -180 and 180')
        return v

    @field_validator('status')
    def validate_status(cls, v):
        valid_statuses = ['running', 'stopped', 'maintenance']
        if v and v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v

class VehicleUpdateRequest(BaseModel):
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    next_station_id: Optional[int] = None
    status: Optional[str] = None
    speed_kmh: Optional[float] = None
    direction_deg: Optional[float] = None
    onboard_count: Optional[int] = None

    @field_validator('current_latitude')
    def validate_current_latitude(cls, v):
        if v is not None and (v < -90 or v > 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('current_longitude')
    def validate_current_longitude(cls, v):
        if v is not None and (v < -180 or v > 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

    @field_validator('status')
    def validate_status(cls, v):
        valid_statuses = ['running', 'stopped', 'maintenance']
        if v and v not in valid_statuses:
            raise ValueError(f'Status must be one of {valid_statuses}')
        return v