from __future__ import annotations

from backend.app.services.ai_service import AiTravelService
from backend.app.services.eta_service import EtaService
from backend.app.services.intelligence_gateway import get_intelligence_gateway
from backend.app.services.load_service import PassengerLoadService
from backend.app.services.recommend_service import (
    RecommendationService,
    TravelExperienceService,
    WalkingTimeService,
)


def get_eta_service() -> EtaService:
    return EtaService(get_intelligence_gateway())


def get_load_service() -> PassengerLoadService:
    return PassengerLoadService(get_intelligence_gateway())


def get_experience_service() -> TravelExperienceService:
    return TravelExperienceService()


def get_walking_service() -> WalkingTimeService:
    return WalkingTimeService(get_intelligence_gateway())


def get_recommendation_service() -> RecommendationService:
    gateway = get_intelligence_gateway()
    return RecommendationService(
        gateway=gateway,
        eta_service=EtaService(gateway),
        load_service=PassengerLoadService(gateway),
        experience_service=TravelExperienceService(),
    )


def get_ai_service() -> AiTravelService:
    return AiTravelService(get_recommendation_service())
