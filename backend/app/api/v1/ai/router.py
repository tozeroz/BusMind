from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.v1.dependencies import get_ai_service
from backend.app.core.api_response import ApiResponse, success_response
from backend.app.schemas.ai_travel import AiTravelRequest
from backend.app.services.ai_service import AiTravelService

router = APIRouter(tags=["AI Travel Assistant"])


@router.post("/ai/travel", response_model=ApiResponse)
async def ai_travel(
    request: AiTravelRequest,
    service: AiTravelService = Depends(get_ai_service),
) -> ApiResponse:
    result = await service.answer(request)
    return success_response(result, "req_ai")
