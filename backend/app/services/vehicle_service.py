from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.cache import memory_cache_provider
from app.cache.cache_keys import vehicle_list
from app.models.bus_line import BusLine, BusStation
from app.models.bus_vehicle import BusVehicle
from app.schemas.vehicle_schema import (
    BusVehicleDTO,
    VehicleCreateRequest,
    VehicleListResponse,
    VehicleUpdateRequest,
)
from app.services.id_service import next_numeric_id


VEHICLE_LIST_CACHE_TTL_SECONDS = 10


def _invalidate_vehicle_cache() -> None:
    memory_cache_provider.delete_prefix("vehicles:list:")


def _as_float(value, default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _calculate_load_rate(vehicle: BusVehicle) -> float:
    if vehicle.capacity and vehicle.capacity > 0 and vehicle.onboard_count is not None:
        return min(max(float(vehicle.onboard_count) / float(vehicle.capacity), 0.0), 1.0)
    return 0.0


def _derive_load_level(load_rate: float) -> str:
    if load_rate <= 0.55:
        return "seats_available"
    if load_rate <= 0.82:
        return "standing_available"
    return "limited_standing"


def _build_maps(
    db: Session,
    vehicles: list[BusVehicle],
) -> tuple[dict[int, BusLine], dict[int, BusStation]]:
    line_ids = sorted({int(vehicle.line_id) for vehicle in vehicles})
    station_ids = sorted(
        {
            int(value)
            for vehicle in vehicles
            for value in (vehicle.current_station_id, vehicle.next_station_id)
            if value is not None
        }
    )
    lines = db.query(BusLine).filter(BusLine.line_id.in_(line_ids)).all() if line_ids else []
    stations = (
        db.query(BusStation).filter(BusStation.station_id.in_(station_ids)).all()
        if station_ids
        else []
    )
    return (
        {int(line.line_id): line for line in lines},
        {int(station.station_id): station for station in stations},
    )


def _vehicle_dto(
    vehicle: BusVehicle,
    line_map: dict[int, BusLine],
    station_map: dict[int, BusStation],
) -> BusVehicleDTO:
    line = line_map.get(int(vehicle.line_id))
    current_station = (
        station_map.get(int(vehicle.current_station_id))
        if vehicle.current_station_id is not None
        else None
    )
    next_station = (
        station_map.get(int(vehicle.next_station_id)) if vehicle.next_station_id is not None else None
    )
    load_rate = _calculate_load_rate(vehicle)
    reported_at = vehicle.last_updated_at or vehicle.updated_at or vehicle.created_at
    return BusVehicleDTO(
        vehicle_id=int(vehicle.vehicle_id),
        vehicle_code=vehicle.vehicle_code,
        line_id=int(vehicle.line_id),
        service_no=vehicle.service_no or (line.line_code if line else None),
        line_name=vehicle.line_name or (line.line_name if line else None),
        current_latitude=_as_float(vehicle.current_latitude),
        current_longitude=_as_float(vehicle.current_longitude),
        latitude=_as_float(vehicle.current_latitude),
        longitude=_as_float(vehicle.current_longitude),
        current_station_id=(
            int(vehicle.current_station_id) if vehicle.current_station_id is not None else None
        ),
        current_station_name=current_station.station_name if current_station else None,
        next_station_id=int(vehicle.next_station_id) if vehicle.next_station_id is not None else None,
        next_station_name=vehicle.next_station_name or (next_station.station_name if next_station else None),
        current_position_text=vehicle.current_position_text,
        progress=0.0,
        status=vehicle.status,
        operation_status=vehicle.status,
        speed_kmh=_as_float(vehicle.speed_kmh),
        speed_kph=_as_float(vehicle.speed_kmh),
        speed=_as_float(vehicle.speed_kmh),
        direction_deg=0.0,
        onboard_count=int(vehicle.onboard_count or 0),
        capacity=int(vehicle.capacity or 0),
        load_level=vehicle.load_level,
        load_code=vehicle.load_code,
        load_score=_as_float(vehicle.load_score) if vehicle.load_score is not None else None,
        load_rate=round(load_rate, 4),
        load_percent=round(load_rate * 100, 2),
        delay_minutes=int(vehicle.delay_minutes or 0),
        data_status=vehicle.data_status,
        last_updated_at=reported_at,
        last_reported_at=vehicle.last_updated_at,
        update_time=reported_at.isoformat() if reported_at else "",
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
    )


def get_vehicle_list(
    db: Session,
    page: int = 1,
    limit: int = 20,
    line_id: Optional[int] = None,
) -> VehicleListResponse:
    cache_key = vehicle_list(page, limit, line_id)
    cached = memory_cache_provider.get(cache_key)
    if isinstance(cached, VehicleListResponse):
        return cached

    query = db.query(BusVehicle)
    if line_id is not None:
        query = query.filter(BusVehicle.line_id == line_id)
    total = query.count()
    vehicles = (
        query.order_by(BusVehicle.vehicle_code, BusVehicle.vehicle_id)
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    line_map, station_map = _build_maps(db, vehicles)
    result = VehicleListResponse(
        vehicles=[_vehicle_dto(vehicle, line_map, station_map) for vehicle in vehicles],
        total=total,
    )
    memory_cache_provider.set(cache_key, result, ttl_seconds=VEHICLE_LIST_CACHE_TTL_SECONDS)
    return result


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Optional[BusVehicleDTO]:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return None
    line_map, station_map = _build_maps(db, [vehicle])
    return _vehicle_dto(vehicle, line_map, station_map)


def _get_station(db: Session, station_id: int | None, label: str) -> BusStation | None:
    if station_id is None:
        return None
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if station is None:
        raise ValueError(f"{label} station not found")
    return station


def create_vehicle(db: Session, request: VehicleCreateRequest) -> BusVehicleDTO:
    line = db.query(BusLine).filter(BusLine.line_id == request.line_id).first()
    if not line:
        raise ValueError("Line not found")

    vehicle_id = request.vehicle_id or next_numeric_id(db, BusVehicle.vehicle_id)
    if db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first():
        raise ValueError("Vehicle id already exists")

    vehicle_code = request.vehicle_code or f"V{vehicle_id}"
    if db.query(BusVehicle).filter(BusVehicle.vehicle_code == vehicle_code).first():
        raise ValueError("Vehicle code already exists")

    current_station = _get_station(db, request.current_station_id, "Current")
    next_station = _get_station(db, request.next_station_id, "Next")
    onboard_count = request.onboard_count if request.onboard_count is not None else 0
    capacity = request.capacity if request.capacity is not None else 60
    load_rate = min(max(onboard_count / capacity, 0.0), 1.0) if capacity else 0.0

    vehicle = BusVehicle(
        vehicle_id=vehicle_id,
        vehicle_code=vehicle_code,
        line_id=request.line_id,
        service_no=line.line_code,
        line_name=line.line_name,
        current_station_id=request.current_station_id,
        next_station_id=request.next_station_id,
        next_station_name=request.next_station_name or (next_station.station_name if next_station else None),
        current_position_text=request.current_position_text,
        current_latitude=request.current_latitude,
        current_longitude=request.current_longitude,
        speed_kmh=request.speed_kmh,
        onboard_count=onboard_count,
        capacity=capacity,
        load_level=request.load_level or _derive_load_level(load_rate),
        load_code=request.load_code,
        load_score=request.load_score,
        status=request.status,
        delay_minutes=request.delay_minutes,
        data_status=request.data_status,
        last_updated_at=datetime.now(),
    )
    if not vehicle.current_position_text and current_station and next_station:
        vehicle.current_position_text = f"{current_station.station_name} → {next_station.station_name}"

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    _invalidate_vehicle_cache()
    line_map, station_map = _build_maps(db, [vehicle])
    return _vehicle_dto(vehicle, line_map, station_map)


def update_vehicle(
    db: Session,
    vehicle_id: int,
    request: VehicleUpdateRequest,
) -> Optional[BusVehicleDTO]:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return None

    values = request.model_dump(exclude_unset=True)
    if "current_station_id" in values:
        _get_station(db, values["current_station_id"], "Current")
        vehicle.current_station_id = values["current_station_id"]
    if "next_station_id" in values:
        next_station = _get_station(db, values["next_station_id"], "Next")
        vehicle.next_station_id = values["next_station_id"]
        if "next_station_name" not in values:
            vehicle.next_station_name = next_station.station_name if next_station else None

    mapping = {
        "current_latitude": "current_latitude",
        "current_longitude": "current_longitude",
        "next_station_name": "next_station_name",
        "current_position_text": "current_position_text",
        "status": "status",
        "speed_kmh": "speed_kmh",
        "onboard_count": "onboard_count",
        "capacity": "capacity",
        "load_level": "load_level",
        "load_code": "load_code",
        "load_score": "load_score",
        "delay_minutes": "delay_minutes",
        "data_status": "data_status",
    }
    for request_name, model_name in mapping.items():
        if request_name in values and values[request_name] is not None:
            setattr(vehicle, model_name, values[request_name])

    if ("onboard_count" in values or "capacity" in values) and "load_level" not in values:
        vehicle.load_level = _derive_load_level(_calculate_load_rate(vehicle))
    vehicle.last_updated_at = datetime.now()

    db.commit()
    db.refresh(vehicle)
    _invalidate_vehicle_cache()
    line_map, station_map = _build_maps(db, [vehicle])
    return _vehicle_dto(vehicle, line_map, station_map)


def delete_vehicle(db: Session, vehicle_id: int) -> bool:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return False
    db.delete(vehicle)
    db.commit()
    _invalidate_vehicle_cache()
    return True


def get_vehicles_by_line(db: Session, line_id: int) -> List[BusVehicleDTO]:
    return get_vehicle_list(db, page=1, limit=100, line_id=line_id).vehicles
