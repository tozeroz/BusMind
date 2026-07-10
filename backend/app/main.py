from fastapi import FastAPI

from app.api import router as api_router
from app.core.exception_handlers import register_intelligence_exception_handlers
from app.db.session import engine
from app.models.user import Base
from app.models import transit  # noqa: F401 - register transit ORM models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="BusMind API",
    description="公交智能调度系统 API",
    version="1.1.0",
)

# Service-B errors use the same code/message/data/trace_id/timestamp envelope.
register_intelligence_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["健康检查"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "BusMind API is running"}
