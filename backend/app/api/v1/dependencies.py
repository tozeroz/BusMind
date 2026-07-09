from __future__ import annotations

from app.services.ai_service import AiTravelService
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import get_intelligence_gateway
from app.services.load_service import PassengerLoadService
from app.services.recommend_service import (
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
