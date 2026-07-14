from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

from sqlalchemy.orm import Session

from app.cache import memory_cache_provider
from app.cache.cache_keys import bus_arrival_service, bus_arrival_stop
from app.cache.cache_provider import CacheProvider
from app.core.time_utils import now_local
from app.models.bus_vehicle import BusVehicle
from app.repositories.transit_repository import TransitRepository
from app.services.intelligence_gateway import (
    CandidateRouteData,
    DemoIntelligenceGateway,
    EtaStatusData,
    LoadStatusData,
    StationData,
    VehicleData,
)
from app.services.recommend_service.transit_graph import TransitGraphService


_shared_demo_gateway = DemoIntelligenceGateway()


class MySQLTransitGateway:
    """Repository-backed gateway with demo fallback for local Service-B tests."""

    def __init__(
        self,
        db: Session | TransitRepository,
        cache: CacheProvider | None = None,
        fallback: DemoIntelligenceGateway | None = None,
        graph_service: TransitGraphService | None = None,
    ) -> None:
        self.repository = db if isinstance(db, TransitRepository) else TransitRepository(db)
        self.cache = cache or memory_cache_provider
        self.fallback = fallback or _shared_demo_gateway
        self.graph_service = graph_service or TransitGraphService(self.repository)

    async def get_station(self, station_id: int) -> StationData:
        station = self.repository.get_station(station_id)
        if station is None:
            return await self.fallback.get_station(station_id)
        return StationData(
            station_id=int(station.station_id),
            station_name=str(station.station_name),
            longitude=float(station.longitude),
            latitude=float(station.latitude),
        )

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        vehicle = self.repository.get_vehicle(vehicle_id)
        if vehicle is None:
            return await self.fallback.get_vehicle(vehicle_id)
        return _vehicle_data(vehicle)

    async def get_latest_eta_status(
        self,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None = None,
    ) -> EtaStatusData | None:
        vehicle = self.repository.get_vehicle(vehicle_id)
        effective_line_id = line_id or (int(vehicle.line_id) if vehicle else None)
        station = self.repository.get_station(target_station_id)

        cached = self._eta_from_cache(vehicle_id, target_station_id, effective_line_id, station)
        if cached is not None:
            return cached

        latest = self.repository.get_latest_eta(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            line_id=effective_line_id,
        )
        if latest is not None:
            return EtaStatusData(
                vehicle_id=int(latest.vehicle_id),
                line_id=int(latest.line_id),
                target_station_id=int(latest.target_station_id),
                eta_minutes=float(latest.eta_minutes),
                arrival_time=latest.arrival_time
                or latest.query_time + timedelta(minutes=float(latest.eta_minutes)),
                query_time=latest.query_time,
                vehicle_to_stop_distance_m=_optional_float(latest.vehicle_to_stop_distance_m),
                speed_kph=_optional_float(latest.speed_kph),
                confidence=_optional_float(latest.confidence),
                source=str(latest.data_source or "bus_eta_status"),
            )

        recent = self.repository.get_recent_lta_arrival(
            station_id=target_station_id,
            vehicle_id=vehicle_id,
            line_id=effective_line_id,
        )
        if recent is None and station is not None:
            recent = self.repository.get_recent_lta_arrival(
                bus_stop_code=str(getattr(station, "bus_stop_code", "") or ""),
                vehicle_id=vehicle_id,
                line_id=effective_line_id,
            )
        if recent is None or recent.eta_minutes is None:
            return None
        return EtaStatusData(
            vehicle_id=int(recent.vehicle_id or vehicle_id),
            line_id=int(recent.line_id or effective_line_id or 0),
            target_station_id=int(recent.station_id or target_station_id),
            eta_minutes=float(recent.eta_minutes),
            arrival_time=recent.estimated_arrival
            or recent.query_time + timedelta(minutes=float(recent.eta_minutes)),
            query_time=recent.query_time,
            vehicle_to_stop_distance_m=_optional_float(recent.vehicle_to_stop_distance_m),
            speed_kph=_optional_float(recent.speed_kph),
            confidence=None,
            source="lta_bus_arrival",
        )

    async def get_latest_load_status(
        self,
        line_id: int,
        station_id: int,
        vehicle_id: int | None = None,
    ) -> LoadStatusData | None:
        station = self.repository.get_station(station_id)
        cached = self._load_from_cache(line_id, station_id, vehicle_id, station)
        if cached is not None:
            return cached

        latest = self.repository.get_latest_load(
            vehicle_id=vehicle_id,
            station_id=station_id,
            line_id=line_id,
        )
        if latest is not None:
            return LoadStatusData(
                vehicle_id=int(latest.vehicle_id) if latest.vehicle_id is not None else vehicle_id,
                line_id=int(latest.line_id),
                station_id=int(latest.station_id or station_id),
                load_level=str(latest.load_level),
                load_code=str(latest.load_code) if latest.load_code else None,
                load_rate=_optional_float(latest.load_rate),
                load_score=_optional_float(latest.load_score),
                onboard_count=_optional_int(latest.onboard_count),
                capacity=_optional_int(latest.capacity),
                confidence=_optional_float(latest.confidence),
                query_time=latest.query_time,
                source=str(latest.data_source or "bus_load_status"),
            )

        recent = self.repository.get_recent_lta_arrival(
            station_id=station_id,
            vehicle_id=vehicle_id,
            line_id=line_id,
        )
        if recent is None and station is not None:
            recent = self.repository.get_recent_lta_arrival(
                bus_stop_code=str(getattr(station, "bus_stop_code", "") or ""),
                vehicle_id=vehicle_id,
                line_id=line_id,
            )
        if recent is None or not recent.load_level:
            return None
        return LoadStatusData(
            vehicle_id=int(recent.vehicle_id) if recent.vehicle_id is not None else vehicle_id,
            line_id=int(recent.line_id or line_id),
            station_id=int(recent.station_id or station_id),
            load_level=str(recent.load_level),
            load_code=str(recent.load_code) if recent.load_code else None,
            load_rate=_optional_float(recent.load_rate),
            load_score=_optional_float(recent.load_score),
            onboard_count=_optional_int(recent.onboard_count),
            capacity=_optional_int(recent.capacity),
            confidence=None,
            query_time=recent.query_time,
            source="lta_bus_arrival",
        )

    async def get_distance_to_station_meters(self, vehicle_id: int, target_station_id: int) -> float:
        latest_eta = await self.get_latest_eta_status(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
        )
        if latest_eta is not None and latest_eta.vehicle_to_stop_distance_m is not None:
            return latest_eta.vehicle_to_stop_distance_m
        vehicle = await self.get_vehicle(vehicle_id)
        station = await self.get_station(target_station_id)
        if vehicle.longitude == 0.0 and vehicle.latitude == 0.0:
            return 1_000.0
        return max(
            250.0,
            _haversine_meters(
                vehicle.longitude,
                vehicle.latitude,
                station.longitude,
                station.latitude,
            )
            * 1.35,
        )

    async def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        if self.repository.get_vehicle(vehicle_id) is None or self.repository.get_station(target_station_id) is None:
            return await self.fallback.get_remaining_stop_count(vehicle_id, target_station_id)
        return self.repository.get_remaining_stop_count(vehicle_id, target_station_id)

    async def get_station_flow_level(self, station_id: int, hour: int) -> str:
        if self.repository.get_station(station_id) is None:
            return await self.fallback.get_station_flow_level(station_id, hour)
        return self.repository.get_station_flow_level(station_id, hour)

    async def get_station_flow_average(self, station_id: int, hour: int) -> float | None:
        if self.repository.get_station(station_id) is None:
            return await self.fallback.get_station_flow_average(station_id, hour)
        return self.repository.get_station_flow_average(station_id, hour)

    async def get_line_frequency_minutes(self, line_id: int) -> float | None:
        value = self.repository.get_line_frequency_minutes(line_id)
        if value is not None:
            return value
        return await self.fallback.get_line_frequency_minutes(line_id)

    async def get_route_congestion_score(
        self,
        line_id: int,
        start_station_id: int,
        end_station_id: int,
    ) -> float | None:
        value = self.repository.get_route_congestion_score(
            line_id,
            start_station_id,
            end_station_id,
        )
        if value is not None:
            return value
        return await self.fallback.get_route_congestion_score(
            line_id,
            start_station_id,
            end_station_id,
        )

    async def get_candidate_routes(
            self,
            start_station_id: int,
            end_station_id: int,
            max_transfer_count: int,
    ) -> list[CandidateRouteData]:
        graph_results = await self._run_with_lock(
            self.graph_service.find_candidates,
            start_station_id,
            end_station_id,
            max_transfer_count,
        )
        attached = [self._attach_first_line_vehicle(candidate) for candidate in graph_results]
        return [candidate for candidate in attached if candidate.vehicle_id > 0]

    def _attach_first_line_vehicle(self, candidate: CandidateRouteData) -> CandidateRouteData:
        """Fill the graph placeholder vehicle from the candidate's first line."""
        if candidate.vehicle_id or not candidate.line_ids:
            return candidate
        vehicle = self.repository.get_latest_vehicle_for_line(candidate.line_ids[0])
        if vehicle is None:
            return candidate
        return replace(candidate, vehicle_id=int(vehicle.vehicle_id))

    @staticmethod
    async def _run_with_lock(func, /, *args):
        """Run a sync graph call from the async gateway surface.

        Snapshot building and graph search are synchronous and can take long
        enough to starve health checks during route search, so run them off the
        event loop.
        """
        return await asyncio.to_thread(func, *args)

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        station = self.repository.find_nearest_station(longitude, latitude)
        if station is None:
            return await self.fallback.find_nearest_station(longitude, latitude)
        return StationData(
            station_id=int(station.station_id),
            station_name=str(station.station_name),
            longitude=float(station.longitude),
            latitude=float(station.latitude),
        )

    async def update_vehicle_status(
        self,
        vehicle_id: int,
        **changes: object,
    ) -> VehicleData:
        db = self.repository.db
        vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            return await self.fallback.update_vehicle_status(vehicle_id, **changes)

        field_map = {
            "longitude": "longitude",
            "latitude": "latitude",
            "current_station_id": "current_station_id",
            "next_station_id": "next_station_id",
            "speed_kph": "speed_kph",
            "onboard_count": "onboard_count",
            "capacity": "capacity",
            "status": "operation_status",
        }
        for key, value in changes.items():
            target = field_map.get(key)
            if target is not None:
                setattr(vehicle, target, value)
        db.commit()
        db.refresh(vehicle)
        return _vehicle_data(vehicle)

    def _eta_from_cache(
        self,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None,
        station: Any,
    ) -> EtaStatusData | None:
        arrival = self._arrival_from_cache(line_id, station)
        if arrival is None:
            return None
        eta_minutes = _optional_float(_get_value(arrival, "eta_minutes"))
        if eta_minutes is None:
            return None
        query_time = now_local()
        arrival_time = _get_value(arrival, "estimated_arrival") or query_time + timedelta(minutes=eta_minutes)
        return EtaStatusData(
            vehicle_id=vehicle_id,
            line_id=int(line_id or 0),
            target_station_id=target_station_id,
            eta_minutes=eta_minutes,
            arrival_time=arrival_time,
            query_time=query_time,
            vehicle_to_stop_distance_m=None,
            speed_kph=None,
            confidence=None,
            source="cache_bus_arrival",
        )

    def _load_from_cache(
        self,
        line_id: int,
        station_id: int,
        vehicle_id: int | None,
        station: Any,
    ) -> LoadStatusData | None:
        arrival = self._arrival_from_cache(line_id, station)
        if arrival is None:
            return None
        load_code = str(_get_value(arrival, "load_code") or "").strip().upper() or None
        if load_code is None:
            return None
        return LoadStatusData(
            vehicle_id=vehicle_id,
            line_id=line_id,
            station_id=station_id,
            load_level=load_code,
            load_code=load_code,
            load_rate=None,
            load_score=None,
            onboard_count=None,
            capacity=None,
            confidence=None,
            query_time=now_local(),
            source="cache_bus_arrival",
        )

    def _arrival_from_cache(self, line_id: int | None, station: Any) -> Any | None:
        if station is None or not getattr(station, "bus_stop_code", None):
            return None
        bus_stop_code = str(station.bus_stop_code)
        line = None
        get_line = getattr(self.repository, "get_line", None)
        if callable(get_line) and line_id is not None:
            line = get_line(line_id)
        service_no = str(line.service_no) if line is not None and line.service_no else None
        candidates: list[Any] = []
        if service_no:
            candidates.append(self.cache.get(bus_arrival_service(bus_stop_code, service_no)))
        candidates.append(self.cache.get(bus_arrival_stop(bus_stop_code)))
        for candidate in candidates:
            arrival = _pick_arrival(candidate, service_no)
            if arrival is not None:
                return arrival
        return None


def _vehicle_data(vehicle: Any) -> VehicleData:
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


def _pick_arrival(value: Any, service_no: str | None) -> Any | None:
    if value is None:
        return None
    if isinstance(value, list):
        if service_no:
            for item in value:
                if str(_get_value(item, "service_no") or "") == service_no:
                    return item
        return value[0] if value else None
    if isinstance(value, dict) and isinstance(value.get("Services"), list):
        return _pick_arrival(value["Services"], service_no)
    return value


def _get_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _haversine_meters(
    longitude_1: float,
    latitude_1: float,
    longitude_2: float,
    latitude_2: float,
) -> float:
    earth_radius = 6_371_000.0
    lon_1, lat_1, lon_2, lat_2 = map(
        radians,
        (longitude_1, latitude_1, longitude_2, latitude_2),
    )
    delta_lon = lon_2 - lon_1
    delta_lat = lat_2 - lat_1
    value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(value))
