"""Standalone application for Postman testing before merging with team A."""

from fastapi import FastAPI

from app.api.v1.intelligence_router import router
from app.core.exception_handlers import register_intelligence_exception_handlers

app = FastAPI(title="BusMind Service-B Demo", version="1.0.0")
register_intelligence_exception_handlers(app)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "module": "service-b"}
