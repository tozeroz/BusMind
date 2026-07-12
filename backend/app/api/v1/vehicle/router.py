from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies.auth import get_current_admin_user, get_db
from app.models.user import User
from app.schemas.user_schema import ApiResponse
from app.schemas.vehicle_schema import VehicleCreateRequest, VehicleUpdateRequest
from app.services.vehicle_service import (
    create_vehicle,
    delete_vehicle,
    get_vehicle_by_id,
    get_vehicle_list,
    get_vehicles_by_line,
    update_vehicle,
)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])
bus_vehicles_router = APIRouter(prefix="/bus-vehicles", tags=["Vehicles"])


def build_response(code: int, message: str, data=None) -> ApiResponse:
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        trace_id=f"req_{uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(),
    )


@router.get("", response_model=ApiResponse, summary="Get Vehicle List")
async def list_vehicles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    result = get_vehicle_list(db, page, limit, line_id)
    return build_response(0, "success", result.model_dump())


# Static paths must be registered before /{vehicle_id}; otherwise FastAPI treats
# "realtime" as a vehicle_id and returns a validation error.
@router.get("/realtime", response_model=ApiResponse, summary="Get Real-time Vehicle Positions")
async def get_realtime_vehicles(
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    if line_id is not None:
        vehicles = get_vehicles_by_line(db, line_id)
    else:
        vehicles = get_vehicle_list(db, page=1, limit=100).vehicles
    return build_response(0, "success", {"vehicles": [item.model_dump() for item in vehicles]})


@bus_vehicles_router.get("/realtime", response_model=ApiResponse, summary="Get Real-time Bus Vehicle Positions")
async def get_bus_realtime_vehicles(
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
):
    if line_id is not None:
        vehicles = get_vehicles_by_line(db, line_id)
    else:
        vehicles = get_vehicle_list(db, page=1, limit=100).vehicles
    return build_response(0, "success", {"vehicles": [item.model_dump() for item in vehicles]})


@router.get("/line/{line_id}", response_model=ApiResponse, summary="Get Vehicles by Line")
async def get_vehicles_for_line(line_id: int, db: Session = Depends(get_db)):
    vehicles = get_vehicles_by_line(db, line_id)
    return build_response(0, "success", {"vehicles": [item.model_dump() for item in vehicles]})


@router.get("/{vehicle_id}", response_model=ApiResponse, summary="Get Vehicle Detail")
async def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump(),
        )
    return build_response(0, "success", vehicle.model_dump())


@router.post("", response_model=ApiResponse, status_code=201, summary="Create Vehicle")
async def create_vehicle_api(
    request: VehicleCreateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    try:
        vehicle = create_vehicle(db, request)
        return build_response(0, "success", vehicle.model_dump())
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if message in {"Vehicle code already exists", "Vehicle id already exists"} else 400
        business_code = 40903 if status_code == 409 else 40001
        raise HTTPException(
            status_code=status_code,
            detail=build_response(business_code, message).model_dump(),
        ) from exc


@router.patch("/{vehicle_id}", response_model=ApiResponse, summary="Update Vehicle")
async def update_vehicle_api(
    vehicle_id: int,
    request: VehicleUpdateRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    try:
        vehicle = update_vehicle(db, vehicle_id, request)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(exc)).model_dump(),
        ) from exc
    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump(),
        )
    return build_response(0, "success", vehicle.model_dump())


@router.delete("/{vehicle_id}", response_model=ApiResponse, summary="Delete Vehicle")
async def delete_vehicle_api(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(get_current_admin_user),
):
    if not delete_vehicle(db, vehicle_id):
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump(),
        )
    return build_response(0, "success", None)