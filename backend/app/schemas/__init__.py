from backend.app.schemas.ai_travel import AiMode, AiTravelRequest, AiTravelResult
from backend.app.schemas.eta import EtaResult
from backend.app.schemas.passenger_load import (
    LoadLevel,
    PassengerLoadPredictionRequest,
    PassengerLoadPredictionResult,
)
from backend.app.schemas.recommendation import (
    Preference,
    RecommendRoutesRequest,
    RecommendRoutesResult,
    RecommendType,
    RouteRecommendation,
)
from backend.app.schemas.travel_experience import (
    ExperienceWeights,
    TravelExperienceRequest,
    TravelExperienceResult,
)
from backend.app.schemas.walking import WalkingTimeRequest, WalkingTimeResult

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
