from __future__ import annotations

from app.core.intelligence_settings import settings
from app.services.ai_service import AiTravelService
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import get_intelligence_gateway
from app.services.load_service import PassengerLoadService
from app.services.lta_service import LtaDataMallClient, LtaDataMallConfig
from app.services.recommend_service import (
    RecommendationService,
    TravelExperienceService,
    WalkingTimeService,
)
from app.services.simulation_service import (
    SimulationService,
    simulation_state_store,
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


def get_simulation_service() -> SimulationService:
    lta_client = None
    if settings.lta_account_key:
        lta_client = LtaDataMallClient(
            LtaDataMallConfig(
                account_key=settings.lta_account_key,
                base_url=settings.lta_base_url,
                timeout_seconds=settings.lta_timeout_seconds,
            )
        )
    return SimulationService(
        gateway=get_intelligence_gateway(),
        store=simulation_state_store,
        lta_client=lta_client,
    )