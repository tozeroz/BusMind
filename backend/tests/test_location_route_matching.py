import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, APIRouter, Depends, Query
from fastapi.testclient import TestClient
from uuid import uuid4
from datetime import datetime, timezone

router = APIRouter(prefix="/location", tags=["Location"])

def get_trace_id() -> str:
    return f"req_{uuid4().hex[:12]}"

def get_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def build_response(code: int, message: str, data=None):
    return {
        "code": code,
        "message": message,
        "data": data,
        "trace_id": get_trace_id(),
        "timestamp": get_timestamp()
    }

# Static paths must be registered before /{station_id}; otherwise FastAPI treats
# "nearby" as a station_id and returns a validation error.
@router.get(
    "/nearby",
    status_code=200,
    summary="Get Nearby Stations"
)
async def get_nearby(
    latitude: float = Query(..., ge=-90, le=90, description="Current latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Current longitude"),
    radius_km: float = Query(1.0, ge=0.1, le=10.0, description="Search radius in km"),
):
    return build_response(0, "success", {"stations": []})

@router.get(
    "/{station_id}",
    status_code=200,
    summary="Get Location/Station Detail"
)
async def get_location(
    station_id: int,
):
    return build_response(0, "success", {"station_id": station_id, "name": f"Station {station_id}"})

app = FastAPI()
app.include_router(router, prefix="/api/v1")

client = TestClient(app)

def test_location_nearby_not_captured_by_station_id():
    """Regression test: /nearby should not be captured by /{station_id}"""
    response = client.get("/api/v1/location/nearby?latitude=31.2304&longitude=121.4737")
    print(f"test_location_nearby_not_captured_by_station_id: {response.status_code}")
    assert response.status_code == 200, f"Expected 200 but got {response.status_code}: {response.text}"
    data = response.json()
    assert data["code"] == 0
    assert "stations" in data["data"]
    print("PASSED: /api/v1/location/nearby returns 200")

def test_location_by_id_still_works():
    """Ensure /{station_id} still works correctly"""
    response = client.get("/api/v1/location/123")
    print(f"test_location_by_id_still_works: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["data"]["station_id"] == 123
    print("PASSED: /api/v1/location/{station_id} works correctly")

def test_location_nearby_with_custom_radius():
    """Test /nearby with custom radius parameter"""
    response = client.get("/api/v1/location/nearby?latitude=31.2304&longitude=121.4737&radius_km=2.5")
    print(f"test_location_nearby_with_custom_radius: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    print("PASSED: /api/v1/location/nearby with custom radius returns 200")

if __name__ == "__main__":
    print("Running location route matching tests...")
    print()
    test_location_nearby_not_captured_by_station_id()
    print()
    test_location_by_id_still_works()
    print()
    test_location_nearby_with_custom_radius()
    print()
    print("All tests passed!")