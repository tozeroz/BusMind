def test_passenger_load_prediction_success(client):
    response = client.post(
        "/api/v1/passenger-load-prediction",
        json={
            "line_id": 1,
            "station_id": 3,
            "vehicle_id": 101,
            "capacity": 60,
            "current_onboard_count": 40,
            "weather": "rain",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert 0 <= data["predicted_load_rate"] <= 2
    assert data["predicted_load_level"] in {
        "seats_available",
        "standing_available",
        "limited_standing",
        "overcrowded",
    }
    assert 0 <= data["load_score"] <= 100


def test_passenger_load_vehicle_line_mismatch(client):
    response = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 2, "station_id": 3, "vehicle_id": 101},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40002


def test_passenger_load_capacity_zero(client):
    response = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 1, "station_id": 3, "capacity": 0},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200
