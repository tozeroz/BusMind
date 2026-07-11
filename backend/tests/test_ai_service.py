from types import SimpleNamespace

import pytest

from app.schemas.ai_travel import AiMode, AiTravelRequest
from app.services.ai_service import AiTravelService
from app.services.ai_service import service as ai_service_module
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
    assert "建议选择" in result.answer
    assert any("AI 服务调用失败" in item for item in result.reminders)


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
