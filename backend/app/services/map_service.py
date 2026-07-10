from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.bus_line import BusLine, BusStation, LineStation
from app.schemas.map_schema import (
    MapStationDTO,
    MapStationResponse,
    RoadSegmentDTO,
    RoadSegmentResponse,
    MapLineDTO,
    MapLineResponse,
    LineMapBoundsDTO,
    LineMapDataDTO
)
import math


def _station_map_by_ids(db: Session, station_ids: list[int]) -> dict[int, BusStation]:
    if not station_ids:
        return {}
    stations = db.query(BusStation).filter(BusStation.station_id.in_(station_ids)).all()
    return {station.station_id: station for station in stations}


def _line_map_by_ids(db: Session, line_ids: list[int]) -> dict[int, BusLine]:
    if not line_ids:
        return {}
    lines = db.query(BusLine).filter(BusLine.line_id.in_(line_ids)).all()
    return {line.line_id: line for line in lines}

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

def get_map_stations(db: Session) -> MapStationResponse:
    stations = db.query(BusStation).all()
    line_stations = db.query(LineStation).order_by(LineStation.line_id, LineStation.order_index).all()
    line_map = _line_map_by_ids(db, list({ls.line_id for ls in line_stations}))

    station_line_map: dict[int, list[LineStation]] = {}
    for ls in line_stations:
        station_line_map.setdefault(ls.station_id, []).append(ls)
    
    station_dtos = []
    for station in stations:
        station_lines = station_line_map.get(station.station_id, [])
        line_ids = [ls.line_id for ls in station_lines]
        line_names = [line_map[ls.line_id].line_name for ls in station_lines if ls.line_id in line_map]
        
        station_dtos.append(MapStationDTO(
            station_id=station.station_id,
            station_name=station.station_name,
            station_code=station.station_code,
            latitude=station.latitude,
            longitude=station.longitude,
            address=station.address,
            zone=station.zone,
            line_ids=line_ids,
            line_names=line_names
        ))
    
    return MapStationResponse(stations=station_dtos, total=len(station_dtos))

def get_road_segments(db: Session) -> RoadSegmentResponse:
    segments = []
    lines = db.query(BusLine).all()
    line_stations = db.query(LineStation).order_by(LineStation.line_id, LineStation.order_index).all()
    station_map = _station_map_by_ids(db, list({ls.station_id for ls in line_stations}))

    line_station_map: dict[int, list[LineStation]] = {}
    for ls in line_stations:
        line_station_map.setdefault(ls.line_id, []).append(ls)
    
    for line in lines:
        current_line_stations = line_station_map.get(line.line_id, [])
        
        for i in range(len(current_line_stations) - 1):
            start_ls = current_line_stations[i]
            end_ls = current_line_stations[i + 1]
            
            start_station = station_map.get(start_ls.station_id)
            end_station = station_map.get(end_ls.station_id)
            
            if start_station and end_station:
                distance = haversine_distance(
                    start_station.latitude, start_station.longitude,
                    end_station.latitude, end_station.longitude
                )
                
                path_coords = [
                    [start_station.longitude, start_station.latitude],
                    [end_station.longitude, end_station.latitude]
                ]
                
                segment_id = f"{line.line_id}_{i}"
                
                segments.append(RoadSegmentDTO(
                    segment_id=int(segment_id.replace("_", "")),
                    line_id=line.line_id,
                    line_name=line.line_name,
                    start_station_id=start_station.station_id,
                    start_station_name=start_station.station_name,
                    end_station_id=end_station.station_id,
                    end_station_name=end_station.station_name,
                    path_coordinates=path_coords,
                    distance_km=round(distance, 4),
                    passenger_flow=None
                ))
    
    return RoadSegmentResponse(segments=segments, total=len(segments))

def get_map_lines(db: Session) -> MapLineResponse:
    lines = db.query(BusLine).all()
    line_stations = db.query(LineStation).order_by(LineStation.line_id, LineStation.order_index).all()
    station_map = _station_map_by_ids(db, list({ls.station_id for ls in line_stations}))

    line_station_map: dict[int, list[LineStation]] = {}
    for ls in line_stations:
        line_station_map.setdefault(ls.line_id, []).append(ls)
    
    line_dtos = []
    for line in lines:
        current_line_stations = line_station_map.get(line.line_id, [])
        
        path_coordinates = []
        start_station_name = None
        end_station_name = None
        for ls in current_line_stations:
            station = station_map.get(ls.station_id)
            if station:
                if start_station_name is None:
                    start_station_name = station.station_name
                end_station_name = station.station_name
                path_coordinates.append([station.longitude, station.latitude])
        
        line_dtos.append(MapLineDTO(
            line_id=line.line_id,
            line_name=line.line_name,
            line_code=line.line_code,
            start_station=start_station_name or line.start_station or "",
            end_station=end_station_name or line.end_station or "",
            path_coordinates=path_coordinates
        ))
    
    return MapLineResponse(lines=line_dtos, total=len(line_dtos))

def get_map_stations_by_line(db: Session, line_id: int) -> MapStationResponse:
    line_stations = db.query(LineStation).filter(
        LineStation.line_id == line_id
    ).order_by(LineStation.order_index).all()
    station_map = _station_map_by_ids(db, [ls.station_id for ls in line_stations])
    
    station_dtos = []
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    line_name = line.line_name if line else ""
    
    for ls in line_stations:
        station = station_map.get(ls.station_id)
        if station:
            station_dtos.append(MapStationDTO(
                station_id=station.station_id,
                station_name=station.station_name,
                station_code=station.station_code,
                latitude=station.latitude,
                longitude=station.longitude,
                address=station.address,
                zone=station.zone,
                line_ids=[line_id],
                line_names=[line_name]
            ))
    
    return MapStationResponse(stations=station_dtos, total=len(station_dtos))


def get_line_map_data(db: Session, line_id: int, direction: Optional[str] = None) -> Optional[LineMapDataDTO]:
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    if not line:
        return None
    
    line_stations = db.query(LineStation).filter(
        LineStation.line_id == line_id
    ).order_by(LineStation.order_index).all()
    
    station_map = _station_map_by_ids(db, [ls.station_id for ls in line_stations])
    
    polyline = []
    station_dtos = []
    
    for ls in line_stations:
        station = station_map.get(ls.station_id)
        if station:
            polyline.append([station.longitude, station.latitude])
            station_dtos.append(MapStationDTO(
                station_id=station.station_id,
                station_name=station.station_name,
                station_code=station.station_code,
                latitude=station.latitude,
                longitude=station.longitude,
                address=station.address,
                zone=station.zone,
                line_ids=[line_id],
                line_names=[line.line_name]
            ))
    
    if polyline:
        latitudes = [coord[1] for coord in polyline]
        longitudes = [coord[0] for coord in polyline]
        bounds = LineMapBoundsDTO(
            min_latitude=min(latitudes),
            max_latitude=max(latitudes),
            min_longitude=min(longitudes),
            max_longitude=max(longitudes)
        )
    else:
        bounds = LineMapBoundsDTO(
            min_latitude=0.0,
            max_latitude=0.0,
            min_longitude=0.0,
            max_longitude=0.0
        )
    
    return LineMapDataDTO(
        line_id=line.line_id,
        line_name=line.line_name,
        line_code=line.line_code,
        polyline=polyline,
        stations=station_dtos,
        bounds=bounds
    )