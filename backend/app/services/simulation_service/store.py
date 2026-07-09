from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from backend.app.core.time_utils import now_local


@dataclass(frozen=True, slots=True)
class PredictionOverride:
    prediction_type: str
    payload: dict[str, Any]
    source: str
    updated_at: datetime
    expires_at: datetime

    @property
    def expired(self) -> bool:
        return now_local() >= self.expires_at


class SimulationStateStore:
    """Process-local state used by the engineer-B simulation/update interfaces.

    This store deliberately does not create or modify database tables owned by
    engineer A or the data engineer.  A production repository can replace it
    later without changing the public API contracts.
    """

    def __init__(self) -> None:
        self._eta: dict[tuple[int, int, int | None], PredictionOverride] = {}
        self._load: dict[tuple[int, int | None, int | None], PredictionOverride] = {}
        self._lock = RLock()

    def clear(self) -> None:
        with self._lock:
            self._eta.clear()
            self._load.clear()

    def set_eta(
        self,
        *,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None,
        payload: dict[str, Any],
        source: str,
        expires_in_seconds: int,
    ) -> PredictionOverride:
        record = self._build_record(
            "eta", payload, source, expires_in_seconds
        )
        with self._lock:
            self._eta[(vehicle_id, target_station_id, line_id)] = record
        return record

    def get_eta(
        self,
        *,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None,
    ) -> PredictionOverride | None:
        keys = [
            (vehicle_id, target_station_id, line_id),
            (vehicle_id, target_station_id, None),
        ]
        with self._lock:
            for key in keys:
                record = self._eta.get(key)
                if record is None:
                    continue
                if record.expired:
                    self._eta.pop(key, None)
                    continue
                return record
        return None

    def set_load(
        self,
        *,
        line_id: int,
        station_id: int | None,
        vehicle_id: int | None,
        payload: dict[str, Any],
        source: str,
        expires_in_seconds: int,
    ) -> PredictionOverride:
        record = self._build_record(
            "passenger_load", payload, source, expires_in_seconds
        )
        with self._lock:
            self._load[(line_id, station_id, vehicle_id)] = record
        return record

    def get_load(
        self,
        *,
        line_id: int,
        station_id: int | None,
        vehicle_id: int | None,
    ) -> PredictionOverride | None:
        keys = [
            (line_id, station_id, vehicle_id),
            (line_id, station_id, None),
            (line_id, None, vehicle_id),
            (line_id, None, None),
        ]
        with self._lock:
            for key in keys:
                record = self._load.get(key)
                if record is None:
                    continue
                if record.expired:
                    self._load.pop(key, None)
                    continue
                return record
        return None

    @staticmethod
    def _build_record(
        prediction_type: str,
        payload: dict[str, Any],
        source: str,
        expires_in_seconds: int,
    ) -> PredictionOverride:
        updated_at = now_local()
        return PredictionOverride(
            prediction_type=prediction_type,
            payload=dict(payload),
            source=source,
            updated_at=updated_at,
            expires_at=updated_at + timedelta(seconds=expires_in_seconds),
        )


simulation_state_store = SimulationStateStore()
