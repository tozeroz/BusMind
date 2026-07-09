from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_load_service
from app.core.api_response import ApiResponse, success_response
from app.schemas.passenger_load import PassengerLoadPredictionRequest
from app.services.load_service import PassengerLoadService

router = APIRouter(tags=["Passenger Load"])


@router.post("/passenger-load-prediction", response_model=ApiResponse)
async def predict_passenger_load(
    request: PassengerLoadPredictionRequest,
    service: PassengerLoadService = Depends(get_load_service),
) -> ApiResponse:
    result = await service.predict(request)
    return success_response(result, "req_load")
