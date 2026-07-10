from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_eta_service
from app.core.api_response import ApiResponse, success_response
from app.services.eta_service import EtaService

router = APIRouter(tags=["ETA"])


@router.get("/eta", response_model=ApiResponse)
async def get_eta(
    vehicle_id: Annotated[int, Query(gt=0)],
    target_station_id: Annotated[int, Query(gt=0)],
    line_id: Annotated[int | None, Query(gt=0)] = None,
    query_time: datetime | None = None,
    service: EtaService = Depends(get_eta_service),
) -> ApiResponse:
    result = await service.calculate_eta(
        vehicle_id=vehicle_id,
        target_station_id=target_station_id,
        line_id=line_id,
        query_time=query_time,
    )
    return success_response(result, "req_eta")
