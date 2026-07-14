from fastapi.testclient import TestClient

from backend.app import main as main_module
from backend.app.main import app


class RecordingRefreshScheduler:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


def test_service_b_routes_are_mounted_in_formal_application():
    client = TestClient(app)
    eta = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 1},
    )
    assert eta.status_code == 200
    assert eta.json()["code"] == 0

    update = client.patch(
        "/api/v1/simulation/vehicle-status/101",
        json={"speed_kph": 20, "onboard_count": 30},
    )
    assert update.status_code == 200
    assert update.json()["data"]["vehicle_id"] == 101


def test_ai_travel_route_is_mounted_in_formal_application():
    client = TestClient(app)

    response = client.post(
        "/api/v1/ai/travel",
        json={"mode": "qa", "question": "下一班车多久到？"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "needs_clarification"
    assert data["missing_fields"] == ["context.items"]
    assert data["used_tools"] == []


def test_formal_application_starts_refresh_scheduler(monkeypatch):
    scheduler = RecordingRefreshScheduler()
    monkeypatch.setattr(main_module, "_refresh_scheduler", scheduler)

    with TestClient(app):
        assert scheduler.started is True
        assert scheduler.stopped is False

    assert scheduler.stopped is True
