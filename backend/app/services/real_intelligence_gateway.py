"""Real data gateway that reads from Team-A's database repositories.

This gateway implements the IntelligenceDataGateway protocol using actual
database queries instead of demo data. It currently supports a minimal set
of methods to demonstrate the integration pattern.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Optional

from sqlalchemy.orm import Session

from app.core.intelligence_exceptions import ResourceNotFoundError
from app.dependencies.auth import get_db
from app.models.bus_line import BusStation, LineStation
from app.models.bus_vehicle import BusVehicle
from app.services.intelligence_gateway import (
    IntelligenceDataGateway,
    StationData,
    VehicleData,
)


class RealIntelligenceGateway:
    """Intelligence gateway backed by real database queries."""

    def __init__(self, db: Session) -> None:
        self._db = db

    async def get_station(self, station_id: int) -> StationData:
        """Get station data by station ID from database."""
        station = self._db.query(BusStation).filter(BusStation.station_id == station_id).first()
        if station is None:
            raise ResourceNotFoundError(f"站点不存在：station_id={station_id}")
        
        return StationData(
            station_id=int(station.station_id),
            station_name=station.station_name,
            longitude=float(station.longitude) if station.longitude else 0.0,
            latitude=float(station.latitude) if station.latitude else 0.0,
        )

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        """Get vehicle data by vehicle ID from database."""
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        return VehicleData(
            vehicle_id=int(vehicle.vehicle_id),
            line_id=int(vehicle.line_id),
            longitude=float(vehicle.current_longitude) if vehicle.current_longitude else 0.0,
            latitude=float(vehicle.current_latitude) if vehicle.current_latitude else 0.0,
            current_station_id=int(vehicle.current_station_id) if vehicle.current_station_id else 0,
            next_station_id=int(vehicle.next_station_id) if vehicle.next_station_id else 0,
            speed_kph=float(vehicle.speed_kmh) if vehicle.speed_kmh else 0.0,
            onboard_count=int(vehicle.onboard_count) if vehicle.onboard_count else 0,
            capacity=int(vehicle.capacity) if vehicle.capacity else 0,
            status=vehicle.status or "normal",
        )

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        """Find the nearest station to the given coordinates."""
        stations = self._db.query(BusStation).all()
        
        if not stations:
            raise ResourceNotFoundError("没有找到任何站点")
        
        nearest_station = min(
            stations,
            key=lambda station: self._haversine_meters(
                longitude,
                latitude,
                float(station.longitude) if station.longitude else 0.0,
                float(station.latitude) if station.latitude else 0.0,
            ),
        )
        
        return StationData(
            station_id=int(nearest_station.station_id),
            station_name=nearest_station.station_name,
            longitude=float(nearest_station.longitude) if nearest_station.longitude else 0.0,
            latitude=float(nearest_station.latitude) if nearest_station.latitude else 0.0,
        )

    async def get_distance_to_station_meters(
        self, vehicle_id: int, target_station_id: int
    ) -> float:
        """Calculate distance from vehicle to target station using Haversine formula.
        
        Strategy:
        1. Get vehicle's current position from BusVehicle table
        2. Get target station's position from BusStation table
        3. Calculate straight-line distance using Haversine formula
        """
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        station = self._db.query(BusStation).filter(BusStation.station_id == target_station_id).first()
        if station is None:
            raise ResourceNotFoundError(f"站点不存在：station_id={target_station_id}")
        
        vehicle_lon = float(vehicle.current_longitude) if vehicle.current_longitude else 0.0
        vehicle_lat = float(vehicle.current_latitude) if vehicle.current_latitude else 0.0
        station_lon = float(station.longitude)
        station_lat = float(station.latitude)
        
        return self._haversine_meters(vehicle_lon, vehicle_lat, station_lon, station_lat)

    async def get_remaining_stop_count(
        self, vehicle_id: int, target_station_id: int
    ) -> int:
        """Calculate remaining stop count from vehicle's current position to target station.
        
        Strategy (minimal realistic version):
        1. Get vehicle's current station and line from BusVehicle table
        2. Get all stations on the line from LineStation table, ordered by sequence
        3. Find current station's position in the sequence
        4. Find target station's position in the sequence
        5. Return the difference (positive if target is ahead, else 0)
        
        If current_station_id is not set, we estimate based on next_station_id.
        """
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        line_id = vehicle.line_id
        
        line_stations = (
            self._db.query(LineStation)
            .filter(LineStation.line_id == line_id)
            .order_by(LineStation.order_index)
            .all()
        )
        
        if not line_stations:
            return 1
        
        station_index_map = {ls.station_id: ls.order_index for ls in line_stations}
        
        current_index = None
        if vehicle.current_station_id and vehicle.current_station_id in station_index_map:
            current_index = station_index_map[vehicle.current_station_id]
        elif vehicle.next_station_id and vehicle.next_station_id in station_index_map:
            current_index = station_index_map[vehicle.next_station_id] - 1
        
        if target_station_id not in station_index_map:
            return 1
        
        target_index = station_index_map[target_station_id]
        
        if current_index is None:
            return max(1, len(line_stations) // 2)
        
        remaining = target_index - current_index
        
        return max(1, remaining) if remaining > 0 else 1

    async def get_latest_eta_status(
        self,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None = None,
    ) -> None:
        return None

    async def get_latest_load_status(
        self,
        line_id: int,
        station_id: int,
        vehicle_id: int | None = None,
    ) -> None:
        return None

    async def get_station_flow_level(self, station_id: int, hour: int) -> str:
        raise NotImplementedError("Not implemented")

    async def get_candidate_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer_count: int,
    ) -> list:
        raise NotImplementedError("Not implemented")

    @staticmethod
    def _haversine_meters(
        longitude_1: float,
        latitude_1: float,
        longitude_2: float,
        latitude_2: float,
    ) -> float:
        """Calculate the Haversine distance between two points in meters."""
        earth_radius = 6_371_000.0
        lon_1, lat_1, lon_2, lat_2 = map(
            radians,
            (longitude_1, latitude_1, longitude_2, latitude_2),
        )
        delta_lon = lon_2 - lon_1
        delta_lat = lat_2 - lat_1
        value = (
            sin(delta_lat / 2) ** 2
            + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        )
        return 2 * earth_radius * asin(sqrt(value))