from __future__ import annotations

from enum import StrEnum

from pydantic import ConfigDict, Field

from app.schemas.common import GeoPoint, StationSummary, StrictModel


class WalkingRouteMode(StrEnum):
    STRAIGHT_LINE = "straight_line"
    MAP_API = "map_api"


class WalkingTimeRequest(StrictModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "origin_longitude": 116.3974,
                    "origin_latitude": 39.9093,
                    "target_station_id": 3,
                    "walking_speed_mps": 1.2,
                    "route_mode": "straight_line",
                }
            ]
        }
    )

    origin_longitude: float = Field(ge=-180, le=180)
    origin_latitude: float = Field(ge=-90, le=90)
    target_station_id: int = Field(gt=0)
    walking_speed_mps: float = Field(default=1.2, ge=0.6, le=2.0)
    route_mode: WalkingRouteMode = WalkingRouteMode.STRAIGHT_LINE


class WalkingTimeResult(StrictModel):
    origin: GeoPoint
    target_station: StationSummary
    walk_distance_meters: float = Field(ge=0)
    walk_time_minutes: float = Field(ge=0)
    walking_speed_mps: float = Field(ge=0.6, le=2.0)
    route_source: WalkingRouteMode
