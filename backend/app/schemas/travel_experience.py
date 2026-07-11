from __future__ import annotations

from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import StrictModel
from app.schemas.passenger_load import LoadLevel


class ExperienceWeights(StrictModel):
    w_eta: float = Field(default=0.20, ge=0, le=1)
    w_load: float = Field(default=0.18, ge=0, le=1)
    w_walk: float = Field(default=0.12, ge=0, le=1)
    w_transfer: float = Field(default=0.08, ge=0, le=1)
    w_frequency: float = Field(default=0.12, ge=0, le=1)
    w_flow: float = Field(default=0.10, ge=0, le=1)
    w_congestion: float = Field(default=0.10, ge=0, le=1)
    w_reliability: float = Field(default=0.10, ge=0, le=1)


class TravelExperienceRequest(StrictModel):
    eta_minutes: float | None = Field(default=None, ge=0, le=240)
    predicted_load_rate: float | None = Field(default=None, ge=0, le=2)
    predicted_load_level: LoadLevel | None = None
    transfer_count: int = Field(ge=0)
    walk_time_minutes: float = Field(ge=0)
    avg_service_frequency: float | None = Field(default=None, ge=0, le=120)
    station_flow_level: str | None = Field(default=None, max_length=20)
    station_flow_mean: float | None = Field(default=None, ge=0)
    congestion_score: float | None = Field(default=None, ge=0, le=1)
    reliability_score: float | None = Field(default=None, ge=0, le=100)
    weights: ExperienceWeights | None = None

    @model_validator(mode="after")
    def load_information_required(self) -> "TravelExperienceRequest":
        if self.predicted_load_rate is None and self.predicted_load_level is None:
            raise ValueError("predicted_load_rate 与 predicted_load_level 至少提供一个")
        return self


class TravelExperienceResult(StrictModel):
    eta_score: float = Field(ge=0, le=100)
    load_score: float = Field(ge=0, le=100)
    walk_score: float = Field(ge=0, le=100)
    transfer_score: float = Field(ge=0, le=100)
    frequency_score: float = Field(ge=0, le=100)
    flow_score: float = Field(ge=0, le=100)
    congestion_score: float = Field(ge=0, le=100)
    reliability_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    factor_weights: ExperienceWeights
    factor_values: dict[str, Any]
    reason: str
