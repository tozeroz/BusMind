from fastapi import FastAPI
from app.api import router as api_router
from app.models.user import Base as UserBase
from app.models.bus_line import Base as BusBase
from app.models.history import Base as HistoryBase
from app.db.session import engine

UserBase.metadata.create_all(bind=engine)
BusBase.metadata.create_all(bind=engine)
HistoryBase.metadata.create_all(bind=engine)

app = FastAPI(
    title="BusMind API",
    description="Bus Intelligent Scheduling System API",
    version="1.0.0"
)

app.include_router(api_router)

@app.get("/", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "message": "BusMind API is running"}