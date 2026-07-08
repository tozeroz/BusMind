def test_recommend_routes_success(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={
            "start_station_id": 1,
            "end_station_id": 12,
            "preference": "balanced",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 3
    assert data["best_experience_route_id"]
    assert data["fastest_route_id"]
    for item in data["items"]:
        assert "predicted_load" in item
        assert item["walk_time_minutes"] >= 0
        assert item["experience_score"] >= 0
        assert item["reason"]


def test_recommend_routes_without_transfer(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={
            "start_station_id": 1,
            "end_station_id": 12,
            "allow_transfer": False,
            "max_transfer_count": 0,
        },
    )
    assert response.status_code == 200
    assert all(item["transfer_count"] == 0 for item in response.json()["data"]["items"])


def test_recommend_routes_same_station(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={"start_station_id": 1, "end_station_id": 1},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40003
