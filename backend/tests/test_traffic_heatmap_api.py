from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.map.router import router as map_router
from app.core.time_utils import now_local
from app.db.base import Base
from app.dependencies.auth import get_db
from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.transit_extra import MapRoadSegment, TrafficSpeedBand
from app.services.traffic_heatmap_service import TrafficHeatmapQuery, get_traffic_heatmap


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _add_line(
    db: Session,
    code: str,
    start_lon: float,
    end_lon: float,
    latitude: float,
) -> tuple[BusLine, BusStation, BusStation, MapRoadSegment]:
    line = BusLine(
        line_name=f"Line {code}",
        line_code=code,
        start_station=f"{code} Start",
        end_station=f"{code} End",
        total_stations=2,
        status="active",
    )
    db.add(line)
    db.flush()
    start = BusStation(
        station_name=f"{code} Start",
        station_code=f"{code}A",
        latitude=latitude,
        longitude=start_lon,
        address="Test Road",
    )
    end = BusStation(
        station_name=f"{code} End",
        station_code=f"{code}B",
        latitude=latitude,
        longitude=end_lon,
        address="Test Road",
    )
    db.add_all([start, end])
    db.flush()
    db.add_all(
        [
            LineStation(
                line_id=line.line_id,
                station_id=start.station_id,
                order_index=1,
                direction="forward",
            ),
            LineStation(
                line_id=line.line_id,
                station_id=end.station_id,
                order_index=2,
                direction="forward",
            ),
        ]
    )
    segment = MapRoadSegment(
        segment_id=f"{code}-001",
        segment_name="Test Road",
        line_id=line.line_id,
        service_no=code,
        line_name=line.line_name,
        direction=1,
        stop_sequence=1,
        start_station_id=start.station_id,
        start_station_name=start.station_name,
        end_station_id=end.station_id,
        end_station_name=end.station_name,
        start_lat=latitude,
        start_lon=start_lon,
        end_lat=latitude,
        end_lon=end_lon,
        path_coordinates=[[start_lon, latitude], [end_lon, latitude]],
    )
    db.add(segment)
    db.flush()
    return line, start, end, segment


def test_heatmap_matches_only_route_nearby_traffic(db_session: Session):
    line, _, _, segment = _add_line(db_session, "10", 103.8000, 103.8100, 1.3000)
    observed_at = now_local().replace(tzinfo=None) - timedelta(minutes=2)
    db_session.add_all(
        [
            TrafficSpeedBand(
                query_time=observed_at,
                link_id=101,
                road_name="Test Road",
                road_category="A",
                speed_band=2,
                minimum_speed_kmh=10,
                maximum_speed_kmh=19,
                congestion_score=0.82,
                heat_color="#legacy",
                start_lon=103.8010,
                start_lat=1.3001,
                end_lon=103.8090,
                end_lat=1.3001,
                line_coordinates=[[103.8010, 1.3001], [103.8090, 1.3001]],
            ),
            TrafficSpeedBand(
                query_time=observed_at,
                link_id=999,
                road_name="Unrelated Road",
                road_category="B",
                speed_band=1,
                minimum_speed_kmh=0,
                maximum_speed_kmh=9,
                congestion_score=1.0,
                heat_color="#legacy",
                start_lon=103.9000,
                start_lat=1.4000,
                end_lon=103.9100,
                end_lat=1.4000,
                line_coordinates=[[103.9000, 1.4000], [103.9100, 1.4000]],
            ),
        ]
    )
    db_session.commit()

    result = get_traffic_heatmap(
        db_session,
        TrafficHeatmapQuery(line_ids=(int(line.line_id),)),
    )

    assert result.matched_count == 1
    assert result.no_data_count == 0
    assert result.traffic_segments[0].route_segment_id == segment.segment_id
    assert result.traffic_segments[0].link_id == 101
    assert result.traffic_segments[0].congestion_level == "severe"
    assert result.traffic_segments[0].heat_color == "#EF4444"
    assert result.traffic_segments[0].data_status == "realtime"
    assert result.traffic_segments[0].query_time == observed_at
    assert all(point[1] == pytest.approx(1.3000) for point in result.traffic_segments[0].coordinates)


def test_heatmap_keeps_route_when_realtime_traffic_is_missing(db_session: Session):
    line, _, _, segment = _add_line(db_session, "20", 103.8200, 103.8300, 1.3200)
    db_session.commit()

    result = get_traffic_heatmap(
        db_session,
        TrafficHeatmapQuery(line_ids=(int(line.line_id),)),
    )

    assert result.matched_count == 0
    assert result.no_data_count == 1
    assert result.traffic_segments[0].route_segment_id == segment.segment_id
    assert result.traffic_segments[0].link_id is None
    assert result.traffic_segments[0].congestion_level == "no_data"
    assert result.traffic_segments[0].heat_color == "#9CA3AF"
    assert result.traffic_segments[0].coordinates


def test_get_heatmap_endpoint_supports_repeated_line_ids(db_session: Session):
    first_line, _, _, _ = _add_line(db_session, "30", 103.8400, 103.8500, 1.3400)
    second_line, _, _, _ = _add_line(db_session, "31", 103.8500, 103.8600, 1.3400)
    db_session.commit()

    app = FastAPI()
    app.include_router(map_router, prefix="/api/v1")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    response = client.get(
        "/api/v1/map/traffic-heatmap",
        params=[("line_id", first_line.line_id), ("line_id", second_line.line_id)],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert set(payload["data"]["line_ids"]) == {first_line.line_id, second_line.line_id}
    assert payload["data"]["no_data_count"] == 2


def test_get_heatmap_endpoint_requires_route_filter(db_session: Session):
    app = FastAPI()
    app.include_router(map_router, prefix="/api/v1")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    response = TestClient(app).get("/api/v1/map/traffic-heatmap")
    assert response.status_code == 400


def test_post_heatmap_uses_only_requested_route_leg(db_session: Session):
    line = BusLine(
        line_name="Line 40",
        line_code="40",
        start_station="40 Start",
        end_station="40 End",
        total_stations=3,
        status="active",
    )
    db_session.add(line)
    db_session.flush()
    stations = [
        BusStation(
            station_name=f"40-{index}",
            station_code=f"40{index}",
            latitude=1.3600,
            longitude=103.8700 + index * 0.005,
            address="Exact Route Road",
        )
        for index in range(3)
    ]
    db_session.add_all(stations)
    db_session.flush()
    for index, station in enumerate(stations, start=1):
        db_session.add(
            LineStation(
                line_id=line.line_id,
                station_id=station.station_id,
                order_index=index,
                direction="forward",
            )
        )
    for index in range(2):
        db_session.add(
            MapRoadSegment(
                segment_id=f"40-forward-{index + 1}",
                segment_name="Exact Route Road",
                line_id=line.line_id,
                service_no="40",
                line_name=line.line_name,
                direction=1,
                stop_sequence=index + 1,
                start_station_id=stations[index].station_id,
                start_station_name=stations[index].station_name,
                end_station_id=stations[index + 1].station_id,
                end_station_name=stations[index + 1].station_name,
                start_lat=stations[index].latitude,
                start_lon=stations[index].longitude,
                end_lat=stations[index + 1].latitude,
                end_lon=stations[index + 1].longitude,
                path_coordinates=[
                    [float(stations[index].longitude), float(stations[index].latitude)],
                    [float(stations[index + 1].longitude), float(stations[index + 1].latitude)],
                ],
            )
        )
    db_session.commit()

    app = FastAPI()
    app.include_router(map_router, prefix="/api/v1")

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    response = TestClient(app).post(
        "/api/v1/map/traffic-heatmap",
        json={
            "route_id": "route-exact-40",
            "route_segments": [
                {
                    "segment_order": 1,
                    "line_id": line.line_id,
                    "boarding_station_id": stations[1].station_id,
                    "alighting_station_id": stations[2].station_id,
                }
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["route_id"] == "route-exact-40"
    assert len(data["route_segments"]) == 1
    assert data["route_segments"][0]["route_segment_id"] == "40-forward-2"
    assert data["traffic_segments"][0]["congestion_level"] == "no_data"
