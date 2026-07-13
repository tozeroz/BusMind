from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.locations.router import router as locations_router
from app.db.base import Base
from app.dependencies.auth import get_db
from app.models.bus_line import BusLine, BusStation, LineStation
from app.models.bus_vehicle import BusVehicle
from app.services.bus_service import get_nearby_stations, get_station_list
from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.recommend_service.transit_graph import TransitGraphBuilder


def _build_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            BusStation.__table__,
            BusLine.__table__,
            LineStation.__table__,
            BusVehicle.__table__,
        ],
    )
    session = sessionmaker(bind=engine)()

    stations = [
        BusStation(
            station_id=station_id,
            station_code=f"S{station_id}",
            station_name=f"Station {station_id}",
            latitude=1.3000 + station_id / 10_000,
            longitude=103.8000 + station_id / 10_000,
        )
        for station_id in range(1, 7)
    ]
    lines = [
        BusLine(line_id=10, line_code="10", line_name="Active line", raw_direction=1, status="running"),
        BusLine(line_id=20, line_code="20", line_name="No vehicle line", raw_direction=1, status="running"),
        BusLine(line_id=30, line_code="30", line_name="Offline line", raw_direction=1, status="active"),
    ]
    line_stations = [
        LineStation(id="10-1", line_id=10, order_index=1, station_id=1),
        LineStation(id="10-2", line_id=10, order_index=2, station_id=2),
        LineStation(id="20-1", line_id=20, order_index=1, station_id=3),
        LineStation(id="20-2", line_id=20, order_index=2, station_id=4),
        LineStation(id="30-1", line_id=30, order_index=1, station_id=5),
        LineStation(id="30-2", line_id=30, order_index=2, station_id=6),
    ]
    vehicles = [
        BusVehicle(vehicle_id=1001, vehicle_code="V1001", line_id=10, status="normal"),
        BusVehicle(vehicle_id=3001, vehicle_code="V3001", line_id=30, status="offline"),
    ]
    session.add_all([*stations, *lines, *line_stations, *vehicles])
    session.commit()
    return session


def test_graph_only_contains_lines_with_non_offline_vehicles():
    session = _build_session()
    try:
        snapshot = TransitGraphBuilder(session).build()

        assert set(snapshot.line_names) == {10}
        assert set(snapshot.station_lookup) == {1, 2}
        assert {node.line_id for node in snapshot.node_station} == {10}
    finally:
        session.close()


def test_gateway_returns_only_candidates_with_real_vehicle_ids():
    session = _build_session()
    try:
        gateway = MySQLTransitGateway(session)

        active = asyncio.run(gateway.get_candidate_routes(1, 2, 2))
        no_vehicle = asyncio.run(gateway.get_candidate_routes(3, 4, 2))
        offline = asyncio.run(gateway.get_candidate_routes(5, 6, 2))

        assert active
        assert all(candidate.vehicle_id == 1001 for candidate in active)
        assert no_vehicle == []
        assert offline == []
    finally:
        session.close()


def test_station_services_preserve_default_and_filter_active_only():
    session = _build_session()
    try:
        all_stations = get_station_list(session, page=1, limit=20)
        active_stations = get_station_list(session, page=1, limit=20, active_only=True)
        active_page = get_station_list(session, page=2, limit=1, active_only=True)
        nearby = get_nearby_stations(
            session,
            latitude=1.3000,
            longitude=103.8000,
            radius_km=5,
            active_only=True,
        )

        assert all_stations.total == 6
        assert active_stations.total == 2
        assert {item.station_id for item in active_stations.stations} == {1, 2}
        assert active_page.total == 2
        assert len(active_page.stations) == 1
        assert {item.station_id for item in nearby.stations} == {1, 2}
    finally:
        session.close()


def test_locations_api_accepts_active_only_without_changing_default():
    session = _build_session()
    app = FastAPI()
    app.include_router(locations_router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: session
    client = TestClient(app)
    try:
        default_response = client.get("/api/v1/locations/search", params={"limit": 20})
        active_response = client.get(
            "/api/v1/locations/search",
            params={"limit": 20, "active_only": True},
        )
        nearby_response = client.get(
            "/api/v1/locations/nearby",
            params={
                "latitude": 1.3000,
                "longitude": 103.8000,
                "radius_km": 5,
                "active_only": True,
            },
        )

        assert default_response.status_code == 200
        assert default_response.json()["data"]["total"] == 6
        assert active_response.status_code == 200
        assert active_response.json()["data"]["total"] == 2
        assert nearby_response.status_code == 200
        assert {item["station_id"] for item in nearby_response.json()["data"]["stations"]} == {1, 2}
    finally:
        session.close()
