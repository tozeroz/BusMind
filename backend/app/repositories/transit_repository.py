from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.transit import (
    BusEtaStatus,
    BusLine,
    BusLoadStatus,
    BusStation,
    BusVehicle,
    LineStation,
    LtaBusArrival,
    PassengerFlowTrend,
)


@dataclass(frozen=True, slots=True)
class RouteSegmentRecord:
    segment_order: int
    line_id: int
    line_name: str
    boarding_station_id: int
    alighting_station_id: int
    ride_time_minutes: float


@dataclass(frozen=True, slots=True)
class CandidateRouteRecord:
    route_id: str
    vehicle_id: int
    line_ids: tuple[int, ...]
    segments: tuple[RouteSegmentRecord, ...]
    boarding_station_id: int
    alighting_station_id: int
    walk_time_minutes: float
    ride_time_minutes: float
    transfer_count: int


class TransitRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_station(self, station_id: int) -> BusStation | None:
        return self.db.query(BusStation).filter(BusStation.station_id == station_id).first()

    def get_vehicle(self, vehicle_id: int) -> BusVehicle | None:
        return self.db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()

    def get_line(self, line_id: int) -> BusLine | None:
        return self.db.query(BusLine).filter(BusLine.line_id == line_id).first()

    def get_latest_eta(
        self,
        vehicle_id: int | None = None,
        target_station_id: int | None = None,
        line_id: int | None = None,
    ) -> BusEtaStatus | None:
        query = self.db.query(BusEtaStatus)
        if vehicle_id is not None:
            query = query.filter(BusEtaStatus.vehicle_id == vehicle_id)
        if target_station_id is not None:
            query = query.filter(BusEtaStatus.target_station_id == target_station_id)
        if line_id is not None:
            query = query.filter(BusEtaStatus.line_id == line_id)
        return query.order_by(desc(BusEtaStatus.query_time)).first()

    def get_latest_load(
        self,
        vehicle_id: int | None = None,
        station_id: int | None = None,
        line_id: int | None = None,
    ) -> BusLoadStatus | None:
        query = self.db.query(BusLoadStatus)
        if vehicle_id is not None:
            query = query.filter(BusLoadStatus.vehicle_id == vehicle_id)
        if station_id is not None:
            query = query.filter(BusLoadStatus.station_id == station_id)
        if line_id is not None:
            query = query.filter(BusLoadStatus.line_id == line_id)
        return query.order_by(desc(BusLoadStatus.query_time)).first()

    def get_recent_lta_arrival(
        self,
        station_id: int | None = None,
        bus_stop_code: str | None = None,
        service_no: str | None = None,
        vehicle_id: int | None = None,
        line_id: int | None = None,
    ) -> LtaBusArrival | None:
        query = self.db.query(LtaBusArrival)
        if station_id is not None:
            query = query.filter(LtaBusArrival.station_id == station_id)
        if bus_stop_code is not None:
            query = query.filter(LtaBusArrival.bus_stop_code == bus_stop_code)
        if service_no is not None:
            query = query.filter(LtaBusArrival.service_no == service_no)
        if vehicle_id is not None:
            query = query.filter(LtaBusArrival.vehicle_id == vehicle_id)
        if line_id is not None:
            query = query.filter(LtaBusArrival.line_id == line_id)
        return query.order_by(desc(LtaBusArrival.query_time)).first()

    def find_nearest_station(self, longitude: float, latitude: float) -> BusStation | None:
        stations = (
            self.db.query(BusStation)
            .filter(BusStation.status == "active")
            .filter(BusStation.longitude.isnot(None), BusStation.latitude.isnot(None))
            .all()
        )
        if not stations:
            return None
        return min(
            stations,
            key=lambda station: _haversine_meters(
                longitude,
                latitude,
                float(station.longitude),
                float(station.latitude),
            ),
        )

    def get_station_flow_level(self, station_id: int, hour: int) -> str:
        rows = (
            self.db.query(PassengerFlowTrend.flow_level, func.count(PassengerFlowTrend.flow_record_id))
            .filter(PassengerFlowTrend.target_type == "station")
            .filter(PassengerFlowTrend.target_id == station_id)
            .filter(func.extract("hour", PassengerFlowTrend.record_time) == hour)
            .filter(PassengerFlowTrend.flow_level.isnot(None))
            .group_by(PassengerFlowTrend.flow_level)
            .order_by(desc(func.count(PassengerFlowTrend.flow_record_id)))
            .all()
        )
        if rows:
            return str(rows[0][0])
        fallback = (
            self.db.query(PassengerFlowTrend.flow_level)
            .filter(PassengerFlowTrend.target_type == "station")
            .filter(PassengerFlowTrend.target_id == station_id)
            .filter(PassengerFlowTrend.flow_level.isnot(None))
            .order_by(desc(PassengerFlowTrend.record_time))
            .first()
        )
        return str(fallback[0]) if fallback else "medium"

    def get_candidate_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        max_transfer_count: int,
        limit: int = 5,
    ) -> list[CandidateRouteRecord]:
        if start_station_id == end_station_id:
            return []
        routes = self._direct_routes(start_station_id, end_station_id, limit)
        if len(routes) >= limit or max_transfer_count <= 0:
            return routes[:limit]
        routes.extend(
            self._one_transfer_routes(
                start_station_id,
                end_station_id,
                limit=max(0, limit - len(routes)),
                existing_route_ids={route.route_id for route in routes},
            )
        )
        return routes[:limit]

    def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        vehicle = self.get_vehicle(vehicle_id)
        if vehicle is None:
            return 1
        target = self._line_station_for_station(vehicle.line_id, target_station_id)
        if target is None:
            return 1
        current = None
        if vehicle.current_station_id is not None:
            current = self._line_station_for_station(vehicle.line_id, int(vehicle.current_station_id))
        if current is None and vehicle.next_station_id is not None:
            current = self._line_station_for_station(vehicle.line_id, int(vehicle.next_station_id))
        if current is None:
            return 1
        return max(1, int(target.stop_sequence) - int(current.stop_sequence))

    def _direct_routes(self, start_station_id: int, end_station_id: int, limit: int) -> list[CandidateRouteRecord]:
        rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == start_station_id)
            .filter(BusLine.status == "running")
            .order_by(LineStation.line_id, LineStation.stop_sequence)
            .all()
        )
        routes: list[CandidateRouteRecord] = []
        for start, line in rows:
            end = (
                self.db.query(LineStation)
                .filter(LineStation.line_id == start.line_id)
                .filter(LineStation.station_id == end_station_id)
                .filter(LineStation.stop_sequence > start.stop_sequence)
                .order_by(LineStation.stop_sequence)
                .first()
            )
            if end is None:
                continue
            vehicle = self._latest_vehicle_for_line(int(start.line_id))
            if vehicle is None:
                continue
            ride_time = self._ride_time_minutes(start, end, line)
            routes.append(
                CandidateRouteRecord(
                    route_id=f"direct_{start.line_id}_{start_station_id}_{end_station_id}",
                    vehicle_id=int(vehicle.vehicle_id),
                    line_ids=(int(start.line_id),),
                    segments=(
                        RouteSegmentRecord(
                            1,
                            int(start.line_id),
                            str(line.line_name or start.line_name or line.service_no),
                            start_station_id,
                            end_station_id,
                            ride_time,
                        ),
                    ),
                    boarding_station_id=start_station_id,
                    alighting_station_id=end_station_id,
                    walk_time_minutes=4.0,
                    ride_time_minutes=ride_time,
                    transfer_count=0,
                )
            )
            if len(routes) >= limit:
                break
        return routes

    def _one_transfer_routes(
        self,
        start_station_id: int,
        end_station_id: int,
        limit: int,
        existing_route_ids: set[str],
    ) -> list[CandidateRouteRecord]:
        start_rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == start_station_id)
            .filter(BusLine.status == "running")
            .order_by(LineStation.line_id, LineStation.stop_sequence)
            .all()
        )
        end_rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == end_station_id)
            .filter(BusLine.status == "running")
            .order_by(LineStation.line_id, LineStation.stop_sequence)
            .all()
        )
        routes: list[CandidateRouteRecord] = []
        for start, first_line in start_rows:
            first_vehicle = self._latest_vehicle_for_line(int(start.line_id))
            if first_vehicle is None:
                continue
            for end, second_line in end_rows:
                if start.line_id == end.line_id:
                    continue
                if self._latest_vehicle_for_line(int(end.line_id)) is None:
                    continue
                transfer_station_id = self._find_transfer_station(start, end)
                if transfer_station_id is None:
                    continue
                first_end = self._line_station_after(int(start.line_id), transfer_station_id, int(start.stop_sequence))
                second_start = self._line_station_before(int(end.line_id), transfer_station_id, int(end.stop_sequence))
                if first_end is None or second_start is None:
                    continue
                first_ride = self._ride_time_minutes(start, first_end, first_line)
                second_ride = self._ride_time_minutes(second_start, end, second_line)
                route_id = f"transfer_{start.line_id}_{end.line_id}_{start_station_id}_{transfer_station_id}_{end_station_id}"
                if route_id in existing_route_ids:
                    continue
                routes.append(
                    CandidateRouteRecord(
                        route_id=route_id,
                        vehicle_id=int(first_vehicle.vehicle_id),
                        line_ids=(int(start.line_id), int(end.line_id)),
                        segments=(
                            RouteSegmentRecord(1, int(start.line_id), str(first_line.line_name or start.line_name or first_line.service_no), start_station_id, transfer_station_id, first_ride),
                            RouteSegmentRecord(2, int(end.line_id), str(second_line.line_name or end.line_name or second_line.service_no), transfer_station_id, end_station_id, second_ride),
                        ),
                        boarding_station_id=start_station_id,
                        alighting_station_id=end_station_id,
                        walk_time_minutes=6.0,
                        ride_time_minutes=round(first_ride + second_ride, 1),
                        transfer_count=1,
                    )
                )
                if len(routes) >= limit:
                    return routes
        return routes

    def _find_transfer_station(self, start: LineStation, end: LineStation) -> int | None:
        row = (
            self.db.query(LineStation.station_id)
            .filter(LineStation.line_id == start.line_id)
            .filter(LineStation.stop_sequence > start.stop_sequence)
            .filter(
                LineStation.station_id.in_(
                    self.db.query(LineStation.station_id)
                    .filter(LineStation.line_id == end.line_id)
                    .filter(LineStation.stop_sequence < end.stop_sequence)
                )
            )
            .order_by(LineStation.stop_sequence)
            .first()
        )
        return int(row[0]) if row else None

    def _latest_vehicle_for_line(self, line_id: int) -> BusVehicle | None:
        return (
            self.db.query(BusVehicle)
            .filter(BusVehicle.line_id == line_id)
            .filter(BusVehicle.operation_status != "offline")
            .order_by(desc(BusVehicle.last_reported_at), desc(BusVehicle.updated_at))
            .first()
        )

    def _line_station_for_station(self, line_id: int, station_id: int) -> LineStation | None:
        return (
            self.db.query(LineStation)
            .filter(LineStation.line_id == line_id)
            .filter(LineStation.station_id == station_id)
            .order_by(LineStation.stop_sequence)
            .first()
        )

    def _line_station_after(self, line_id: int, station_id: int, after_sequence: int) -> LineStation | None:
        return (
            self.db.query(LineStation)
            .filter(LineStation.line_id == line_id)
            .filter(LineStation.station_id == station_id)
            .filter(LineStation.stop_sequence > after_sequence)
            .order_by(LineStation.stop_sequence)
            .first()
        )

    def _line_station_before(self, line_id: int, station_id: int, before_sequence: int) -> LineStation | None:
        return (
            self.db.query(LineStation)
            .filter(LineStation.line_id == line_id)
            .filter(LineStation.station_id == station_id)
            .filter(LineStation.stop_sequence < before_sequence)
            .order_by(desc(LineStation.stop_sequence))
            .first()
        )

    @staticmethod
    def _ride_time_minutes(start: LineStation, end: LineStation, line: BusLine) -> float:
        if start.route_distance_km is not None and end.route_distance_km is not None:
            distance = max(0.0, float(end.route_distance_km) - float(start.route_distance_km))
            if distance > 0:
                return round(max(3.0, distance / 22.0 * 60.0), 1)
        stop_count = max(1, int(end.stop_sequence) - int(start.stop_sequence))
        base_per_stop = 2.0
        if line.avg_service_frequency is not None:
            base_per_stop = 1.6 if float(line.avg_service_frequency) <= 8 else 2.1
        return round(max(3.0, stop_count * base_per_stop), 1)


def _haversine_meters(longitude_1: float, latitude_1: float, longitude_2: float, latitude_2: float) -> float:
    earth_radius = 6_371_000.0
    lon_1, lat_1, lon_2, lat_2 = map(radians, (longitude_1, latitude_1, longitude_2, latitude_2))
    delta_lon = lon_2 - lon_1
    delta_lat = lat_2 - lat_1
    value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
    return 2 * earth_radius * asin(sqrt(value))

