from app.schemas.ai_travel import AiMode, AiTravelRequest, AiTravelResult
from app.schemas.eta import EtaResult
from app.schemas.passenger_load import (
    LoadLevel,
    PassengerLoadPredictionRequest,
    PassengerLoadPredictionResult,
)
from app.schemas.recommendation import (
    Preference,
    RecommendRoutesRequest,
    RecommendRoutesResult,
    RecommendType,
    RouteRecommendation,
)
from app.schemas.travel_experience import (
    ExperienceWeights,
    TravelExperienceRequest,
    TravelExperienceResult,
)
from app.schemas.walking import WalkingTimeRequest, WalkingTimeResult

__all__ = [
    "AiMode",
    "AiTravelRequest",
    "AiTravelResult",
    "EtaResult",
    "LoadLevel",
    "PassengerLoadPredictionRequest",
    "PassengerLoadPredictionResult",
    "Preference",
    "RecommendRoutesRequest",
    "RecommendRoutesResult",
    "RecommendType",
    "RouteRecommendation",
    "ExperienceWeights",
    "TravelExperienceRequest",
    "TravelExperienceResult",
    "WalkingTimeRequest",
    "WalkingTimeResult",
]
