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
from backend.app.schemas.simulation import (
    LtaBusArrivalRefreshRequest,
    LtaBusArrivalRefreshResult,
    PredictionResultUpdateRequest,
    PredictionResultUpdateResult,
    PredictionType,
    VehicleRunStatus,
    VehicleStatusUpdateRequest,
    VehicleStatusUpdateResult,
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
