from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies import (
    get_ai_service,
    get_recommendation_service,
    get_transit_gateway,
)
from app.api.v1.intelligence_router import router
from app.core.exception_handlers import register_intelligence_exception_handlers
from app.dependencies.auth import get_current_admin_user
from app.services.ai_service import AiTravelService
from app.services.intelligence_gateway import (
    DemoIntelligenceGateway,
    configure_intelligence_gateway,
)
from app.services.simulation_service import simulation_state_store


class AiTravelServiceWithoutApiKey(AiTravelService):
    """Keep automated integration tests independent of external DeepSeek access."""

    @staticmethod
    def _build_default_client():
        return None


def test_full_service_b_workflow():
    simulation_state_store.clear()
    demo_gateway = DemoIntelligenceGateway()
    configure_intelligence_gateway(demo_gateway)
    app = FastAPI()
    register_intelligence_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_current_admin_user] = lambda: object()
    app.dependency_overrides[get_transit_gateway] = lambda: demo_gateway
    app.dependency_overrides[get_ai_service] = lambda: AiTravelServiceWithoutApiKey(
        get_recommendation_service()
    )
    client = TestClient(app)

    vehicle_update = client.patch(
        "/api/v1/simulation/vehicle-status/101",
        json={"speed_kph": 21, "onboard_count": 33, "status": "normal"},
    )
    assert vehicle_update.status_code == 200

    eta_update = client.post(
        "/api/v1/simulation/prediction-results",
        json={
            "prediction_type": "eta",
            "vehicle_id": 101,
            "line_id": 1,
            "target_station_id": 1,
            "predicted_eta_minutes": 3.2,
            "model_version": "integration_eta_v1",
        },
    )
    assert eta_update.status_code == 200

    load_update = client.post(
        "/api/v1/simulation/prediction-results",
        json={
            "prediction_type": "passenger_load",
            "vehicle_id": 101,
            "line_id": 1,
            "station_id": 1,
            "predicted_load_rate": 0.55,
            "predicted_load_level": "seats_available",
            "capacity": 60,
            "model_version": "integration_load_v1",
        },
    )
    assert load_update.status_code == 200

    eta = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 1, "line_id": 1},
    )
    assert eta.status_code == 200
    assert eta.json()["data"]["predicted_eta_minutes"] == 3.2

    load = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 1, "station_id": 1, "vehicle_id": 101},
    )
    assert load.status_code == 200
    assert load.json()["data"]["predicted_load_rate"] == 0.55

    recommendation = client.post(
        "/api/v1/recommend-routes",
        json={"start_station_id": 1, "end_station_id": 12},
    )
    assert recommendation.status_code == 200
    recommendation_data = recommendation.json()["data"]

    ai = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "explain",
            "route_id": recommendation_data["best_experience_route_id"],
            "context": recommendation_data,
        },
    )
    assert ai.status_code == 200
    assert ai.json()["data"]["answer"]
    assert ai.json()["data"]["fallback"] is True
