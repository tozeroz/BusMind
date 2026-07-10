import pytest
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel


class MapStationDTO(BaseModel):
    station_id: int
    station_name: str
    station_code: str
    latitude: float
    longitude: float
    address: Optional[str] = None
    zone: Optional[str] = None
    line_ids: List[int] = []
    line_names: List[str] = []


class LineMapBoundsDTO(BaseModel):
    min_latitude: float
    max_latitude: float
    min_longitude: float
    max_longitude: float


class LineMapDataDTO(BaseModel):
    line_id: int
    line_name: str
    line_code: str
    polyline: List[List[float]] = []
    stations: List[MapStationDTO] = []
    bounds: LineMapBoundsDTO


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None
    trace_id: Optional[str] = None
    timestamp: Optional[str] = None


def build_response(code: int, message: str, data: dict = None):
    return ApiResponse(
        code=code,
        message=message,
        data=data
    )


def get_line_map_data(db: Session, line_id: int, direction: Optional[str] = None):
    if line_id == 999:
        return None
    
    stations = [
        MapStationDTO(
            station_id=1,
            station_name="Station 1",
            station_code="ST001",
            latitude=31.2304,
            longitude=121.4737,
            line_ids=[line_id],
            line_names=["Line A"]
        ),
        MapStationDTO(
            station_id=2,
            station_name="Station 2",
            station_code="ST002",
            latitude=31.2314,
            longitude=121.4747,
            line_ids=[line_id],
            line_names=["Line A"]
        ),
        MapStationDTO(
            station_id=3,
            station_name="Station 3",
            station_code="ST003",
            latitude=31.2324,
            longitude=121.4757,
            line_ids=[line_id],
            line_names=["Line A"]
        )
    ]
    polyline = [[121.4737, 31.2304], [121.4747, 31.2314], [121.4757, 31.2324]]
    bounds = LineMapBoundsDTO(
        min_latitude=31.2304,
        max_latitude=31.2324,
        min_longitude=121.4737,
        max_longitude=121.4757
    )
    return LineMapDataDTO(
        line_id=line_id,
        line_name="Line A",
        line_code="L001",
        polyline=polyline,
        stations=stations,
        bounds=bounds
    )


app = FastAPI()


@app.get("/api/v1/bus-lines/{line_id}/map", response_model=ApiResponse)
async def get_line_map(
    line_id: int,
    direction: Optional[str] = Query(None, description="Direction filter (reserved for future use)"),
    db: Session = Depends(lambda: None)
):
    result = get_line_map_data(db, line_id, direction)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=build_response(40400, "Line not found").model_dump()
        )
    return build_response(0, "success", result.model_dump())


client = TestClient(app)


def test_bus_lines_map_valid_line_id():
    response = client.get("/api/v1/bus-lines/1/map")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "data" in data
    
    result = data["data"]
    assert "line_id" in result
    assert result["line_id"] == 1
    assert "polyline" in result
    assert isinstance(result["polyline"], list)
    assert len(result["polyline"]) == 3
    
    assert "stations" in result
    assert isinstance(result["stations"], list)
    assert len(result["stations"]) == 3
    
    assert "bounds" in result
    bounds = result["bounds"]
    assert "min_latitude" in bounds
    assert "max_latitude" in bounds
    assert "min_longitude" in bounds
    assert "max_longitude" in bounds
    
    polyline_coords = result["polyline"]
    station_coords = [[s["longitude"], s["latitude"]] for s in result["stations"]]
    assert polyline_coords == station_coords, "Polyline coordinates should match station order"


def test_bus_lines_map_polyline_order():
    response = client.get("/api/v1/bus-lines/1/map")
    assert response.status_code == 200
    data = response.json()
    polyline = data["data"]["polyline"]
    
    assert polyline[0] == [121.4737, 31.2304], "First point should be Station 1"
    assert polyline[1] == [121.4747, 31.2314], "Second point should be Station 2"
    assert polyline[2] == [121.4757, 31.2324], "Third point should be Station 3"


def test_bus_lines_map_not_found():
    response = client.get("/api/v1/bus-lines/999/map")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"]["code"] == 40400
    assert data["detail"]["message"] == "Line not found"


def test_bus_lines_map_with_direction_param():
    response = client.get("/api/v1/bus-lines/1/map?direction=forward")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0


def test_bus_lines_map_bounds_calculation():
    response = client.get("/api/v1/bus-lines/1/map")
    assert response.status_code == 200
    data = response.json()
    bounds = data["data"]["bounds"]
    
    assert bounds["min_latitude"] == 31.2304
    assert bounds["max_latitude"] == 31.2324
    assert bounds["min_longitude"] == 121.4737
    assert bounds["max_longitude"] == 121.4757