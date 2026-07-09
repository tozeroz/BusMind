from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.map_service import (
    get_map_stations,
    get_road_segments,
    get_map_lines,
    get_map_stations_by_line
)
from app.schemas.map_schema import (
    MapStationResponse,
    RoadSegmentResponse,
    MapLineResponse
)
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/map", tags=["Map"])

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
    "/stations",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Map Stations",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_map_stations(
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    if line_id:
        result = get_map_stations_by_line(db, line_id)
    else:
        result = get_map_stations(db)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/road-segments",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Road Segments",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_road_segments(
    db: Session = Depends(get_db)
):
    result = get_road_segments(db)
    return build_response(0, "success", result.model_dump())

@router.get(
    "/lines",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Map Lines",
    responses={
        200: {"description": "Get success"}
    }
)
async def list_map_lines(
    db: Session = Depends(get_db)
):
    result = get_map_lines(db)
    return build_response(0, "success", result.model_dump())