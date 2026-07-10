from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import floor
from typing import Any

import httpx

from app.core.time_utils import now_local


class LtaDataMallError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class LtaBusArrival:
    bus_stop_code: str
    service_no: str
    operator: str
    estimated_arrival: datetime
    eta_minutes: float
    monitored: bool
    latitude: float | None
    longitude: float | None
    load_code: str
    feature: str
    bus_type: str


@dataclass(frozen=True, slots=True)
class LtaTrafficSpeedBand:
    query_time: datetime
    link_id: int | None
    road_name: str | None
    road_category: str | None
    speed_band: int
    minimum_speed_kmh: float | None
    maximum_speed_kmh: float | None
    congestion_score: float
    heat_color: str | None
    start_lon: float
    start_lat: float
    end_lon: float
    end_lat: float
    line_coordinates: list[list[float]]


@dataclass(frozen=True, slots=True)
class LtaDataMallConfig:
    account_key: str
    base_url: str = "https://datamall2.mytransport.sg/ltaodataservice"
    timeout_seconds: float = 12.0


class LtaDataMallClient:
    """Minimal client for LTA DataMall v3 Bus Arrival.

    Only Bus Arrival is implemented because ETA and vehicle load belong to
    engineer B. Bus Stops, Bus Routes and Bus Services remain engineer A/data
    engineer responsibilities.
    """

    def __init__(self, config: LtaDataMallConfig) -> None:
        self.config = config

    async def get_bus_arrivals(
        self,
        bus_stop_code: str,
        service_no: str | None = None,
    ) -> list[LtaBusArrival]:
        url = f"{self.config.base_url.rstrip('/')}/v3/BusArrival"
        params: dict[str, str] = {"BusStopCode": bus_stop_code}
        if service_no:
            params["ServiceNo"] = service_no
        headers = {
            "AccountKey": self.config.account_key,
            "accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise LtaDataMallError("LTA DataMall 请求超时") from exc
        except httpx.HTTPError as exc:
            raise LtaDataMallError("LTA DataMall 网络请求失败") from exc

        if response.status_code >= 400:
            raise LtaDataMallError(
                f"LTA DataMall 返回 HTTP {response.status_code}: {_safe_error(response)}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise LtaDataMallError("LTA DataMall 返回了非 JSON 响应") from exc

        services = body.get("Services")
        if not isinstance(services, list):
            raise LtaDataMallError("LTA DataMall 响应缺少 Services")

        arrivals: list[LtaBusArrival] = []
        for service in services:
            if not isinstance(service, dict):
                continue
            current_service = str(service.get("ServiceNo") or "").strip()
            if service_no and current_service != service_no:
                continue
            next_bus = service.get("NextBus")
            if not isinstance(next_bus, dict):
                continue
            parsed = _parse_next_bus(
                bus_stop_code=bus_stop_code,
                service_no=current_service,
                operator=str(service.get("Operator") or "").strip(),
                next_bus=next_bus,
            )
            if parsed is not None:
                arrivals.append(parsed)
        return arrivals

    async def get_traffic_speed_bands(
        self,
        *,
        page_size: int = 500,
        max_pages: int | None = None,
    ) -> list[LtaTrafficSpeedBand]:
        rows: list[LtaTrafficSpeedBand] = []
        query_time = now_local()
        for page_index, skip in enumerate(range(0, 10_000_000, page_size)):
            if max_pages is not None and page_index >= max_pages:
                break
            body = await self._get_json(
                "v4/TrafficSpeedBands",
                params={"$skip": str(skip)},
            )
            value = body.get("value")
            if not isinstance(value, list) or not value:
                break
            for item in value:
                if not isinstance(item, dict):
                    continue
                parsed = _parse_traffic_speed_band(item, query_time)
                if parsed is not None:
                    rows.append(parsed)
            if len(value) < page_size:
                break
        return rows

    async def _get_json(
        self,
        endpoint: str,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {
            "AccountKey": self.config.account_key,
            "accept": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.get(url, params=params, headers=headers)
        except httpx.TimeoutException as exc:
            raise LtaDataMallError("LTA DataMall 请求超时") from exc
        except httpx.HTTPError as exc:
            raise LtaDataMallError("LTA DataMall 网络请求失败") from exc

        if response.status_code >= 400:
            raise LtaDataMallError(
                f"LTA DataMall 返回 HTTP {response.status_code}: {_safe_error(response)}"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise LtaDataMallError("LTA DataMall 返回了非 JSON 响应") from exc
        if not isinstance(body, dict):
            raise LtaDataMallError("LTA DataMall 返回了非对象 JSON 响应")
        return body


def _parse_next_bus(
    *,
    bus_stop_code: str,
    service_no: str,
    operator: str,
    next_bus: dict[str, Any],
) -> LtaBusArrival | None:
    raw_arrival = str(next_bus.get("EstimatedArrival") or "").strip()
    if not raw_arrival:
        return None
    try:
        estimated_arrival = datetime.fromisoformat(raw_arrival.replace("Z", "+00:00"))
    except ValueError:
        return None

    seconds = (estimated_arrival - now_local()).total_seconds()
    eta_minutes = float(max(0, floor(seconds / 60)))
    return LtaBusArrival(
        bus_stop_code=bus_stop_code,
        service_no=service_no,
        operator=operator,
        estimated_arrival=estimated_arrival,
        eta_minutes=eta_minutes,
        monitored=int(next_bus.get("Monitored") or 0) == 1,
        latitude=_optional_float(next_bus.get("Latitude")),
        longitude=_optional_float(next_bus.get("Longitude")),
        load_code=str(next_bus.get("Load") or "").strip().upper(),
        feature=str(next_bus.get("Feature") or "").strip(),
        bus_type=str(next_bus.get("Type") or "").strip(),
    )


def _optional_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result == 0.0:
        return None
    return result


SPEED_BAND_COLOR = {
    1: "#8b0000",
    2: "#c62828",
    3: "#ef5350",
    4: "#fb8c00",
    5: "#fdd835",
    6: "#9ccc65",
    7: "#43a047",
    8: "#1b5e20",
}


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_traffic_speed_band(
    item: dict[str, Any],
    query_time: datetime,
) -> LtaTrafficSpeedBand | None:
    speed_band = _optional_int(item.get("SpeedBand"))
    start_lon = _optional_float(item.get("StartLon"))
    start_lat = _optional_float(item.get("StartLat"))
    end_lon = _optional_float(item.get("EndLon"))
    end_lat = _optional_float(item.get("EndLat"))
    if (
        speed_band is None
        or start_lon is None
        or start_lat is None
        or end_lon is None
        or end_lat is None
    ):
        return None
    congestion_score = round(min(1.0, max(0.0, (8 - speed_band) / 7)), 4)
    return LtaTrafficSpeedBand(
        query_time=query_time,
        link_id=_optional_int(item.get("LinkID")),
        road_name=_optional_str(item.get("RoadName")),
        road_category=_optional_str(item.get("RoadCategory")),
        speed_band=speed_band,
        minimum_speed_kmh=_optional_float(item.get("MinimumSpeed")),
        maximum_speed_kmh=_optional_float(item.get("MaximumSpeed")),
        congestion_score=congestion_score,
        heat_color=SPEED_BAND_COLOR.get(speed_band),
        start_lon=start_lon,
        start_lat=start_lat,
        end_lon=end_lon,
        end_lat=end_lat,
        line_coordinates=[[start_lon, start_lat], [end_lon, end_lat]],
    )


def _optional_str(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _safe_error(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return "请求失败"
    if isinstance(body, dict):
        for key in ("message", "Message", "error"):
            value = body.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()[:200]
    return "请求失败"
