from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.core.intelligence_exceptions import ResourceNotFoundError
from app.repositories.transit_repository import TransitRepository
from app.services.intelligence_gateway import (
    CandidateRouteData,
    RouteSegmentData,
    StationData,
    VehicleData,
)


class MySQLTransitGateway:
    """Repository-backed gateway for ETA, load and recommendation services."""

    def __init__(self, db: Session | TransitRepository) -> None:
        self.repository = db if isinstance(db, TransitRepository) else TransitRepository(db)

    async def get_station(self, station_id: int) -> StationData:
        station = self.repository.get_station(station_id)
        if station is None:
            raise ResourceNotFoundError(f"未找到公交站点 station_id={station_id}")
        return StationData(
            station_id=int(station.station_id),
            station_name=str(station.station_name),
            longitude=float(station.longitude),
            latitude=float(station.latitude),
        )

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        vehicle = self.repository.get_vehicle(vehicle_id)
        if vehicle is None:
            raise ResourceNotFoundError(f"未找到公交车辆 vehicle_id={vehicle_id}")
        return VehicleData(
            vehicle_id=int(vehicle.vehicle_id),
            line_id=int(vehicle.line_id),
            longitude=float(vehicle.longitude or 0.0),
            latitude=float(vehicle.latitude or 0.0),
            current_station_id=int(vehicle.current_station_id or 0),
            next_station_id=int(vehicle.next_station_id or 0),
            speed_kph=float(vehicle.speed_kph or 18.0),
            onboard_count=int(vehicle.onboard_count or 0),
            capacity=int(vehicle.capacity or 60),
            status=str(vehicle.operation_status or "normal"),
        )

    async def get_distance_to_station_meters(self, vehicle_id: int, target_station_id: int) -> float:
        latest_eta = self.repository.get_latest_eta(vehicle_id=vehicle_id, target_station_id=target_station_id)
        if latest_eta is not None and latest_eta.vehicle_to_stop_distance_m is not None:
            return float(latest_eta.vehicle_to_stop_distance_m)
        vehicle = await self.get_vehicle(vehicle_id)
        station = await self.get_station(target_station_id)
        if vehicle.longitude == 0.0 and vehicle.latitude == 0.0:
            return 1_000.0
        return max(
            250.0,
            _haversine_meters(vehicle.longitude, vehicle.latitude, station.longitude, station.latitude) * 1.35,
        )

    async def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        await self.get_vehicle(vehicle_id)
        await self.get_station(target_station_id)
        return self.repository.get_remaining_stop_count(vehicle_id, target_station_id)

    async def get_station_flow_level(self, station_id: int, hour: int) -> str:
        await self.get_station(station_id)
        return self.repository.get_station_flow_level(station_id, hour)

    async def get_candidate_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer_count: int,
    ) -> list[CandidateRouteData]:
        await self.get_station(start_station_id)
        await self.get_station(end_station_id)
        records = self.repository.get_candidate_routes(start_station_id, end_station_id, max_transfer_count)
        return [
            CandidateRouteData(
                route_id=record.route_id,
                vehicle_id=record.vehicle_id,
                line_ids=record.line_ids,
                segments=tuple(
                    RouteSegmentData(
                        segment_order=segment.segment_order,
                        line_id=segment.line_id,
                        line_name=segment.line_name,
                        boarding_station_id=segment.boarding_station_id,
                        alighting_station_id=segment.alighting_station_id,
                        ride_time_minutes=segment.ride_time_minutes,
                    )
                    for segment in record.segments
                ),
                boarding_station_id=record.boarding_station_id,
                alighting_station_id=record.alighting_station_id,
                walk_time_minutes=record.walk_time_minutes,
                ride_time_minutes=record.ride_time_minutes,
                transfer_count=record.transfer_count,
            )
            for record in records
        ]

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        station = self.repository.find_nearest_station(longitude, latitude)
        if station is None:
            raise ResourceNotFoundError("未找到可用公交站点")
        return StationData(
            station_id=int(station.station_id),
            station_name=str(station.station_name),
            longitude=float(station.longitude),
            latitude=float(station.latitude),
        )


def _haversine_meters(longitude_1: float, latitude_1: float, longitude_2: float, latitude_2: float) -> float:
    earth_radius = 6_371_000.0
    lon_1, lat_1, lon_2, lat_2 = map(radians, (longitude_1, latitude_1, longitude_2, latitude_2))
    delta_lon = lon_2 - lon_1
    delta_lat = lat_2 - lat_1
    value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(value))
