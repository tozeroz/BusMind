from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.history import PassengerFlowPrediction, EtaPrediction
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

print("Testing PassengerFlowPrediction query compile...")
try:
    query = db.query(PassengerFlowPrediction)
    print(f"Query: {query}")
    print(f"Query compiled: {query.statement.compile()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*50 + "\n")

print("Testing EtaPrediction query compile...")
try:
    query = db.query(EtaPrediction).filter(EtaPrediction.line_id == 1)
    print(f"Query: {query}")
    print(f"Query compiled: {query.statement.compile()}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

db.close()