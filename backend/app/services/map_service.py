from sqlalchemy.orm import Session
from typing import Optional, List
from app.models.bus_line import BusLine, BusStation, LineStation
from app.schemas.map_schema import (
    MapStationDTO,
    MapStationResponse,
    RoadSegmentDTO,
    RoadSegmentResponse,
    MapLineDTO,
    MapLineResponse
)
import math

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
    
    station_dtos = []
    for station in stations:
        line_stations = db.query(LineStation).filter(LineStation.station_id == station.station_id).all()
        line_ids = [ls.line_id for ls in line_stations]
        line_names = []
        
        for ls in line_stations:
            line = db.query(BusLine).filter(BusLine.line_id == ls.line_id).first()
            if line:
                line_names.append(line.line_name)
        
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
    
    for line in lines:
        line_stations = db.query(LineStation).filter(
            LineStation.line_id == line.line_id
        ).order_by(LineStation.order_index).all()
        
        for i in range(len(line_stations) - 1):
            start_ls = line_stations[i]
            end_ls = line_stations[i + 1]
            
            start_station = db.query(BusStation).filter(
                BusStation.station_id == start_ls.station_id
            ).first()
            end_station = db.query(BusStation).filter(
                BusStation.station_id == end_ls.station_id
            ).first()
            
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
    
    line_dtos = []
    for line in lines:
        line_stations = db.query(LineStation).filter(
            LineStation.line_id == line.line_id
        ).order_by(LineStation.order_index).all()
        
        path_coordinates = []
        for ls in line_stations:
            station = db.query(BusStation).filter(BusStation.station_id == ls.station_id).first()
            if station:
                path_coordinates.append([station.longitude, station.latitude])
        
        line_dtos.append(MapLineDTO(
            line_id=line.line_id,
            line_name=line.line_name,
            line_code=line.line_code,
            start_station=line.start_station,
            end_station=line.end_station,
            path_coordinates=path_coordinates
        ))
    
    return MapLineResponse(lines=line_dtos, total=len(line_dtos))

def get_map_stations_by_line(db: Session, line_id: int) -> MapStationResponse:
    line_stations = db.query(LineStation).filter(
        LineStation.line_id == line_id
    ).order_by(LineStation.order_index).all()
    
    station_dtos = []
    line = db.query(BusLine).filter(BusLine.line_id == line_id).first()
    line_name = line.line_name if line else ""
    
    for ls in line_stations:
        station = db.query(BusStation).filter(BusStation.station_id == ls.station_id).first()
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