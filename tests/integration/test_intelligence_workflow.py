from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.v1.intelligence_router import router
from backend.app.core.exception_handlers import register_intelligence_exception_handlers


def test_full_service_b_workflow():
    app = FastAPI()
    register_intelligence_exception_handlers(app)
    app.include_router(router, prefix="/api/v1")
    client = TestClient(app)

    eta = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 1, "line_id": 1},
    )
    assert eta.status_code == 200

    load = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 1, "station_id": 1, "vehicle_id": 101},
    )
    assert load.status_code == 200

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
