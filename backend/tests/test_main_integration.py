from fastapi.testclient import TestClient

from backend.app.main import app


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
