from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.history import PassengerFlowTrend, EtaPrediction, LoadPrediction
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Testing PassengerFlowTrend query...")
try:
    result = db.query(PassengerFlowTrend).first()
    print(f"PassengerFlowTrend query successful: {result}")
except Exception as e:
    print(f"PassengerFlowTrend error: {e}")

print("\nTesting EtaPrediction query...")
try:
    result = db.query(EtaPrediction).first()
    print(f"EtaPrediction query successful: {result}")
except Exception as e:
    print(f"EtaPrediction error: {e}")

print("\nTesting LoadPrediction query...")
try:
    result = db.query(LoadPrediction).first()
    print(f"LoadPrediction query successful: {result}")
except Exception as e:
    print(f"LoadPrediction error: {e}")

db.close()