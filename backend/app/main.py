from fastapi import FastAPI
from backend.app.api import router as api_router
from backend.app.models.user import Base
from backend.app.db.session import engine

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BusMind API",
    description="公交智能调度系统 API",
    version="1.0.0"
)

app.include_router(api_router)

@app.get("/", tags=["健康检查"])
async def health_check():
    return {"status": "ok", "message": "BusMind API is running"}