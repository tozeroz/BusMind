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
    get_map_stations_by_line,
)
from app.services.traffic_heatmap_service import TrafficHeatmapQuery, get_traffic_heatmap
from app.schemas.map_schema import (
    MapStationResponse,
    RoadSegmentResponse,
    MapLineResponse,
)
from app.schemas.traffic_heatmap import TrafficHeatmapRequest
from app.schemas.user_schema import ApiResponse

router = APIRouter(prefix="/map", tags=["Map"])

# 地图模块接口说明：
# - /stations: 获取站点坐标列表，用于地图标记展示
# - /road-segments: 获取路段信息（站点间连线），包含路径坐标
# - /lines: 获取完整线路信息，包含整条线路的路径坐标
# - /traffic-heatmap: 仅返回推荐路线附近的道路实时拥堵分段

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
def list_map_stations(
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
def list_road_segments(
    line_ids: Optional[str] = Query(None, description="Comma-separated line ids, e.g. 15,105"),
    bbox: Optional[str] = Query(None, description="min_lon,min_lat,max_lon,max_lat"),
    db: Session = Depends(get_db)
):
    parsed_line_ids = _parse_line_ids(line_ids)
    parsed_bbox = _parse_bbox(bbox)
    result = get_road_segments(db, parsed_line_ids, parsed_bbox)
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
def list_map_lines(
    db: Session = Depends(get_db)
):
    result = get_map_lines(db)
    return build_response(0, "success", result.model_dump())


def _parse_line_ids(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    try:
        return tuple(
            sorted(
                {
                    int(item.strip())
                    for item in value.split(",")
                    if item.strip()
                }
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="line_ids must be comma-separated integers") from exc


def _parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        parts = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="bbox must be min_lon,min_lat,max_lon,max_lat") from exc
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="bbox must be min_lon,min_lat,max_lon,max_lat")
    min_lon, min_lat, max_lon, max_lat = parts
    if min_lon > max_lon or min_lat > max_lat:
        raise HTTPException(status_code=400, detail="bbox min values must not exceed max values")
    return parts

def _validate_heatmap_bounds(
    min_lat: float | None,
    max_lat: float | None,
    min_lon: float | None,
    max_lon: float | None,
) -> None:
    values = (min_lat, max_lat, min_lon, max_lon)
    if any(value is not None for value in values) and not all(value is not None for value in values):
        raise HTTPException(
            status_code=400,
            detail="min_lat, max_lat, min_lon and max_lon must be provided together",
        )
    if min_lat is not None and max_lat is not None and min_lat > max_lat:
        raise HTTPException(status_code=400, detail="min_lat must not be greater than max_lat")
    if min_lon is not None and max_lon is not None and min_lon > max_lon:
        raise HTTPException(status_code=400, detail="min_lon must not be greater than max_lon")


@router.get(
    "/traffic-heatmap",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Recommended Route Traffic Heatmap",
    responses={
        200: {"description": "Get success"},
        400: {"description": "Route filter is missing or invalid"},
    },
)
async def get_route_traffic_heatmap(
    line_id: list[int] | None = Query(None, description="Repeat for transfer routes, e.g. line_id=1&line_id=2"),
    segment_id: list[str] | None = Query(None, description="Exact map_road_segment ids"),
    observed_at: Optional[datetime] = Query(None, description="Use the latest traffic sample at or before this time"),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    match_radius_m: float = Query(120.0, ge=20.0, le=500.0),
    stale_after_minutes: int = Query(15, ge=1, le=1440),
    db: Session = Depends(get_db),
):
    if not line_id and not segment_id:
        raise HTTPException(status_code=400, detail="at least one line_id or segment_id is required")
    _validate_heatmap_bounds(min_lat, max_lat, min_lon, max_lon)
    result = get_traffic_heatmap(
        db,
        TrafficHeatmapQuery(
            line_ids=tuple(sorted(set(line_id or []))),
            segment_ids=tuple(dict.fromkeys(segment_id or [])),
            observed_at=observed_at,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            match_radius_m=match_radius_m,
            stale_after_minutes=stale_after_minutes,
        ),
    )
    return build_response(0, "success", result.model_dump())


@router.post(
    "/traffic-heatmap",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Exact Recommended Route Traffic Heatmap",
    responses={200: {"description": "Get success"}},
)
async def post_route_traffic_heatmap(
    payload: TrafficHeatmapRequest,
    db: Session = Depends(get_db),
):
    result = get_traffic_heatmap(
        db,
        TrafficHeatmapQuery(
            route_id=payload.route_id,
            route_segments=tuple(payload.route_segments),
            observed_at=payload.observed_at,
            min_lat=payload.min_lat,
            max_lat=payload.max_lat,
            min_lon=payload.min_lon,
            max_lon=payload.max_lon,
            match_radius_m=payload.match_radius_m,
            stale_after_minutes=payload.stale_after_minutes,
        ),
    )
    return build_response(0, "success", result.model_dump())

