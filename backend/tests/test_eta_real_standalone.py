"""Standalone test for ETA API with real database data."""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import only what we need to avoid dependency issues
from app.models.transit import Base, BusStation, BusLine, BusVehicle, LineStation
from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.eta_service import EtaService

async def test_eta_with_real_database():
    """Regression test for ETA API with real database data.
    
    This test uses real database models and real gateway implementation
    to verify that /api/v1/eta works correctly with real A-side data.
    """
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
    
    print(f"ETA Result for real data:")
    print(f"  vehicle_id: {result.vehicle_id}")
    print(f"  target_station_id: {result.target_station_id}")
    print(f"  predicted_eta_minutes: {result.predicted_eta_minutes}")
    print(f"  model_version: {result.model_version}")
    print(f"  factors: {result.factors}")
    
    assert result.vehicle_id == 2001
    assert result.target_station_id == 1003
    assert result.predicted_eta_minutes > 0
    assert result.factors["remaining_stop_count"] == 2
    assert result.factors["distance_meters"] > 0
    
    print("\nPASSED: ETA calculation with real database data")
    
    # Test with non-existent vehicle
    try:
        await service.calculate_eta(vehicle_id=99999, target_station_id=1001)
        assert False, "Expected exception for non-existent vehicle"
    except Exception as e:
        assert "未找到公交车辆" in str(e) or "车辆不存在" in str(e)
        print("PASSED: ETA raises error for non-existent vehicle")
    
    # Test with non-existent station
    try:
        await service.calculate_eta(vehicle_id=2001, target_station_id=99999)
        assert False, "Expected exception for non-existent station"
    except Exception as e:
        assert "未找到公交站点" in str(e) or "站点不存在" in str(e)
        print("PASSED: ETA raises error for non-existent station")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing ETA API with Real Database Integration")
    print("=" * 70)
    print()
    
    asyncio.run(test_eta_with_real_database())
    
    print()
    print("=" * 70)
    print("All real database ETA tests passed!")
    print("=" * 70)