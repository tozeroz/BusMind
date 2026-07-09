from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.bus_vehicle import BusVehicle
from app.models.bus_line import BusLine, BusStation
from app.schemas.vehicle_schema import (
    BusVehicleDTO,
    VehicleListResponse,
    VehicleCreateRequest,
    VehicleUpdateRequest
)

def get_vehicle_list(db: Session, page: int = 1, limit: int = 20, line_id: Optional[int] = None) -> VehicleListResponse:
    offset = (page - 1) * limit
    query = db.query(BusVehicle)
    
    if line_id:
        query = query.filter(BusVehicle.line_id == line_id)
    
    vehicles = query.order_by(BusVehicle.vehicle_code).offset(offset).limit(limit).all()
    total = query.count()
    
    vehicle_dtos = []
    for vehicle in vehicles:
        line = db.query(BusLine).filter(BusLine.line_id == vehicle.line_id).first()
        current_station = db.query(BusStation).filter(BusStation.station_id == vehicle.current_station_id).first()
        next_station = db.query(BusStation).filter(BusStation.station_id == vehicle.next_station_id).first()
        
        load_rate = (vehicle.onboard_count / vehicle.capacity) * 100 if vehicle.capacity > 0 else 0.0
        
        vehicle_dtos.append(BusVehicleDTO(
            vehicle_id=vehicle.vehicle_id,
            vehicle_code=vehicle.vehicle_code,
            line_id=vehicle.line_id,
            line_name=line.line_name if line else None,
            current_latitude=vehicle.current_latitude or 0.0,
            current_longitude=vehicle.current_longitude or 0.0,
            latitude=vehicle.current_latitude or 0.0,
            longitude=vehicle.current_longitude or 0.0,
            current_station_id=vehicle.current_station_id,
            current_station_name=current_station.station_name if current_station else None,
            next_station_id=vehicle.next_station_id,
            next_station_name=next_station.station_name if next_station else None,
            progress=vehicle.progress or 0.0,
            status=vehicle.status,
            speed_kmh=vehicle.speed_kmh or 0.0,
            speed=vehicle.speed_kmh or 0.0,
            direction_deg=vehicle.direction_deg or 0.0,
            onboard_count=vehicle.onboard_count or 0,
            capacity=vehicle.capacity or 60,
            load_rate=round(load_rate, 2),
            last_updated_at=vehicle.last_updated_at,
            update_time=vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else "",
            created_at=vehicle.created_at
        ))
    
    return VehicleListResponse(vehicles=vehicle_dtos, total=total)

def get_vehicle_by_id(db: Session, vehicle_id: int) -> Optional[BusVehicleDTO]:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return None
    
    line = db.query(BusLine).filter(BusLine.line_id == vehicle.line_id).first()
    current_station = db.query(BusStation).filter(BusStation.station_id == vehicle.current_station_id).first()
    next_station = db.query(BusStation).filter(BusStation.station_id == vehicle.next_station_id).first()
    
    load_rate = (vehicle.onboard_count / vehicle.capacity) * 100 if vehicle.capacity > 0 else 0.0
    
    return BusVehicleDTO(
        vehicle_id=vehicle.vehicle_id,
        vehicle_code=vehicle.vehicle_code,
        line_id=vehicle.line_id,
        line_name=line.line_name if line else None,
        current_latitude=vehicle.current_latitude or 0.0,
        current_longitude=vehicle.current_longitude or 0.0,
        latitude=vehicle.current_latitude or 0.0,
        longitude=vehicle.current_longitude or 0.0,
        current_station_id=vehicle.current_station_id,
        current_station_name=current_station.station_name if current_station else None,
        next_station_id=vehicle.next_station_id,
        next_station_name=next_station.station_name if next_station else None,
        progress=vehicle.progress or 0.0,
        status=vehicle.status,
        speed_kmh=vehicle.speed_kmh or 0.0,
        speed=vehicle.speed_kmh or 0.0,
        direction_deg=vehicle.direction_deg or 0.0,
        onboard_count=vehicle.onboard_count or 0,
        capacity=vehicle.capacity or 60,
        load_rate=round(load_rate, 2),
        last_updated_at=vehicle.last_updated_at,
        update_time=vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else "",
        created_at=vehicle.created_at
    )

def create_vehicle(db: Session, request: VehicleCreateRequest) -> BusVehicleDTO:
    existing_vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_code == request.vehicle_code).first()
    if existing_vehicle:
        raise ValueError("Vehicle code already exists")
    
    line = db.query(BusLine).filter(BusLine.line_id == request.line_id).first()
    if not line:
        raise ValueError("Line not found")
    
    new_vehicle = BusVehicle(
        vehicle_code=request.vehicle_code,
        line_id=request.line_id,
        current_latitude=request.current_latitude,
        current_longitude=request.current_longitude,
        current_station_id=request.current_station_id,
        next_station_id=request.next_station_id,
        progress=request.progress or 0.0,
        status=request.status or "running",
        speed_kmh=request.speed_kmh or 0.0,
        direction_deg=request.direction_deg or 0.0,
        onboard_count=request.onboard_count or 0,
        capacity=request.capacity or 60
    )
    
    db.add(new_vehicle)
    db.commit()
    db.refresh(new_vehicle)
    
    current_station = db.query(BusStation).filter(BusStation.station_id == new_vehicle.current_station_id).first()
    next_station = db.query(BusStation).filter(BusStation.station_id == new_vehicle.next_station_id).first()
    load_rate = (new_vehicle.onboard_count / new_vehicle.capacity) * 100 if new_vehicle.capacity > 0 else 0.0
    
    return BusVehicleDTO(
        vehicle_id=new_vehicle.vehicle_id,
        vehicle_code=new_vehicle.vehicle_code,
        line_id=new_vehicle.line_id,
        line_name=line.line_name,
        current_latitude=new_vehicle.current_latitude or 0.0,
        current_longitude=new_vehicle.current_longitude or 0.0,
        latitude=new_vehicle.current_latitude or 0.0,
        longitude=new_vehicle.current_longitude or 0.0,
        current_station_id=new_vehicle.current_station_id,
        current_station_name=current_station.station_name if current_station else None,
        next_station_id=new_vehicle.next_station_id,
        next_station_name=next_station.station_name if next_station else None,
        progress=new_vehicle.progress or 0.0,
        status=new_vehicle.status,
        speed_kmh=new_vehicle.speed_kmh or 0.0,
        speed=new_vehicle.speed_kmh or 0.0,
        direction_deg=new_vehicle.direction_deg or 0.0,
        onboard_count=new_vehicle.onboard_count or 0,
        capacity=new_vehicle.capacity or 60,
        load_rate=round(load_rate, 2),
        last_updated_at=new_vehicle.last_updated_at,
        update_time=new_vehicle.last_updated_at.isoformat() if new_vehicle.last_updated_at else "",
        created_at=new_vehicle.created_at
    )

def update_vehicle(db: Session, vehicle_id: int, request: VehicleUpdateRequest) -> Optional[BusVehicleDTO]:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return None
    
    if request.current_latitude is not None:
        vehicle.current_latitude = request.current_latitude
    if request.current_longitude is not None:
        vehicle.current_longitude = request.current_longitude
    if request.current_station_id is not None:
        vehicle.current_station_id = request.current_station_id
    if request.next_station_id is not None:
        vehicle.next_station_id = request.next_station_id
    if request.progress is not None:
        vehicle.progress = request.progress
    if request.status is not None:
        vehicle.status = request.status
    if request.speed_kmh is not None:
        vehicle.speed_kmh = request.speed_kmh
    if request.direction_deg is not None:
        vehicle.direction_deg = request.direction_deg
    if request.onboard_count is not None:
        vehicle.onboard_count = request.onboard_count
    
    db.commit()
    db.refresh(vehicle)
    
    line = db.query(BusLine).filter(BusLine.line_id == vehicle.line_id).first()
    current_station = db.query(BusStation).filter(BusStation.station_id == vehicle.current_station_id).first()
    next_station = db.query(BusStation).filter(BusStation.station_id == vehicle.next_station_id).first()
    load_rate = (vehicle.onboard_count / vehicle.capacity) * 100 if vehicle.capacity > 0 else 0.0
    
    return BusVehicleDTO(
        vehicle_id=vehicle.vehicle_id,
        vehicle_code=vehicle.vehicle_code,
        line_id=vehicle.line_id,
        line_name=line.line_name if line else None,
        current_latitude=vehicle.current_latitude or 0.0,
        current_longitude=vehicle.current_longitude or 0.0,
        latitude=vehicle.current_latitude or 0.0,
        longitude=vehicle.current_longitude or 0.0,
        current_station_id=vehicle.current_station_id,
        current_station_name=current_station.station_name if current_station else None,
        next_station_id=vehicle.next_station_id,
        next_station_name=next_station.station_name if next_station else None,
        progress=vehicle.progress or 0.0,
        status=vehicle.status,
        speed_kmh=vehicle.speed_kmh or 0.0,
        speed=vehicle.speed_kmh or 0.0,
        direction_deg=vehicle.direction_deg or 0.0,
        onboard_count=vehicle.onboard_count or 0,
        capacity=vehicle.capacity or 60,
        load_rate=round(load_rate, 2),
        last_updated_at=vehicle.last_updated_at,
        update_time=vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else "",
        created_at=vehicle.created_at
    )

def delete_vehicle(db: Session, vehicle_id: int) -> bool:
    vehicle = db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
    if not vehicle:
        return False
    
    db.delete(vehicle)
    db.commit()
    return True

def get_vehicles_by_line(db: Session, line_id: int) -> List[BusVehicleDTO]:
    vehicles = db.query(BusVehicle).filter(BusVehicle.line_id == line_id).all()
    
    vehicle_dtos = []
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    
    for vehicle in vehicles:
        current_station = db.query(BusStation).filter(BusStation.station_id == vehicle.current_station_id).first()
        next_station = db.query(BusStation).filter(BusStation.station_id == vehicle.next_station_id).first()
        load_rate = (vehicle.onboard_count / vehicle.capacity) * 100 if vehicle.capacity > 0 else 0.0
        
        vehicle_dtos.append(BusVehicleDTO(
            vehicle_id=vehicle.vehicle_id,
            vehicle_code=vehicle.vehicle_code,
            line_id=vehicle.line_id,
            line_name=line.line_name if line else None,
            current_latitude=vehicle.current_latitude or 0.0,
            current_longitude=vehicle.current_longitude or 0.0,
            latitude=vehicle.current_latitude or 0.0,
            longitude=vehicle.current_longitude or 0.0,
            current_station_id=vehicle.current_station_id,
            current_station_name=current_station.station_name if current_station else None,
            next_station_id=vehicle.next_station_id,
            next_station_name=next_station.station_name if next_station else None,
            progress=vehicle.progress or 0.0,
            status=vehicle.status,
            speed_kmh=vehicle.speed_kmh or 0.0,
            speed=vehicle.speed_kmh or 0.0,
            direction_deg=vehicle.direction_deg or 0.0,
            onboard_count=vehicle.onboard_count or 0,
            capacity=vehicle.capacity or 60,
            load_rate=round(load_rate, 2),
            last_updated_at=vehicle.last_updated_at,
            update_time=vehicle.last_updated_at.isoformat() if vehicle.last_updated_at else "",
            created_at=vehicle.created_at
        ))
    
    return vehicle_dtos