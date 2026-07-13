from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any, Optional
from app.cache import memory_cache_provider
from app.cache.cache_keys import bus_arrival_service, bus_arrival_stop
from app.core.time_utils import now_local
from app.dependencies.auth import get_db
from app.services.collector_service.service import LtaCollectorService
from app.services.lta_service import LtaDataMallClient, LtaDataMallConfig, LtaDataMallError
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


def _payload_value(payload: Any, key: str):
    if isinstance(payload, dict):
        return payload.get(key)
    return getattr(payload, key, None)


def _parse_arrival_time(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=now_local().tzinfo)
        return parsed
    except ValueError:
        return None


def _eta_minutes_from_payload(payload: Any) -> float | None:
    estimated_arrival = _parse_arrival_time(_payload_value(payload, "estimated_arrival"))
    if estimated_arrival is not None:
        remaining_seconds = (estimated_arrival - now_local()).total_seconds()
        return round(max(0.0, remaining_seconds / 60), 1)
    try:
        return round(float(_payload_value(payload, "eta_minutes")), 1)
    except (TypeError, ValueError):
        return None


def _normalize_bus_arrival(payload: Any) -> dict[str, Any] | None:
    eta_minutes = _eta_minutes_from_payload(payload)
    if eta_minutes is None:
        return None
    return {
        "bus_stop_code": _payload_value(payload, "bus_stop_code"),
        "service_no": _payload_value(payload, "service_no"),
        "operator": _payload_value(payload, "operator"),
        "visit_order": _payload_value(payload, "visit_order"),
        "estimated_arrival": _payload_value(payload, "estimated_arrival"),
        "eta_minutes": eta_minutes,
        "load_code": _payload_value(payload, "load_code"),
        "query_time": _payload_value(payload, "query_time"),
        "source": "memory_cache",
    }


def _arrival_items(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("Services"), list):
        return value["Services"]
    return [value]


async def _refresh_bus_arrival_cache(
    bus_stop_code: str,
    service_no: str | None,
) -> list[dict[str, object]]:
    from app.core.intelligence_settings import settings as intelligence_settings

    if not intelligence_settings.lta_account_key:
        return []
    client = LtaDataMallClient(
        LtaDataMallConfig(
            account_key=intelligence_settings.lta_account_key,
            base_url=intelligence_settings.lta_base_url,
            timeout_seconds=intelligence_settings.lta_timeout_seconds,
        )
    )
    collector = LtaCollectorService(client)
    return await collector.refresh_bus_arrival(bus_stop_code, service_no)

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
    "/bus-arrival",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Cached Bus Arrival",
)
async def get_cached_bus_arrival(
    bus_stop_code: str = Query(..., min_length=1),
    service_no: Optional[str] = Query(None, min_length=1),
):
    normalized_stop_code = bus_stop_code.strip()
    normalized_service_no = service_no.strip() if service_no else None
    cached = memory_cache_provider.get(bus_arrival_stop(normalized_stop_code))
    if normalized_service_no:
        cached = memory_cache_provider.get(
            bus_arrival_service(normalized_stop_code, normalized_service_no)
        ) or cached
    arrivals = [
        item
        for item in (_normalize_bus_arrival(payload) for payload in _arrival_items(cached))
        if item is not None
    ]
    if normalized_service_no:
        arrivals = [
            item for item in arrivals
            if str(item.get("service_no") or "") == normalized_service_no
        ]
    if not arrivals:
        try:
            fresh_payloads = await _refresh_bus_arrival_cache(
                normalized_stop_code,
                normalized_service_no,
            )
            arrivals = [
                item
                for item in (
                    _normalize_bus_arrival(payload)
                    for payload in _arrival_items(fresh_payloads)
                )
                if item is not None
            ]
        except LtaDataMallError:
            arrivals = []
    arrivals.sort(key=lambda item: float(item["eta_minutes"]))
    return build_response(
        0,
        "success",
        {
            "bus_stop_code": normalized_stop_code,
            "service_no": normalized_service_no,
            "arrivals": arrivals,
            "next_arrival": arrivals[0] if arrivals else None,
            "source": "memory_cache_or_lta" if arrivals else "cache_miss",
        },
    )

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

