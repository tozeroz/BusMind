from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.history import EtaPrediction, LoadPrediction, PassengerFlowPrediction, PassengerFlowTrend
from app.schemas.history_schema import (
    EtaPredictionDTO,
    LoadPredictionDTO,
    PassengerFlowPredictionDTO,
    PassengerFlowResponse,
    PassengerFlowSummary,
    PassengerFlowTrendDTO,
)


def _as_float(value):
    return float(value) if value is not None else None


def get_passenger_flow_trend(
    db: Session,
    line_id: Optional[int] = None,
    station_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: str = "hour",
) -> PassengerFlowResponse:
    # The final schema currently stores station flow records. ``line_id`` is kept
    # for API compatibility and only matches records explicitly imported as line.
    query = db.query(PassengerFlowTrend)
    if line_id is not None:
        query = query.filter(
            PassengerFlowTrend.target_type == "line",
            PassengerFlowTrend.target_id == line_id,
        )
    if station_id is not None:
        query = query.filter(
            PassengerFlowTrend.target_type == "station",
            PassengerFlowTrend.target_id == station_id,
        )
    if start_date is not None:
        query = query.filter(PassengerFlowTrend.record_time >= start_date)
    if end_date is not None:
        query = query.filter(PassengerFlowTrend.record_time <= end_date)

    records = query.order_by(PassengerFlowTrend.record_time).all()
    items = [
        PassengerFlowTrendDTO(
            flow_record_id=int(record.flow_record_id),
            target_type=record.target_type,
            target_id=int(record.target_id),
            bus_stop_code=record.bus_stop_code,
            record_time=record.record_time,
            day_type=record.day_type,
            tap_in_volume=int(record.tap_in_volume),
            tap_out_volume=int(record.tap_out_volume),
            total_flow=int(record.total_flow),
            flow_level=record.flow_level,
            data_source=record.data_source,
        )
        for record in records
    ]

    total_tap_in = sum(item.tap_in_volume for item in items)
    total_tap_out = sum(item.tap_out_volume for item in items)
    total_flow = sum(item.total_flow for item in items)
    peak = max(items, key=lambda item: item.total_flow, default=None)
    levels: dict[str, int] = {}
    for item in items:
        if item.flow_level:
            levels[item.flow_level] = levels.get(item.flow_level, 0) + 1

    return PassengerFlowResponse(
        items=items,
        summary=PassengerFlowSummary(
            total_tap_in=total_tap_in,
            total_tap_out=total_tap_out,
            total_flow=total_flow,
            peak_hour=peak.record_time.hour if peak and peak.record_time else None,
            peak_flow=peak.total_flow if peak else None,
            dominant_flow_level=max(levels, key=levels.get) if levels else None,
        ),
    )


def get_passenger_flow_prediction(
    db: Session,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
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
    return [
        PassengerFlowPredictionDTO(
            prediction_id=int(record.prediction_id),
            target_type=record.target_type,
            target_id=record.target_id,
            prediction_time=record.prediction_time,
            predict_time=record.predict_time,
            predicted_flow=int(record.predicted_flow),
            crowd_level=record.crowd_level,
            confidence=_as_float(record.confidence),
            model_version=record.model_version,
        )
        for record in query.order_by(PassengerFlowPrediction.predict_time).all()
    ]


def _eta_dto(record: EtaPrediction) -> EtaPredictionDTO:
    return EtaPredictionDTO(
        eta_prediction_id=int(record.eta_prediction_id),
        vehicle_id=int(record.vehicle_id),
        line_id=int(record.line_id),
        target_station_id=int(record.target_station_id),
        bus_stop_code=record.bus_stop_code,
        prediction_time=record.prediction_time,
        predicted_eta_minutes=float(record.predicted_eta_minutes),
        arrival_time=record.arrival_time,
        vehicle_to_stop_distance_m=_as_float(record.vehicle_to_stop_distance_m),
        speed_kph=_as_float(record.speed_kph),
        confidence=_as_float(record.confidence),
        data_source=record.data_source,
        model_version=None,
        created_at=record.created_at,
    )


def _load_dto(record: LoadPrediction) -> LoadPredictionDTO:
    return LoadPredictionDTO(
        load_prediction_id=int(record.load_prediction_id),
        vehicle_id=int(record.vehicle_id),
        line_id=int(record.line_id),
        station_id=int(record.station_id) if record.station_id is not None else None,
        bus_stop_code=record.bus_stop_code,
        prediction_time=record.prediction_time,
        load_code=record.load_code,
        predicted_load_level=record.predicted_load_level,
        load_score=_as_float(record.load_score),
        predicted_load_rate=_as_float(record.predicted_load_rate),
        onboard_count=record.onboard_count,
        capacity=record.capacity,
        confidence=_as_float(record.confidence),
        data_source=record.data_source,
        model_version=None,
        created_at=record.created_at,
    )


def get_eta_prediction(
    db: Session,
    vehicle_id: int,
    target_station_id: int,
    line_id: Optional[int] = None,
) -> Optional[EtaPredictionDTO]:
    query = db.query(EtaPrediction).filter(
        EtaPrediction.vehicle_id == vehicle_id,
        EtaPrediction.target_station_id == target_station_id,
    )
    if line_id is not None:
        query = query.filter(EtaPrediction.line_id == line_id)
    record = query.order_by(EtaPrediction.prediction_time.desc()).first()
    return _eta_dto(record) if record else None


def get_load_prediction(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
) -> Optional[LoadPredictionDTO]:
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    if vehicle_id is not None:
        query = query.filter(LoadPrediction.vehicle_id == vehicle_id)
    record = query.order_by(LoadPrediction.prediction_time.desc()).first()
    return _load_dto(record) if record else None


def get_eta_predictions_by_line(
    db: Session,
    line_id: int,
    target_station_id: Optional[int] = None,
) -> list[EtaPredictionDTO]:
    query = db.query(EtaPrediction).filter(EtaPrediction.line_id == line_id)
    if target_station_id is not None:
        query = query.filter(EtaPrediction.target_station_id == target_station_id)
    return [_eta_dto(record) for record in query.order_by(EtaPrediction.prediction_time.desc()).all()]


def get_load_predictions_by_line(
    db: Session,
    line_id: int,
    station_id: Optional[int] = None,
) -> list[LoadPredictionDTO]:
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    return [_load_dto(record) for record in query.order_by(LoadPrediction.prediction_time.desc()).all()]


def get_predictions(
    db: Session,
    prediction_type: Optional[str] = None,
    line_id: Optional[int] = None,
    station_id: Optional[int] = None,
    vehicle_id: Optional[int] = None,
) -> list[dict]:
    results = []
    
    if prediction_type is None or prediction_type == "eta":
        eta_query = db.query(EtaPrediction)
        if line_id is not None:
            eta_query = eta_query.filter(EtaPrediction.line_id == line_id)
        if station_id is not None:
            eta_query = eta_query.filter(EtaPrediction.target_station_id == station_id)
        if vehicle_id is not None:
            eta_query = eta_query.filter(EtaPrediction.vehicle_id == vehicle_id)
        
        for record in eta_query.order_by(EtaPrediction.prediction_time.desc()).all():
            dto = _eta_dto(record)
            results.append({
                "prediction_type": "eta",
                **dto.__dict__
            })
    
    if prediction_type is None or prediction_type == "passenger_load":
        load_query = db.query(LoadPrediction)
        if line_id is not None:
            load_query = load_query.filter(LoadPrediction.line_id == line_id)
        if station_id is not None:
            load_query = load_query.filter(LoadPrediction.station_id == station_id)
        if vehicle_id is not None:
            load_query = load_query.filter(LoadPrediction.vehicle_id == vehicle_id)
        
        for record in load_query.order_by(LoadPrediction.prediction_time.desc()).all():
            dto = _load_dto(record)
            results.append({
                "prediction_type": "passenger_load",
                **dto.__dict__
            })
    
    if prediction_type is None or prediction_type == "passenger_flow":
        flow_query = db.query(PassengerFlowPrediction)
        if line_id is not None:
            flow_query = flow_query.filter(PassengerFlowPrediction.target_type == "line")
            flow_query = flow_query.filter(PassengerFlowPrediction.target_id == str(line_id))
        if station_id is not None:
            flow_query = flow_query.filter(PassengerFlowPrediction.target_type == "station")
            flow_query = flow_query.filter(PassengerFlowPrediction.target_id == str(station_id))
        
        for record in flow_query.order_by(PassengerFlowPrediction.predict_time.desc()).all():
            dto = PassengerFlowPredictionDTO(
                prediction_id=int(record.prediction_id),
                target_type=record.target_type,
                target_id=record.target_id,
                prediction_time=record.prediction_time,
                predict_time=record.predict_time,
                predicted_flow=int(record.predicted_flow),
                crowd_level=record.crowd_level,
                confidence=_as_float(record.confidence),
                model_version=record.model_version,
            )
            results.append({
                "prediction_type": "passenger_flow",
                **dto.__dict__
            })
    
    return sorted(results, key=lambda x: x.get('prediction_time') or x.get('predict_time'), reverse=True)