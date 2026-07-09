"""Narrow data gateway owned by service-side engineer B.

This module does not implement team-A APIs or database repositories.  It defines
only the data contract required by ETA/load/recommend services.  Team A can
replace the demo gateway with an adapter backed by its repositories.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import asin, cos, radians, sin, sqrt
from typing import Protocol

from backend.app.core.intelligence_exceptions import ResourceNotFoundError


@dataclass(frozen=True, slots=True)
class StationData:
    station_id: int
    station_name: str
    longitude: float
    latitude: float


@dataclass(frozen=True, slots=True)
class VehicleData:
    vehicle_id: int
    line_id: int
    longitude: float
    latitude: float
    current_station_id: int
    next_station_id: int
    speed_kph: float
    onboard_count: int
    capacity: int
    status: str = "normal"


@dataclass(frozen=True, slots=True)
class RouteSegmentData:
    segment_order: int
    line_id: int
    line_name: str
    boarding_station_id: int
    alighting_station_id: int
    ride_time_minutes: float


@dataclass(frozen=True, slots=True)
class CandidateRouteData:
    route_id: str
    vehicle_id: int
    line_ids: tuple[int, ...]
    segments: tuple[RouteSegmentData, ...]
    boarding_station_id: int
    alighting_station_id: int
    walk_time_minutes: float
    ride_time_minutes: float
    transfer_count: int


class IntelligenceDataGateway(Protocol):
    async def get_station(self, station_id: int) -> StationData: ...

    async def get_vehicle(self, vehicle_id: int) -> VehicleData: ...

    async def get_distance_to_station_meters(
        self, vehicle_id: int, target_station_id: int
    ) -> float: ...

    async def get_remaining_stop_count(
        self, vehicle_id: int, target_station_id: int
    ) -> int: ...

    async def get_station_flow_level(self, station_id: int, hour: int) -> str: ...

    async def get_candidate_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer_count: int,
    ) -> list[CandidateRouteData]: ...

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData: ...


class DemoIntelligenceGateway:
    """Deterministic demo data used only before database/model integration."""

    def __init__(self) -> None:
        self._stations = {
            1: StationData(1, "东门站", 116.39740, 39.90930),
            2: StationData(2, "图书馆站", 116.40120, 39.91060),
            3: StationData(3, "教学楼站", 116.40510, 39.91220),
            4: StationData(4, "南门站", 116.40330, 39.90670),
            5: StationData(5, "西门站", 116.39280, 39.91010),
            12: StationData(12, "创新中心站", 116.41180, 39.91480),
        }
        self._vehicles = {
            101: VehicleData(101, 1, 116.3906, 39.9088, 5, 1, 24.0, 38, 60),
            102: VehicleData(102, 2, 116.3879, 39.9100, 5, 1, 22.0, 24, 60),
            103: VehicleData(103, 3, 116.3950, 39.9048, 4, 1, 26.0, 47, 60),
        }

    async def get_station(self, station_id: int) -> StationData:
        station = self._stations.get(station_id)
        if station is None:
            raise ResourceNotFoundError(f"站点不存在：station_id={station_id}")
        return station

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        vehicle = self._vehicles.get(vehicle_id)
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        return vehicle

    async def get_distance_to_station_meters(
        self, vehicle_id: int, target_station_id: int
    ) -> float:
        vehicle = await self.get_vehicle(vehicle_id)
        station = await self.get_station(target_station_id)
        straight = _haversine_meters(
            vehicle.longitude,
            vehicle.latitude,
            station.longitude,
            station.latitude,
        )
        # Road network distance is normally longer than straight-line distance.
        return max(250.0, straight * 1.35)

    async def get_remaining_stop_count(
        self, vehicle_id: int, target_station_id: int
    ) -> int:
        await self.get_vehicle(vehicle_id)
        await self.get_station(target_station_id)
        return max(1, min(8, abs(target_station_id - 1) + 1))

    async def get_station_flow_level(self, station_id: int, hour: int) -> str:
        await self.get_station(station_id)
        if hour in {7, 8, 9, 17, 18, 19}:
            return "high"
        if hour in {10, 11, 12, 13, 14, 15, 16}:
            return "medium"
        return "low"

    async def get_candidate_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer_count: int,
    ) -> list[CandidateRouteData]:
        await self.get_station(start_station_id)
        await self.get_station(end_station_id)
        if start_station_id == end_station_id:
            return []

        routes = [
            CandidateRouteData(
                route_id="route_001",
                vehicle_id=101,
                line_ids=(1,),
                segments=(
                    RouteSegmentData(
                        1, 1, "校园1号线", start_station_id, end_station_id, 18.0
                    ),
                ),
                boarding_station_id=start_station_id,
                alighting_station_id=end_station_id,
                walk_time_minutes=4.5,
                ride_time_minutes=18.0,
                transfer_count=0,
            ),
            CandidateRouteData(
                route_id="route_002",
                vehicle_id=102,
                line_ids=(2,),
                segments=(
                    RouteSegmentData(
                        1, 2, "校园2号线", start_station_id, end_station_id, 16.0
                    ),
                ),
                boarding_station_id=start_station_id,
                alighting_station_id=end_station_id,
                walk_time_minutes=8.0,
                ride_time_minutes=16.0,
                transfer_count=0,
            ),
        ]
        if max_transfer_count >= 1:
            routes.append(
                CandidateRouteData(
                    route_id="route_003",
                    vehicle_id=103,
                    line_ids=(3, 1),
                    segments=(
                        RouteSegmentData(
                            1, 3, "校园快线", start_station_id, 3, 7.0
                        ),
                        RouteSegmentData(2, 1, "校园1号线", 3, end_station_id, 8.0),
                    ),
                    boarding_station_id=start_station_id,
                    alighting_station_id=end_station_id,
                    walk_time_minutes=3.5,
                    ride_time_minutes=15.0,
                    transfer_count=1,
                )
            )
        return routes

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        return min(
            self._stations.values(),
            key=lambda station: _haversine_meters(
                longitude,
                latitude,
                station.longitude,
                station.latitude,
            ),
        )

    async def update_vehicle_status(
        self,
        vehicle_id: int,
        **changes: object,
    ) -> VehicleData:
        current = await self.get_vehicle(vehicle_id)
        allowed = {
            "longitude",
            "latitude",
            "current_station_id",
            "next_station_id",
            "speed_kph",
            "onboard_count",
            "capacity",
            "status",
        }
        safe_changes = {key: value for key, value in changes.items() if key in allowed}
        updated = replace(current, **safe_changes)
        self._vehicles[vehicle_id] = updated
        return updated


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


_gateway: IntelligenceDataGateway = DemoIntelligenceGateway()


def get_intelligence_gateway() -> IntelligenceDataGateway:
    return _gateway


def configure_intelligence_gateway(gateway: IntelligenceDataGateway) -> None:
    """Replace demo data with a team-A repository adapter at application startup."""

    global _gateway
    _gateway = gateway
