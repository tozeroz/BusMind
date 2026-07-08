def test_eta_success(client):
    response = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["predicted_eta_minutes"] > 0
    assert body["data"]["model_version"] in {"eta_rule_v1", "eta_external_model"}
    assert "distance_meters" in body["data"]["factors"]


def test_eta_wrong_line(client):
    response = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 2},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40002


def test_eta_validation_envelope(client):
    response = client.get("/api/v1/eta", params={"vehicle_id": 101})
    assert response.status_code == 422
    assert response.json()["code"] == 42200
