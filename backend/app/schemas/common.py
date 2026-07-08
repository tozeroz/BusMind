from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class GeoPoint(StrictModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)


class StationSummary(StrictModel):
    station_id: int = Field(gt=0)
    station_name: str = Field(min_length=1, max_length=100)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    latitude: float | None = Field(default=None, ge=-90, le=90)


class RouteSegment(StrictModel):
    segment_order: int = Field(ge=1)
    line_id: int = Field(gt=0)
    line_name: str = Field(min_length=1, max_length=100)
    boarding_station_id: int = Field(gt=0)
    alighting_station_id: int = Field(gt=0)
    ride_time_minutes: float = Field(ge=0)


class ToolResult(StrictModel):
    tool_name: str
    success: bool
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
