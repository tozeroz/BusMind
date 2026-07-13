from __future__ import annotations

from app.core.intelligence_exceptions import BusinessError
from app.core.intelligence_settings import settings
from app.schemas.passenger_load import LoadLevel
from app.schemas.travel_experience import (
    ExperienceWeights,
    TravelExperienceRequest,
    TravelExperienceResult,
)
from app.services.load_service.service import LOAD_LEVEL_SCORE, PassengerLoadService


NEUTRAL_SCORE = 60.0


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 1)


def _eta_score_from_minutes(eta_minutes: float | None) -> float:
    if eta_minutes is None:
        return NEUTRAL_SCORE
    return _clamp_score(100.0 - eta_minutes * 2.4)


def _walk_score_from_minutes(walk_time_minutes: float) -> float:
    return _clamp_score(100.0 - walk_time_minutes * 2.5)


def _transfer_score_from_count(transfer_count: int) -> float:
    return _clamp_score(100.0 - transfer_count * 30.0)


def _frequency_score_from_minutes(avg_service_frequency: float | None) -> float:
    if avg_service_frequency is None:
        return NEUTRAL_SCORE
    if avg_service_frequency <= 4:
        return 96.0
    if avg_service_frequency <= 6:
        return 88.0
    if avg_service_frequency <= 8:
        return 78.0
    if avg_service_frequency <= 10:
        return 66.0
    if avg_service_frequency <= 12:
        return 54.0
    if avg_service_frequency <= 15:
        return 40.0
    return 25.0


def _flow_score_from_context(station_flow_mean: float | None, station_flow_level: str | None) -> float:
    if station_flow_mean is not None:
        if station_flow_mean <= 300:
            return 92.0
        if station_flow_mean <= 700:
            return 78.0
        if station_flow_mean <= 1200:
            return 62.0
        if station_flow_mean <= 1800:
            return 44.0
        return 28.0
    level = (station_flow_level or "").lower()
    if level == "low":
        return 90.0
    if level == "medium":
        return 65.0
    if level == "high":
        return 35.0
    return NEUTRAL_SCORE


def _congestion_score_to_comfort(congestion_score: float | None) -> float:
    if congestion_score is None:
        return NEUTRAL_SCORE
    pressure = congestion_score if congestion_score <= 1 else congestion_score / 100.0
    return _clamp_score(100.0 - pressure * 70.0)


def _reliability_score_from_value(reliability_score: float | None) -> float:
    if reliability_score is None:
        return NEUTRAL_SCORE
    return _clamp_score(reliability_score)


def _default_experience_weights() -> ExperienceWeights:
    weights = ExperienceWeights(
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
    if total_weight <= 0:
        return ExperienceWeights()
    if abs(total_weight - 1.0) <= 1e-6:
        return weights
    return ExperienceWeights(
        w_eta=weights.w_eta / total_weight,
        w_load=weights.w_load / total_weight,
        w_walk=weights.w_walk / total_weight,
        w_transfer=weights.w_transfer / total_weight,
        w_frequency=weights.w_frequency / total_weight,
        w_flow=weights.w_flow / total_weight,
        w_congestion=weights.w_congestion / total_weight,
        w_reliability=weights.w_reliability / total_weight,
    )


def _build_experience_reason(
    *,
    eta_minutes: float | None,
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
    avg_service_frequency: float | None,
    station_flow_level: str | None,
    congestion_score: float | None,
    reliability_score: float | None,
) -> str:
    parts: list[str] = []
    if eta_minutes is None:
        parts.append("缺少实时 ETA，已使用降级估算")
    else:
        parts.append(f"预计等待约 {eta_minutes:.1f} 分钟")
    parts.append(f"客载状态为 {load_level}")
    parts.append(f"步行约 {walk_time_minutes:.1f} 分钟")
    parts.append("无需换乘" if transfer_count == 0 else f"需要换乘 {transfer_count} 次")
    if avg_service_frequency is not None:
        parts.append(f"平均发车间隔约 {avg_service_frequency:.1f} 分钟")
    if station_flow_level:
        parts.append(f"历史客流等级为 {station_flow_level}")
    if congestion_score is not None:
        parts.append("已结合实时道路拥堵特征")
    if reliability_score is not None:
        parts.append(f"数据可靠性约 {reliability_score:.1f} 分")
    return "；".join(parts) + "。"


class TravelExperienceService:
    def evaluate(self, request: TravelExperienceRequest) -> TravelExperienceResult:
        weights = request.weights or _default_experience_weights()
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
        eta_score = _eta_score_from_minutes(request.eta_minutes)
        load_score = (
            PassengerLoadService.calculate_load_score(request.predicted_load_rate, level)
            if request.predicted_load_rate is not None
            else LOAD_LEVEL_SCORE[level]
        )
        walk_score = _walk_score_from_minutes(request.walk_time_minutes)
        transfer_score = _transfer_score_from_count(request.transfer_count)
        frequency_score = _frequency_score_from_minutes(request.avg_service_frequency)
        flow_score = _flow_score_from_context(
            request.station_flow_mean,
            request.station_flow_level,
        )
        congestion_score = _congestion_score_to_comfort(request.congestion_score)
        reliability_score = _reliability_score_from_value(request.reliability_score)

        score = round(
            weights.w_eta * eta_score
            + weights.w_load * load_score
            + weights.w_walk * walk_score
            + weights.w_transfer * transfer_score
            + weights.w_frequency * frequency_score
            + weights.w_flow * flow_score
            + weights.w_congestion * congestion_score
            + weights.w_reliability * reliability_score,
            1,
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
            reason=_build_experience_reason(
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
