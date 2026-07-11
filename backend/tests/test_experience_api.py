def test_experience_example_matches_document(client):
    response = client.post(
        "/api/v1/travel-experience/evaluate",
        json={
            "predicted_load_rate": 0.77,
            "transfer_count": 0,
            "walk_time_minutes": 6.5,
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["load_score"] == 58.0
    assert data["walk_score"] == 83.8
    assert data["transfer_score"] == 100.0
    assert data["experience_score"] == 65.7


def test_experience_rejects_invalid_weights(client):
    response = client.post(
        "/api/v1/travel-experience/evaluate",
        json={
            "predicted_load_level": "seats_available",
            "transfer_count": 0,
            "walk_time_minutes": 5,
            "weights": {"w_load": 0.5, "w_walk": 0.5, "w_transfer": 0.5},
        },
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40002


def test_experience_requires_load_information(client):
    response = client.post(
        "/api/v1/travel-experience/evaluate",
        json={"transfer_count": 0, "walk_time_minutes": 5},
    )
    assert response.status_code == 422
    assert response.json()["code"] == 42200
