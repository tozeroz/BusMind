from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.history import PassengerFlowPrediction, EtaPrediction, LoadPrediction
from app.schemas.history_schema import PassengerFlowPredictionDTO, EtaPredictionDTO, LoadPredictionDTO
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Testing PassengerFlowPrediction DTO conversion...")
try:
    records = db.query(PassengerFlowPrediction).order_by(PassengerFlowPrediction.predict_time).all()
    print(f"Found {len(records)} records")
    for record in records:
        print(f"Record: {record}")
        dto = PassengerFlowPredictionDTO(
            prediction_id=record.prediction_id,
            target_type=record.target_type,
            target_id=record.target_id,
            prediction_time=record.prediction_time,
            predict_time=record.predict_time,
            predicted_flow=record.predicted_flow,
            crowd_level=record.crowd_level,
            confidence=record.confidence,
            model_version=record.model_version
        )
        print(f"DTO: {dto}")
        print(f"DTO model_dump: {dto.model_dump()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50 + "\n")

print("Testing EtaPrediction DTO conversion...")
try:
    records = db.query(EtaPrediction).order_by(EtaPrediction.created_at.desc()).all()
    print(f"Found {len(records)} records")
    for record in records:
        print(f"Record: {record}")
        dto = EtaPredictionDTO(
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
        print(f"DTO: {dto}")
        print(f"DTO model_dump: {dto.model_dump()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

db.close()