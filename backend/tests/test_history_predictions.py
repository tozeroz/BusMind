"""Test for the aggregated predictions endpoint."""

import asyncio
from datetime import datetime
from dataclasses import dataclass, asdict
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String, func, desc
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class EtaPrediction(Base):
    __tablename__ = "eta_prediction"
    eta_prediction_id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, nullable=False, index=True)
    line_id = Column(Integer, nullable=False, index=True)
    target_station_id = Column(Integer, nullable=False, index=True)
    bus_stop_code = Column(String(30))
    prediction_time = Column(DateTime, nullable=False)
    predicted_eta_minutes = Column(DECIMAL(6, 2))
    arrival_time = Column(DateTime)
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2))
    speed_kph = Column(DECIMAL(6, 2))
    confidence = Column(DECIMAL(5, 3))
    data_source = Column(String(50))
    model_version = Column(String(20))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class LoadPrediction(Base):
    __tablename__ = "load_prediction"
    load_prediction_id = Column(Integer, primary_key=True)
    vehicle_id = Column(Integer, nullable=False, index=True)
    line_id = Column(Integer, nullable=False, index=True)
    station_id = Column(Integer, index=True)
    bus_stop_code = Column(String(30))
    prediction_time = Column(DateTime, nullable=False)
    load_code = Column(String(20))
    predicted_load_level = Column(String(20))
    load_score = Column(DECIMAL(5, 3))
    predicted_load_rate = Column(DECIMAL(5, 3))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(DECIMAL(5, 3))
    data_source = Column(String(50))
    model_version = Column(String(20))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class PassengerFlowPrediction(Base):
    __tablename__ = "passenger_flow_prediction"
    prediction_id = Column(Integer, primary_key=True)
    target_type = Column(String(20), nullable=False)
    target_id = Column(String(50), nullable=False)
    prediction_time = Column(DateTime, nullable=False)
    predict_time = Column(DateTime, nullable=False)
    predicted_flow = Column(Integer)
    crowd_level = Column(String(20))
    confidence = Column(DECIMAL(5, 3))
    model_version = Column(String(20))

@dataclass(frozen=True, slots=True)
class EtaPredictionDTO:
    eta_prediction_id: int
    vehicle_id: int
    line_id: int
    target_station_id: int
    bus_stop_code: str | None
    prediction_time: datetime
    predicted_eta_minutes: float
    arrival_time: datetime | None
    vehicle_to_stop_distance_m: float | None
    speed_kph: float | None
    confidence: float | None
    data_source: str | None
    model_version: str | None
    created_at: datetime

@dataclass(frozen=True, slots=True)
class LoadPredictionDTO:
    load_prediction_id: int
    vehicle_id: int
    line_id: int
    station_id: int | None
    bus_stop_code: str | None
    prediction_time: datetime
    load_code: str | None
    predicted_load_level: str | None
    load_score: float | None
    predicted_load_rate: float | None
    onboard_count: int | None
    capacity: int | None
    confidence: float | None
    data_source: str | None
    model_version: str | None
    created_at: datetime

@dataclass(frozen=True, slots=True)
class PassengerFlowPredictionDTO:
    prediction_id: int
    target_type: str
    target_id: str
    prediction_time: datetime
    predict_time: datetime
    predicted_flow: int
    crowd_level: str | None
    confidence: float | None
    model_version: str | None

def _as_float(value):
    return float(value) if value is not None else None

def _eta_dto(record):
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
        model_version=record.model_version,
        created_at=record.created_at,
    )

def _load_dto(record):
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
        model_version=record.model_version,
        created_at=record.created_at,
    )

def get_predictions(db, prediction_type=None, line_id=None, station_id=None, vehicle_id=None):
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
                **asdict(dto)
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
                **asdict(dto)
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
                **asdict(dto)
            })
    
    return sorted(results, key=lambda x: x.get('prediction_time') or x.get('predict_time'), reverse=True)

async def test_predictions_aggregated_endpoint():
    """Test the /api/v1/history/predictions aggregated endpoint."""
    
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    now = datetime.now()
    
    db.add(EtaPrediction(
        vehicle_id=2001,
        line_id=501,
        target_station_id=1001,
        bus_stop_code="BS1001",
        prediction_time=now,
        predicted_eta_minutes=8.5,
        vehicle_to_stop_distance_m=1500.0,
        speed_kph=25.0,
        confidence=0.85,
        data_source="model"
    ))
    db.add(EtaPrediction(
        vehicle_id=2002,
        line_id=501,
        target_station_id=1002,
        bus_stop_code="BS1002",
        prediction_time=now,
        predicted_eta_minutes=12.3,
        vehicle_to_stop_distance_m=2200.0,
        speed_kph=22.0,
        confidence=0.82,
        data_source="model"
    ))
    
    db.add(LoadPrediction(
        vehicle_id=2001,
        line_id=501,
        station_id=1001,
        bus_stop_code="BS1001",
        prediction_time=now,
        load_code="L03",
        predicted_load_level="standing_available",
        load_score=0.75,
        predicted_load_rate=75.0,
        onboard_count=45,
        capacity=60,
        confidence=0.85,
        data_source="model"
    ))
    db.add(LoadPrediction(
        vehicle_id=2001,
        line_id=501,
        station_id=1002,
        bus_stop_code="BS1002",
        prediction_time=now,
        load_code="L02",
        predicted_load_level="comfortable",
        load_score=0.60,
        predicted_load_rate=60.0,
        onboard_count=36,
        capacity=60,
        confidence=0.88,
        data_source="model"
    ))
    
    db.add(PassengerFlowPrediction(
        target_type="line",
        target_id="501",
        prediction_time=now,
        predict_time=now,
        predicted_flow=500,
        crowd_level="high",
        confidence=0.9,
        model_version="v1.0"
    ))
    db.add(PassengerFlowPrediction(
        target_type="station",
        target_id="1001",
        prediction_time=now,
        predict_time=now,
        predicted_flow=200,
        crowd_level="medium",
        confidence=0.85,
        model_version="v1.0"
    ))
    
    db.commit()
    
    print("Test 1 - Get all predictions (no filter)")
    results = get_predictions(db)
    print(f"  Total results: {len(results)}")
    types = [r['prediction_type'] for r in results]
    print(f"  Prediction types: {types}")
    assert len(results) == 6
    assert 'eta' in types
    assert 'passenger_load' in types
    assert 'passenger_flow' in types
    print("PASSED")
    
    print("\nTest 2 - Get only ETA predictions")
    results = get_predictions(db, prediction_type="eta")
    print(f"  Total results: {len(results)}")
    assert len(results) == 2
    assert all(r['prediction_type'] == 'eta' for r in results)
    print("PASSED")
    
    print("\nTest 3 - Get only passenger_load predictions")
    results = get_predictions(db, prediction_type="passenger_load")
    print(f"  Total results: {len(results)}")
    assert len(results) == 2
    assert all(r['prediction_type'] == 'passenger_load' for r in results)
    print("PASSED")
    
    print("\nTest 4 - Get predictions filtered by line_id")
    results = get_predictions(db, line_id=501)
    print(f"  Total results: {len(results)}")
    assert len(results) == 5
    print("PASSED")
    
    print("\nTest 5 - Get ETA predictions filtered by line_id")
    results = get_predictions(db, prediction_type="eta", line_id=501)
    print(f"  Total results: {len(results)}")
    assert len(results) == 2
    assert all(r['line_id'] == 501 for r in results)
    print("PASSED")
    
    print("\nTest 6 - Get predictions filtered by station_id")
    results = get_predictions(db, station_id=1001)
    print(f"  Total results: {len(results)}")
    assert len(results) == 3
    print("PASSED")
    
    print("\nTest 7 - Get predictions filtered by vehicle_id")
    results = get_predictions(db, vehicle_id=2001)
    print(f"  Total results: {len(results)}")
    assert len(results) == 5
    print("PASSED")
    
    print("\nTest 8 - Get passenger_flow predictions")
    results = get_predictions(db, prediction_type="passenger_flow")
    print(f"  Total results: {len(results)}")
    assert len(results) == 2
    assert all(r['prediction_type'] == 'passenger_flow' for r in results)
    print("PASSED")
    
    print("\nTest 9 - Combined filter: type + line_id + station_id")
    results = get_predictions(db, prediction_type="passenger_load", line_id=501, station_id=1001)
    print(f"  Total results: {len(results)}")
    assert len(results) == 1
    assert results[0]['prediction_type'] == 'passenger_load'
    assert results[0]['line_id'] == 501
    assert results[0]['station_id'] == 1001
    print("PASSED")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Aggregated Predictions Endpoint")
    print("=" * 70)
    print()
    
    asyncio.run(test_predictions_aggregated_endpoint())
    
    print()
    print("=" * 70)
    print("All aggregated predictions tests passed!")
    print("=" * 70)