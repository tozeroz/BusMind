from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CongestionLevel = Literal[
    "free_flow",
    "slow",
    "congested",
    "severe",
    "no_data",
]
TrafficDataStatus = Literal["realtime", "stale", "no_data"]


class TrafficHeatmapRouteSegmentRequest(BaseModel):
    segment_order: int = Field(ge=1)
    line_id: int = Field(gt=0)
    boarding_station_id: int = Field(gt=0)
    alighting_station_id: int = Field(gt=0)


class TrafficHeatmapRequest(BaseModel):
    route_id: str | None = Field(default=None, min_length=1, max_length=100)
    route_segments: list[TrafficHeatmapRouteSegmentRequest] = Field(min_length=1)
    observed_at: datetime | None = None
    min_lat: float | None = Field(default=None, ge=-90, le=90)
    max_lat: float | None = Field(default=None, ge=-90, le=90)
    min_lon: float | None = Field(default=None, ge=-180, le=180)
    max_lon: float | None = Field(default=None, ge=-180, le=180)
    match_radius_m: float = Field(default=120.0, ge=20.0, le=500.0)
    stale_after_minutes: int = Field(default=15, ge=1, le=1440)

    @model_validator(mode="after")
    def validate_bounds(self) -> "TrafficHeatmapRequest":
        bounds = (self.min_lat, self.max_lat, self.min_lon, self.max_lon)
        if any(value is not None for value in bounds) and not all(value is not None for value in bounds):
            raise ValueError("min_lat, max_lat, min_lon and max_lon must be provided together")
        if self.min_lat is not None and self.max_lat is not None and self.min_lat > self.max_lat:
            raise ValueError("min_lat must not be greater than max_lat")
        if self.min_lon is not None and self.max_lon is not None and self.min_lon > self.max_lon:
            raise ValueError("min_lon must not be greater than max_lon")
        return self


class RouteGeometrySegmentDTO(BaseModel):
    route_segment_id: str
    line_id: int
    segment_order: int | None = None
    road_name: str | None = None
    coordinates: list[list[float]] = Field(default_factory=list)


class TrafficHeatmapSegmentDTO(BaseModel):
    route_segment_id: str
    line_id: int
    segment_order: int | None = None
    link_id: int | None = None
    road_name: str | None = None
    road_category: str | None = None
    coordinates: list[list[float]] = Field(default_factory=list)
    speed_band: int | None = None
    minimum_speed_kmh: float | None = None
    maximum_speed_kmh: float | None = None
    congestion_score: float | None = Field(default=None, ge=0, le=1)
    congestion_level: CongestionLevel
    congestion_label: str
    heat_color: str
    observed_at: datetime | None = None
    query_time: datetime | None = None
    data_status: TrafficDataStatus
    is_stale: bool = False
    match_distance_m: float | None = Field(default=None, ge=0)


class TrafficHeatmapResponse(BaseModel):
    route_id: str | None = None
    line_ids: list[int] = Field(default_factory=list)
    route_segments: list[RouteGeometrySegmentDTO] = Field(default_factory=list)
    traffic_segments: list[TrafficHeatmapSegmentDTO] = Field(default_factory=list)
    total: int
    matched_count: int
    no_data_count: int
    observed_at: datetime | None = None
    generated_at: datetime
    stale_after_minutes: int
