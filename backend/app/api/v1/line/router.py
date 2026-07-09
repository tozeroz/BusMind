from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.bus_service import (
    get_line_list,
    get_line_by_id,
    create_line,
    update_line,
    delete_line,
    get_line_stations,
    add_line_station,
    update_line_station,
    remove_line_station,
    get_station_list,
    get_station_by_id,
    create_station,
    update_station,
    delete_station,
    get_nearby_stations,
    get_station_lines,
    get_stations_with_coordinates
)
from app.schemas.bus_schema import (
    BusLineDTO,
    BusLineWithStationsDTO,
    BusLineCreateRequest,
    BusLineUpdateRequest,
    BusStationDTO,
    BusStationCreateRequest,
    BusStationUpdateRequest,
    LineStationDTO,
    LineStationCreateRequest,
    LineStationUpdateRequest,
    NearbyStationResponse,
    StationLinesResponse,
    LineListResponse,
    StationListResponse
)
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/lines", tags=["Lines"])

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
    summary="Get Line List",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_lines(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    line_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    result = get_line_list(db, page, limit, line_name)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Line Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Line not found"}
    }
)
async def get_line(
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
    "",
    response_model=ApiResponse,
    status_code=201,
    summary="Create Line",
    responses={
        201: {"description": "Create success"},
        400: {"description": "Bad request"},
        409: {"description": "Line code exists"}
    }
)
async def create_line_api(
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
    "/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Update Line",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Line not found"}
    }
)
async def update_line_api(
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
    "/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Delete Line",
    responses={
        200: {"description": "Delete success"},
        404: {"description": "Line not found"}
    }
)
async def delete_line_api(
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
    "/{line_id}/stations",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Line Stations",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_line_stations(
    line_id: int,
    db: Session = Depends(get_db)
):
    stations = get_line_stations(db, line_id)
    return build_response(0, "success", {"stations": stations})

@router.post(
    "/{line_id}/stations",
    response_model=ApiResponse,
    status_code=201,
    summary="Add Station to Line",
    responses={
        201: {"description": "Add success"},
        400: {"description": "Bad request"},
        409: {"description": "Station already in line"}
    }
)
async def add_station_to_line(
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
                detail=build_response(40901, str(e)).model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@router.patch(
    "/stations/{line_station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Update Line Station Order/Direction",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Line station not found"}
    }
)
async def update_line_station_api(
    line_station_id: int,
    request: LineStationUpdateRequest,
    db: Session = Depends(get_db)
):
    result = update_line_station(db, line_station_id, request)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=build_response(40402, "Line station not found").model_dump()
        )
    return build_response(0, "success", result.model_dump())

@router.delete(
    "/stations/{line_station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Remove Station from Line",
    responses={
        200: {"description": "Remove success"},
        404: {"description": "Line station not found"}
    }
)
async def remove_station_from_line(
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


station_router = APIRouter(prefix="/stations", tags=["Stations"])

@station_router.get(
    "",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Station List",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_stations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    station_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    result = get_station_list(db, page, limit, station_name)
    return build_response(0, "success", result.model_dump())

@station_router.get(
    "/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Station Detail",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Station not found"}
    }
)
async def get_station(
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

@station_router.post(
    "",
    response_model=ApiResponse,
    status_code=201,
    summary="Create Station",
    responses={
        201: {"description": "Create success"},
        400: {"description": "Bad request"},
        409: {"description": "Station code exists"}
    }
)
async def create_station_api(
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
                detail=build_response(40902, "Station code already exists").model_dump()
            )
        raise HTTPException(
            status_code=400,
            detail=build_response(40001, str(e)).model_dump()
        )

@station_router.patch(
    "/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Update Station",
    responses={
        200: {"description": "Update success"},
        404: {"description": "Station not found"}
    }
)
async def update_station_api(
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

@station_router.delete(
    "/{station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Delete Station",
    responses={
        200: {"description": "Delete success"},
        404: {"description": "Station not found"}
    }
)
async def delete_station_api(
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

@station_router.get(
    "/{station_id}/lines",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Station Lines",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Station not found"}
    }
)
async def get_station_lines_api(
    station_id: int,
    db: Session = Depends(get_db)
):
    result = get_station_lines(db, station_id)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=build_response(40401, "Station not found").model_dump()
        )
    return build_response(0, "success", result.model_dump())

@station_router.post(
    "/nearby",
    response_model=ApiResponse,
    status_code=200,
    summary="Search Nearby Stations",
    responses={
        200: {"description": "Get success"}
    }
)
async def search_nearby_stations(
    latitude: float = Body(..., embed=True),
    longitude: float = Body(..., embed=True),
    radius_km: float = Body(1.0, embed=True),
    db: Session = Depends(get_db)
):
    result = get_nearby_stations(db, latitude, longitude, radius_km)
    return build_response(0, "success", result.model_dump())

@station_router.get(
    "/coordinates/all",
    response_model=ApiResponse,
    status_code=200,
    summary="Get All Station Coordinates",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_all_station_coordinates(
    db: Session = Depends(get_db)
):
    stations = get_stations_with_coordinates(db)
    return build_response(0, "success", {"stations": stations})