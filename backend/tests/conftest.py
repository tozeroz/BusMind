from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies import (
    get_ai_service,
    get_recommendation_service,
    get_transit_gateway,
)
from app.api.v1.intelligence_router import router
from app.core.exception_handlers import register_intelligence_exception_handlers
from app.services.ai_service import AiTravelService
from app.services.intelligence_gateway import (
    DemoIntelligenceGateway,
    configure_intelligence_gateway,
    get_intelligence_gateway,
)
from app.services.simulation_service import simulation_state_store


class AiTravelServiceWithoutApiKey(AiTravelService):
    """Test-only service that behaves as if no DeepSeek key were configured."""

    @staticmethod
    def _build_default_client():
        return None


@pytest.fixture(autouse=True)
def reset_service_b_state():
    simulation_state_store.clear()
    configure_intelligence_gateway(DemoIntelligenceGateway())
    yield
    simulation_state_store.clear()
    configure_intelligence_gateway(DemoIntelligenceGateway())


@pytest.fixture()
def app() -> FastAPI:
    application = FastAPI()
    register_intelligence_exception_handlers(application)
    application.include_router(router, prefix="/api/v1")
    application.dependency_overrides[get_transit_gateway] = get_intelligence_gateway
    return application


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture()
def client_without_deepseek(app: FastAPI):
    """Return a client whose AI dependency never reads the real .env API key."""

    app.dependency_overrides[get_ai_service] = lambda: AiTravelServiceWithoutApiKey(
        get_recommendation_service()
    )
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_ai_service, None)
