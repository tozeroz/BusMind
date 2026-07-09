from __future__ import annotations

from fastapi import APIRouter, Depends, Path

from backend.app.api.v1.dependencies import get_simulation_service
from backend.app.core.api_response import ApiResponse, success_response
from backend.app.schemas.simulation import (
    LtaBusArrivalRefreshRequest,
    PredictionResultUpdateRequest,
    VehicleStatusUpdateRequest,
)
from backend.app.services.simulation_service import SimulationService

router = APIRouter(prefix="/simulation", tags=["Simulation and Prediction Updates"])


@router.patch("/vehicle-status/{vehicle_id}", response_model=ApiResponse)
async def update_vehicle_status(
    request: VehicleStatusUpdateRequest,
    vehicle_id: int = Path(gt=0),
    service: SimulationService = Depends(get_simulation_service),
) -> ApiResponse:
    result = await service.update_vehicle_status(vehicle_id, request)
    return success_response(result, "req_sim_vehicle")


@router.post("/prediction-results", response_model=ApiResponse)
async def update_prediction_result(
    request: PredictionResultUpdateRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> ApiResponse:
    result = service.update_prediction_result(request)
    return success_response(result, "req_sim_prediction")


@router.post("/lta-bus-arrival/refresh", response_model=ApiResponse)
async def refresh_lta_bus_arrival(
    request: LtaBusArrivalRefreshRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> ApiResponse:
    result = await service.refresh_from_lta(request)
    return success_response(result, "req_lta_arrival")
