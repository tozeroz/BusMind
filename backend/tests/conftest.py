from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.intelligence_router import router
from backend.app.core.exception_handlers import register_intelligence_exception_handlers


@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()
    register_intelligence_exception_handlers(application)
    application.include_router(router, prefix="/api/v1")
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
