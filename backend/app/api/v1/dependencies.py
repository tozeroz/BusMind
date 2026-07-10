from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from fastapi.params import Depends as DependsMarker
from sqlalchemy.orm import Session

from app.core.intelligence_settings import settings
from app.db.session import SessionLocal
from app.services.ai_service import AiTravelService
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import get_intelligence_gateway
from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.load_service import PassengerLoadService
from app.services.lta_service import LtaDataMallClient, LtaDataMallConfig
from app.services.collector_service.service import LtaCollectorService
from app.services.recommend_service import (
    RecommendationService,
    TravelExperienceService,
    WalkingTimeService,
)
from app.services.sync_service.service import CacheSyncService
from app.services.simulation_service import (
    SimulationService,
    simulation_state_store,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_transit_gateway(db: Session = Depends(get_db)) -> MySQLTransitGateway:
    return MySQLTransitGateway(db)


def get_eta_service(
    gateway: MySQLTransitGateway = Depends(get_transit_gateway),
) -> EtaService:
    return EtaService(gateway)


def get_load_service(
    gateway: MySQLTransitGateway = Depends(get_transit_gateway),
) -> PassengerLoadService:
    return PassengerLoadService(gateway)


def get_experience_service() -> TravelExperienceService:
    return TravelExperienceService()


def get_walking_service(
    gateway: MySQLTransitGateway = Depends(get_transit_gateway),
) -> WalkingTimeService:
    return WalkingTimeService(gateway)


def get_recommendation_service(
    gateway: MySQLTransitGateway = Depends(get_transit_gateway),
) -> RecommendationService:
    if isinstance(gateway, DependsMarker):
        gateway = get_intelligence_gateway()
    return RecommendationService(
        gateway=gateway,
        eta_service=EtaService(gateway),
        load_service=PassengerLoadService(gateway),
        experience_service=TravelExperienceService(),
    )


def get_ai_service(
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> AiTravelService:
    if isinstance(recommendation_service, DependsMarker):
        recommendation_service = get_recommendation_service()
    return AiTravelService(recommendation_service)


def get_lta_client() -> LtaDataMallClient | None:
    if not settings.lta_account_key:
        return None
    return LtaDataMallClient(
        LtaDataMallConfig(
            account_key=settings.lta_account_key,
            base_url=settings.lta_base_url,
            timeout_seconds=settings.lta_timeout_seconds,
        )
    )


def get_lta_collector_service() -> LtaCollectorService | None:
    lta_client = get_lta_client()
    if lta_client is None:
        return None
    return LtaCollectorService(lta_client)


def get_cache_sync_service() -> CacheSyncService:
    return CacheSyncService()


def get_simulation_service(
    gateway: MySQLTransitGateway = Depends(get_transit_gateway),
) -> SimulationService:
    return SimulationService(
        gateway=gateway,
        store=simulation_state_store,
        lta_client=get_lta_client(),
    )
