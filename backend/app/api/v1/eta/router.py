from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.v1.dependencies import get_eta_service
from app.core.api_response import ApiResponse, success_response
from app.services.eta_service import EtaService

router = APIRouter(tags=["ETA"])


@router.get(
    "/eta",
    response_model=ApiResponse,
    summary="查询 LTA 实时 ETA（预计到站时间）",
    description=(
        "基于 LTA Bus Arrival 实时数据（MySQL 缓存）返回指定车辆到目标站点的预计到站时间。"
        "数据来源为 LTA 实时接口 + 仿真覆盖 + 规则兜底，非自研 ETA 预测模型。"
        "响应字段 `predicted_eta_minutes` / `model_version` 为历史兼容命名，不代表 ML 预测。"
    ),
)
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