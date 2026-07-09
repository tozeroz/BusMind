from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from app.schemas.common import RouteSegment, StationSummary, StrictModel
from app.schemas.passenger_load import LoadLevel


class Preference(StrEnum):
    BALANCED = "balanced"
    LOW_LOAD = "low_load"
    LESS_WALKING = "less_walking"
    LESS_TRANSFER = "less_transfer"
    FASTEST = "fastest"


class RecommendType(StrEnum):
    BEST_EXPERIENCE = "best_experience"
    LEAST_CROWDED = "least_crowded"
    LEAST_WALKING = "least_walking"
    LEAST_TRANSFER = "least_transfer"
    FASTEST = "fastest"


class RecommendRoutesRequest(StrictModel):
    start_station_id: int | None = Field(default=None, gt=0)
    end_station_id: int | None = Field(default=None, gt=0)
    origin_longitude: float | None = Field(default=None, ge=-180, le=180)
    origin_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    depart_time: datetime | None = None
    preference: Preference = Preference.BALANCED
    allow_transfer: bool = True
    max_transfer_count: int = Field(default=2, ge=0, le=5)
    max_walk_minutes: float | None = Field(default=None, ge=0, le=180)

    @model_validator(mode="after")
    def validate_locations(self) -> "RecommendRoutesRequest":
        has_station_pair = self.start_station_id is not None and self.end_station_id is not None
        has_origin = self.origin_longitude is not None and self.origin_latitude is not None
        has_destination = (
            self.destination_longitude is not None and self.destination_latitude is not None
        )
        if not has_station_pair and not (has_origin and has_destination):
            raise ValueError("åé»æa¾eµ·ç»ç¹ç«ç¼å·ï¼ææa¾å®æ´çeµ·ç»ç¹åæ ")
        if not self.allow_transfer and self.max_transfer_count != 0:
            self.max_transfer_count = 0
        return self


class PredictedLoadSummary(StrictModel):
    predicted_load_rate: float | None = Field(default=None, ge=0, le=1)
    predicted_load_level: LoadLevel
    predicted_onboard_count: int | None = Field(default=None, ge=0)
    capacity: int | None = Field(default=None, gt=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    load_score: float = Field(ge=0, le=100)


class RouteRecommendation(StrictModel):
    route_id: str
    line_ids: list[int]
    segments: list[RouteSegment]
    boarding_station: StationSummary
    alighting_station: StationSummary
    predicted_eta_minutes: float = Field(ge=0)
    predicted_load: PredictedLoadSummary
    walk_time_minutes: float = Field(ge=0)
    ride_time_minutes: float = Field(ge=0)
    total_time_minutes: float = Field(ge=0)
    transfer_count: int = Field(ge=0)
    experience_score: float = Field(ge=0, le=100)
    recommend_types: list[RecommendType] = Field(default_factory=list)
    reason: str


class RecommendRoutesResult(StrictModel):
    items: list[RouteRecommendation]
    best_experience_route_id: str
    fastest_route_id: str
    least_crowded_route_id: str
    least_walking_route_id: str
    least_transfer_route_id: str
    preference: Preference
    generated_at: datetime
