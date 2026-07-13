from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.time_utils import ensure_local_datetime, now_local
from app.models.transit_extra import MapRoadSegment, TrafficSpeedBand
from app.schemas.traffic_heatmap import (
    RouteGeometrySegmentDTO,
    TrafficHeatmapResponse,
    TrafficHeatmapRouteSegmentRequest,
    TrafficHeatmapSegmentDTO,
)
from app.services.map_service import get_road_segments


logger = logging.getLogger(__name__)
NO_DATA_COLOR = "#9CA3AF"
FREE_FLOW_COLOR = "#22C55E"
SLOW_COLOR = "#EAB308"
CONGESTED_COLOR = "#F97316"
SEVERE_COLOR = "#EF4444"
CONGESTION_LABELS = {
    "free_flow": "畅通",
    "slow": "缓行",
    "congested": "拥堵",
    "severe": "严重拥堵",
    "no_data": "暂无路况数据",
}


@dataclass(frozen=True, slots=True)
class TrafficHeatmapQuery:
    route_id: str | None = None
    line_ids: tuple[int, ...] = ()
    segment_ids: tuple[str, ...] = ()
    route_segments: tuple[TrafficHeatmapRouteSegmentRequest, ...] = ()
    observed_at: datetime | None = None
    min_lat: float | None = None
    max_lat: float | None = None
    min_lon: float | None = None
    max_lon: float | None = None
    match_radius_m: float = 120.0
    stale_after_minutes: int = 15


@dataclass(frozen=True, slots=True)
class _RouteSegment:
    route_segment_id: str
    line_id: int
    segment_order: int | None
    road_name: str | None
    coordinates: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class _TrafficRecord:
    link_id: int
    road_name: str | None
    road_category: str | None
    coordinates: tuple[tuple[float, float], ...]
    speed_band: int
    minimum_speed_kmh: float | None
    maximum_speed_kmh: float | None
    congestion_score: float
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class _Match:
    route_index: int
    traffic: _TrafficRecord
    distance_m: float
    projection: float
    start_projection: float
    end_projection: float
    rank_score: float


def _is_schema_missing_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return (
        "no such table" in text
        or "no such column" in text
        or "doesn't exist" in text
        or ("unknown column" in text)
    )


def _normalise_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    # traffic_speed_bands.query_time is stored as local wall-clock time without
    # tzinfo by the existing sync service. Convert an aware API value to the
    # configured project timezone before comparing it with the database column.
    return ensure_local_datetime(value).replace(tzinfo=None)


def _normalise_coordinates(value, fallback: Sequence[Sequence[float]] | None = None) -> tuple[tuple[float, float], ...]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            value = None
    result: list[tuple[float, float]] = []
    if isinstance(value, (list, tuple)):
        for point in value:
            if isinstance(point, dict):
                lon = point.get("longitude", point.get("lon"))
                lat = point.get("latitude", point.get("lat"))
            elif isinstance(point, (list, tuple)) and len(point) >= 2:
                lon, lat = point[0], point[1]
            else:
                continue
            try:
                result.append((float(lon), float(lat)))
            except (TypeError, ValueError):
                continue
    if len(result) >= 2:
        return tuple(result)
    if fallback:
        try:
            converted = tuple((float(point[0]), float(point[1])) for point in fallback)
        except (TypeError, ValueError, IndexError):
            return ()
        return converted if len(converted) >= 2 else ()
    return ()


def _route_segment_from_model(row: MapRoadSegment, segment_order: int | None = None) -> _RouteSegment:
    coordinates = _normalise_coordinates(
        row.path_coordinates,
        fallback=((row.start_lon, row.start_lat), (row.end_lon, row.end_lat)),
    )
    return _RouteSegment(
        route_segment_id=str(row.segment_id),
        line_id=int(row.line_id),
        segment_order=segment_order if segment_order is not None else row.stop_sequence,
        road_name=row.segment_name or row.line_name,
        coordinates=coordinates,
    )


def _route_segment_from_dto(row, segment_order: int | None = None) -> _RouteSegment:
    return _RouteSegment(
        route_segment_id=str(row.segment_id),
        line_id=int(row.line_id),
        segment_order=segment_order if segment_order is not None else row.stop_sequence,
        road_name=row.segment_name or row.line_name,
        coordinates=_normalise_coordinates(row.path_coordinates),
    )


def _slice_rows_for_route_leg(rows, request: TrafficHeatmapRouteSegmentRequest):
    """Return only the contiguous map rows for one recommendation leg.

    A line can contain separate direction records with overlapping stop
    sequences. Search each direction independently so a transfer leg never
    accidentally includes the opposite direction or the whole line.
    """

    line_rows = [row for row in rows if int(row.line_id) == request.line_id]
    if not line_rows:
        return []

    by_direction: dict[int | None, list] = {}
    for row in line_rows:
        by_direction.setdefault(getattr(row, "direction", None), []).append(row)

    for direction_rows in by_direction.values():
        ordered = sorted(
            direction_rows,
            key=lambda row: (
                getattr(row, "stop_sequence", None) is None,
                getattr(row, "stop_sequence", None) or 0,
                str(getattr(row, "segment_id", "")),
            ),
        )
        start_indexes = [
            index
            for index, row in enumerate(ordered)
            if int(row.start_station_id) == request.boarding_station_id
        ]
        end_indexes = [
            index
            for index, row in enumerate(ordered)
            if int(row.end_station_id) == request.alighting_station_id
        ]
        for start_index in start_indexes:
            later_ends = [index for index in end_indexes if index >= start_index]
            if later_ends:
                return ordered[start_index : min(later_ends) + 1]
    return []


def _slice_line_route(
    rows: list[MapRoadSegment],
    request: TrafficHeatmapRouteSegmentRequest,
) -> list[_RouteSegment]:
    selected = _slice_rows_for_route_leg(rows, request)
    result: list[_RouteSegment] = []
    for row in selected:
        segment = _route_segment_from_model(row, segment_order=request.segment_order)
        if segment.coordinates:
            result.append(segment)
    return result


def _slice_line_route_dtos(rows, request: TrafficHeatmapRouteSegmentRequest) -> list[_RouteSegment]:
    selected = _slice_rows_for_route_leg(rows, request)
    result: list[_RouteSegment] = []
    for row in selected:
        segment = _route_segment_from_dto(row, segment_order=request.segment_order)
        if segment.coordinates:
            result.append(segment)
    return result


def _load_route_segments(db: Session, query: TrafficHeatmapQuery) -> list[_RouteSegment]:
    try:
        model_query = db.query(MapRoadSegment)
        if query.segment_ids:
            model_query = model_query.filter(MapRoadSegment.segment_id.in_(query.segment_ids))
        elif query.line_ids or query.route_segments:
            line_ids = sorted(set(query.line_ids) | {item.line_id for item in query.route_segments})
            model_query = model_query.filter(MapRoadSegment.line_id.in_(line_ids))
        rows = model_query.order_by(
            MapRoadSegment.line_id,
            MapRoadSegment.direction,
            MapRoadSegment.stop_sequence,
        ).all()
    except (OperationalError, ProgrammingError) as exc:
        if not _is_schema_missing_error(exc):
            raise
        logger.warning("traffic heatmap route skeleton unavailable: %s", exc)
        db.rollback()
        rows = []

    if query.route_segments and rows:
        selected: list[_RouteSegment] = []
        for request in sorted(query.route_segments, key=lambda item: item.segment_order):
            selected.extend(_slice_line_route(rows, request))
        return _filter_route_by_bounds(selected, query)

    if rows:
        selected: list[_RouteSegment] = []
        for row in rows:
            segment = _route_segment_from_model(row)
            if segment.coordinates:
                selected.append(segment)
        return _filter_route_by_bounds(selected, query)

    # ``map_road_segment`` is allowed to be absent in a local/demo database.
    # Reuse the existing map service fallback based on line_station coordinates.
    response = get_road_segments(db)
    selected_dtos = response.segments
    if query.segment_ids:
        selected_dtos = [item for item in selected_dtos if item.segment_id in query.segment_ids]
    line_ids = set(query.line_ids) | {item.line_id for item in query.route_segments}
    if line_ids:
        selected_dtos = [item for item in selected_dtos if item.line_id in line_ids]
    if query.route_segments:
        selected: list[_RouteSegment] = []
        for request in sorted(query.route_segments, key=lambda item: item.segment_order):
            selected.extend(_slice_line_route_dtos(selected_dtos, request))
        return _filter_route_by_bounds(selected, query)

    selected: list[_RouteSegment] = []
    for item in selected_dtos:
        segment = _route_segment_from_dto(item)
        if segment.coordinates:
            selected.append(segment)
    return _filter_route_by_bounds(selected, query)


def _bounds_are_complete(query: TrafficHeatmapQuery) -> bool:
    return None not in (query.min_lat, query.max_lat, query.min_lon, query.max_lon)


def _segment_bounds(segment: _RouteSegment) -> tuple[float, float, float, float]:
    longitudes = [point[0] for point in segment.coordinates]
    latitudes = [point[1] for point in segment.coordinates]
    return min(latitudes), max(latitudes), min(longitudes), max(longitudes)


def _bounds_intersect(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    first_min_lat, first_max_lat, first_min_lon, first_max_lon = first
    second_min_lat, second_max_lat, second_min_lon, second_max_lon = second
    return not (
        first_max_lat < second_min_lat
        or first_min_lat > second_max_lat
        or first_max_lon < second_min_lon
        or first_min_lon > second_max_lon
    )


def _filter_route_by_bounds(segments: list[_RouteSegment], query: TrafficHeatmapQuery) -> list[_RouteSegment]:
    if not _bounds_are_complete(query):
        return segments
    requested_bounds = (
        float(query.min_lat),
        float(query.max_lat),
        float(query.min_lon),
        float(query.max_lon),
    )
    return [segment for segment in segments if _bounds_intersect(_segment_bounds(segment), requested_bounds)]


def _route_query_bounds(
    route_segments: Sequence[_RouteSegment],
    query: TrafficHeatmapQuery,
) -> tuple[float, float, float, float]:
    if _bounds_are_complete(query):
        return (
            float(query.min_lat),
            float(query.max_lat),
            float(query.min_lon),
            float(query.max_lon),
        )

    latitudes = [point[1] for segment in route_segments for point in segment.coordinates]
    longitudes = [point[0] for segment in route_segments for point in segment.coordinates]
    mean_lat = sum(latitudes) / len(latitudes)
    lat_buffer = query.match_radius_m / 111_320.0 + 0.001
    lon_scale = max(0.2, math.cos(math.radians(mean_lat)))
    lon_buffer = query.match_radius_m / (111_320.0 * lon_scale) + 0.001
    return (
        min(latitudes) - lat_buffer,
        max(latitudes) + lat_buffer,
        min(longitudes) - lon_buffer,
        max(longitudes) + lon_buffer,
    )


def _latest_traffic_rows(
    db: Session,
    bounds: tuple[float, float, float, float],
    observed_at: datetime | None,
) -> list[TrafficSpeedBand]:
    min_lat, max_lat, min_lon, max_lon = bounds
    as_of = _normalise_datetime(observed_at)

    spatial_filter = or_(
        and_(
            TrafficSpeedBand.start_lat.between(min_lat, max_lat),
            TrafficSpeedBand.start_lon.between(min_lon, max_lon),
        ),
        and_(
            TrafficSpeedBand.end_lat.between(min_lat, max_lat),
            TrafficSpeedBand.end_lon.between(min_lon, max_lon),
        ),
    )

    latest_query = db.query(
        TrafficSpeedBand.link_id.label("link_id"),
        func.max(TrafficSpeedBand.query_time).label("latest_time"),
    ).filter(
        TrafficSpeedBand.link_id.isnot(None),
        spatial_filter,
    )
    if as_of is not None:
        latest_query = latest_query.filter(TrafficSpeedBand.query_time <= as_of)
    latest_subquery = latest_query.group_by(TrafficSpeedBand.link_id).subquery()

    try:
        return (
            db.query(TrafficSpeedBand)
            .join(
                latest_subquery,
                and_(
                    TrafficSpeedBand.link_id == latest_subquery.c.link_id,
                    TrafficSpeedBand.query_time == latest_subquery.c.latest_time,
                ),
            )
            .filter(spatial_filter)
            .all()
        )
    except (OperationalError, ProgrammingError) as exc:
        if _is_schema_missing_error(exc):
            logger.warning("traffic speed bands unavailable: %s", exc)
            db.rollback()
            return []
        raise


def _traffic_record(row: TrafficSpeedBand) -> _TrafficRecord | None:
    if row.link_id is None:
        return None
    coordinates = _normalise_coordinates(
        row.line_coordinates,
        fallback=((row.start_lon, row.start_lat), (row.end_lon, row.end_lat)),
    )
    if not coordinates:
        return None
    speed_band = int(row.speed_band)
    score = (
        float(row.congestion_score)
        if row.congestion_score is not None
        else (8 - speed_band) / 7
    )
    score = min(1.0, max(0.0, score))
    return _TrafficRecord(
        link_id=int(row.link_id),
        road_name=row.road_name,
        road_category=row.road_category,
        coordinates=coordinates,
        speed_band=speed_band,
        minimum_speed_kmh=(
            float(row.minimum_speed_kmh) if row.minimum_speed_kmh is not None else None
        ),
        maximum_speed_kmh=(
            float(row.maximum_speed_kmh) if row.maximum_speed_kmh is not None else None
        ),
        congestion_score=round(score, 4),
        observed_at=row.query_time,
    )


def _to_xy(point: tuple[float, float], reference_lat: float) -> tuple[float, float]:
    lon, lat = point
    return (
        lon * 111_320.0 * math.cos(math.radians(reference_lat)),
        lat * 111_320.0,
    )


def _point_to_segment_distance(
    point: tuple[float, float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[float, float]:
    reference_lat = (point[1] + start[1] + end[1]) / 3
    px, py = _to_xy(point, reference_lat)
    ax, ay = _to_xy(start, reference_lat)
    bx, by = _to_xy(end, reference_lat)
    dx, dy = bx - ax, by - ay
    length_squared = dx * dx + dy * dy
    if length_squared <= 1e-9:
        return math.hypot(px - ax, py - ay), 0.0
    projection = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_squared))
    nearest_x = ax + projection * dx
    nearest_y = ay + projection * dy
    return math.hypot(px - nearest_x, py - nearest_y), projection


def _point_distance(start: tuple[float, float], end: tuple[float, float]) -> float:
    reference_lat = (start[1] + end[1]) / 2
    start_xy = _to_xy(start, reference_lat)
    end_xy = _to_xy(end, reference_lat)
    return math.hypot(end_xy[0] - start_xy[0], end_xy[1] - start_xy[1])


def _polyline_segment_lengths(
    coordinates: Sequence[tuple[float, float]],
) -> tuple[list[float], float]:
    lengths = [
        _point_distance(coordinates[index], coordinates[index + 1])
        for index in range(len(coordinates) - 1)
    ]
    return lengths, sum(lengths)


def _point_to_polyline_distance(
    point: tuple[float, float],
    coordinates: Sequence[tuple[float, float]],
) -> tuple[float, float]:
    best_distance = float("inf")
    best_projection = 0.0
    segment_lengths, total_length = _polyline_segment_lengths(coordinates)
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        distance, local_projection = _point_to_segment_distance(
            point,
            coordinates[index],
            coordinates[index + 1],
        )
        if distance < best_distance:
            best_distance = distance
            if total_length > 1e-9:
                best_projection = (traversed + local_projection * segment_length) / total_length
            else:
                best_projection = 0.0
        traversed += segment_length
    return best_distance, best_projection


def _interpolate_polyline(
    coordinates: Sequence[tuple[float, float]],
    projection: float,
) -> tuple[float, float]:
    projection = max(0.0, min(1.0, projection))
    segment_lengths, total_length = _polyline_segment_lengths(coordinates)
    if total_length <= 1e-9:
        return coordinates[0]
    target = projection * total_length
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        if traversed + segment_length >= target or index == len(segment_lengths) - 1:
            local = 0.0 if segment_length <= 1e-9 else (target - traversed) / segment_length
            start = coordinates[index]
            end = coordinates[index + 1]
            return (
                start[0] + (end[0] - start[0]) * local,
                start[1] + (end[1] - start[1]) * local,
            )
        traversed += segment_length
    return coordinates[-1]


def _slice_polyline(
    coordinates: Sequence[tuple[float, float]],
    start_projection: float,
    end_projection: float,
) -> tuple[tuple[float, float], ...]:
    start_projection, end_projection = sorted(
        (max(0.0, min(1.0, start_projection)), max(0.0, min(1.0, end_projection)))
    )
    segment_lengths, total_length = _polyline_segment_lengths(coordinates)
    if total_length <= 1e-9:
        return tuple(coordinates)

    start_distance = start_projection * total_length
    end_distance = end_projection * total_length
    result = [_interpolate_polyline(coordinates, start_projection)]
    traversed = 0.0
    for index, segment_length in enumerate(segment_lengths):
        traversed += segment_length
        if start_distance < traversed < end_distance:
            result.append(coordinates[index + 1])
    result.append(_interpolate_polyline(coordinates, end_projection))

    deduplicated: list[tuple[float, float]] = []
    for point in result:
        if not deduplicated or _point_distance(deduplicated[-1], point) > 0.05:
            deduplicated.append(point)
    if len(deduplicated) < 2:
        return tuple(coordinates)
    return tuple(deduplicated)


def _direction_alignment(
    route_coordinates: Sequence[tuple[float, float]],
    traffic_coordinates: Sequence[tuple[float, float]],
) -> float:
    route_start, route_end = route_coordinates[0], route_coordinates[-1]
    traffic_start, traffic_end = traffic_coordinates[0], traffic_coordinates[-1]
    reference_lat = (route_start[1] + route_end[1] + traffic_start[1] + traffic_end[1]) / 4
    route_start_xy = _to_xy(route_start, reference_lat)
    route_end_xy = _to_xy(route_end, reference_lat)
    traffic_start_xy = _to_xy(traffic_start, reference_lat)
    traffic_end_xy = _to_xy(traffic_end, reference_lat)
    route_vector = (
        route_end_xy[0] - route_start_xy[0],
        route_end_xy[1] - route_start_xy[1],
    )
    traffic_vector = (
        traffic_end_xy[0] - traffic_start_xy[0],
        traffic_end_xy[1] - traffic_start_xy[1],
    )
    route_length = math.hypot(*route_vector)
    traffic_length = math.hypot(*traffic_vector)
    if route_length < 10 or traffic_length < 10:
        return 1.0
    cosine = (route_vector[0] * traffic_vector[0] + route_vector[1] * traffic_vector[1]) / (
        route_length * traffic_length
    )
    return abs(cosine)


def _best_route_match(
    traffic: _TrafficRecord,
    route_segments: Sequence[_RouteSegment],
    match_radius_m: float,
) -> _Match | None:
    midpoint = traffic.coordinates[len(traffic.coordinates) // 2]
    best: _Match | None = None
    for route_index, route in enumerate(route_segments):
        distance, projection = _point_to_polyline_distance(midpoint, route.coordinates)
        if distance > match_radius_m:
            continue
        alignment = _direction_alignment(route.coordinates, traffic.coordinates)
        if alignment < 0.45:
            continue
        _, start_projection = _point_to_polyline_distance(traffic.coordinates[0], route.coordinates)
        _, end_projection = _point_to_polyline_distance(traffic.coordinates[-1], route.coordinates)
        rank_score = distance + (1.0 - alignment) * 25.0
        candidate = _Match(
            route_index=route_index,
            traffic=traffic,
            distance_m=distance,
            projection=projection,
            start_projection=start_projection,
            end_projection=end_projection,
            rank_score=rank_score,
        )
        if best is None or candidate.rank_score < best.rank_score:
            best = candidate
    return best


def _matched_route_coordinates(route: _RouteSegment, match: _Match) -> tuple[tuple[float, float], ...]:
    start_projection = match.start_projection
    end_projection = match.end_projection
    _, route_length = _polyline_segment_lengths(route.coordinates)
    _, traffic_length = _polyline_segment_lengths(match.traffic.coordinates)

    # If both traffic endpoints project to almost the same point, retain a small
    # section whose length approximates the LTA road band. This also guarantees
    # that the returned heat geometry remains on the recommended route itself.
    projected_span = abs(end_projection - start_projection)
    estimated_span = (
        min(1.0, traffic_length / route_length) if route_length > 1e-9 else 1.0
    )
    if projected_span < 0.002:
        half_span = max(0.002, estimated_span / 2)
        start_projection = match.projection - half_span
        end_projection = match.projection + half_span
    return _slice_polyline(route.coordinates, start_projection, end_projection)


def _congestion_style(score: float) -> tuple[str, str]:
    if score < 0.25:
        return "free_flow", FREE_FLOW_COLOR
    if score < 0.50:
        return "slow", SLOW_COLOR
    if score < 0.75:
        return "congested", CONGESTED_COLOR
    return "severe", SEVERE_COLOR


def _is_stale(observed_at: datetime, now: datetime, stale_after_minutes: int) -> bool:
    current = now
    observed = observed_at
    if current.tzinfo is not None and observed.tzinfo is None:
        current = current.replace(tzinfo=None)
    elif current.tzinfo is None and observed.tzinfo is not None:
        observed = observed.replace(tzinfo=None)
    return current - observed > timedelta(minutes=stale_after_minutes)


def _route_geometry_dto(segment: _RouteSegment) -> RouteGeometrySegmentDTO:
    return RouteGeometrySegmentDTO(
        route_segment_id=segment.route_segment_id,
        line_id=segment.line_id,
        segment_order=segment.segment_order,
        road_name=segment.road_name,
        coordinates=[[point[0], point[1]] for point in segment.coordinates],
    )


def get_traffic_heatmap(db: Session, query: TrafficHeatmapQuery) -> TrafficHeatmapResponse:
    if not (query.line_ids or query.segment_ids or query.route_segments):
        raise ValueError("at least one line_id, segment_id or route_segment is required")
    if query.match_radius_m < 20 or query.match_radius_m > 500:
        raise ValueError("match_radius_m must be between 20 and 500")
    if _bounds_are_complete(query):
        if float(query.min_lat) > float(query.max_lat):
            raise ValueError("min_lat must not be greater than max_lat")
        if float(query.min_lon) > float(query.max_lon):
            raise ValueError("min_lon must not be greater than max_lon")

    route_segments = _load_route_segments(db, query)
    generated_at = now_local()
    if not route_segments:
        return TrafficHeatmapResponse(
            route_id=query.route_id,
            line_ids=sorted(set(query.line_ids) | {item.line_id for item in query.route_segments}),
            route_segments=[],
            traffic_segments=[],
            total=0,
            matched_count=0,
            no_data_count=0,
            observed_at=None,
            generated_at=generated_at,
            stale_after_minutes=query.stale_after_minutes,
        )

    traffic_rows = _latest_traffic_rows(
        db,
        bounds=_route_query_bounds(route_segments, query),
        observed_at=query.observed_at,
    )
    traffic_by_link: dict[int, _TrafficRecord] = {}
    for row in traffic_rows:
        record = _traffic_record(row)
        if record is None:
            continue
        current = traffic_by_link.get(record.link_id)
        if current is None or record.observed_at > current.observed_at:
            traffic_by_link[record.link_id] = record
    traffic_records = list(traffic_by_link.values())

    matches_by_route: dict[int, list[_Match]] = {index: [] for index in range(len(route_segments))}
    for traffic in traffic_records:
        match = _best_route_match(traffic, route_segments, query.match_radius_m)
        if match is not None:
            matches_by_route[match.route_index].append(match)

    traffic_segments: list[TrafficHeatmapSegmentDTO] = []
    matched_count = 0
    no_data_count = 0
    latest_observed_at: datetime | None = None

    for route_index, route in enumerate(route_segments):
        matches = sorted(
            matches_by_route[route_index],
            key=lambda item: (item.projection, item.distance_m, item.traffic.link_id),
        )
        if not matches:
            no_data_count += 1
            traffic_segments.append(
                TrafficHeatmapSegmentDTO(
                    route_segment_id=route.route_segment_id,
                    line_id=route.line_id,
                    segment_order=route.segment_order,
                    link_id=None,
                    road_name=route.road_name,
                    road_category=None,
                    coordinates=[[point[0], point[1]] for point in route.coordinates],
                    speed_band=None,
                    minimum_speed_kmh=None,
                    maximum_speed_kmh=None,
                    congestion_score=None,
                    congestion_level="no_data",
                    congestion_label=CONGESTION_LABELS["no_data"],
                    heat_color=NO_DATA_COLOR,
                    observed_at=None,
                    query_time=None,
                    data_status="no_data",
                    is_stale=False,
                    match_distance_m=None,
                )
            )
            continue

        for match in matches:
            traffic = match.traffic
            congestion_level, heat_color = _congestion_style(traffic.congestion_score)
            stale = _is_stale(traffic.observed_at, generated_at, query.stale_after_minutes)
            matched_count += 1
            if latest_observed_at is None or traffic.observed_at > latest_observed_at:
                latest_observed_at = traffic.observed_at
            traffic_segments.append(
                TrafficHeatmapSegmentDTO(
                    route_segment_id=route.route_segment_id,
                    line_id=route.line_id,
                    segment_order=route.segment_order,
                    link_id=traffic.link_id,
                    road_name=traffic.road_name or route.road_name,
                    road_category=traffic.road_category,
                    coordinates=[
                        [point[0], point[1]]
                        for point in _matched_route_coordinates(route, match)
                    ],
                    speed_band=traffic.speed_band,
                    minimum_speed_kmh=traffic.minimum_speed_kmh,
                    maximum_speed_kmh=traffic.maximum_speed_kmh,
                    congestion_score=traffic.congestion_score,
                    congestion_level=congestion_level,
                    congestion_label=CONGESTION_LABELS[congestion_level],
                    heat_color=heat_color,
                    observed_at=traffic.observed_at,
                    query_time=traffic.observed_at,
                    data_status="stale" if stale else "realtime",
                    is_stale=stale,
                    match_distance_m=round(match.distance_m, 2),
                )
            )

    return TrafficHeatmapResponse(
        route_id=query.route_id,
        line_ids=sorted({segment.line_id for segment in route_segments}),
        route_segments=[_route_geometry_dto(segment) for segment in route_segments],
        traffic_segments=traffic_segments,
        total=len(traffic_segments),
        matched_count=matched_count,
        no_data_count=no_data_count,
        observed_at=latest_observed_at,
        generated_at=generated_at,
        stale_after_minutes=query.stale_after_minutes,
    )
