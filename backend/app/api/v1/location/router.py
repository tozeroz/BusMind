from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.bus_service import get_station_by_id, get_nearby_stations
from app.schemas.bus_schema import BusStationDTO, NearbyStationResponse
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/location", tags=["Location"])

def get_trace_id() -> str:
    return f"req_{uuid4().hex[:12]}"

def get_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def build_response(code: int, message: str, data=None) -> ApiResponse:
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        trace_id=get_trace_id(),
        timestamp=get_timestamp()
    )

@router.get(
    "/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Location/Station Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Location not found"}
    }
)
async def get_location(
    station_id: int,
    db: Session = Depends(get_db)
):
    station = get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=404,
            detail=build_response(40401, "Location not found").model_dump()
        )
    return build_response(0, "success", station.model_dump())

@router.get(
    "/nearby",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Nearby Stations",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_nearby(
    latitude: float = Query(..., ge=-90, le=90, description="Current latitude"),
    longitude: float = Query(..., ge=-180, le=180, description="Current longitude"),
    radius_km: float = Query(1.0, ge=0.1, le=10.0, description="Search radius in km"),
    db: Session = Depends(get_db)
):
    result = get_nearby_stations(db, latitude, longitude, radius_km)
    return build_response(0, "success", result.model_dump())