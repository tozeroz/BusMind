import pytest

from backend.app.schemas.ai_travel import AiMode, AiTravelRequest
from backend.app.schemas.recommendation import RecommendRoutesRequest
from backend.app.services.ai_service import AiTravelService
from backend.app.services.eta_service import EtaService
from backend.app.services.intelligence_gateway import DemoIntelligenceGateway
from backend.app.services.load_service import PassengerLoadService
from backend.app.services.recommend_service import RecommendationService, TravelExperienceService


class FakeDeepSeekClient:
    async def chat(self, messages):
        assert messages[0]["role"] == "system"
        return "建议选择体验分更高且车内更宽松的路线。"


@pytest.mark.asyncio
async def test_ai_service_uses_deepseek_when_available():
    gateway = DemoIntelligenceGateway()
    recommendation = RecommendationService(
        gateway,
        EtaService(gateway),
        PassengerLoadService(gateway),
        TravelExperienceService(),
    )
    service = AiTravelService(recommendation, client=FakeDeepSeekClient())
    result = await service.answer(
        AiTravelRequest(
            mode=AiMode.SUGGEST,
            start_station_id=1,
            end_station_id=12,
            question="怎么走？",
        )
    )
    assert result.fallback is False
    assert "体验分" in result.answer
