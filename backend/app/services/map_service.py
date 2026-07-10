from __future__ import annotations

import json
import math
from typing import Any

from sqlalchemy.orm import Session

from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.transit_extra import MapRoadSegment
from app.schemas.map_schema import (
    LineMapBoundsDTO,
    LineMapDataDTO,
    MapLineDTO,
    MapLineResponse,
    MapStationDTO,
    MapStationResponse,
    RoadSegmentDTO,
    RoadSegmentResponse,
)


def _as_float(value, default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _normalize_path(value: Any) -> list[list[float]]:
    if value is None:
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    result: list[list[float]] = []
    for point in value:
        if isinstance(point, (list, tuple)) and len(point) >= 2:
            try:
                result.append([float(point[0]), float(point[1])])
            except (TypeError, ValueError):
                continue
        elif isinstance(point, dict):
            lon = point.get("longitude", point.get("lon"))
            lat = point.get("latitude", point.get("lat"))
            try:
                result.append([float(lon), float(lat)])
            except (TypeError, ValueError):
                continue
    return result


def _station_map_by_ids(db: Session, station_ids: list[int]) -> dict[int, BusStation]:
    ids = sorted(set(station_ids))
    if not ids:
        return {}
    rows = db.query(BusStation).filter(BusStation.station_id.in_(ids)).all()
    return {int(row.station_id): row for row in rows}


def _line_map_by_ids(db: Session, line_ids: list[int]) -> dict[int, BusLine]:
    ids = sorted(set(line_ids))
    if not ids:
        return {}
    rows = db.query(BusLine).filter(BusLine.line_id.in_(ids)).all()
    return {int(row.line_id): row for row in rows}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def get_map_stations(db: Session) -> MapStationResponse:
    stations = db.query(BusStation).all()
    line_stations = (
        db.query(LineStation)
        .order_by(LineStation.line_id, LineStation.order_index)
        .all()
    )
    line_map = _line_map_by_ids(db, [int(item.line_id) for item in line_stations])
    by_station: dict[int, list[LineStation]] = {}
    for item in line_stations:
        by_station.setdefault(int(item.station_id), []).append(item)

    items: list[MapStationDTO] = []
    for station in stations:
        relations = by_station.get(int(station.station_id), [])
        line_ids: list[int] = []
        line_names: list[str] = []
        service_nos: list[str] = []
        for relation in relations:
            line = line_map.get(int(relation.line_id))
            if not line or int(line.line_id) in line_ids:
                continue
            line_ids.append(int(line.line_id))
            line_names.append(line.line_name)
            service_nos.append(line.line_code)
        items.append(
            MapStationDTO(
                station_id=int(station.station_id),
                station_name=station.station_name,
                station_code=station.station_code or "",
                bus_stop_code=station.station_code,
                latitude=_as_float(station.latitude),
                longitude=_as_float(station.longitude),
                address=station.address,
                road_name=station.address,
                zone=None,
                line_ids=line_ids,
                line_names=line_names,
                service_nos=service_nos,
            )
        )
    return MapStationResponse(stations=items, total=len(items))


def _road_segment_dto(segment: MapRoadSegment) -> RoadSegmentDTO:
    path = _normalize_path(segment.path_coordinates)
    if not path:
        path = [
            [_as_float(segment.start_lon), _as_float(segment.start_lat)],
            [_as_float(segment.end_lon), _as_float(segment.end_lat)],
        ]
    distance = _as_float(segment.segment_distance_km)
    flow = _as_float(segment.avg_passenger_flow) if segment.avg_passenger_flow is not None else None
    return RoadSegmentDTO(
        segment_id=segment.segment_id,
        segment_name=segment.segment_name,
        line_id=int(segment.line_id),
        service_no=segment.service_no,
        line_name=segment.line_name or "",
        direction=segment.direction,
        stop_sequence=segment.stop_sequence,
        start_station_id=int(segment.start_station_id),
        start_station_name=segment.start_station_name or "",
        end_station_id=int(segment.end_station_id),
        end_station_name=segment.end_station_name or "",
        path_coordinates=path,
        distance_km=distance,
        segment_distance_km=distance,
        ride_time_minutes=(
            _as_float(segment.ride_time_minutes) if segment.ride_time_minutes is not None else None
        ),
        avg_speed_kph=_as_float(segment.avg_speed_kph) if segment.avg_speed_kph is not None else None,
        delay_minutes=int(segment.delay_minutes or 0),
        passenger_flow=flow,
        avg_passenger_flow=flow,
        flow_level=segment.flow_level,
    )


def _synthesized_road_segments(db: Session) -> list[RoadSegmentDTO]:
    lines = db.query(BusLine).all()
    relations = (
        db.query(LineStation)
        .order_by(LineStation.line_id, LineStation.order_index)
        .all()
    )
    station_map = _station_map_by_ids(db, [int(item.station_id) for item in relations])
    by_line: dict[int, list[LineStation]] = {}
    for item in relations:
        by_line.setdefault(int(item.line_id), []).append(item)

    result: list[RoadSegmentDTO] = []
    for line in lines:
        line_relations = by_line.get(int(line.line_id), [])
        for index in range(len(line_relations) - 1):
            start_relation = line_relations[index]
            end_relation = line_relations[index + 1]
            start = station_map.get(int(start_relation.station_id))
            end = station_map.get(int(end_relation.station_id))
            if not start or not end:
                continue
            distance = haversine_distance(
                _as_float(start.latitude),
                _as_float(start.longitude),
                _as_float(end.latitude),
                _as_float(end.longitude),
            )
            segment_id = f"{line.line_id}_{start_relation.order_index:03d}"
            result.append(
                RoadSegmentDTO(
                    segment_id=segment_id,
                    segment_name=f"{start.station_name} - {end.station_name}",
                    line_id=int(line.line_id),
                    service_no=line.line_code,
                    line_name=line.line_name,
                    direction=int(line.raw_direction or 1),
                    stop_sequence=start_relation.order_index,
                    start_station_id=int(start.station_id),
                    start_station_name=start.station_name,
                    end_station_id=int(end.station_id),
                    end_station_name=end.station_name,
                    path_coordinates=[
                        [_as_float(start.longitude), _as_float(start.latitude)],
                        [_as_float(end.longitude), _as_float(end.latitude)],
                    ],
                    distance_km=round(distance, 4),
                    segment_distance_km=round(distance, 4),
                )
            )
    return result


def get_road_segments(db: Session) -> RoadSegmentResponse:
    rows = db.query(MapRoadSegment).order_by(MapRoadSegment.line_id, MapRoadSegment.stop_sequence).all()
    segments = [_road_segment_dto(row) for row in rows] if rows else _synthesized_road_segments(db)
    return RoadSegmentResponse(segments=segments, total=len(segments))


def get_map_lines(db: Session) -> MapLineResponse:
    lines = db.query(BusLine).order_by(BusLine.line_code, BusLine.raw_direction).all()
    relations = (
        db.query(LineStation)
        .order_by(LineStation.line_id, LineStation.order_index)
        .all()
    )
    station_map = _station_map_by_ids(db, [int(item.station_id) for item in relations])
    by_line: dict[int, list[LineStation]] = {}
    for item in relations:
        by_line.setdefault(int(item.line_id), []).append(item)

    items: list[MapLineDTO] = []
    for line in lines:
        path: list[list[float]] = []
        start_name = ""
        end_name = ""
        for relation in by_line.get(int(line.line_id), []):
            station = station_map.get(int(relation.station_id))
            if not station:
                continue
            if not start_name:
                start_name = station.station_name
            end_name = station.station_name
            path.append([_as_float(station.longitude), _as_float(station.latitude)])
        items.append(
            MapLineDTO(
                line_id=int(line.line_id),
                line_name=line.line_name,
                line_code=line.line_code,
                service_no=line.line_code,
                start_station=start_name or line.start_station or "",
                end_station=end_name or line.end_station or "",
                path_coordinates=path,
            )
        )
    return MapLineResponse(lines=items, total=len(items))


def get_map_stations_by_line(db: Session, line_id: int) -> MapStationResponse:
    relations = (
        db.query(LineStation)
        .filter(LineStation.line_id == line_id)
        .order_by(LineStation.order_index)
        .all()
    )
    station_map = _station_map_by_ids(db, [int(item.station_id) for item in relations])
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    items = []
    for relation in relations:
        station = station_map.get(int(relation.station_id))
        if not station:
            continue
        items.append(
            MapStationDTO(
                station_id=int(station.station_id),
                station_name=station.station_name,
                station_code=station.station_code or "",
                bus_stop_code=station.station_code,
                latitude=_as_float(station.latitude),
                longitude=_as_float(station.longitude),
                address=station.address,
                road_name=station.address,
                zone=None,
                line_ids=[line_id],
                line_names=[line.line_name if line else ""],
                service_nos=[line.line_code if line else ""],
            )
        )
    return MapStationResponse(stations=items, total=len(items))


def get_line_map_data(db: Session, line_id: int, direction: str | None = None) -> LineMapDataDTO | None:
    # Direction is reserved for future use. The current schema stores one ordered
    # station chain per line record, so we ignore it for now while keeping the API stable.
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if line is None:
        return None

    station_response = get_map_stations_by_line(db, line_id)
    stations = station_response.stations
    polyline = [[station.longitude, station.latitude] for station in stations]

    if polyline:
        longitudes = [point[0] for point in polyline]
        latitudes = [point[1] for point in polyline]
        bounds = LineMapBoundsDTO(
            min_latitude=min(latitudes),
            max_latitude=max(latitudes),
            min_longitude=min(longitudes),
            max_longitude=max(longitudes),
        )
    else:
        bounds = LineMapBoundsDTO(
            min_latitude=0.0,
            max_latitude=0.0,
            min_longitude=0.0,
            max_longitude=0.0,
        )

    return LineMapDataDTO(
        line_id=int(line.line_id),
        line_name=line.line_name,
        line_code=line.line_code,
        polyline=polyline,
        stations=stations,
        bounds=bounds,
    )
