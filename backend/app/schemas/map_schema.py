from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class MapStationDTO(BaseModel):
    station_id: int
    station_name: str
    station_code: str = ""
    bus_stop_code: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    road_name: Optional[str] = None
    zone: Optional[str] = None
    line_ids: List[int] = Field(default_factory=list)
    line_names: List[str] = Field(default_factory=list)
    service_nos: List[str] = Field(default_factory=list)


class MapStationResponse(BaseModel):
    stations: List[MapStationDTO]
    total: int


class RoadSegmentDTO(BaseModel):
    segment_id: str
    segment_name: Optional[str] = None
    line_id: int
    service_no: Optional[str] = None
    line_name: str
    direction: Optional[int] = None
    stop_sequence: Optional[int] = None
    start_station_id: int
    start_station_name: str
    end_station_id: int
    end_station_name: str
    path_coordinates: List[List[float]] = Field(default_factory=list)
    distance_km: float = 0.0
    segment_distance_km: Optional[float] = None
    ride_time_minutes: Optional[float] = None
    avg_speed_kph: Optional[float] = None
    delay_minutes: int = 0
    passenger_flow: Optional[float] = None
    avg_passenger_flow: Optional[float] = None
    flow_level: Optional[str] = None


class RoadSegmentResponse(BaseModel):
    segments: List[RoadSegmentDTO]
    total: int


class MapLineDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    service_no: Optional[str] = None
    start_station: str
    end_station: str
    color: str = "#3B82F6"
    path_coordinates: List[List[float]] = Field(default_factory=list)


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
    polyline: List[List[float]] = Field(default_factory=list)
    stations: List[MapStationDTO] = Field(default_factory=list)
    bounds: LineMapBoundsDTO


class GeoJSONLineStringDTO(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: List[List[float]] = Field(default_factory=list)


class LineGeometryPropertiesDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str


class LineGeometryFeatureDTO(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: GeoJSONLineStringDTO
    properties: LineGeometryPropertiesDTO
