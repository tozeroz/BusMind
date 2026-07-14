from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.schemas.common import StrictModel
from app.schemas.recommendation import Preference, RouteRecommendation


class AiMode(StrEnum):
    QA = "qa"
    SUGGEST = "suggest"
    EXPLAIN = "explain"


class AiTravelStatus(StrEnum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    DEGRADED = "degraded"


class AiTravelRequest(StrictModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mode": "suggest",
                    "question": "哪条路线比较舒适？",
                    "start_station_id": 1,
                    "end_station_id": 12,
                    "preference": "balanced",
                },
                {
                    "mode": "qa",
                    "question": "高峰期出行有什么建议？",
                },
            ]
        }
    )

    mode: AiMode
    question: str | None = Field(default=None, min_length=1, max_length=1000)
    route_id: str | None = Field(default=None, max_length=100)
    start_station_id: int | None = Field(default=None, gt=0)
    end_station_id: int | None = Field(default=None, gt=0)
    preference: Preference = Preference.BALANCED
    context: dict[str, Any] | None = None

    @field_validator("preference", mode="before")
    @classmethod
    def normalize_preference(cls, value: Any) -> Any:
        # low_load is kept as an input alias for the existing home-page client.
        if value == Preference.LOW_LOAD or value == Preference.LOW_LOAD.value:
            return Preference.COMFORT
        return value

    @model_validator(mode="after")
    def validate_mode_fields(self) -> "AiTravelRequest":
        if self.mode == AiMode.QA and not self.question:
            raise ValueError("qa mode requires question")
        if self.mode == AiMode.EXPLAIN and not _context_has_valid_route(self.context):
            raise ValueError(
                "explain mode requires context.items with at least one valid route"
            )
        return self


class AiTravelResult(StrictModel):
    answer: str
    mode: AiMode
    status: AiTravelStatus = AiTravelStatus.COMPLETED
    missing_fields: list[str] = Field(default_factory=list)
    used_tools: list[str]
    related_routes: list[RouteRecommendation]
    reminders: list[str]
    fallback: bool


def _context_has_valid_route(context: dict[str, Any] | None) -> bool:
    if not context:
        return False

    candidate: Any = context
    if isinstance(candidate.get("data"), dict):
        candidate = candidate["data"]
    items = candidate.get("items") if isinstance(candidate, dict) else None
    if not isinstance(items, list):
        return False

    for item in items[:10]:
        try:
            RouteRecommendation.model_validate(item)
            return True
        except Exception:
            continue
    return False
