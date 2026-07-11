from __future__ import annotations

from algorithm.recommend import (
    ScoreWeights,
    build_experience_reason,
    calculate_experience_score,
    congestion_score_to_comfort,
    eta_score_from_minutes,
    flow_score_from_context,
    frequency_score_from_minutes,
    reliability_score_from_value,
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
            w_eta=settings.weight_eta,
            w_load=settings.weight_load,
            w_walk=settings.weight_walk,
            w_transfer=settings.weight_transfer,
            w_frequency=settings.weight_frequency,
            w_flow=settings.weight_flow,
            w_congestion=settings.weight_congestion,
            w_reliability=settings.weight_reliability,
        )
        total_weight = (
            weights.w_eta
            + weights.w_load
            + weights.w_walk
            + weights.w_transfer
            + weights.w_frequency
            + weights.w_flow
            + weights.w_congestion
            + weights.w_reliability
        )
        if abs(total_weight - 1.0) > 1e-6:
            raise BusinessError(40002, "travel experience weights must sum to 1", 400)

        level = request.predicted_load_level or self._level_from_rate(
            request.predicted_load_rate or 0.0
        )
        eta_score = eta_score_from_minutes(request.eta_minutes)
        load_score = (
            PassengerLoadService.calculate_load_score(request.predicted_load_rate, level)
            if request.predicted_load_rate is not None
            else LOAD_LEVEL_SCORE[level]
        )
        walk_score = walk_score_from_minutes(request.walk_time_minutes)
        transfer_score = transfer_score_from_count(request.transfer_count)
        frequency_score = frequency_score_from_minutes(request.avg_service_frequency)
        flow_score = flow_score_from_context(
            request.station_flow_mean,
            request.station_flow_level,
        )
        congestion_score = congestion_score_to_comfort(request.congestion_score)
        reliability_score = reliability_score_from_value(request.reliability_score)

        score = calculate_experience_score(
            eta_score=eta_score,
            load_score=load_score,
            walk_score=walk_score,
            transfer_score=transfer_score,
            frequency_score=frequency_score,
            flow_score=flow_score,
            congestion_score=congestion_score,
            reliability_score=reliability_score,
            weights=ScoreWeights(
                w_eta=weights.w_eta,
                w_load=weights.w_load,
                w_walk=weights.w_walk,
                w_transfer=weights.w_transfer,
                w_frequency=weights.w_frequency,
                w_flow=weights.w_flow,
                w_congestion=weights.w_congestion,
                w_reliability=weights.w_reliability,
            ),
        )
        return TravelExperienceResult(
            eta_score=eta_score,
            load_score=load_score,
            walk_score=walk_score,
            transfer_score=transfer_score,
            frequency_score=frequency_score,
            flow_score=flow_score,
            congestion_score=congestion_score,
            reliability_score=reliability_score,
            experience_score=score,
            factor_weights=weights,
            factor_values={
                "eta_minutes": request.eta_minutes,
                "predicted_load_rate": request.predicted_load_rate,
                "predicted_load_level": level.value,
                "walk_time_minutes": request.walk_time_minutes,
                "transfer_count": request.transfer_count,
                "avg_service_frequency": request.avg_service_frequency,
                "station_flow_level": request.station_flow_level,
                "station_flow_mean": request.station_flow_mean,
                "congestion_score": request.congestion_score,
                "reliability_score": request.reliability_score,
            },
            reason=build_experience_reason(
                load_level=level.value,
                eta_minutes=request.eta_minutes,
                walk_time_minutes=request.walk_time_minutes,
                transfer_count=request.transfer_count,
                avg_service_frequency=request.avg_service_frequency,
                station_flow_level=request.station_flow_level,
                congestion_score=request.congestion_score,
                reliability_score=request.reliability_score,
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
