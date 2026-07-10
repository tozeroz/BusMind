import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from app.api.v1.line.router import bus_stations_router

@pytest.fixture(scope="module")
def app():
    application = FastAPI()
    application.include_router(bus_stations_router, prefix="/api/v1")
    return application

@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)

def test_bus_stations_nearby_valid_coordinates(client):
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "stations": [
            {
                "station_id": 1,
                "station_name": "Station A",
                "station_code": "ST001",
                "latitude": 31.2304,
                "longitude": 121.4737,
                "address": "Address A",
                "zone": "ZoneA",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "distance_km": 0.5
            },
            {
                "station_id": 2,
                "station_name": "Station B",
                "station_code": "ST002",
                "latitude": 31.2314,
                "longitude": 121.4747,
                "address": "Address B",
                "zone": "ZoneB",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "distance_km": 1.2
            }
        ],
        "total": 2
    }
    
    with patch('app.api.v1.line.router.get_nearby_stations') as mock_get_nearby:
        with patch('app.api.v1.line.router.get_db'):
            mock_get_nearby.return_value = mock_response
            
            response = client.get(
                "/api/v1/bus-stations/nearby",
                params={
                    "latitude": 31.2304,
                    "longitude": 121.4737,
                    "radius_meters": 2000,
                    "limit": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "stations" in data["data"]
            assert data["data"]["total"] == 2
            
            distances = [s["distance_km"] for s in data["data"]["stations"]]
            assert distances == sorted(distances), "Stations should be sorted by distance ascending"

def test_bus_stations_nearby_invalid_latitude(client):
    response = client.get(
        "/api/v1/bus-stations/nearby",
        params={
            "latitude": 120.0,
            "longitude": 121.4737,
            "radius_meters": 1000
        }
    )
    assert response.status_code == 422

def test_bus_stations_nearby_invalid_longitude(client):
    response = client.get(
        "/api/v1/bus-stations/nearby",
        params={
            "latitude": 31.2304,
            "longitude": 200.0,
            "radius_meters": 1000
        }
    )
    assert response.status_code == 422

def test_bus_stations_nearby_not_eaten_by_station_id(client):
    with patch('app.api.v1.line.router.get_db'):
        response = client.get("/api/v1/bus-stations/nearby")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert any("latitude" in str(err.get("loc", [])) for err in data["detail"])

def test_bus_stations_nearby_radius_conversion(client):
    mock_response = MagicMock()
    mock_response.model_dump.return_value = {
        "stations": [],
        "total": 0
    }
    
    with patch('app.api.v1.line.router.get_nearby_stations') as mock_get_nearby:
        with patch('app.api.v1.line.router.get_db'):
            mock_get_nearby.return_value = mock_response
            
            response = client.get(
                "/api/v1/bus-stations/nearby",
                params={
                    "latitude": 31.2304,
                    "longitude": 121.4737,
                    "radius_meters": 2500,
                    "limit": 10
                }
            )
            
            assert response.status_code == 200
            mock_get_nearby.assert_called_once()
            call_args = mock_get_nearby.call_args
            assert call_args[0][0] is not None
            assert call_args[0][1] == 31.2304
            assert call_args[0][2] == 121.4737
            assert call_args[0][3] == 2.5