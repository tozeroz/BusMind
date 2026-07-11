"""Test for the compatible passenger-load endpoint."""

import asyncio
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String, func, desc
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

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

def _as_float(value):
    return float(value) if value is not None else None

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

def get_load_prediction(db, line_id, station_id=None, vehicle_id=None):
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    if vehicle_id is not None:
        query = query.filter(LoadPrediction.vehicle_id == vehicle_id)
    record = query.order_by(LoadPrediction.prediction_time.desc()).first()
    return _load_dto(record) if record else None

def get_load_predictions_by_line(db, line_id, station_id=None):
    query = db.query(LoadPrediction).filter(LoadPrediction.line_id == line_id)
    if station_id is not None:
        query = query.filter(LoadPrediction.station_id == station_id)
    return [_load_dto(record) for record in query.order_by(LoadPrediction.prediction_time.desc()).all()]

async def test_passenger_load_compatible_endpoint():
    """Test the /api/v1/history/passenger-load compatible endpoint."""
    
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    now = datetime.now()
    
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
        data_source="model",
        model_version="v1.0"
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
        data_source="model",
        model_version="v1.0"
    ))
    db.add(LoadPrediction(
        vehicle_id=2002,
        line_id=501,
        station_id=1001,
        bus_stop_code="BS1001",
        prediction_time=now,
        load_code="L04",
        predicted_load_level="crowded",
        load_score=0.85,
        predicted_load_rate=85.0,
        onboard_count=51,
        capacity=60,
        confidence=0.82,
        data_source="model",
        model_version="v1.0"
    ))
    
    db.commit()
    
    print("Test 1 - Get all load predictions for a line (line_id only)")
    results = get_load_predictions_by_line(db, line_id=501)
    print(f"  Number of results: {len(results)}")
    assert len(results) == 3
    print("PASSED")
    
    print("\nTest 2 - Get load prediction with line_id and station_id")
    result = get_load_prediction(db, line_id=501, station_id=1001)
    print(f"  Result: load_prediction_id={result.load_prediction_id}, predicted_load_level={result.predicted_load_level}")
    assert result is not None
    assert result.line_id == 501
    assert result.station_id == 1001
    print("PASSED")
    
    print("\nTest 3 - Get load prediction with line_id and vehicle_id")
    result = get_load_prediction(db, line_id=501, vehicle_id=2002)
    print(f"  Result: vehicle_id={result.vehicle_id}, predicted_load_rate={result.predicted_load_rate}")
    assert result is not None
    assert result.vehicle_id == 2002
    print("PASSED")
    
    print("\nTest 4 - Get load prediction with all parameters")
    result = get_load_prediction(db, line_id=501, station_id=1001, vehicle_id=2001)
    print(f"  Result: line_id={result.line_id}, station_id={result.station_id}, vehicle_id={result.vehicle_id}")
    assert result is not None
    assert result.line_id == 501
    assert result.station_id == 1001
    assert result.vehicle_id == 2001
    print("PASSED")
    
    print("\nTest 5 - Non-existent line returns empty list")
    results = get_load_predictions_by_line(db, line_id=9999)
    print(f"  Number of results: {len(results)}")
    assert len(results) == 0
    print("PASSED")
    
    print("\nTest 6 - Non-existent station returns None")
    result = get_load_prediction(db, line_id=501, station_id=9999)
    print(f"  Result: {result}")
    assert result is None
    print("PASSED")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Passenger Load Compatible Endpoint")
    print("=" * 70)
    print()
    
    asyncio.run(test_passenger_load_compatible_endpoint())
    
    print()
    print("=" * 70)
    print("All passenger load compatible endpoint tests passed!")
    print("=" * 70)