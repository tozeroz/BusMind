from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.bus_service import (
    get_line_list,
    get_station_list,
    get_line_by_id,
    get_station_by_id,
    create_line,
    create_station,
    update_line,
    update_station,
    delete_line,
    delete_station,
    add_line_station,
    remove_line_station
)
from app.schemas.bus_schema import (
    BusLineDTO,
    BusLineCreateRequest,
    BusLineUpdateRequest,
    BusStationDTO,
    BusStationCreateRequest,
    BusStationUpdateRequest,
    LineStationCreateRequest,
    LineListResponse,
    StationListResponse
)
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

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
    "/lines",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Get Line List",
    responses={
        200: {"description": "Get success"}
    }
)
async def admin_list_lines(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    line_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    result = get_line_list(db, page, limit, line_name)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/lines/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Get Line Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Line not found"}
    }
)
async def admin_get_line(
    line_id: int,
    db: Session = Depends(get_db)
):
    line = get_line_by_id(db, line_id)
    if not line:
        raise HTTPException(
            status_code=404,
            detail=build_response(40400, "Line not found").model_dump()
        )
    return build_response(0, "success", line.model_dump())

@router.post(
    "/lines",
    response_model=ApiResponse,
    status_code=201,
    summary="Admin Create Line",
    responses={
        201: {"description": "Create success"},
        400: {"description": "Bad request"},
        409: {"description": "Line code exists"}
    }
)
async def admin_create_line(
    request: BusLineCreateRequest,
    db: Session = Depends(get_db)
):
    try:
        line = create_line(db, request)
        return build_response(0, "success", line.model_dump())
    except ValueError as e:
        if str(e) == "Line code already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40900, "Line code already exists").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.patch(
    "/lines/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Update Line",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Line not found"}
    }
)
async def admin_update_line(
    line_id: int,
    request: BusLineUpdateRequest,
    db: Session = Depends(get_db)
):
    line = update_line(db, line_id, request)
    if not line:
        raise HTTPException(
            status_code=404,
            detail=build_response(40400, "Line not found").model_dump()
        )
    return build_response(0, "success", line.model_dump())

@router.delete(
    "/lines/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Delete Line",
    responses={
        200: {"description": "Delete success"},
        404: {"description": "Line not found"}
    }
)
async def admin_delete_line(
    line_id: int,
    db: Session = Depends(get_db)
):
    success = delete_line(db, line_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=build_response(40400, "Line not found").model_dump()
        )
    return build_response(0, "success", None)

@router.get(
    "/stations",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Get Station List",
    responses={
        200: {"description": "Get success"}
    }
)
async def admin_list_stations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    station_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    result = get_station_list(db, page, limit, station_name)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/stations/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Get Station Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Station not found"}
    }
)
async def admin_get_station(
    station_id: int,
    db: Session = Depends(get_db)
):
    station = get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=404,
            detail=build_response(40401, "Station not found").model_dump()
        )
    return build_response(0, "success", station.model_dump())

@router.post(
    "/stations",
    response_model=ApiResponse,
    status_code=201,
    summary="Admin Create Station",
    responses={
        201: {"description": "Create success"},
        400: {"description": "Bad request"},
        409: {"description": "Station code exists"}
    }
)
async def admin_create_station(
    request: BusStationCreateRequest,
    db: Session = Depends(get_db)
):
    try:
        station = create_station(db, request)
        return build_response(0, "success", station.model_dump())
    except ValueError as e:
        if str(e) == "Station code already exists":
            raise HTTPException(
                status_code=409,
                detail=build_response(40901, "Station code already exists").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.patch(
    "/stations/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Update Station",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Station not found"}
    }
)
async def admin_update_station(
    station_id: int,
    request: BusStationUpdateRequest,
    db: Session = Depends(get_db)
):
    station = update_station(db, station_id, request)
    if not station:
        raise HTTPException(
            status_code=404,
            detail=build_response(40401, "Station not found").model_dump()
        )
    return build_response(0, "success", station.model_dump())

@router.delete(
    "/stations/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Delete Station",
    responses={
        200: {"description": "Delete success"},
        404: {"description": "Station not found"}
    }
)
async def admin_delete_station(
    station_id: int,
    db: Session = Depends(get_db)
):
    success = delete_station(db, station_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=build_response(40401, "Station not found").model_dump()
        )
    return build_response(0, "success", None)

@router.post(
    "/lines/{line_id}/stations",
    response_model=ApiResponse,
    status_code=201,
    summary="Admin Add Station to Line",
    responses={
        201: {"description": "Add success"},
        400: {"description": "Bad request"},
        409: {"description": "Station already in line"}
    }
)
async def admin_add_station_to_line(
    line_id: int,
    request: LineStationCreateRequest,
    db: Session = Depends(get_db)
):
    try:
        request.line_id = line_id
        result = add_line_station(db, request)
        return build_response(0, "success", result.model_dump())
    except ValueError as e:
        if str(e) == "Station already in line":
            raise HTTPException(
                status_code=409,
                detail=build_response(40902, str(e)).model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.delete(
    "/line-stations/{line_station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Admin Remove Station from Line",
    responses={
        200: {"description": "Remove success"},
        404: {"description": "Line station not found"}
    }
)
async def admin_remove_station_from_line(
    line_station_id: int,
    db: Session = Depends(get_db)
):
    success = remove_line_station(db, line_station_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=build_response(40402, "Line station not found").model_dump()
        )
    return build_response(0, "success", None)