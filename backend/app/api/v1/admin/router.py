from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.dependencies import (
    get_cache_sync_service,
    get_db,
    get_lta_collector_service,
)
from app.cache.cache_keys import (
    bus_arrival_service,
    bus_arrival_stop,
    traffic_speed_bands_latest,
)
from app.core.api_response import ApiResponse, success_response
from app.core.intelligence_exceptions import ModelUnavailableError
from app.core.time_utils import now_local
from app.schemas.admin_refresh import (
    LtaBusArrivalAdminRefreshRequest,
    LtaRefreshAdminResult,
    LtaTrafficSpeedBandsAdminRefreshRequest,
)
from app.services.collector_service.service import LtaCollectorService
from app.services.sync_service.service import CacheSyncService

router = APIRouter(prefix="/admin/lta", tags=["Admin LTA Refresh"])


@router.post("/bus-arrival/refresh", response_model=ApiResponse)
async def refresh_bus_arrival(
    request: LtaBusArrivalAdminRefreshRequest,
    collector: LtaCollectorService | None = Depends(get_lta_collector_service),
    sync_service: CacheSyncService = Depends(get_cache_sync_service),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if collector is None:
        raise ModelUnavailableError(50320, "未配置 LTA_ACCOUNT_KEY，无法调用 LTA Bus Arrival API")

    payloads = await collector.refresh_bus_arrival(
        request.bus_stop_code,
        request.service_no,
    )
    synced = 0
    skipped = 0
    if request.sync_to_db:
        try:
            service_nos = _service_nos_from_payloads(payloads, request.service_no)
            for service_no in service_nos:
                result = sync_service.sync_bus_arrival(db, request.bus_stop_code, service_no)
                synced += result.processed
                skipped += result.skipped
            db.commit()
        except Exception:
            db.rollback()
            raise

    cache_keys = [bus_arrival_stop(request.bus_stop_code)]
    if request.service_no:
        cache_keys.append(bus_arrival_service(request.bus_stop_code, request.service_no))
    result = LtaRefreshAdminResult(
        dataset="lta_bus_arrival",
        collected=len(payloads),
        synced=synced,
        skipped=skipped,
        cache_keys=cache_keys,
        refreshed_at=now_local(),
    )
    return success_response(result, "req_admin_lta_arrival")


@router.post("/traffic-speed-bands/refresh", response_model=ApiResponse)
async def refresh_traffic_speed_bands(
    request: LtaTrafficSpeedBandsAdminRefreshRequest,
    collector: LtaCollectorService | None = Depends(get_lta_collector_service),
    sync_service: CacheSyncService = Depends(get_cache_sync_service),
    db: Session = Depends(get_db),
) -> ApiResponse:
    if collector is None:
        raise ModelUnavailableError(50320, "未配置 LTA_ACCOUNT_KEY，无法调用 LTA Traffic Speed Bands API")

    payloads = await collector.refresh_traffic_speed_bands()
    synced = 0
    skipped = 0
    if request.sync_to_db:
        try:
            sync_result = sync_service.sync_traffic_speed_bands(db, payloads)
            synced = sync_result.processed
            skipped = sync_result.skipped
            db.commit()
        except Exception:
            db.rollback()
            raise

    result = LtaRefreshAdminResult(
        dataset="traffic_speed_bands",
        collected=len(payloads),
        synced=synced,
        skipped=skipped,
        cache_keys=[traffic_speed_bands_latest()],
        refreshed_at=now_local(),
    )
    return success_response(result, "req_admin_traffic_speed")


def _service_nos_from_payloads(
    payloads: list[dict[str, object]],
    requested_service_no: str | None,
) -> list[str]:
    if requested_service_no:
        return [requested_service_no]
    service_nos = {
        str(payload.get("service_no") or "").strip()
        for payload in payloads
        if str(payload.get("service_no") or "").strip()
    }
    return sorted(service_nos)
