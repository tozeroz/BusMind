from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha1
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.cache import CacheProvider, memory_cache_provider
from app.cache.cache_keys import bus_arrival_service


LOAD_LEVEL = {
    "SEA": "seats_available",
    "SDA": "standing_available",
    "LSD": "limited_standing",
}
LOAD_SCORE = {"SEA": 100.0, "SDA": 70.0, "LSD": 35.0}
LOAD_RATE = {"SEA": 0.45, "SDA": 0.72, "LSD": 0.92}
BUS_CAPACITY = {"SD": 80, "DD": 120, "BD": 140}


@dataclass(frozen=True, slots=True)
class SyncResult:
    processed: int = 0
    skipped: int = 0


class CacheSyncService:
    def __init__(self, cache: CacheProvider | None = None) -> None:
        self.cache = cache or memory_cache_provider

    def sync_bus_arrival(
        self,
        db: Session,
        bus_stop_code: str,
        service_no: str,
    ) -> SyncResult:
        cached = self.cache.get(bus_arrival_service(bus_stop_code, service_no))
        if not isinstance(cached, dict):
            return SyncResult(skipped=1)

        station_id = _lookup_scalar(
            db,
            "SELECT station_id FROM bus_station WHERE bus_stop_code = :bus_stop_code",
            {"bus_stop_code": bus_stop_code},
        )
        line = db.execute(
            text(
                """
                SELECT line_id, line_name
                FROM bus_line
                WHERE service_no = :service_no
                ORDER BY direction, line_id
                LIMIT 1
                """
            ),
            {"service_no": service_no},
        ).mappings().first()
        if station_id is None or line is None:
            return SyncResult(skipped=1)

        row = _build_arrival_row(cached, int(station_id), int(line["line_id"]), str(line["line_name"]))
        _upsert_bus_vehicle(db, row)
        _upsert_eta_status(db, row)
        _upsert_load_status(db, row)
        _insert_lta_arrival(db, row)
        return SyncResult(processed=1)


def _lookup_scalar(db: Session, sql: str, params: dict[str, object]) -> object | None:
    return db.execute(text(sql), params).scalar_one_or_none()


def _build_arrival_row(payload: dict[str, Any], station_id: int, line_id: int, line_name: str) -> dict[str, Any]:
    load_code = str(payload.get("load_code") or "").upper()
    bus_type = str(payload.get("bus_type") or "").upper()
    capacity = BUS_CAPACITY.get(bus_type, 80)
    load_rate = LOAD_RATE.get(load_code, 0.45)
    vehicle_id = _stable_positive_int(
        "|".join(
            [
                str(payload.get("service_no") or ""),
                str(payload.get("bus_stop_code") or ""),
                str(payload.get("estimated_arrival") or ""),
                bus_type,
            ]
        )
    )
    query_time = _parse_datetime(payload.get("query_time")) or datetime.now()
    estimated_arrival = _parse_datetime(payload.get("estimated_arrival"))
    eta_minutes = _optional_float(payload.get("eta_minutes"))
    return {
        "query_time": query_time,
        "station_id": station_id,
        "bus_stop_code": payload.get("bus_stop_code"),
        "service_no": payload.get("service_no"),
        "line_id": line_id,
        "line_name": line_name,
        "operator": payload.get("operator"),
        "visit_order": 1,
        "estimated_arrival": estimated_arrival,
        "eta_minutes": eta_minutes,
        "duration_ms": int(eta_minutes * 60 * 1000) if eta_minutes is not None else None,
        "monitored": 1 if payload.get("monitored") else 0,
        "vehicle_id": vehicle_id,
        "vehicle_code": f"V{vehicle_id}",
        "vehicle_latitude": _optional_float(payload.get("latitude")),
        "vehicle_longitude": _optional_float(payload.get("longitude")),
        "visit_number": 1,
        "load_code": load_code or None,
        "load_level": LOAD_LEVEL.get(load_code, "standing_available"),
        "load_score": LOAD_SCORE.get(load_code, 60.0),
        "load_rate": load_rate,
        "onboard_count": round(capacity * load_rate),
        "capacity": capacity,
        "bus_type": bus_type or None,
        "feature": payload.get("feature"),
        "speed_kph": None,
    }


def _stable_positive_int(value: str) -> int:
    return int(sha1(value.encode("utf-8")).hexdigest()[:12], 16)


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _optional_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _upsert_bus_vehicle(db: Session, row: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO bus_vehicle (
                vehicle_id, vehicle_code, line_id, service_no, line_name,
                current_station_id, next_station_id, longitude, latitude,
                onboard_count, capacity, load_level, load_code, load_score,
                operation_status, data_status, last_reported_at
            ) VALUES (
                :vehicle_id, :vehicle_code, :line_id, :service_no, :line_name,
                :station_id, :station_id, :vehicle_longitude, :vehicle_latitude,
                :onboard_count, :capacity, :load_level, :load_code, :load_score,
                'normal', 'realtime', :query_time
            )
            ON DUPLICATE KEY UPDATE
                line_id = VALUES(line_id),
                service_no = VALUES(service_no),
                line_name = VALUES(line_name),
                current_station_id = VALUES(current_station_id),
                next_station_id = VALUES(next_station_id),
                longitude = VALUES(longitude),
                latitude = VALUES(latitude),
                onboard_count = VALUES(onboard_count),
                capacity = VALUES(capacity),
                load_level = VALUES(load_level),
                load_code = VALUES(load_code),
                load_score = VALUES(load_score),
                data_status = VALUES(data_status),
                last_reported_at = VALUES(last_reported_at)
            """
        ),
        row,
    )


def _upsert_eta_status(db: Session, row: dict[str, Any]) -> None:
    if row["eta_minutes"] is None:
        return
    db.execute(
        text(
            """
            INSERT INTO bus_eta_status (
                vehicle_id, line_id, target_station_id, bus_stop_code, query_time,
                eta_minutes, arrival_time, speed_kph, data_source
            ) VALUES (
                :vehicle_id, :line_id, :station_id, :bus_stop_code, :query_time,
                :eta_minutes, :estimated_arrival, :speed_kph, 'lta_bus_arrival_cache'
            )
            ON DUPLICATE KEY UPDATE
                eta_minutes = VALUES(eta_minutes),
                arrival_time = VALUES(arrival_time),
                speed_kph = VALUES(speed_kph),
                data_source = VALUES(data_source)
            """
        ),
        row,
    )


def _upsert_load_status(db: Session, row: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO bus_load_status (
                vehicle_id, line_id, station_id, bus_stop_code, query_time,
                load_code, load_level, load_score, load_rate, onboard_count,
                capacity, confidence, data_source
            ) VALUES (
                :vehicle_id, :line_id, :station_id, :bus_stop_code, :query_time,
                :load_code, :load_level, :load_score, :load_rate, :onboard_count,
                :capacity, 0.90, 'lta_bus_arrival_cache'
            )
            ON DUPLICATE KEY UPDATE
                load_code = VALUES(load_code),
                load_level = VALUES(load_level),
                load_score = VALUES(load_score),
                load_rate = VALUES(load_rate),
                onboard_count = VALUES(onboard_count),
                capacity = VALUES(capacity),
                confidence = VALUES(confidence),
                data_source = VALUES(data_source)
            """
        ),
        row,
    )


def _insert_lta_arrival(db: Session, row: dict[str, Any]) -> None:
    db.execute(
        text(
            """
            INSERT INTO lta_bus_arrival (
                query_time, station_id, bus_stop_code, service_no, line_id, line_name,
                operator, visit_order, estimated_arrival, eta_minutes,
                duration_ms, monitored, vehicle_id, vehicle_latitude, vehicle_longitude,
                visit_number, load_code, load_level, load_score,
                load_rate, onboard_count, capacity, bus_type, feature, speed_kph
            ) VALUES (
                :query_time, :station_id, :bus_stop_code, :service_no, :line_id, :line_name,
                :operator, :visit_order, :estimated_arrival, :eta_minutes,
                :duration_ms, :monitored, :vehicle_id, :vehicle_latitude, :vehicle_longitude,
                :visit_number, :load_code, :load_level, :load_score,
                :load_rate, :onboard_count, :capacity, :bus_type, :feature, :speed_kph
            )
            ON DUPLICATE KEY UPDATE
                estimated_arrival = VALUES(estimated_arrival),
                eta_minutes = VALUES(eta_minutes),
                load_level = VALUES(load_level),
                load_score = VALUES(load_score)
            """
        ),
        row,
    )
