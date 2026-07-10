from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import math
from app.models.bus_line import BusLine, BusStation, LineStation
from app.schemas.bus_schema import (
    BusLineDTO,
    BusLineWithStationsDTO,
    BusLineCreateRequest,
    BusLineUpdateRequest,
    BusStationDTO,
    BusStationCreateRequest,
    BusStationUpdateRequest,
    LineStationDTO,
    LineStationCreateRequest,
    LineStationUpdateRequest,
    NearbyStationDTO,
    NearbyStationResponse,
    StationLinesResponse,
    LineListResponse,
    StationListResponse
)


def _station_map_by_ids(db: Session, station_ids: list[int]) -> dict[int, BusStation]:
    if not station_ids:
        return {}
    stations = db.query(BusStation).filter(BusStation.station_id.in_(station_ids)).all()
    return {station.station_id: station for station in stations}


def _station_map_by_codes(db: Session, station_codes: list[str]) -> dict[str, BusStation]:
    normalized_codes = [code for code in station_codes if code]
    if not normalized_codes:
        return {}
    stations = db.query(BusStation).filter(BusStation.station_code.in_(normalized_codes)).all()
    return {station.station_code: station for station in stations}


def _line_terminal_names(
    line: BusLine,
    station_by_code: dict[str, BusStation],
) -> tuple[str, str]:
    start_station = station_by_code.get(line.start_station)
    end_station = station_by_code.get(line.end_station)
    return (
        start_station.station_name if start_station else (line.start_station or ""),
        end_station.station_name if end_station else (line.end_station or ""),
    )


def _build_line_dto(
    line: BusLine,
    station_by_code: dict[str, BusStation],
) -> BusLineDTO:
    start_station_name, end_station_name = _line_terminal_names(line, station_by_code)
    return BusLineDTO(
        line_id=line.line_id,
        line_name=line.line_name,
        line_code=line.line_code,
        start_station=start_station_name,
        end_station=end_station_name,
        total_stations=line.total_stations,
        distance_km=line.distance_km,
        first_departure_time=line.first_departure_time,
        last_departure_time=line.last_departure_time,
        interval_minutes=line.interval_minutes,
        status=line.status,
        created_at=line.created_at
    )

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def get_line_list(db: Session, page: int = 1, limit: int = 20, line_name: Optional[str] = None) -> LineListResponse:
    offset = (page - 1) * limit
    query = db.query(BusLine)
    
    if line_name:
        query = query.filter(BusLine.line_name.like(f"%{line_name}%"))
    
    lines = query.order_by(BusLine.line_code).offset(offset).limit(limit).all()
    total = query.count()

    station_by_code = _station_map_by_codes(
        db,
        [line.start_station for line in lines] + [line.end_station for line in lines],
    )
    line_dtos = [_build_line_dto(line, station_by_code) for line in lines]
    
    return LineListResponse(lines=line_dtos, total=total)

def get_line_by_id(db: Session, line_id: int) -> Optional[BusLineWithStationsDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return None
    
    line_stations = db.query(LineStation).filter(
        LineStation.line_id == line_id
    ).order_by(LineStation.order_index).all()

    station_map = _station_map_by_ids(db, [ls.station_id for ls in line_stations])
    
    station_dtos = []
    for ls in line_stations:
        station = station_map.get(ls.station_id)
        if station:
            station_dtos.append(LineStationDTO(
                id=ls.id,
                line_id=ls.line_id,
                station_id=ls.station_id,
                order_index=ls.order_index,
                direction=ls.direction,
                station=BusStationDTO(
                    station_id=station.station_id,
                    station_name=station.station_name,
                    station_code=station.station_code,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    address=station.address,
                    zone=station.zone,
                    created_at=station.created_at
                )
            ))
    
    station_by_code = _station_map_by_codes(db, [line.start_station, line.end_station])
    line_dto = _build_line_dto(line, station_by_code)

    return BusLineWithStationsDTO(
        **line_dto.model_dump(),
        stations=station_dtos
    )

def create_line(db: Session, request: BusLineCreateRequest) -> BusLineDTO:
    existing_line = db.query(BusLine).filter(BusLine.line_code == request.line_code).first()
    if existing_line:
        raise ValueError("Line code already exists")
    
    new_line = BusLine(
        line_name=request.line_name,
        line_code=request.line_code,
        start_station=request.start_station,
        end_station=request.end_station,
        total_stations=request.total_stations or 0,
        distance_km=request.distance_km or 0.0,
        first_departure_time=request.first_departure_time,
        last_departure_time=request.last_departure_time,
        interval_minutes=request.interval_minutes or 10,
        status=request.status or "active"
    )
    
    db.add(new_line)
    db.commit()
    db.refresh(new_line)
    
    station_by_code = _station_map_by_codes(db, [new_line.start_station, new_line.end_station])
    return _build_line_dto(new_line, station_by_code)

def update_line(db: Session, line_id: int, request: BusLineUpdateRequest) -> Optional[BusLineDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return None
    
    if request.line_name is not None:
        line.line_name = request.line_name
    if request.start_station is not None:
        line.start_station = request.start_station
    if request.end_station is not None:
        line.end_station = request.end_station
    if request.total_stations is not None:
        line.total_stations = request.total_stations
    if request.distance_km is not None:
        line.distance_km = request.distance_km
    if request.first_departure_time is not None:
        line.first_departure_time = request.first_departure_time
    if request.last_departure_time is not None:
        line.last_departure_time = request.last_departure_time
    if request.interval_minutes is not None:
        line.interval_minutes = request.interval_minutes
    if request.status is not None:
        line.status = request.status
    
    db.commit()
    db.refresh(line)
    
    station_by_code = _station_map_by_codes(db, [line.start_station, line.end_station])
    return _build_line_dto(line, station_by_code)

def delete_line(db: Session, line_id: int) -> bool:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return False
    
    db.query(LineStation).filter(LineStation.line_id == line_id).delete()
    db.delete(line)
    db.commit()
    return True

def get_line_stations(db: Session, line_id: int) -> List[LineStationDTO]:
    line_stations = db.query(LineStation).filter(
        LineStation.line_id == line_id
    ).order_by(LineStation.order_index).all()

    station_map = _station_map_by_ids(db, [ls.station_id for ls in line_stations])
    
    station_dtos = []
    for ls in line_stations:
        station = station_map.get(ls.station_id)
        if station:
            station_dtos.append(LineStationDTO(
                id=ls.id,
                line_id=ls.line_id,
                station_id=ls.station_id,
                order_index=ls.order_index,
                direction=ls.direction,
                station=BusStationDTO(
                    station_id=station.station_id,
                    station_name=station.station_name,
                    station_code=station.station_code,
                    latitude=station.latitude,
                    longitude=station.longitude,
                    address=station.address,
                    zone=station.zone,
                    created_at=station.created_at
                )
            ))
    
    return station_dtos

def get_station_list(db: Session, page: int = 1, limit: int = 20, station_name: Optional[str] = None) -> StationListResponse:
    offset = (page - 1) * limit
    query = db.query(BusStation)
    
    if station_name:
        query = query.filter(BusStation.station_name.like(f"%{station_name}%"))
    
    stations = query.order_by(BusStation.station_code).offset(offset).limit(limit).all()
    total = query.count()
    
    station_dtos = [
        BusStationDTO(
            station_id=station.station_id,
            station_name=station.station_name,
            station_code=station.station_code,
            latitude=station.latitude,
            longitude=station.longitude,
            address=station.address,
            zone=station.zone,
            created_at=station.created_at
        ) for station in stations
    ]
    
    return StationListResponse(stations=station_dtos, total=total)

def get_station_by_id(db: Session, station_id: int) -> Optional[BusStationDTO]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return None
    
    return BusStationDTO(
        station_id=station.station_id,
        station_name=station.station_name,
        station_code=station.station_code,
        latitude=station.latitude,
        longitude=station.longitude,
        address=station.address,
        zone=station.zone,
        created_at=station.created_at
    )

def create_station(db: Session, request: BusStationCreateRequest) -> BusStationDTO:
    existing_station = db.query(BusStation).filter(BusStation.station_code == request.station_code).first()
    if existing_station:
        raise ValueError("Station code already exists")
    
    new_station = BusStation(
        station_name=request.station_name,
        station_code=request.station_code,
        latitude=request.latitude,
        longitude=request.longitude,
        address=request.address,
        zone=request.zone
    )
    
    db.add(new_station)
    db.commit()
    db.refresh(new_station)
    
    return BusStationDTO(
        station_id=new_station.station_id,
        station_name=new_station.station_name,
        station_code=new_station.station_code,
        latitude=new_station.latitude,
        longitude=new_station.longitude,
        address=new_station.address,
        zone=new_station.zone,
        created_at=new_station.created_at
    )

def update_station(db: Session, station_id: int, request: BusStationUpdateRequest) -> Optional[BusStationDTO]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return None
    
    if request.station_name is not None:
        station.station_name = request.station_name
    if request.latitude is not None:
        station.latitude = request.latitude
    if request.longitude is not None:
        station.longitude = request.longitude
    if request.address is not None:
        station.address = request.address
    if request.zone is not None:
        station.zone = request.zone
    
    db.commit()
    db.refresh(station)
    
    return BusStationDTO(
        station_id=station.station_id,
        station_name=station.station_name,
        station_code=station.station_code,
        latitude=station.latitude,
        longitude=station.longitude,
        address=station.address,
        zone=station.zone,
        created_at=station.created_at
    )

def delete_station(db: Session, station_id: int) -> bool:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return False
    
    db.query(LineStation).filter(LineStation.station_id == station_id).delete()
    db.delete(station)
    db.commit()
    return True

def add_line_station(db: Session, request: LineStationCreateRequest) -> Optional[LineStationDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == request.line_id).first()
    if not line:
        raise ValueError("Line not found")
    
    station = db.query(BusStation).filter(BusStation.station_id == request.station_id).first()
    if not station:
        raise ValueError("Station not found")
    
    existing = db.query(LineStation).filter(
        LineStation.line_id == request.line_id,
        LineStation.station_id == request.station_id
    ).first()
    if existing:
        raise ValueError("Station already in line")
    
    new_line_station = LineStation(
        line_id=request.line_id,
        station_id=request.station_id,
        order_index=request.order_index,
        direction=request.direction
    )
    
    db.add(new_line_station)
    db.commit()
    db.refresh(new_line_station)
    
    return LineStationDTO(
        id=new_line_station.id,
        line_id=new_line_station.line_id,
        station_id=new_line_station.station_id,
        order_index=new_line_station.order_index,
        direction=new_line_station.direction,
        station=BusStationDTO(
            station_id=station.station_id,
            station_name=station.station_name,
            station_code=station.station_code,
            latitude=station.latitude,
            longitude=station.longitude,
            address=station.address,
            zone=station.zone,
            created_at=station.created_at
        )
    )

def update_line_station(db: Session, line_station_id: int, request: LineStationUpdateRequest) -> Optional[LineStationDTO]:
    line_station = db.query(LineStation).filter(LineStation.id == line_station_id).first()
    if not line_station:
        return None
    
    if request.order_index is not None:
        line_station.order_index = request.order_index
    if request.direction is not None:
        line_station.direction = request.direction
    
    db.commit()
    db.refresh(line_station)
    
    station = db.query(BusStation).filter(BusStation.station_id == line_station.station_id).first()
    
    return LineStationDTO(
        id=line_station.id,
        line_id=line_station.line_id,
        station_id=line_station.station_id,
        order_index=line_station.order_index,
        direction=line_station.direction,
        station=BusStationDTO(
            station_id=station.station_id,
            station_name=station.station_name,
            station_code=station.station_code,
            latitude=station.latitude,
            longitude=station.longitude,
            address=station.address,
            zone=station.zone,
            created_at=station.created_at
        ) if station else None
    )

def remove_line_station(db: Session, line_station_id: int) -> bool:
    line_station = db.query(LineStation).filter(LineStation.id == line_station_id).first()
    if not line_station:
        return False
    
    db.delete(line_station)
    db.commit()
    return True

def get_nearby_stations(db: Session, latitude: float, longitude: float, radius_km: float = 1.0) -> NearbyStationResponse:
    all_stations = db.query(BusStation).all()
    
    nearby_stations = []
    for station in all_stations:
        distance = haversine_distance(latitude, longitude, station.latitude, station.longitude)
        if distance <= radius_km:
            nearby_stations.append({
                'station': station,
                'distance': distance
            })
    
    nearby_stations.sort(key=lambda x: x['distance'])
    
    station_dtos = [
        NearbyStationDTO(
            station_id=s['station'].station_id,
            station_name=s['station'].station_name,
            station_code=s['station'].station_code,
            latitude=s['station'].latitude,
            longitude=s['station'].longitude,
            address=s['station'].address,
            zone=s['station'].zone,
            created_at=s['station'].created_at,
            distance_km=round(s['distance'], 4)
        ) for s in nearby_stations
    ]
    
    return NearbyStationResponse(stations=station_dtos, total=len(station_dtos))

def get_station_lines(db: Session, station_id: int) -> Optional[StationLinesResponse]:
    station = db.query(BusStation).filter(BusStation.station_id == station_id).first()
    if not station:
        return None
    
    line_stations = db.query(LineStation).filter(LineStation.station_id == station_id).all()
    line_ids = [ls.line_id for ls in line_stations]
    
    lines = db.query(BusLine).filter(BusLine.line_id.in_(line_ids)).all()
    
    station_by_code = _station_map_by_codes(
        db,
        [line.start_station for line in lines] + [line.end_station for line in lines],
    )
    line_dtos = [_build_line_dto(line, station_by_code) for line in lines]
    
    return StationLinesResponse(
        station_id=station.station_id,
        station_name=station.station_name,
        lines=line_dtos,
        total_lines=len(line_dtos)
    )

def get_stations_with_coordinates(db: Session) -> List[BusStationDTO]:
    stations = db.query(BusStation).all()
    
    return [
        BusStationDTO(
            station_id=station.station_id,
            station_name=station.station_name,
            station_code=station.station_code,
            latitude=station.latitude,
            longitude=station.longitude,
            address=station.address,
            zone=station.zone,
            created_at=station.created_at
        ) for station in stations
    ]
