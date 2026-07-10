import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, APIRouter, Query
from fastapi.testclient import TestClient
from typing import Optional
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
bus_vehicles_router = APIRouter(prefix="/bus-vehicles", tags=["Vehicles"])

def build_response(code: int, message: str, data=None):
    return {
        "code": code,
        "message": message,
        "data": data,
        "trace_id": f"req_{uuid4().hex[:12]}",
        "timestamp": datetime.now(timezone.utc).astimezone().isoformat(),
    }

@router.get("", summary="Get Vehicle List")
async def list_vehicles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    line_id: Optional[int] = Query(None, ge=1),
):
    return build_response(0, "success", {"vehicles": [], "total": 0})

@router.get("/realtime", summary="Get Real-time Vehicle Positions")
async def get_realtime_vehicles(
    line_id: Optional[int] = Query(None, ge=1),
):
    return build_response(0, "success", {"vehicles": []})

@router.get("/line/{line_id}", summary="Get Vehicles by Line")
async def get_vehicles_for_line(line_id: int):
    return build_response(0, "success", {"vehicles": []})

@router.get("/{vehicle_id}", summary="Get Vehicle Detail")
async def get_vehicle(vehicle_id: int):
    return build_response(0, "success", {"vehicle_id": vehicle_id})

@bus_vehicles_router.get("/realtime", summary="Get Real-time Bus Vehicle Positions")
async def get_bus_realtime_vehicles(
    line_id: Optional[int] = Query(None, ge=1),
):
    return build_response(0, "success", {"vehicles": []})

app = FastAPI()
app.include_router(router, prefix="/api/v1")
app.include_router(bus_vehicles_router, prefix="/api/v1")

client = TestClient(app)

def test_vehicles_realtime_route_not_captured_by_vehicle_id():
    response = client.get("/api/v1/vehicles/realtime")
    print(f"test_vehicles_realtime_route_not_captured_by_vehicle_id: {response.status_code}")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "vehicles" in data["data"]
    print("PASSED: /api/v1/vehicles/realtime returns 200")

def test_vehicles_by_id_still_works():
    response = client.get("/api/v1/vehicles/123")
    print(f"test_vehicles_by_id_still_works: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["vehicle_id"] == 123
    print("PASSED: /api/v1/vehicles/{vehicle_id} works correctly")

def test_vehicles_by_line_still_works():
    response = client.get("/api/v1/vehicles/line/5")
    print(f"test_vehicles_by_line_still_works: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "vehicles" in data["data"]
    print("PASSED: /api/v1/vehicles/line/{line_id} works correctly")

def test_bus_vehicles_realtime_still_works():
    response = client.get("/api/v1/bus-vehicles/realtime")
    print(f"test_bus_vehicles_realtime_still_works: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "vehicles" in data["data"]
    print("PASSED: /api/v1/bus-vehicles/realtime returns 200")

if __name__ == "__main__":
    print("Running route matching tests...")
    print()
    test_vehicles_realtime_route_not_captured_by_vehicle_id()
    print()
    test_vehicles_by_id_still_works()
    print()
    test_vehicles_by_line_still_works()
    print()
    test_bus_vehicles_realtime_still_works()
    print()
    print("All tests passed!")