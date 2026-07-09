from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.intelligence_exceptions import (
    BusinessError,
    ModelUnavailableError,
)
from backend.app.core.time_utils import ensure_local_datetime, now_local
from backend.app.schemas.passenger_load import LoadLevel
from backend.app.schemas.simulation import (
    LtaBusArrivalRefreshRequest,
    LtaBusArrivalRefreshResult,
    PredictionResultUpdateRequest,
    PredictionResultUpdateResult,
    PredictionType,
    VehicleRunStatus,
    VehicleStatusUpdateRequest,
    VehicleStatusUpdateResult,
)
from backend.app.services.intelligence_gateway import IntelligenceDataGateway, VehicleData
from backend.app.services.lta_service import LtaDataMallClient, LtaDataMallError
from backend.app.services.simulation_service.store import SimulationStateStore


_LTA_LOAD_MAP: dict[str, tuple[LoadLevel, float]] = {
    "SEA": (LoadLevel.SEATS_AVAILABLE, 0.45),
    "SDA": (LoadLevel.STANDING_AVAILABLE, 0.72),
    "LSD": (LoadLevel.LIMITED_STANDING, 0.92),
}


class SimulationService:
    def __init__(
        self,
        gateway: IntelligenceDataGateway,
        store: SimulationStateStore,
        lta_client: LtaDataMallClient | None = None,
    ) -> None:
        self.gateway = gateway
        self.store = store
        self.lta_client = lta_client

    async def update_vehicle_status(
        self,
        vehicle_id: int,
        request: VehicleStatusUpdateRequest,
    ) -> VehicleStatusUpdateResult:
        current = await self.gateway.get_vehicle(vehicle_id)
        changes = request.model_dump(exclude_none=True)
        if request.current_station_id is not None:
            await self.gateway.get_station(request.current_station_id)
        if request.next_station_id is not None:
            await self.gateway.get_station(request.next_station_id)

        effective_capacity = request.capacity or current.capacity
        effective_onboard = (
            request.onboard_count
            if request.onboard_count is not None
            else current.onboard_count
        )
        if effective_onboard > effective_capacity * 2:
            raise BusinessError(
                40002,
                "更新后的 onboard_count 不应超过 capacity 的 2 倍",
                400,
            )

        updater = getattr(self.gateway, "update_vehicle_status", None)
        if not callable(updater):
            raise ModelUnavailableError(
                50311,
                "当前数据网关不支持写入车辆状态；请由服务端 A 的 Repository 适配器实现 update_vehicle_status",
            )
        updated: VehicleData = await updater(vehicle_id, **changes)
        return self._vehicle_result(updated, source="simulation")

    def update_prediction_result(
        self,
        request: PredictionResultUpdateRequest,
    ) -> PredictionResultUpdateResult:
        payload: dict[str, Any]
        if request.prediction_type == PredictionType.ETA:
            assert request.vehicle_id is not None
            assert request.line_id is not None
            assert request.target_station_id is not None
            eta_minutes = self._resolve_eta_minutes(
                request.predicted_eta_minutes,
                request.arrival_time,
            )
            arrival_time = request.arrival_time
            if arrival_time is not None:
                arrival_time = ensure_local_datetime(arrival_time)
            prediction_time = ensure_local_datetime(request.prediction_time)
            payload = {
                "prediction_time": prediction_time,
                "predicted_eta_minutes": eta_minutes,
                "arrival_time": arrival_time,
                "confidence": request.confidence,
                "model_version": request.model_version,
                "metadata": request.metadata,
            }
            record = self.store.set_eta(
                vehicle_id=request.vehicle_id,
                target_station_id=request.target_station_id,
                line_id=request.line_id,
                payload=payload,
                source=request.source,
                expires_in_seconds=request.expires_in_seconds,
            )
            storage_key = (
                f"eta:{request.vehicle_id}:{request.target_station_id}:"
                f"{request.line_id}"
            )
        else:
            assert request.vehicle_id is not None
            assert request.line_id is not None
            level = request.predicted_load_level
            rate = request.predicted_load_rate
            if level is None and rate is not None:
                level = _level_from_rate(rate)
            if rate is None and level is not None:
                rate = _default_rate_for_level(level)
            assert level is not None and rate is not None
            prediction_time = ensure_local_datetime(request.prediction_time)
            capacity = request.capacity
            count = request.predicted_onboard_count
            if count is None and capacity is not None:
                count = int(round(capacity * rate))
            load_score = request.load_score
            if load_score is None:
                load_score = _load_score_from_rate(rate)
            payload = {
                "prediction_time": prediction_time,
                "predicted_load_rate": round(rate, 4),
                "predicted_load_level": level.value,
                "predicted_onboard_count": count,
                "onboard_count": count,
                "capacity": capacity,
                "load_score": load_score,
                "confidence": request.confidence,
                "model_version": request.model_version,
                "metadata": request.metadata,
            }
            record = self.store.set_load(
                line_id=request.line_id,
                station_id=request.station_id,
                vehicle_id=request.vehicle_id,
                payload=payload,
                source=request.source,
                expires_in_seconds=request.expires_in_seconds,
            )
            storage_key = (
                f"passenger_load:{request.line_id}:"
                f"{request.station_id if request.station_id is not None else '*'}:"
                f"{request.vehicle_id}"
            )

        return PredictionResultUpdateResult(
            prediction_type=request.prediction_type,
            storage_key=storage_key,
            source=record.source,
            model_version=request.model_version,
            payload=_json_safe_payload(record.payload),
            updated_at=record.updated_at,
            expires_at=record.expires_at,
        )

    async def refresh_from_lta(
        self,
        request: LtaBusArrivalRefreshRequest,
    ) -> LtaBusArrivalRefreshResult:
        if self.lta_client is None:
            raise ModelUnavailableError(
                50320,
                "未配置 LTA_ACCOUNT_KEY，无法调用 LTA Bus Arrival API",
            )
        await self.gateway.get_vehicle(request.vehicle_id)
        await self.gateway.get_station(request.station_id)
        try:
            arrivals = await self.lta_client.get_bus_arrivals(
                request.bus_stop_code,
                request.service_no,
            )
        except LtaDataMallError as exc:
            raise ModelUnavailableError(50321, str(exc)) from exc
        if not arrivals:
            raise BusinessError(
                40410,
                "LTA 当前未返回该站点和线路的到站数据",
                404,
            )
        arrival = arrivals[0]
        level, rate = _LTA_LOAD_MAP.get(
            arrival.load_code,
            (LoadLevel.STANDING_AVAILABLE, 0.72),
        )
        onboard_count = int(round(request.capacity * rate))
        eta_record = self.store.set_eta(
            vehicle_id=request.vehicle_id,
            target_station_id=request.station_id,
            line_id=request.line_id,
            payload={
                "predicted_eta_minutes": arrival.eta_minutes,
                "arrival_time": arrival.estimated_arrival,
                "confidence": 0.95 if arrival.monitored else 0.78,
                "model_version": "lta_bus_arrival_v3",
                "metadata": {
                    "bus_stop_code": arrival.bus_stop_code,
                    "service_no": arrival.service_no,
                    "operator": arrival.operator,
                    "monitored": arrival.monitored,
                },
            },
            source="lta_bus_arrival",
            expires_in_seconds=request.expires_in_seconds,
        )
        self.store.set_load(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
            payload={
                "predicted_load_rate": rate,
                "predicted_load_level": level.value,
                "predicted_onboard_count": onboard_count,
                "capacity": request.capacity,
                "confidence": 0.92,
                "model_version": "lta_bus_arrival_v3",
                "metadata": {
                    "lta_load_code": arrival.load_code,
                    "bus_stop_code": arrival.bus_stop_code,
                    "service_no": arrival.service_no,
                },
            },
            source="lta_bus_arrival",
            expires_in_seconds=request.expires_in_seconds,
        )

        vehicle_changes: dict[str, Any] = {
            "onboard_count": onboard_count,
            "capacity": request.capacity,
            "status": "normal",
        }
        if arrival.longitude is not None:
            vehicle_changes["longitude"] = arrival.longitude
        if arrival.latitude is not None:
            vehicle_changes["latitude"] = arrival.latitude
        updater = getattr(self.gateway, "update_vehicle_status", None)
        if callable(updater):
            await updater(request.vehicle_id, **vehicle_changes)

        return LtaBusArrivalRefreshResult(
            bus_stop_code=arrival.bus_stop_code,
            service_no=arrival.service_no,
            operator=arrival.operator,
            vehicle_id=request.vehicle_id,
            line_id=request.line_id,
            station_id=request.station_id,
            predicted_eta_minutes=arrival.eta_minutes,
            estimated_arrival=arrival.estimated_arrival,
            predicted_load_level=level,
            predicted_load_rate=rate,
            monitored=arrival.monitored,
            latitude=arrival.latitude,
            longitude=arrival.longitude,
            feature=arrival.feature,
            bus_type=arrival.bus_type,
            source="lta_bus_arrival",
            refreshed_at=eta_record.updated_at,
            expires_at=eta_record.expires_at,
        )

    @staticmethod
    def _resolve_eta_minutes(
        predicted_eta_minutes: float | None,
        arrival_time: datetime | None,
    ) -> float:
        if predicted_eta_minutes is not None:
            return round(float(predicted_eta_minutes), 1)
        assert arrival_time is not None
        seconds = (ensure_local_datetime(arrival_time) - now_local()).total_seconds()
        return round(max(0.0, seconds / 60), 1)

    @staticmethod
    def _vehicle_result(
        vehicle: VehicleData,
        *,
        source: str,
    ) -> VehicleStatusUpdateResult:
        try:
            status = VehicleRunStatus(vehicle.status)
        except ValueError:
            status = VehicleRunStatus.NORMAL
        return VehicleStatusUpdateResult(
            vehicle_id=vehicle.vehicle_id,
            line_id=vehicle.line_id,
            longitude=vehicle.longitude,
            latitude=vehicle.latitude,
            current_station_id=vehicle.current_station_id,
            next_station_id=vehicle.next_station_id,
            speed_kph=vehicle.speed_kph,
            onboard_count=vehicle.onboard_count,
            capacity=vehicle.capacity,
            status=status,
            source=source,
            updated_at=now_local(),
        )


def _level_from_rate(rate: float) -> LoadLevel:
    if rate <= 0.60:
        return LoadLevel.SEATS_AVAILABLE
    if rate <= 0.85:
        return LoadLevel.STANDING_AVAILABLE
    if rate <= 1.0:
        return LoadLevel.LIMITED_STANDING
    return LoadLevel.OVERCROWDED


def _default_rate_for_level(level: LoadLevel) -> float:
    return {
        LoadLevel.SEATS_AVAILABLE: 0.45,
        LoadLevel.STANDING_AVAILABLE: 0.72,
        LoadLevel.LIMITED_STANDING: 0.92,
        LoadLevel.OVERCROWDED: 1.10,
    }[level]


def _load_score_from_rate(rate: float) -> float:
    return float(round(max(0.0, min(100.0, 100.0 - min(rate, 2.0) * 55.0))))


def _json_safe_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in payload.items():
        result[key] = value.isoformat() if isinstance(value, datetime) else value
    return result
