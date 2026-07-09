from datetime import datetime, timedelta, timezone


def test_vehicle_status_update_changes_following_load_input(client):
    update = client.patch(
        "/api/v1/simulation/vehicle-status/101",
        json={
            "longitude": 116.4001,
            "latitude": 39.9101,
            "speed_kph": 18.5,
            "onboard_count": 50,
            "capacity": 60,
            "status": "delayed",
        },
    )
    assert update.status_code == 200
    data = update.json()["data"]
    assert data["speed_kph"] == 18.5
    assert data["onboard_count"] == 50
    assert data["status"] == "delayed"

    load = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 1, "station_id": 3, "vehicle_id": 101},
    )
    assert load.status_code == 200
    assert load.json()["data"]["predicted_onboard_count"] >= 48


def test_manual_eta_prediction_update_is_consumed_by_eta_api(client):
    update = client.post(
        "/api/v1/simulation/prediction-results",
        json={
            "prediction_type": "eta",
            "vehicle_id": 101,
            "line_id": 1,
            "target_station_id": 3,
            "predicted_eta_minutes": 2.5,
            "confidence": 0.97,
            "model_version": "eta_demo_refresh_v2",
            "expires_in_seconds": 300,
        },
    )
    assert update.status_code == 200
    assert update.json()["data"]["storage_key"] == "eta:101:3:1"

    eta = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 1},
    )
    assert eta.status_code == 200
    data = eta.json()["data"]
    assert data["predicted_eta_minutes"] == 2.5
    assert data["model_version"] == "eta_demo_refresh_v2"
    assert data["factors"]["source"] == "simulation"


def test_manual_load_prediction_update_is_consumed_by_load_api(client):
    update = client.post(
        "/api/v1/simulation/prediction-results",
        json={
            "prediction_type": "passenger_load",
            "vehicle_id": 101,
            "line_id": 1,
            "station_id": 3,
            "predicted_load_level": "limited_standing",
            "predicted_load_rate": 0.93,
            "predicted_onboard_count": 56,
            "capacity": 60,
            "confidence": 0.96,
            "model_version": "load_demo_refresh_v2",
        },
    )
    assert update.status_code == 200

    load = client.post(
        "/api/v1/passenger-load-prediction",
        json={"line_id": 1, "station_id": 3, "vehicle_id": 101},
    )
    assert load.status_code == 200
    data = load.json()["data"]
    assert data["predicted_load_level"] == "limited_standing"
    assert data["predicted_load_rate"] == 0.93
    assert data["predicted_onboard_count"] == 56
    assert data["model_version"] == "load_demo_refresh_v2"


def test_prediction_update_validates_required_fields(client):
    response = client.post(
        "/api/v1/simulation/prediction-results",
        json={"prediction_type": "eta", "vehicle_id": 101},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200


def test_eta_update_can_derive_minutes_from_arrival_time(client):
    arrival = datetime.now(timezone.utc) + timedelta(minutes=6)
    response = client.post(
        "/api/v1/simulation/prediction-results",
        json={
            "prediction_type": "eta",
            "vehicle_id": 101,
            "line_id": 1,
            "target_station_id": 3,
            "arrival_time": arrival.isoformat(),
        },
    )
    assert response.status_code == 200
    assert 5.0 <= response.json()["data"]["payload"]["predicted_eta_minutes"] <= 6.1


def test_lta_refresh_reports_missing_account_key(client):
    response = client.post(
        "/api/v1/simulation/lta-bus-arrival/refresh",
        json={
            "bus_stop_code": "83139",
            "service_no": "15",
            "vehicle_id": 101,
            "line_id": 1,
            "station_id": 3,
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == 50320
