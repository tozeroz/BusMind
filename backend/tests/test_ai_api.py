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


def test_ai_explain_without_route_context_requests_snapshot_or_context(client):
    response = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "explain",
            "question": "为什么推荐这条路线？",
            "route_id": "route-001",
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "needs_clarification"
    assert data["missing_fields"] == ["conversation_id", "context.items"]
    assert data["conversation_id"]


def test_ai_explain_empty_route_context_requests_snapshot_or_context(client):
    response = client.post(
        "/api/v1/ai/travel",
        json={
            "mode": "explain",
            "question": "为什么推荐这条路线？",
            "route_id": "route-001",
            "context": {"items": []},
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "needs_clarification"
    assert data["missing_fields"] == ["conversation_id", "context.items"]


def test_ai_automatic_mode_extracts_station_slots(client_without_deepseek):
    response = client_without_deepseek.post(
        "/api/v1/ai/travel",
        json={"question": "从站点1到站点12怎么走，尽量少换乘"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["mode"] == "suggest"
    assert data["resolved_slots"]["start_station_id"] == 1
    assert data["resolved_slots"]["end_station_id"] == 12
    assert data["resolved_slots"]["preference"] == "less_transfer"
    assert data["conversation_id"]


def test_ai_conversation_keeps_partial_slots_across_requests(client_without_deepseek):
    first_response = client_without_deepseek.post(
        "/api/v1/ai/travel",
        json={"question": "从站点1怎么走"},
    )
    first = first_response.json()["data"]
    assert first["status"] == "needs_clarification"
    assert first["missing_fields"] == ["end_station_id"]

    second_response = client_without_deepseek.post(
        "/api/v1/ai/travel",
        json={
            "question": "到站点12",
            "conversation_id": first["conversation_id"],
        },
    )
    second = second_response.json()["data"]
    assert second_response.status_code == 200
    assert second["mode"] == "suggest"
    assert second["resolved_slots"]["start_station_id"] == 1
    assert second["resolved_slots"]["end_station_id"] == 12
    assert second["related_routes"]
