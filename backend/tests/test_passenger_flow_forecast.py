from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.api.v1.history.router import router as history_router
from app.dependencies.auth import get_db
from app.services.passenger_flow_forecast_service import (
    MODEL_VERSION_BASELINE,
    MODEL_VERSION_RIDGE,
    ensure_station_prediction,
)


def _build_database(database_url: str):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE passenger_flow_trend (
                    flow_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_type TEXT NOT NULL,
                    target_id INTEGER NOT NULL,
                    bus_stop_code TEXT,
                    record_time DATETIME NOT NULL,
                    record_hour INTEGER,
                    day_type TEXT,
                    tap_in_volume INTEGER NOT NULL DEFAULT 0,
                    tap_out_volume INTEGER NOT NULL DEFAULT 0,
                    total_flow INTEGER NOT NULL DEFAULT 0,
                    flow_level TEXT,
                    data_source TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE passenger_flow_prediction (
                    prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    prediction_time DATETIME NOT NULL,
                    predict_time DATETIME NOT NULL,
                    predicted_flow INTEGER NOT NULL,
                    crowd_level TEXT NOT NULL,
                    confidence NUMERIC,
                    model_version TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    return engine


def _seed_station_history(db, station_id: int, *, days: int = 21) -> None:
    start = datetime(2026, 6, 1, 0, 0, 0)
    for day_offset in range(days):
        for hour in range(24):
            record_time = start + timedelta(days=day_offset, hours=hour)
            weekday_bonus = 18 if record_time.weekday() < 5 else -6
            peak_bonus = 22 if hour in {7, 8, 18, 19} else 0
            total_flow = 35 + hour * 2 + weekday_bonus + peak_bonus
            tap_in = total_flow // 2
            tap_out = total_flow - tap_in
            db.execute(
                text(
                    """
                    INSERT INTO passenger_flow_trend (
                        target_type, target_id, bus_stop_code, record_time,
                        record_hour, day_type, tap_in_volume, tap_out_volume,
                        total_flow, flow_level, data_source
                    ) VALUES (
                        'station', :station_id, :bus_stop_code, :record_time,
                        :record_hour, :day_type, :tap_in_volume, :tap_out_volume,
                        :total_flow, :flow_level, 'unit_test'
                    )
                    """
                ),
                {
                    "station_id": station_id,
                    "bus_stop_code": f"BS{station_id}",
                    "record_time": record_time,
                    "record_hour": record_time.hour,
                    "day_type": "weekday" if record_time.weekday() < 5 else "weekend",
                    "tap_in_volume": tap_in,
                    "tap_out_volume": tap_out,
                    "total_flow": total_flow,
                    "flow_level": "medium" if total_flow >= 50 else "low",
                },
            )
    db.commit()


def test_ensure_station_prediction_generates_and_reuses_rows(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'forecast_service.sqlite'}"
    engine = _build_database(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()

    try:
        _seed_station_history(db, 1001)
        now = datetime(2026, 7, 10, 9, 30, 0)

        first = ensure_station_prediction(db, 1001, now=now)
        assert first.created == 168
        assert first.deleted == 0
        assert first.reused == 0
        assert first.skipped is False
        assert first.model_version in {MODEL_VERSION_RIDGE, MODEL_VERSION_BASELINE}

        count = db.execute(
            text("SELECT COUNT(*) FROM passenger_flow_prediction WHERE target_type='station' AND target_id='1001'")
        ).scalar_one()
        assert count == 168

        min_max = db.execute(
            text(
                """
                SELECT MIN(predicted_flow) AS min_flow, MAX(predict_time) AS max_predict_time
                FROM passenger_flow_prediction
                WHERE target_type='station' AND target_id='1001'
                """
            )
        ).first()
        assert int(min_max.min_flow) >= 0
        assert str(min_max.max_predict_time).startswith("2026-07-17 08:00:00")

        second = ensure_station_prediction(db, 1001, now=now)
        assert second.created == 0
        assert second.deleted == 0
        assert second.reused == 168
        assert second.reason == "up_to_date"

        count_after = db.execute(
            text("SELECT COUNT(*) FROM passenger_flow_prediction WHERE target_type='station' AND target_id='1001'")
        ).scalar_one()
        assert count_after == 168
    finally:
        db.close()
        engine.dispose()


def test_prediction_api_backfills_station_forecast(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'forecast_api.sqlite'}"
    engine = _build_database(database_url)
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = session_local()

    try:
        _seed_station_history(db, 2002)

        app = FastAPI()
        app.include_router(history_router, prefix="/api/v1")

        def override_get_db():
            try:
                yield db
            finally:
                pass

        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)

        response = client.get(
            "/api/v1/history/passenger-flow/prediction",
            params={"target_type": "station", "target_id": "2002"},
        )
        assert response.status_code == 200
        payload = response.json()["data"]
        assert len(payload) == 168
        assert payload[0]["target_type"] == "station"
        assert payload[0]["target_id"] == "2002"
        assert payload[0]["model_version"] in {MODEL_VERSION_RIDGE, MODEL_VERSION_BASELINE}

        stored_count = db.execute(
            text("SELECT COUNT(*) FROM passenger_flow_prediction WHERE target_type='station' AND target_id='2002'")
        ).scalar_one()
        assert stored_count == 168

        second = client.get(
            "/api/v1/history/passenger-flow/prediction",
            params={"target_type": "station", "target_id": "2002"},
        )
        assert second.status_code == 200
        stored_count_again = db.execute(
            text("SELECT COUNT(*) FROM passenger_flow_prediction WHERE target_type='station' AND target_id='2002'")
        ).scalar_one()
        assert stored_count_again == 168
    finally:
        db.close()
        engine.dispose()
