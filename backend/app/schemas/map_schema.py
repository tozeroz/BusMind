from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MapStationDTO(BaseModel):
    station_id: int
    station_name: str
    station_code: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    zone: Optional[str] = None
    line_ids: List[int] = []
    line_names: List[str] = []

class MapStationResponse(BaseModel):
    stations: List[MapStationDTO]
    total: int

class RoadSegmentDTO(BaseModel):
    segment_id: int
    line_id: int
    line_name: str
    start_station_id: int
    start_station_name: str
    end_station_id: int
    end_station_name: str
    path_coordinates: List[List[float]] = []
    distance_km: float
    passenger_flow: Optional[int] = 0

class RoadSegmentResponse(BaseModel):
    segments: List[RoadSegmentDTO]
    total: int

class MapLineDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    start_station: str
    end_station: str
    color: str = "#3B82F6"
    path_coordinates: List[List[float]] = []

class MapLineResponse(BaseModel):
    lines: List[MapLineDTO]
    total: int

class LineMapBoundsDTO(BaseModel):
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float

class LineMapDataDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    polyline: List[List[float]] = []
    stations: List[MapStationDTO] = []
    bounds: LineMapBoundsDTO