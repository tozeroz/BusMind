from types import SimpleNamespace

import pytest

from app.schemas.ai_travel import AiMode, AiTravelRequest, AiTravelStatus
from app.schemas.recommendation import Preference, RecommendRoutesRequest
from app.services.ai_service import AiTravelService
from app.services.ai_service import service as ai_service_module
from app.services.ai_service.orchestration import ConversationStore
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import DemoIntelligenceGateway
from app.services.load_service import PassengerLoadService
from app.services.recommend_service import (
    RecommendationService,
    TravelExperienceService,
)
from llm.providers.deepseek import DeepSeekClient, DeepSeekError


class FakeDeepSeekClient:
    def __init__(self) -> None:
        self.messages = None

    async def chat(self, messages):
        self.messages = messages
        return "建议选择体验分更高的路线，车内更宽敞"


class FailingDeepSeekClient:
    async def chat(self, messages):
        raise DeepSeekError("测试连接失败")


def _recommendation_service() -> RecommendationService:
    gateway = DemoIntelligenceGateway()
    return RecommendationService(
        gateway,
        EtaService(gateway),
        PassengerLoadService(gateway),
        TravelExperienceService(),
    )


@pytest.mark.asyncio
async def test_ai_service_uses_deepseek_when_available():
    fake_client = FakeDeepSeekClient()
    service = AiTravelService(_recommendation_service(), client=fake_client)
    result = await service.answer(
        AiTravelRequest(
            mode=AiMode.SUGGEST,
            start_station_id=1,
            end_station_id=12,
            question="怎么走？",
        )
    )

    assert result.fallback is False
    assert "体验" in result.answer
    assert "deepseek" in result.used_tools
    assert result.related_routes
    assert result.related_routes[0].segments[0].line_name.startswith("校园")
    assert "怎么走？" in fake_client.messages[1]["content"]
    assert "校园" in fake_client.messages[1]["content"]
    assert '"contract_version":"1.0"' in fake_client.messages[1]["content"]
    assert '"source":"recommendation_service"' in fake_client.messages[1]["content"]
    assert '"model_must_not_invent_realtime_data":true' in fake_client.messages[1]["content"]


@pytest.mark.asyncio
async def test_ai_service_reports_provider_failure_and_falls_back():
    service = AiTravelService(
        _recommendation_service(),
        client=FailingDeepSeekClient(),
    )
    result = await service.answer(
        AiTravelRequest(
            mode=AiMode.SUGGEST,
            start_station_id=1,
            end_station_id=12,
        )
    )

    assert result.fallback is True
    assert result.status == AiTravelStatus.DEGRADED
    assert "建议选择" in result.answer
    assert any("AI 服务调用失败" in item for item in result.reminders)


@pytest.mark.asyncio
async def test_ai_service_does_not_call_model_without_qa_evidence():
    fake_client = FakeDeepSeekClient()
    service = AiTravelService(_recommendation_service(), client=fake_client)

    result = await service.answer(
        AiTravelRequest(mode=AiMode.QA, question="下一班车多久到？")
    )

    assert result.status == AiTravelStatus.NEEDS_CLARIFICATION
    assert result.missing_fields == ["context.items"]
    assert result.fallback is False
    assert fake_client.messages is None


@pytest.mark.asyncio
async def test_ai_service_reports_unknown_explain_route_without_calling_model():
    recommendation_service = _recommendation_service()
    recommendation = await recommendation_service.recommend(
        RecommendRoutesRequest(start_station_id=1, end_station_id=12)
    )
    fake_client = FakeDeepSeekClient()
    service = AiTravelService(recommendation_service, client=fake_client)

    result = await service.answer(
        AiTravelRequest(
            mode=AiMode.EXPLAIN,
            question="为什么推荐这条路线？",
            route_id="route-does-not-exist",
            context={
                "items": [item.model_dump(mode="json") for item in recommendation.items]
            },
        )
    )

    assert result.status == AiTravelStatus.NEEDS_CLARIFICATION
    assert result.missing_fields == ["route_id"]
    assert result.related_routes
    assert fake_client.messages is None


@pytest.mark.asyncio
async def test_ai_service_explains_only_the_selected_context_route():
    recommendation_service = _recommendation_service()
    recommendation = await recommendation_service.recommend(
        RecommendRoutesRequest(start_station_id=1, end_station_id=12)
    )
    selected = recommendation.items[-1]
    fake_client = FakeDeepSeekClient()
    service = AiTravelService(recommendation_service, client=fake_client)

    result = await service.answer(
        AiTravelRequest(
            mode=AiMode.EXPLAIN,
            question="为什么推荐这条路线？",
            route_id=selected.route_id,
            context={
                "data": {
                    "items": [
                        item.model_dump(mode="json") for item in recommendation.items
                    ]
                }
            },
        )
    )

    assert result.status == AiTravelStatus.COMPLETED
    assert result.fallback is False
    assert result.used_tools == ["provided_route_context", "deepseek"]
    assert [route.route_id for route in result.related_routes] == [selected.route_id]
    assert '"source":"request_context"' in fake_client.messages[1]["content"]
    assert f'"route_id":"{selected.route_id}"' in fake_client.messages[1]["content"]


def test_ai_request_normalizes_legacy_low_load_preference():
    request = AiTravelRequest(
        mode=AiMode.SUGGEST,
        question="想坐不太挤的车",
        start_station_id=1,
        end_station_id=12,
        preference="low_load",
    )

    assert request.preference == Preference.COMFORT


@pytest.mark.asyncio
async def test_ai_service_completes_recommend_explain_alternative_conversation():
    recommendation_service = _recommendation_service()
    original_recommend = recommendation_service.recommend
    calls = 0

    async def counted_recommend(request):
        nonlocal calls
        calls += 1
        return await original_recommend(request)

    recommendation_service.recommend = counted_recommend
    service = AiTravelService(
        recommendation_service,
        client=FakeDeepSeekClient(),
        store=ConversationStore(),
    )

    first = await service.answer(
        AiTravelRequest(question="从站点1到站点12怎么走，想舒适一点")
    )
    assert first.mode == AiMode.SUGGEST
    assert first.resolved_slots["start_station_id"] == 1
    assert first.resolved_slots["end_station_id"] == 12
    assert first.resolved_slots["preference"] == "comfort"
    assert len(first.related_routes) > 1
    first_route_id = first.related_routes[0].route_id

    explained = await service.answer(
        AiTravelRequest(
            question="为什么推荐这条？",
            conversation_id=first.conversation_id,
        )
    )
    assert explained.mode == AiMode.EXPLAIN
    assert explained.related_routes[0].route_id == first_route_id
    assert explained.used_tools == ["conversation_snapshot", "deepseek"]

    alternative = await service.answer(
        AiTravelRequest(
            question="换一条",
            conversation_id=first.conversation_id,
        )
    )
    assert alternative.mode == AiMode.SUGGEST
    assert alternative.related_routes[0].route_id != first_route_id
    assert alternative.used_tools == ["conversation_snapshot", "deepseek"]
    assert calls == 1

    refreshed = await service.answer(
        AiTravelRequest(
            question="从站点2到站点5怎么走",
            conversation_id=first.conversation_id,
        )
    )
    assert refreshed.resolved_slots["start_station_id"] == 2
    assert refreshed.resolved_slots["end_station_id"] == 5
    assert "recommend_routes" in refreshed.used_tools
    assert calls == 2

    preference_refreshed = await service.answer(
        AiTravelRequest(
            question="改成最快的方案",
            conversation_id=first.conversation_id,
        )
    )
    assert preference_refreshed.mode == AiMode.SUGGEST
    assert preference_refreshed.resolved_slots["preference"] == "fastest"
    assert "recommend_routes" in preference_refreshed.used_tools
    assert calls == 3


@pytest.mark.asyncio
async def test_ai_service_explain_without_snapshot_returns_clarification():
    service = AiTravelService(
        _recommendation_service(),
        client=FakeDeepSeekClient(),
        store=ConversationStore(),
    )

    result = await service.answer(AiTravelRequest(question="为什么推荐这条？"))

    assert result.mode == AiMode.EXPLAIN
    assert result.status == AiTravelStatus.NEEDS_CLARIFICATION
    assert result.missing_fields == ["conversation_id", "context.items"]
    assert result.conversation_id


def test_default_client_is_built_from_loaded_settings(monkeypatch):
    monkeypatch.setattr(
        ai_service_module,
        "settings",
        SimpleNamespace(
            deepseek_api_key="sk-test",
            deepseek_base_url="https://api.deepseek.com",
            deepseek_model="deepseek-v4-flash",
            deepseek_timeout_seconds=20.0,
            deepseek_max_tokens=700,
            deepseek_temperature=0.2,
        ),
    )

    client = AiTravelService._build_default_client()

    assert isinstance(client, DeepSeekClient)
    assert client.config.api_key == "sk-test"
    assert client.config.model == "deepseek-v4-flash"
