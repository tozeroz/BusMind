"""
Regression tests for static path vs dynamic path routing conflicts.

This test file ensures that static sub-paths are not incorrectly captured by
dynamic path parameters like {id}. This was a common issue in FastAPI where
routes like /realtime would be matched by /{vehicle_id} if registered later.

Tested routes:
- /api/v1/vehicles/realtime vs /api/v1/vehicles/{vehicle_id}
- /api/v1/location/nearby vs /api/v1/location/{station_id}
- /api/v1/stations/nearby vs /api/v1/stations/{station_id}
- /api/v1/stations/coordinates/all vs /api/v1/stations/{station_id}
- /api/v1/locations/nearby vs /api/v1/locations/{location_id}
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, APIRouter, Query, Body
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional

def build_response(code: int, message: str, data=None):
    return {
        "code": code,
        "message": message,
        "data": data,
        "trace_id": f"req_{uuid4().hex[:12]}",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

# ------------------------------
# Vehicles Router
# ------------------------------
vehicles_router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

@vehicles_router.get("")
async def list_vehicles(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return build_response(0, "success", {"vehicles": [], "total": 0})

# Static path before dynamic path
@vehicles_router.get("/realtime")
async def get_realtime_vehicles(line_id: Optional[int] = Query(None, ge=1)):
    return build_response(0, "success", {"vehicles": []})

@vehicles_router.get("/line/{line_id}")
async def get_vehicles_for_line(line_id: int):
    return build_response(0, "success", {"vehicles": []})

# Dynamic path at the end
@vehicles_router.get("/{vehicle_id}")
async def get_vehicle(vehicle_id: int):
    return build_response(0, "success", {"vehicle_id": vehicle_id})

# ------------------------------
# Location Router
# ------------------------------
location_router = APIRouter(prefix="/location", tags=["Location"])

# Static path before dynamic path
@location_router.get("/nearby")
async def get_nearby(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(1.0, ge=0.1, le=10.0),
):
    return build_response(0, "success", {"stations": []})

# Dynamic path at the end
@location_router.get("/{station_id}")
async def get_location(station_id: int):
    return build_response(0, "success", {"station_id": station_id})

# ------------------------------
# Stations Router
# ------------------------------
stations_router = APIRouter(prefix="/stations", tags=["Stations"])

@stations_router.get("")
async def list_stations(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return build_response(0, "success", {"stations": [], "total": 0})

# Static paths before dynamic path
@stations_router.post("/nearby")
async def search_nearby_stations(
    latitude: float = Body(..., embed=True),
    longitude: float = Body(..., embed=True),
    radius_km: float = Body(1.0, embed=True),
):
    return build_response(0, "success", {"stations": []})

@stations_router.get("/coordinates/all")
async def get_all_station_coordinates():
    return build_response(0, "success", {"stations": []})

# Dynamic path at the end
@stations_router.get("/{station_id}")
async def get_station(station_id: int):
    return build_response(0, "success", {"station_id": station_id})

# ------------------------------
# Locations Router
# ------------------------------
locations_router = APIRouter(prefix="/locations", tags=["Locations"])

# Static paths before dynamic path
@locations_router.get("/search")
async def search_locations(keyword: Optional[str] = Query(None)):
    return build_response(0, "success", {"locations": [], "total": 0})

@locations_router.get("/nearby")
async def get_nearby_locations(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(1.0, ge=0.1, le=10.0),
):
    return build_response(0, "success", {"stations": []})

@locations_router.get("/map/stations")
async def get_map_stations():
    return build_response(0, "success", {"stations": [], "total": 0})

# Dynamic path at the end
@locations_router.get("/{location_id}")
async def get_location_detail(location_id: int):
    return build_response(0, "success", {"location_id": location_id})

# ------------------------------
# Setup Test App
# ------------------------------
app = FastAPI()
app.include_router(vehicles_router, prefix="/api/v1")
app.include_router(location_router, prefix="/api/v1")
app.include_router(stations_router, prefix="/api/v1")
app.include_router(locations_router, prefix="/api/v1")

client = TestClient(app)

# ------------------------------
# Test Cases
# ------------------------------

def test_vehicles_realtime_not_captured_by_vehicle_id():
    """Regression test: /vehicles/realtime should not be captured by /vehicles/{vehicle_id}"""
    response = client.get("/api/v1/vehicles/realtime")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "vehicles" in data["data"]
    print("PASSED: /api/v1/vehicles/realtime returns 200")

def test_vehicles_by_id_still_works():
    """Ensure /vehicles/{vehicle_id} still works correctly"""
    response = client.get("/api/v1/vehicles/123")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["vehicle_id"] == 123
    print("PASSED: /api/v1/vehicles/{vehicle_id} works correctly")

def test_vehicles_line_still_works():
    """Ensure /vehicles/line/{line_id} still works correctly"""
    response = client.get("/api/v1/vehicles/line/5")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "vehicles" in data["data"]
    print("PASSED: /api/v1/vehicles/line/{line_id} works correctly")

def test_location_nearby_not_captured_by_station_id():
    """Regression test: /location/nearby should not be captured by /location/{station_id}"""
    response = client.get("/api/v1/location/nearby?latitude=31.2304&longitude=121.4737")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/location/nearby returns 200")

def test_location_by_id_still_works():
    """Ensure /location/{station_id} still works correctly"""
    response = client.get("/api/v1/location/456")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["station_id"] == 456
    print("PASSED: /api/v1/location/{station_id} works correctly")

def test_stations_nearby_not_captured_by_station_id():
    """Regression test: /stations/nearby should not be captured by /stations/{station_id}"""
    response = client.post("/api/v1/stations/nearby", json={"latitude": 31.2304, "longitude": 121.4737})
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/stations/nearby returns 200")

def test_stations_coordinates_all_not_captured():
    """Regression test: /stations/coordinates/all should not be captured by /stations/{station_id}"""
    response = client.get("/api/v1/stations/coordinates/all")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/stations/coordinates/all returns 200")

def test_stations_by_id_still_works():
    """Ensure /stations/{station_id} still works correctly"""
    response = client.get("/api/v1/stations/789")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["station_id"] == 789
    print("PASSED: /api/v1/stations/{station_id} works correctly")

def test_locations_nearby_not_captured_by_location_id():
    """Regression test: /locations/nearby should not be captured by /locations/{location_id}"""
    response = client.get("/api/v1/locations/nearby?latitude=31.2304&longitude=121.4737")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/locations/nearby returns 200")

def test_locations_search_not_captured():
    """Regression test: /locations/search should not be captured by /locations/{location_id}"""
    response = client.get("/api/v1/locations/search?keyword=test")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    print("PASSED: /api/v1/locations/search returns 200")

def test_locations_map_stations_not_captured():
    """Regression test: /locations/map/stations should not be captured by /locations/{location_id}"""
    response = client.get("/api/v1/locations/map/stations")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/locations/map/stations returns 200")

def test_locations_by_id_still_works():
    """Ensure /locations/{location_id} still works correctly"""
    response = client.get("/api/v1/locations/101")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["location_id"] == 101
    print("PASSED: /api/v1/locations/{location_id} works correctly")

if __name__ == "__main__":
    print("=" * 70)
    print("Running Static vs Dynamic Path Routing Conflict Regression Tests")
    print("=" * 70)
    print()
    
    test_vehicles_realtime_not_captured_by_vehicle_id()
    print()
    test_vehicles_by_id_still_works()
    print()
    test_vehicles_line_still_works()
    print()
    test_location_nearby_not_captured_by_station_id()
    print()
    test_location_by_id_still_works()
    print()
    test_stations_nearby_not_captured_by_station_id()
    print()
    test_stations_coordinates_all_not_captured()
    print()
    test_stations_by_id_still_works()
    print()
    test_locations_nearby_not_captured_by_location_id()
    print()
    test_locations_search_not_captured()
    print()
    test_locations_map_stations_not_captured()
    print()
    test_locations_by_id_still_works()
    
    print()
    print("=" * 70)
    print("All regression tests passed!")
    print("=" * 70)