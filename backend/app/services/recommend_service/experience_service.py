from __future__ import annotations

from algorithm.recommend import (
    ScoreWeights,
    build_experience_reason,
    calculate_experience_score,
    transfer_score_from_count,
    walk_score_from_minutes,
)
from app.core.intelligence_exceptions import BusinessError
from app.core.intelligence_settings import settings
from app.schemas.passenger_load import LoadLevel
from app.schemas.travel_experience import (
    ExperienceWeights,
    TravelExperienceRequest,
    TravelExperienceResult,
)
from app.services.load_service.service import LOAD_LEVEL_SCORE, PassengerLoadService


class TravelExperienceService:
    def evaluate(self, request: TravelExperienceRequest) -> TravelExperienceResult:
        weights = request.weights or ExperienceWeights(
            w_load=settings.weight_load,
            w_walk=settings.weight_walk,
            w_transfer=settings.weight_transfer,
        )
        total_weight = weights.w_load + weights.w_walk + weights.w_transfer
        if abs(total_weight - 1.0) > 1e-6:
            raise BusinessError(40002, "w_load、w_walk、w_transfer 之和必须为 1", 400)
        level = request.predicted_load_level or self._level_from_rate(
            request.predicted_load_rate or 0.0
        )
        load_score = (
            PassengerLoadService.calculate_load_score(request.predicted_load_rate, level)
            if request.predicted_load_rate is not None
            else LOAD_LEVEL_SCORE[level]
        )
        walk_score = walk_score_from_minutes(request.walk_time_minutes)
        transfer_score = transfer_score_from_count(request.transfer_count)
        score = calculate_experience_score(
            load_score,
            walk_score,
            transfer_score,
            ScoreWeights(
                w_load=weights.w_load,
                w_walk=weights.w_walk,
                w_transfer=weights.w_transfer,
            ),
        )
        return TravelExperienceResult(
            load_score=load_score,
            walk_score=walk_score,
            transfer_score=transfer_score,
            experience_score=score,
            factor_weights=weights,
            factor_values={
                "predicted_load_rate": request.predicted_load_rate,
                "predicted_load_level": level.value,
                "walk_time_minutes": request.walk_time_minutes,
                "transfer_count": request.transfer_count,
            },
            reason=build_experience_reason(
                level.value,
                request.walk_time_minutes,
                request.transfer_count,
            ),
        )

    @staticmethod
    def _level_from_rate(rate: float) -> LoadLevel:
        if rate <= 0.60:
            return LoadLevel.SEATS_AVAILABLE
        if rate <= 0.85:
            return LoadLevel.STANDING_AVAILABLE
        if rate <= 1.0:
            return LoadLevel.LIMITED_STANDING
        return LoadLevel.OVERCROWDED