from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.transit_extra import TrafficSpeedBand
from app.repositories.transit_repository import TransitRepository


def _session_with_traffic_rows():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TrafficSpeedBand.__table__.create(engine)
    session = sessionmaker(bind=engine)()
    latest = datetime(2026, 7, 13, 12, 0, 0)
    session.add_all(
        [
            TrafficSpeedBand(
                traffic_record_id=1,
                query_time=latest,
                link_id=101,
                road_name="Nearby latest",
                speed_band=3,
                congestion_score=0.7,
                start_lon=103.8000,
                start_lat=1.3000,
                end_lon=103.8100,
                end_lat=1.3000,
            ),
            TrafficSpeedBand(
                traffic_record_id=2,
                query_time=latest,
                link_id=202,
                road_name="Far latest",
                speed_band=5,
                congestion_score=0.2,
                start_lon=103.9000,
                start_lat=1.4000,
                end_lon=103.9100,
                end_lat=1.4000,
            ),
            TrafficSpeedBand(
                traffic_record_id=3,
                query_time=latest - timedelta(minutes=5),
                link_id=303,
                road_name="Closer but stale",
                speed_band=1,
                congestion_score=1.0,
                start_lon=103.8040,
                start_lat=1.3000,
                end_lon=103.8060,
                end_lat=1.3000,
            ),
        ]
    )
    session.commit()
    return engine, session


def test_coordinate_lookup_selects_nearest_row_from_latest_snapshot_in_one_query():
    engine, session = _session_with_traffic_rows()
    select_count = 0

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(engine, "before_cursor_execute", count_selects)
    try:
        result = TransitRepository(session).get_segment_traffic(
            start_lon=103.8010,
            start_lat=1.3000,
            end_lon=103.8090,
            end_lat=1.3000,
        )

        assert result is not None
        assert result.link_id == 101
        assert result.road_name == "Nearby latest"
        assert select_count == 1
    finally:
        event.remove(engine, "before_cursor_execute", count_selects)
        session.close()


def test_coordinate_lookup_falls_back_to_global_nearest_when_box_is_empty():
    _engine, session = _session_with_traffic_rows()
    try:
        result = TransitRepository(session).get_segment_traffic(
            start_lon=104.5000,
            start_lat=1.9000,
            end_lon=104.5100,
            end_lat=1.9000,
        )

        assert result is not None
        assert result.link_id == 202
    finally:
        session.close()
