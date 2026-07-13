from __future__ import annotations

from datetime import time
import math
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.bus_line import BusLine, BusStation, LineStation
from app.schemas.bus_schema import (
    BusLineCreateRequest,
    BusLineDTO,
    BusLineUpdateRequest,
    BusLineWithStationsDTO,
    BusStationCreateRequest,
    BusStationDTO,
    BusStationUpdateRequest,
    LineListResponse,
    LineStationCreateRequest,
    LineStationDTO,
    LineStationUpdateRequest,
    NearbyStationDTO,
    NearbyStationResponse,
    StationLinesResponse,
    StationListResponse,
)
from app.services.id_service import next_numeric_id, station_id_from_code


def _as_float(value, default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _parse_time(value: str | time | None) -> time | None:
    if value is None or isinstance(value, time):
        return value
    text = value.strip()
    if not text:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            from datetime import datetime

            return datetime.strptime(text, fmt).time()
        except ValueError:
            continue
    raise ValueError(f"Invalid time value: {value}")


def _station_dto(station: BusStation) -> BusStationDTO:
    return BusStationDTO(
        station_id=int(station.station_id),
        station_name=station.station_name,
        station_code=station.station_code or "",
        bus_stop_code=station.station_code,
        latitude=_as_float(station.latitude),
        longitude=_as_float(station.longitude),
        address=station.address,
        road_name=station.address,
        zone=None,
        status=station.status,
        created_at=station.created_at,
        updated_at=station.updated_at,
    )


def _station_map_by_ids(db: Session, station_ids: list[int | None]) -> dict[int, BusStation]:
    ids = sorted({int(value) for value in station_ids if value is not None})
    if not ids:
        return {}
    rows = db.query(BusStation).filter(BusStation.station_id.in_(ids)).all()
    return {int(row.station_id): row for row in rows}


def _station_map_by_codes(db: Session, station_codes: list[str | None]) -> dict[str, BusStation]:
    codes = sorted({str(value) for value in station_codes if value})
    if not codes:
        return {}
    rows = db.query(BusStation).filter(BusStation.station_code.in_(codes)).all()
    return {str(row.station_code): row for row in rows if row.station_code}


def _line_terminal_names(
    line: BusLine,
    station_by_id: dict[int, BusStation],
    station_by_code: dict[str, BusStation],
) -> tuple[str, str]:
    origin = station_by_id.get(int(line.origin_station_id)) if line.origin_station_id is not None else None
    destination = (
        station_by_id.get(int(line.destination_station_id))
        if line.destination_station_id is not None
        else None
    )
    if origin is None and line.start_station:
        origin = station_by_code.get(line.start_station)
    if destination is None and line.end_station:
        destination = station_by_code.get(line.end_station)
    return (
        origin.station_name if origin else (line.start_station or ""),
        destination.station_name if destination else (line.end_station or ""),
    )


def _build_line_dto(
    line: BusLine,
    station_by_id: dict[int, BusStation] | None = None,
    station_by_code: dict[str, BusStation] | None = None,
) -> BusLineDTO:
    station_by_id = station_by_id or {}
    station_by_code = station_by_code or {}
    start_name, end_name = _line_terminal_names(line, station_by_id, station_by_code)
    return BusLineDTO(
        line_id=int(line.line_id),
        line_name=line.line_name,
        line_code=line.line_code,
        service_no=line.line_code,
        operator=line.operator,
        direction=int(line.raw_direction or 1),
        start_station=start_name,
        end_station=end_name,
        origin_station_id=int(line.origin_station_id) if line.origin_station_id is not None else None,
        destination_station_id=(
            int(line.destination_station_id) if line.destination_station_id is not None else None
        ),
        total_stations=line.total_stations,
        distance_km=line.distance_km,
        first_departure_time=line.first_departure_time,
        last_departure_time=line.last_departure_time,
        interval_minutes=line.interval_minutes,
        am_peak_freq=line.am_peak_freq,
        am_offpeak_freq=line.am_offpeak_freq,
        pm_peak_freq=line.pm_peak_freq,
        pm_offpeak_freq=line.pm_offpeak_freq,
        status=line.status,
        created_at=line.created_at,
        updated_at=line.updated_at,
    )


def _line_station_dto(item: LineStation, station: BusStation) -> LineStationDTO:
    return LineStationDTO(
        id=str(item.id),
        line_station_id=str(item.id),
        line_id=int(item.line_id),
        station_id=int(item.station_id),
        order_index=item.order_index,
        stop_sequence=item.order_index,
        direction=item.direction,
        service_no=item.service_no,
        line_name=item.line_name,
        operator=item.operator,
        route_distance_km=_as_float(item.route_distance_km) if item.route_distance_km is not None else None,
        station=_station_dto(station),
    )


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


def _bounding_box(latitude: float, longitude: float, radius_km: float) -> tuple[float, float, float, float]:
    lat_delta = radius_km / 111.32
    cos_lat = max(math.cos(math.radians(latitude)), 0.01)
    lon_delta = radius_km / (111.32 * cos_lat)
    return (
        latitude - lat_delta,
        latitude + lat_delta,
        longitude - lon_delta,
        longitude + lon_delta,
    )


def get_line_list(
    db: Session,
    page: int = 1,
    limit: int = 20,
    line_name: Optional[str] = None,
) -> LineListResponse:
    query = db.query(BusLine)
    if line_name:
        query = query.filter(BusLine.line_name.like(f"%{line_name}%"))
    total = query.count()
    lines = (
        query.order_by(BusLine.line_code, BusLine.raw_direction)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    station_by_id = _station_map_by_ids(
        db,
        [value for line in lines for value in (line.origin_station_id, line.destination_station_id)],
    )
    station_by_code = _station_map_by_codes(
        db,
        [value for line in lines for value in (line.start_station, line.end_station)],
    )
    return LineListResponse(
        lines=[_build_line_dto(line, station_by_id, station_by_code) for line in lines],
        total=total,
    )


def get_line_by_id(db: Session, line_id: int) -> Optional[BusLineWithStationsDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return None
    line_stations = (
        db.query(LineStation)
        .filter(LineStation.line_id == line_id)
        .order_by(LineStation.order_index)
        .all()
    )
    station_map = _station_map_by_ids(db, [item.station_id for item in line_stations])
    terminal_map = _station_map_by_ids(db, [line.origin_station_id, line.destination_station_id])
    code_map = _station_map_by_codes(db, [line.start_station, line.end_station])
    line_dto = _build_line_dto(line, terminal_map, code_map)
    return BusLineWithStationsDTO(
        **line_dto.model_dump(),
        stations=[
            _line_station_dto(item, station_map[int(item.station_id)])
            for item in line_stations
            if int(item.station_id) in station_map
        ],
    )


def create_line(db: Session, request: BusLineCreateRequest) -> BusLineDTO:
    existing = (
        db.query(BusLine)
        .filter(
            BusLine.line_code == request.line_code,
            BusLine.raw_direction == request.direction,
        )
        .first()
    )
    if existing:
        raise ValueError("Line code already exists")

    line_id = request.line_id or next_numeric_id(db, BusLine.line_id)
    if db.query(BusLine).filter(BusLine.line_id == line_id).first():
        raise ValueError("Line id already exists")

    station_map = _station_map_by_ids(db, [request.origin_station_id, request.destination_station_id])
    origin_station = station_map.get(request.origin_station_id) if request.origin_station_id else None
    destination_station = (
        station_map.get(request.destination_station_id) if request.destination_station_id else None
    )

    new_line = BusLine(
        line_id=line_id,
        line_name=request.line_name,
        line_code=request.line_code,
        operator=request.operator,
        raw_direction=request.direction,
        category=request.category,
        origin_station_id=request.origin_station_id,
        start_station=(origin_station.station_code if origin_station else request.start_station) or None,
        destination_station_id=request.destination_station_id,
        end_station=(destination_station.station_code if destination_station else request.end_station) or None,
        am_peak_freq=request.am_peak_freq,
        am_offpeak_freq=request.am_offpeak_freq,
        pm_peak_freq=request.pm_peak_freq,
        pm_offpeak_freq=request.pm_offpeak_freq,
        avg_service_frequency=request.interval_minutes,
        loop_desc=request.loop_desc,
        status=request.status,
    )
    db.add(new_line)
    db.commit()
    db.refresh(new_line)
    return _build_line_dto(
        new_line,
        _station_map_by_ids(db, [new_line.origin_station_id, new_line.destination_station_id]),
        _station_map_by_codes(db, [new_line.start_station, new_line.end_station]),
    )


def update_line(
    db: Session,
    line_id: int,
    request: BusLineUpdateRequest,
) -> Optional[BusLineDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return None

    values = request.model_dump(exclude_unset=True)
    direct_fields = {
        "line_name": "line_name",
        "operator": "operator",
        "direction": "raw_direction",
        "category": "category",
        "origin_station_id": "origin_station_id",
        "destination_station_id": "destination_station_id",
        "start_station": "start_station",
        "end_station": "end_station",
        "am_peak_freq": "am_peak_freq",
        "am_offpeak_freq": "am_offpeak_freq",
        "pm_peak_freq": "pm_peak_freq",
        "pm_offpeak_freq": "pm_offpeak_freq",
        "loop_desc": "loop_desc",
        "status": "status",
    }
    for request_name, model_name in direct_fields.items():
        if request_name in values:
            setattr(line, model_name, values[request_name])
    if "interval_minutes" in values:
        line.avg_service_frequency = values["interval_minutes"]

    # If a terminal station ID is changed, keep the imported-code snapshot in sync.
    if "origin_station_id" in values and values["origin_station_id"] is not None:
        station = db.query(BusStation).filter(BusStation.station_id == values["origin_station_id"]).first()
        if not station:
            raise ValueError("Origin station not found")
        line.start_station = station.station_code
    if "destination_station_id" in values and values["destination_station_id"] is not None:
        station = (
            db.query(BusStation)
            .filter(BusStation.station_id == values["destination_station_id"])
            .first()
        )
        if not station:
            raise ValueError("Destination station not found")
        line.end_station = station.station_code

    db.commit()
    db.refresh(line)
    return _build_line_dto(
        line,
        _station_map_by_ids(db, [line.origin_station_id, line.destination_station_id]),
        _station_map_by_codes(db, [line.start_station, line.end_station]),
    )


def delete_line(db: Session, line_id: int) -> bool:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return False
    db.delete(line)
    db.commit()
    return True


def get_line_stations(db: Session, line_id: int) -> List[LineStationDTO]:
    items = (
        db.query(LineStation)
        .filter(LineStation.line_id == line_id)
        .order_by(LineStation.order_index)
        .all()
    )
    station_map = _station_map_by_ids(db, [item.station_id for item in items])
    return [
        _line_station_dto(item, station_map[int(item.station_id)])
        for item in items
        if int(item.station_id) in station_map
    ]


def get_station_list(
    db: Session,
    page: int = 1,
    limit: int = 20,
    station_name: Optional[str] = None,
) -> StationListResponse:
    query = db.query(BusStation)
    if station_name:
        query = query.filter(BusStation.station_name.like(f"%{station_name}%"))
    total = query.count()
    stations = (
        query.order_by(BusStation.station_code, BusStation.station_id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return StationListResponse(stations=[_station_dto(item) for item in stations], total=total)


def get_station_by_id(db: Session, station_id: int) -> Optional[BusStationDTO]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    return _station_dto(station) if station else None


def create_station(db: Session, request: BusStationCreateRequest) -> BusStationDTO:
    if request.station_code:
        existing = db.query(BusStation).filter(BusStation.station_code == request.station_code).first()
        if existing:
            raise ValueError("Station code already exists")

    station_id = request.station_id or station_id_from_code(request.station_code)
    if station_id is None or db.query(BusStation).filter(BusStation.station_id == station_id).first():
        if request.station_id is not None:
            raise ValueError("Station id already exists")
        station_id = next_numeric_id(db, BusStation.station_id)

    station = BusStation(
        station_id=station_id,
        station_name=request.station_name,
        station_code=request.station_code,
        latitude=request.latitude,
        longitude=request.longitude,
        address=request.address,
        status=request.status,
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return _station_dto(station)


def update_station(
    db: Session,
    station_id: int,
    request: BusStationUpdateRequest,
) -> Optional[BusStationDTO]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return None
    values = request.model_dump(exclude_unset=True)
    code = values.get("station_code", values.get("bus_stop_code"))
    if code is not None:
        duplicate = (
            db.query(BusStation)
            .filter(BusStation.station_code == code, BusStation.station_id != station_id)
            .first()
        )
        if duplicate:
            raise ValueError("Station code already exists")
        station.station_code = code
    if "station_name" in values:
        station.station_name = values["station_name"]
    if "latitude" in values:
        station.latitude = values["latitude"]
    if "longitude" in values:
        station.longitude = values["longitude"]
    if "address" in values or "road_name" in values:
        station.address = values.get("address", values.get("road_name"))
    if "status" in values:
        station.status = values["status"]
    db.commit()
    db.refresh(station)
    return _station_dto(station)


def delete_station(db: Session, station_id: int) -> bool:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return False
    db.delete(station)
    db.commit()
    return True


def add_line_station(db: Session, request: LineStationCreateRequest) -> LineStationDTO:
    line = db.query(BusLine).filter(BusLine.line_id == request.line_id).first()
    if not line:
        raise ValueError("Line not found")
    station = db.query(BusStation).filter(BusStation.station_id == request.station_id).first()
    if not station:
        raise ValueError("Station not found")

    # The final database uniqueness rule is (line_id, stop_sequence). A loop route
    # may legitimately pass the same station more than once.
    existing_sequence = (
        db.query(LineStation)
        .filter(
            LineStation.line_id == request.line_id,
            LineStation.order_index == request.order_index,
        )
        .first()
    )
    if existing_sequence:
        raise ValueError("Station sequence already exists")

    line_station_id = f"{request.line_id}_{request.order_index:03d}"
    if db.query(LineStation).filter(LineStation.id == line_station_id).first():
        raise ValueError("Line station id already exists")

    item = LineStation(
        id=line_station_id,
        line_id=request.line_id,
        service_no=line.line_code,
        line_name=line.line_name,
        operator=line.operator,
        direction=request.direction,
        order_index=request.order_index,
        station_id=request.station_id,
        station_code=station.station_code,
        route_distance_km=request.route_distance_km,
        wd_first_bus=_parse_time(request.wd_first_bus),
        wd_last_bus=_parse_time(request.wd_last_bus),
        sat_first_bus=_parse_time(request.sat_first_bus),
        sat_last_bus=_parse_time(request.sat_last_bus),
        sun_first_bus=_parse_time(request.sun_first_bus),
        sun_last_bus=_parse_time(request.sun_last_bus),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return _line_station_dto(item, station)


def update_line_station(
    db: Session,
    line_station_id: str,
    request: LineStationUpdateRequest,
) -> Optional[LineStationDTO]:
    item = db.query(LineStation).filter(LineStation.id == str(line_station_id)).first()
    if not item:
        return None
    values = request.model_dump(exclude_unset=True)
    if "order_index" in values and values["order_index"] != item.order_index:
        duplicate = (
            db.query(LineStation)
            .filter(
                LineStation.line_id == item.line_id,
                LineStation.order_index == values["order_index"],
                LineStation.id != item.id,
            )
            .first()
        )
        if duplicate:
            raise ValueError("Station sequence already exists")
        item.order_index = values["order_index"]
        item.id = f"{item.line_id}_{item.order_index:03d}"
    if "direction" in values:
        item.direction = values["direction"]
    if "route_distance_km" in values:
        item.route_distance_km = values["route_distance_km"]
    db.commit()
    db.refresh(item)
    station = db.query(BusStation).filter(BusStation.station_id == item.station_id).first()
    return _line_station_dto(item, station) if station else None


def remove_line_station(db: Session, line_station_id: str) -> bool:
    item = db.query(LineStation).filter(LineStation.id == str(line_station_id)).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def get_nearby_stations(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = 1.0,
) -> NearbyStationResponse:
    min_lat, max_lat, min_lon, max_lon = _bounding_box(latitude, longitude, radius_km)
    candidates: list[tuple[BusStation, float]] = []
    query = (
        db.query(BusStation)
        .filter(BusStation.latitude >= min_lat)
        .filter(BusStation.latitude <= max_lat)
        .filter(BusStation.longitude >= min_lon)
        .filter(BusStation.longitude <= max_lon)
    )
    for station in query.all():
        distance = haversine_distance(
            latitude,
            longitude,
            _as_float(station.latitude),
            _as_float(station.longitude),
        )
        if distance <= radius_km:
            candidates.append((station, distance))
    candidates.sort(key=lambda item: item[1])
    return NearbyStationResponse(
        stations=[
            NearbyStationDTO(**_station_dto(station).model_dump(), distance_km=round(distance, 4))
            for station, distance in candidates
        ],
        total=len(candidates),
    )


def get_station_lines(db: Session, station_id: int) -> Optional[StationLinesResponse]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return None
    line_ids = [
        int(value[0])
        for value in db.query(LineStation.line_id).filter(LineStation.station_id == station_id).distinct().all()
    ]
    lines = db.query(BusLine).filter(BusLine.line_id.in_(line_ids)).all() if line_ids else []
    station_by_id = _station_map_by_ids(
        db,
        [value for line in lines for value in (line.origin_station_id, line.destination_station_id)],
    )
    station_by_code = _station_map_by_codes(
        db,
        [value for line in lines for value in (line.start_station, line.end_station)],
    )
    line_dtos = [_build_line_dto(line, station_by_id, station_by_code) for line in lines]
    return StationLinesResponse(
        station_id=int(station.station_id),
        station_name=station.station_name,
        lines=line_dtos,
        total_lines=len(line_dtos),
    )


def get_stations_with_coordinates(db: Session) -> List[BusStationDTO]:
    return [_station_dto(station) for station in db.query(BusStation).all()]
