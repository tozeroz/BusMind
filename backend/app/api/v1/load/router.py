from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_load_service
from app.core.api_response import ApiResponse, success_response
from app.schemas.passenger_load import (
    PassengerLoadPredictionRequest,
    RealtimePassengerLoadRequest,
    RealtimePassengerLoadResult,
)
from app.services.load_service import PassengerLoadService

router = APIRouter(tags=["Passenger Load"])


@router.post(
    "/passenger-load-prediction",
    response_model=ApiResponse,
    summary="查询客载状态（兼容旧路径）",
    description="基于 LTA 实时客载数据返回指定线路/站点/车辆的客载状态。此路径为兼容保留，推荐使用 POST /realtime-passenger-load。",
)
async def predict_passenger_load(
    request: PassengerLoadPredictionRequest,
    service: PassengerLoadService = Depends(get_load_service),
) -> ApiResponse:
    result = await service.predict(request)
    return success_response(result, "req_load")


@router.post(
    "/realtime-passenger-load",
    response_model=ApiResponse,
    summary="查询 LTA 实时客载状态",
    description="基于 LTA Bus Arrival 实时客载字段，返回指定线路/站点/车辆的当前客载状态（load_level、load_rate、onboard_count 等）。数据来源为 LTA 实时接口 + MySQL 缓存，非自研预测模型。",
)
async def get_realtime_passenger_load(
    request: RealtimePassengerLoadRequest,
    service: PassengerLoadService = Depends(get_load_service),
) -> ApiResponse:
    predicted = await service.predict(
        PassengerLoadPredictionRequest(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
            target_time=request.target_time,
            current_onboard_count=request.current_onboard_count,
            capacity=request.capacity,
            weather=request.weather,
        )
    )
    result = RealtimePassengerLoadResult(
        line_id=predicted.line_id,
        station_id=predicted.station_id,
        vehicle_id=predicted.vehicle_id,
        onboard_count=predicted.predicted_onboard_count,
        capacity=predicted.capacity,
        load_rate=predicted.predicted_load_rate,
        load_level=predicted.predicted_load_level,
        load_score=predicted.load_score,
        confidence=predicted.confidence,
        query_time=predicted.predict_time,
        feature_summary=predicted.feature_summary,
        model_version=predicted.model_version,
    )
    return success_response(result, "req_load")