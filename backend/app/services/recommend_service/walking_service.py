from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app.core.intelligence_settings import settings
from app.schemas.common import GeoPoint, StationSummary
from app.schemas.walking import WalkingRouteMode, WalkingTimeRequest, WalkingTimeResult
from app.services.intelligence_gateway import IntelligenceDataGateway


class WalkingTimeService:
    def __init__(self, gateway: IntelligenceDataGateway) -> None:
        self.gateway = gateway

    async def estimate(self, request: WalkingTimeRequest) -> WalkingTimeResult:
        station = await self.gateway.get_station(request.target_station_id)
        straight_distance = _haversine_meters(
            request.origin_longitude,
            request.origin_latitude,
            station.longitude,
            station.latitude,
        )
        # No map-provider ownership is assumed. map_api requests safely fall back
        # to the documented straight-line estimate until a map adapter is added.
        route_source = WalkingRouteMode.STRAIGHT_LINE
        distance = straight_distance * settings.walking_road_factor
        minutes = distance / request.walking_speed_mps / 60
        return WalkingTimeResult(
            origin=GeoPoint(
                longitude=request.origin_longitude,
                latitude=request.origin_latitude,
            ),
            target_station=StationSummary(
                station_id=station.station_id,
                station_name=station.station_name,
                longitude=station.longitude,
                latitude=station.latitude,
            ),
            walk_distance_meters=round(distance, 1),
            walk_time_minutes=round(minutes, 1),
            walking_speed_mps=request.walking_speed_mps,
            route_source=route_source,
        )


def _haversine_meters(
    longitude_1: float,
    latitude_1: float,
    longitude_2: float,
    latitude_2: float,
) -> float:
    earth_radius = 6_371_000.0
    lon_1, lat_1, lon_2, lat_2 = map(
        radians, (longitude_1, latitude_1, longitude_2, latitude_2)
    )
    delta_lon = lon_2 - lon_1
    delta_lat = lat_2 - lat_1
    value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(value))
