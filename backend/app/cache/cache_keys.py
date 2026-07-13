from __future__ import annotations

from datetime import datetime


def bus_arrival_stop(bus_stop_code: str) -> str:
    return f"bus_arrival:{bus_stop_code}"


def bus_arrival_service(bus_stop_code: str, service_no: str) -> str:
    return f"bus_arrival:{bus_stop_code}:{service_no}"


def traffic_speed_bands_latest() -> str:
    return "traffic_speed_bands:latest"


def traffic_speed_band_link(link_id: int | str) -> str:
    return f"traffic_speed_bands:{link_id}"


def recommend_route(
    start_station_id: int,
    end_station_id: int,
    preference: str,
    moment: datetime,
    allow_transfer: bool,
    max_transfer_count: int,
    bucket_minutes: int = 5,
) -> str:
    minute_bucket = moment.minute - (moment.minute % bucket_minutes)
    time_bucket = moment.replace(minute=minute_bucket, second=0, microsecond=0).strftime("%Y%m%d%H%M")
    return (
        f"recommend:{start_station_id}:{end_station_id}:{preference}:"
        f"{int(allow_transfer)}:{max_transfer_count}:{time_bucket}"
    )


def map_stations(line_id: int | None = None) -> str:
    suffix = "all" if line_id is None else str(line_id)
    return f"map:stations:v1:{suffix}"


def map_lines() -> str:
    return "map:lines:v1"


def map_road_segments(
    line_ids: tuple[int, ...] = (),
    bbox: tuple[float, float, float, float] | None = None,
) -> str:
    line_part = ",".join(str(line_id) for line_id in line_ids) if line_ids else "all"
    bbox_part = (
        "all"
        if bbox is None
        else ",".join(f"{value:.6f}" for value in bbox)
    )
    return f"map:road_segments:v1:{line_part}:{bbox_part}"


def line_list(page: int, limit: int, line_name: str | None = None) -> str:
    name_part = (line_name or "").strip().lower()
    return f"lines:list:v1:{page}:{limit}:{name_part}"


def vehicle_list(page: int, limit: int, line_id: int | None = None) -> str:
    line_part = "all" if line_id is None else str(line_id)
    return f"vehicles:list:v1:{page}:{limit}:{line_part}"


def passenger_flow_trend(
    line_id: int | None,
    station_id: int | None,
    start_date: datetime | None,
    end_date: datetime | None,
    granularity: str,
) -> str:
    start_part = start_date.isoformat() if start_date else "latest"
    end_part = end_date.isoformat() if end_date else "latest"
    return (
        f"history:passenger_flow:v1:{line_id or 'all'}:{station_id or 'all'}:"
        f"{start_part}:{end_part}:{granularity}"
    )


def bus_arrival_lock(bus_stop_code: str, service_no: str) -> str:
    return f"lock:bus_arrival:{bus_stop_code}:{service_no}"
