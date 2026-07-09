def test_walking_time_success(client):
    response = client.post(
        "/api/v1/walking-time-estimation",
        json={
            "origin_longitude": 116.3974,
            "origin_latitude": 39.9093,
            "target_station_id": 3,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["walk_distance_meters"] >= 0
    assert data["walk_time_minutes"] >= 0
    assert data["route_source"] == "straight_line"


def test_walking_speed_out_of_range(client):
    response = client.post(
        "/api/v1/walking-time-estimation",
        json={
            "origin_longitude": 116.3974,
            "origin_latitude": 39.9093,
            "target_station_id": 3,
            "walking_speed_mps": 5,
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200
