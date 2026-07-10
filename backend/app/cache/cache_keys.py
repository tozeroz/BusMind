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
    bucket_minutes: int = 5,
) -> str:
    minute_bucket = moment.minute - (moment.minute % bucket_minutes)
    time_bucket = moment.replace(minute=minute_bucket, second=0, microsecond=0).strftime("%Y%m%d%H%M")
    return f"recommend:{start_station_id}:{end_station_id}:{preference}:{time_bucket}"


def bus_arrival_lock(bus_stop_code: str, service_no: str) -> str:
    return f"lock:bus_arrival:{bus_stop_code}:{service_no}"
