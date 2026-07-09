import pytest

from app.schemas.ai_travel import AiMode, AiTravelRequest
from app.schemas.recommendation import RecommendRoutesRequest
from app.services.ai_service import AiTravelService
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import DemoIntelligenceGateway
from app.services.load_service import PassengerLoadService
from app.services.recommend_service import RecommendationService, TravelExperienceService


class FakeDeepSeekClient:
    async def chat(self, messages):
        assert messages[0]["role"] == "system"
        return "å»ºe®®éæ©a½éªåæ´é«ae½¦åæ´å®½æ¾çe·¯çºã?


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
            question="æa¹eµï¼",
        )
    )
    assert result.fallback is False
    assert "a½éªå? in result.answer
