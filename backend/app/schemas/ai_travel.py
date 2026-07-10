from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from app.schemas.common import StrictModel
from app.schemas.recommendation import Preference, RouteRecommendation


class AiMode(StrEnum):
    QA = "qa"
    SUGGEST = "suggest"
    EXPLAIN = "explain"


class AiTravelRequest(StrictModel):
    mode: AiMode
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    route_id: str | None = Field(default=None, max_length=100)
    start_station_id: int | None = Field(default=None, gt=0)
    end_station_id: int | None = Field(default=None, gt=0)
    preference: Preference = Preference.BALANCED
    context: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AiTravelRequest":
        if self.mode == AiMode.QA and not self.question:
            raise ValueError("qa mode requires question")
        if self.mode == AiMode.EXPLAIN and not self.route_id and not self.context:
            raise ValueError("explain mode requires route_id or context")
        if self.mode == AiMode.SUGGEST:
            has_station_pair = self.start_station_id is not None and self.end_station_id is not None
            if not has_station_pair and not self.context:
                raise ValueError("suggest mode requires start/end stations or context")
        return self


class AiTravelResult(StrictModel):
    answer: str
    mode: AiMode
    used_tools: list[str]
    related_routes: list[RouteRecommendation]
    reminders: list[str]
    fallback: bool