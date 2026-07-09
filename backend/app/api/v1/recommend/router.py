from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import (
    get_experience_service,
    get_recommendation_service,
    get_walking_service,
)
from app.core.api_response import ApiResponse, success_response
from app.schemas.recommendation import RecommendRoutesRequest
from app.schemas.travel_experience import TravelExperienceRequest
from app.schemas.walking import WalkingTimeRequest
from app.services.recommend_service import (
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
