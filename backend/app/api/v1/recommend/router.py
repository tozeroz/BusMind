from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.v1.dependencies import (
    get_experience_service,
    get_recommendation_service,
    get_walking_service,
)
from backend.app.core.api_response import ApiResponse, success_response
from backend.app.schemas.recommendation import RecommendRoutesRequest
from backend.app.schemas.travel_experience import TravelExperienceRequest
from backend.app.schemas.walking import WalkingTimeRequest
from backend.app.services.recommend_service import (
    RecommendationService,
    TravelExperienceService,
    WalkingTimeService,
)

router = APIRouter(tags=["Travel Experience and Recommendation"])


@router.post("/walking-time-estimation", response_model=ApiResponse)
async def estimate_walking_time(
    request: WalkingTimeRequest,
    service: WalkingTimeService = Depends(get_walking_service),
) -> ApiResponse:
    result = await service.estimate(request)
    return success_response(result, "req_walk")


@router.post("/travel-experience/evaluate", response_model=ApiResponse)
async def evaluate_travel_experience(
    request: TravelExperienceRequest,
    service: TravelExperienceService = Depends(get_experience_service),
) -> ApiResponse:
    result = service.evaluate(request)
    return success_response(result, "req_exp")


@router.post("/recommend-routes", response_model=ApiResponse)
async def recommend_routes(
    request: RecommendRoutesRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> ApiResponse:
    result = await service.recommend(request)
    return success_response(result, "req_rec")
