from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from pathlib import Path
import sys

# Make repository-level packages available for both direct Uvicorn and start.py.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI

from app.api import router as api_router
from app.core.config import settings
from app.core.exception_handlers import register_intelligence_exception_handlers
from app.db.schema_check import validate_database_schema
from app.db.session import engine
from app.models import Base

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)

    if settings.VALIDATE_DB_SCHEMA_ON_STARTUP:
        issues = validate_database_schema(engine)
        if issues:
            details = "; ".join(
                f"{item.object_name}: {item.issue}"
                for item in issues
            )
            raise RuntimeError(
                f"Database schema validation failed: {details}"
            )

        logger.info("Database schema validation passed")

    yield


app = FastAPI(
    title="BusMind API",
    description="公交智能调度系统 API",
    version="1.2.0",
    lifespan=lifespan,
)

register_intelligence_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["健康检查"])
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "message": "BusMind API is running",
    }
