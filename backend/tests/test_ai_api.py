def test_ai_suggest_falls_back_without_api_key(client):
    response = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "suggest",
            "start_station_id": 1,
            "end_station_id": 12,
            "question": "哪条路线比较舒适？",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["answer"]
    assert data["fallback"] is True
    assert "recommend_routes" in data["used_tools"]
    assert data["related_routes"]


def test_ai_qa_requires_question(client):
    response = client.post("/api/v1/ai/travel", json={"mode": "qa"})
    assert response.status_code == 422
    assert response.json()["code"] == 42200
