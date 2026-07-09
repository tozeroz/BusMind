from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.vehicle_service import (
    get_vehicle_list,
    get_vehicle_by_id,
    create_vehicle,
    update_vehicle,
    delete_vehicle,
    get_vehicles_by_line
)
from app.schemas.vehicle_schema import (
    BusVehicleDTO,
    VehicleListResponse,
    VehicleCreateRequest,
    VehicleUpdateRequest
)
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

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
    "",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Vehicle List",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_vehicles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    result = get_vehicle_list(db, page, limit, line_id)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/{vehicle_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Vehicle Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Vehicle not found"}
    }
)
async def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump()
        )
    return build_response(0, "success", vehicle.model_dump())

@router.post(
    "",
    response_model=ApiResponse,
    status_code=201,
    summary="Create Vehicle",
    responses={
        201: {"description": "Create success"},
        400: {"description": "Bad request"},
        409: {"description": "Vehicle code exists"}
    }
)
async def create_vehicle_api(
    request: VehicleCreateRequest,
    db: Session = Depends(get_db)
):
    try:
        vehicle = create_vehicle(db, request)
        return build_response(0, "success", vehicle.model_dump())
    except ValueError as e:
        if str(e) == "Vehicle code already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40903, "Vehicle code already exists").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.patch(
    "/{vehicle_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Update Vehicle",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Vehicle not found"}
    }
)
async def update_vehicle_api(
    vehicle_id: int,
    request: VehicleUpdateRequest,
    db: Session = Depends(get_db)
):
    vehicle = update_vehicle(db, vehicle_id, request)
    if not vehicle:
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump()
        )
    return build_response(0, "success", vehicle.model_dump())

@router.delete(
    "/{vehicle_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Delete Vehicle",
    responses={
        200: {"description": "Delete success"},
        404: {"description": "Vehicle not found"}
    }
)
async def delete_vehicle_api(
    vehicle_id: int,
    db: Session = Depends(get_db)
):
    success = delete_vehicle(db, vehicle_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=build_response(40403, "Vehicle not found").model_dump()
        )
    return build_response(0, "success", None)

@router.get(
    "/line/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Vehicles by Line",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_vehicles_for_line(
    line_id: int,
    db: Session = Depends(get_db)
):
    vehicles = get_vehicles_by_line(db, line_id)
    return build_response(0, "success", {"vehicles": vehicles})