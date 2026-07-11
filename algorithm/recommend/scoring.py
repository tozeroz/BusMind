"""Pure scoring functions for BusMind recommendation ranking."""

from __future__ import annotations

from dataclasses import dataclass


NEUTRAL_SCORE = 60.0


@dataclass(frozen=True, slots=True)
class ScoreWeights:
    w_eta: float = 0.20
    w_load: float = 0.18
    w_walk: float = 0.12
    w_transfer: float = 0.08
    w_frequency: float = 0.12
    w_flow: float = 0.10
    w_congestion: float = 0.10
    w_reliability: float = 0.10

    def validate(self) -> None:
        values = (
            self.w_eta,
            self.w_load,
            self.w_walk,
            self.w_transfer,
            self.w_frequency,
            self.w_flow,
            self.w_congestion,
            self.w_reliability,
        )
        if min(values) < 0:
            raise ValueError("weights must be non-negative")
        if abs(sum(values) - 1.0) > 1e-6:
            raise ValueError("weights must sum to 1.0")


def _clamp_score(value: float) -> float:
    return float(round(max(0.0, min(100.0, value)), 1))


def eta_score_from_minutes(eta_minutes: float | None) -> float:
    if eta_minutes is None:
        return NEUTRAL_SCORE
    if eta_minutes < 0:
        raise ValueError("eta_minutes must be non-negative")
    return _clamp_score(100.0 - eta_minutes * 2.4)


def load_score_from_rate(load_rate: float | None) -> float:
    if load_rate is None:
        return NEUTRAL_SCORE
    if not 0 <= load_rate <= 2:
        raise ValueError("load_rate must be between 0 and 2")
    return _clamp_score(100.0 - min(load_rate, 2.0) * 55.0)


def walk_score_from_minutes(walk_time_minutes: float) -> float:
    if walk_time_minutes < 0:
        raise ValueError("walk_time_minutes must be non-negative")
    return _clamp_score(100.0 - walk_time_minutes * 2.5)


def transfer_score_from_count(transfer_count: int) -> float:
    if transfer_count < 0:
        raise ValueError("transfer_count must be non-negative")
    return _clamp_score(100.0 - transfer_count * 30.0)


def frequency_score_from_minutes(avg_service_frequency: float | None) -> float:
    if avg_service_frequency is None:
        return NEUTRAL_SCORE
    if avg_service_frequency < 0:
        raise ValueError("avg_service_frequency must be non-negative")
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


def flow_score_from_context(
    station_flow_mean: float | None,
    station_flow_level: str | None = None,
) -> float:
    if station_flow_mean is not None:
        if station_flow_mean < 0:
            raise ValueError("station_flow_mean must be non-negative")
        if station_flow_mean <= 300:
            return 92.0
        if station_flow_mean <= 700:
            return 78.0
        if station_flow_mean <= 1200:
            return 62.0
        if station_flow_mean <= 1800:
            return 44.0
        return 28.0

    level = (station_flow_level or "").strip().lower()
    if level == "low":
        return 90.0
    if level == "medium":
        return 65.0
    if level == "high":
        return 35.0
    return NEUTRAL_SCORE


def congestion_score_to_comfort(congestion_score: float | None) -> float:
    if congestion_score is None:
        return NEUTRAL_SCORE
    if not 0 <= congestion_score <= 1:
        raise ValueError("congestion_score must be between 0 and 1")
    return _clamp_score(100.0 - congestion_score * 70.0)


def reliability_score_from_value(reliability_score: float | None) -> float:
    if reliability_score is None:
        return NEUTRAL_SCORE
    if not 0 <= reliability_score <= 100:
        raise ValueError("reliability_score must be between 0 and 100")
    return _clamp_score(reliability_score)


def calculate_experience_score(
    *,
    eta_score: float,
    load_score: float,
    walk_score: float,
    transfer_score: float,
    frequency_score: float,
    flow_score: float,
    congestion_score: float,
    reliability_score: float,
    weights: ScoreWeights,
) -> float:
    weights.validate()
    scores = (
        eta_score,
        load_score,
        walk_score,
        transfer_score,
        frequency_score,
        flow_score,
        congestion_score,
        reliability_score,
    )
    for score in scores:
        if not 0 <= score <= 100:
            raise ValueError("all score components must be between 0 and 100")
    value = (
        weights.w_eta * eta_score
        + weights.w_load * load_score
        + weights.w_walk * walk_score
        + weights.w_transfer * transfer_score
        + weights.w_frequency * frequency_score
        + weights.w_flow * flow_score
        + weights.w_congestion * congestion_score
        + weights.w_reliability * reliability_score
    )
    return round(value, 1)
