def test_ai_suggest_falls_back_without_api_key(client_without_deepseek):
    response = client_without_deepseek.post(
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


def test_ai_suggest_reports_missing_station_fields(client_without_deepseek):
    response = client_without_deepseek.post(
        "/api/v1/ai/travel",
        json={"mode": "suggest", "question": "帮我推荐路线"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "needs_clarification"
    assert data["missing_fields"] == ["start_station_id", "end_station_id"]
    assert data["fallback"] is False
    assert data["used_tools"] == []


def test_ai_explain_rejects_route_id_without_route_context(client):
    response = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "explain",
            "question": "为什么推荐这条路线？",
            "route_id": "route-001",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42200


def test_ai_explain_rejects_empty_route_context(client):
    response = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "explain",
            "question": "为什么推荐这条路线？",
            "route_id": "route-001",
            "context": {"items": []},
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == 42200
