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
from app.schemas.simulation import (
    LtaBusArrivalRefreshRequest,
    LtaBusArrivalRefreshResult,
    PredictionResultUpdateRequest,
    PredictionResultUpdateResult,
    PredictionType,
    VehicleRunStatus,
    VehicleStatusUpdateRequest,
    VehicleStatusUpdateResult,
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
    "ExperienceWeights",
    "LoadLevel",
    "LtaBusArrivalRefreshRequest",
    "LtaBusArrivalRefreshResult",
    "PassengerLoadPredictionRequest",
    "PassengerLoadPredictionResult",
    "PredictionResultUpdateRequest",
    "PredictionResultUpdateResult",
    "PredictionType",
    "Preference",
    "RecommendRoutesRequest",
    "RecommendRoutesResult",
    "RecommendType",
    "RouteRecommendation",
    "TravelExperienceRequest",
    "TravelExperienceResult",
    "VehicleRunStatus",
    "VehicleStatusUpdateRequest",
    "VehicleStatusUpdateResult",
    "WalkingTimeRequest",
    "WalkingTimeResult",
]