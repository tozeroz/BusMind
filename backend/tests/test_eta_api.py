"""Tests for ETA API."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.v1.dependencies import get_eta_service
from app.api.v1.intelligence_router import router
from app.core.exception_handlers import register_intelligence_exception_handlers
from app.models.transit import Base, BusStation, BusLine, BusVehicle, LineStation
from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.eta_service import EtaService
from app.services.simulation_service import simulation_state_store


def test_eta_success(client):
    response = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["predicted_eta_minutes"] > 0
    assert body["data"]["model_version"] in {"eta_rule_v1", "eta_external_model"}
    assert "distance_meters" in body["data"]["factors"]


def test_eta_wrong_line(client):
    response = client.get(
        "/api/v1/eta",
        params={"vehicle_id": 101, "target_station_id": 3, "line_id": 2},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40002


def test_eta_validation_envelope(client):
    response = client.get("/api/v1/eta", params={"vehicle_id": 101})
    assert response.status_code == 422
    assert response.json()["code"] == 42200


async def test_eta_with_real_database_async():
    """Regression test for ETA API with real database data.
    
    This test uses real database models and real gateway implementation
    to verify that /api/v1/eta works correctly with real A-side data.
    """
    import asyncio
    from datetime import datetime
    
    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Insert real-like test data with realistic IDs (not demo 101/3)
    db.add(BusStation(
        station_id=1001, 
        station_name="人民广场站", 
        bus_stop_code="BS1001",
        latitude=31.2304, 
        longitude=121.4737
    ))
    db.add(BusStation(
        station_id=1002, 
        station_name="南京东路站", 
        bus_stop_code="BS1002",
        latitude=31.2315, 
        longitude=121.4745
    ))
    db.add(BusStation(
        station_id=1003, 
        station_name="外滩站", 
        bus_stop_code="BS1003",
        latitude=31.2330, 
        longitude=121.4760
    ))
    
    db.add(BusLine(
        line_id=501, 
        service_no="501",
        line_name="501路",
        avg_service_frequency=10.0
    ))
    
    db.add(BusVehicle(
        vehicle_id=2001, 
        vehicle_code="VH2001", 
        line_id=501,
        current_station_id=1001, 
        next_station_id=1002,
        latitude=31.2306, 
        longitude=121.4738,
        speed_kph=25.0, 
        onboard_count=15, 
        capacity=50,
        operation_status="normal",
        last_reported_at=datetime.now()
    ))
    
    db.add(LineStation(
        line_station_id="LS001", 
        line_id=501, 
        stop_sequence=1, 
        station_id=1001
    ))
    db.add(LineStation(
        line_station_id="LS002", 
        line_id=501, 
        stop_sequence=2, 
        station_id=1002
    ))
    db.add(LineStation(
        line_station_id="LS003", 
        line_id=501, 
        stop_sequence=3, 
        station_id=1003
    ))
    
    db.commit()
    
    # Create gateway and service using real database
    gateway = MySQLTransitGateway(db)
    service = EtaService(gateway)
    
    # Test ETA calculation with real data (not demo data)
    result = await service.calculate_eta(vehicle_id=2001, target_station_id=1003)
    
    assert result.vehicle_id == 2001
    assert result.target_station_id == 1003
    assert result.predicted_eta_minutes > 0
    assert result.factors["remaining_stop_count"] == 2
    assert result.factors["distance_meters"] > 0
    
    # Test with non-existent vehicle
    try:
        await service.calculate_eta(vehicle_id=99999, target_station_id=1001)
        assert False, "Expected exception for non-existent vehicle"
    except Exception as e:
        assert "未找到公交车辆" in str(e) or "车辆不存在" in str(e)
    
    # Test with non-existent station
    try:
        await service.calculate_eta(vehicle_id=2001, target_station_id=99999)
        assert False, "Expected exception for non-existent station"
    except Exception as e:
        assert "未找到公交站点" in str(e) or "站点不存在" in str(e)
    
    db.close()


def test_eta_with_real_database():
    """Wrapper for async test."""
    import asyncio
    asyncio.run(test_eta_with_real_database_async())


if __name__ == "__main__":
    print("Running ETA API tests...")
    test_eta_with_real_database()
    print("All tests passed!")