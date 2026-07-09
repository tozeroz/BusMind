from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
from app.models.history import PassengerFlowTrend, PassengerFlowPrediction, EtaPrediction, LoadPrediction
from app.schemas.history_schema import (
    PassengerFlowTrendDTO,
    PassengerFlowSummary,
    PassengerFlowResponse,
    PassengerFlowPredictionDTO,
    EtaPredictionDTO,
    LoadPredictionDTO
)

def get_passenger_flow_trend(
    db: Session,
    line_id: Optional[int] = None,
    station_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: str = "hour"
) -> PassengerFlowResponse:
    query = db.query(PassengerFlowTrend)
    
    if station_id:
        query = query.filter(PassengerFlowTrend.target_id == station_id, PassengerFlowTrend.target_type == "station")
    
    if start_date:
        query = query.filter(PassengerFlowTrend.record_time >= start_date)
    
    if end_date:
        query = query.filter(PassengerFlowTrend.record_time <= end_date)
    
    records = query.order_by(PassengerFlowTrend.record_time).all()
    
    items = []
    total_tap_in = 0
    total_tap_out = 0
    total_flow = 0
    peak_flow = 0
    peak_hour = None
    flow_levels = {}
    
    for record in records:
        items.append(PassengerFlowTrendDTO(
            flow_record_id=record.flow_record_id,
            target_type=record.target_type,
            target_id=record.target_id,
            bus_stop_code=record.bus_stop_code,
            record_time=record.record_time,
            day_type=record.day_type,
            tap_in_volume=record.tap_in_volume,
            tap_out_volume=record.tap_out_volume,
            total_flow=record.total_flow,
            flow_level=record.flow_level,
            data_source=record.data_source
        ))
        total_tap_in += record.tap_in_volume
        total_tap_out += record.tap_out_volume
        total_flow += record.total_flow
        if record.total_flow > peak_flow:
            peak_flow = record.total_flow
            peak_hour = record.record_time.hour if record.record_time else None
        if record.flow_level:
            flow_levels[record.flow_level] = flow_levels.get(record.flow_level, 0) + 1
    
    dominant_flow_level = max(flow_levels, key=flow_levels.get) if flow_levels else None
    
    summary = PassengerFlowSummary(
        total_tap_in=total_tap_in,
        total_tap_out=total_tap_out,
        total_flow=total_flow,
        peak_hour=peak_hour,
        peak_flow=peak_flow if peak_flow > 0 else None,
        dominant_flow_level=dominant_flow_level
    )
    
    return PassengerFlowResponse(items=items, summary=summary)

def get_passenger_flow_prediction(
    db: Session,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> list[PassengerFlowPredictionDTO]:
    query = db.query(PassengerFlowPrediction)
    
    if target_type:
        query = query.filter(PassengerFlowPrediction.target_type == target_type)
    
    if target_id:
        query = query.filter(PassengerFlowPrediction.target_id == target_id)
    
    if start_time:
        query = query.filter(PassengerFlowPrediction.predict_time >= start_time)
    
    if end_time:
        query = query.filter(PassengerFlowPrediction.predict_time <= end_time)
    
    records = query.order_by(PassengerFlowPrediction.predict_time).all()
    
    return [PassengerFlowPredictionDTO(
        prediction_id=record.prediction_id,
        target_type=record.target_type,
        target_id=record.target_id,
        prediction_time=record.prediction_time,
        predict_time=record.predict_time,
        predicted_flow=record.predicted_flow,
        crowd_level=record.crowd_level,
        confidence=record.confidence,
        model_version=record.model_version
    ) for record in records]

def get_eta_prediction(
    db: Session,
    vehicle_id: int,
    target_station_id: int,
    line_id: Optional[int] = None
) -> Optional[EtaPredictionDTO]:
    query = db.query(EtaPrediction)\
        .filter(EtaPrediction.vehicle_id == vehicle_id)\
        .filter(EtaPrediction.target_station_id == target_station_id)
    
    if line_id:
        query = query.filter(EtaPrediction.line_id == line_id)
    
    record = query.order_by(EtaPrediction.created_at.desc()).first()
    
    if record:
        return EtaPredictionDTO(
            eta_prediction_id=record.eta_prediction_id,
            vehicle_id=record.vehicle_id,
            line_id=record.line_id,
            target_station_id=record.target_station_id,
            prediction_time=record.prediction_time,
            predicted_eta_minutes=record.predicted_eta_minutes,
            arrival_time=record.arrival_time,
            vehicle_to_stop_distance_m=record.vehicle_to_stop_distance_m,
            speed_kph=record.speed_kph,
            confidence=record.confidence,
            model_version=record.model_version,
            created_at=record.created_at
        )
    return None

def get_load_prediction(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None
) -> Optional[LoadPredictionDTO]:
    query = db.query(LoadPrediction)\
        .filter(LoadPrediction.line_id == line_id)
    
    if station_id:
        query = query.filter(LoadPrediction.station_id == station_id)
    
    if vehicle_id:
        query = query.filter(LoadPrediction.vehicle_id == vehicle_id)
    
    record = query.order_by(LoadPrediction.created_at.desc()).first()
    
    if record:
        return LoadPredictionDTO(
            load_prediction_id=record.load_prediction_id,
            vehicle_id=record.vehicle_id,
            line_id=record.line_id,
            station_id=record.station_id,
            prediction_time=record.prediction_time,
            predicted_load_level=record.predicted_load_level,
            load_score=record.load_score,
            predicted_load_rate=record.predicted_load_rate,
            onboard_count=record.onboard_count,
            capacity=record.capacity,
            confidence=record.confidence,
            model_version=record.model_version,
            created_at=record.created_at
        )
    return None

def get_eta_predictions_by_line(
    db: Session,
    line_id: int,
    target_station_id: Optional[int] = None
) -> list[EtaPredictionDTO]:
    query = db.query(EtaPrediction)\
        .filter(EtaPrediction.line_id == line_id)
    
    if target_station_id:
        query = query.filter(EtaPrediction.target_station_id == target_station_id)
    
    records = query.order_by(EtaPrediction.created_at.desc()).all()
    
    return [EtaPredictionDTO(
        eta_prediction_id=record.eta_prediction_id,
        vehicle_id=record.vehicle_id,
        line_id=record.line_id,
        target_station_id=record.target_station_id,
        prediction_time=record.prediction_time,
        predicted_eta_minutes=record.predicted_eta_minutes,
        arrival_time=record.arrival_time,
        vehicle_to_stop_distance_m=record.vehicle_to_stop_distance_m,
        speed_kph=record.speed_kph,
        confidence=record.confidence,
        model_version=record.model_version,
        created_at=record.created_at
    ) for record in records]

def get_load_predictions_by_line(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None
) -> list[LoadPredictionDTO]:
    query = db.query(LoadPrediction)\
        .filter(LoadPrediction.line_id == line_id)
    
    if station_id:
        query = query.filter(LoadPrediction.station_id == station_id)
    
    records = query.order_by(LoadPrediction.created_at.desc()).all()
    
    return [LoadPredictionDTO(
        load_prediction_id=record.load_prediction_id,
        vehicle_id=record.vehicle_id,
        line_id=record.line_id,
        station_id=record.station_id,
        prediction_time=record.prediction_time,
        predicted_load_level=record.predicted_load_level,
        load_score=record.load_score,
        predicted_load_rate=record.predicted_load_rate,
        onboard_count=record.onboard_count,
        capacity=record.capacity,
        confidence=record.confidence,
        model_version=record.model_version,
        created_at=record.created_at
    ) for record in records]