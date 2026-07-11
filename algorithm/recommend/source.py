"""Source enums shared by offline and online recommendation flows."""

from __future__ import annotations

from enum import Enum


class FeatureSource(str, Enum):
    OFFLINE_DATA = "offline_data"
    ONLINE_BACKEND = "online_backend"

    @classmethod
    def coerce(cls, value: str | "FeatureSource" | None) -> "FeatureSource":
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.ONLINE_BACKEND
        normalized = str(value).strip().lower()
        for item in cls:
            if item.value == normalized:
                return item
        raise ValueError(f"unsupported feature source: {value}")
