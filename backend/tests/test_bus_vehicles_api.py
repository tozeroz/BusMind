import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.api.v1.vehicle.router import bus_vehicles_router

@pytest.fixture(scope="module")
def app_with_bus_vehicles():
    application = FastAPI()
    application.include_router(bus_vehicles_router, prefix="/api/v1")
    return application

@pytest.fixture(scope="module")
def client_bus_vehicles(app_with_bus_vehicles):
    return TestClient(app_with_bus_vehicles)

def test_bus_vehicles_realtime_with_line_id(client_bus_vehicles):
    mock_vehicles = [
        {"vehicle_id": 1, "vehicle_code": "V001", "line_id": 1},
        {"vehicle_id": 2, "vehicle_code": "V002", "line_id": 1}
    ]
    
    with patch('app.api.v1.vehicle.router.get_vehicles_by_line') as mock_get_by_line:
        with patch('app.api.v1.vehicle.router.get_db'):
            mock_get_by_line.return_value = mock_vehicles
            
            response = client_bus_vehicles.get("/api/v1/bus-vehicles/realtime?line_id=1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "vehicles" in data["data"]
            assert isinstance(data["data"]["vehicles"], list)

def test_bus_vehicles_realtime_without_line_id(client_bus_vehicles):
    mock_vehicle_list = MagicMock()
    mock_vehicle_list.vehicles = []
    
    with patch('app.api.v1.vehicle.router.get_vehicle_list') as mock_get_list:
        with patch('app.api.v1.vehicle.router.get_db'):
            mock_get_list.return_value = mock_vehicle_list
            
            response = client_bus_vehicles.get("/api/v1/bus-vehicles/realtime")
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "vehicles" in data["data"]
            assert isinstance(data["data"]["vehicles"], list)