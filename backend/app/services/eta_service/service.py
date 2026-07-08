from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from backend.app.core.intelligence_exceptions import BusinessError
from backend.app.core.intelligence_settings import settings
from backend.app.core.time_utils import ensure_local_datetime
from backend.app.schemas.eta import EtaResult
from backend.app.services.intelligence_gateway import IntelligenceDataGateway
from backend.app.services.model_adapter import OptionalPredictor


class EtaService:
    def __init__(
        self,
        gateway: IntelligenceDataGateway,
        predictor: OptionalPredictor | None = None,
    ) -> None:
        self.gateway = gateway
        self.predictor = predictor or OptionalPredictor(settings.eta_predictor_path)

    async def calculate_eta(
        self,
        vehicle_id: int,
        target_station_id: int,
        line_id: int | None = None,
        query_time: datetime | None = None,
    ) -> EtaResult:
        moment = ensure_local_datetime(query_time)
        vehicle = await self.gateway.get_vehicle(vehicle_id)
        await self.gateway.get_station(target_station_id)

        if line_id is not None and vehicle.line_id != line_id:
            raise BusinessError(
                40002,
                f"车辆 {vehicle_id} 不属于线路 {line_id}",
                400,
            )
        if vehicle.status == "offline":
            raise BusinessError(50301, f"车辆 {vehicle_id} 当前离线，无法计算 ETA", 503)

        distance_meters = await self.gateway.get_distance_to_station_meters(
            vehicle_id, target_station_id
        )
        stop_count = await self.gateway.get_remaining_stop_count(vehicle_id, target_station_id)
        is_peak = moment.hour in {7, 8, 9, 17, 18, 19}
        time_factor = 1.22 if is_peak else 1.0
        effective_speed_kph = max(vehicle.speed_kph, 8.0)

        features: dict[str, Any] = {
            "vehicle_id": vehicle_id,
            "line_id": vehicle.line_id,
            "target_station_id": target_station_id,
            "distance_to_stop": distance_meters,
            "remaining_stop_count": stop_count,
            "speed_kph": effective_speed_kph,
            "hour": moment.hour,
            "day_type": "weekend" if moment.weekday() >= 5 else "weekday",
            "is_peak": is_peak,
        }

        model_result = await self.predictor.predict(features)
        eta_minutes, model_version = self._parse_model_result(model_result)
        if eta_minutes is None:
            travel_minutes = distance_meters / (effective_speed_kph * 1000 / 60)
            stop_delay_minutes = stop_count * 0.45
            eta_minutes = travel_minutes * time_factor + stop_delay_minutes
            model_version = "eta_rule_v1"

        eta_minutes = round(max(0.1, min(float(eta_minutes), 240.0)), 1)
        return EtaResult(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            predicted_eta_minutes=eta_minutes,
            arrival_time=moment + timedelta(minutes=eta_minutes),
            factors={
                "distance_meters": round(distance_meters, 1),
                "remaining_stop_count": stop_count,
                "speed_kph": round(effective_speed_kph, 1),
                "is_peak": is_peak,
                "time_factor": time_factor,
                "day_type": features["day_type"],
            },
            model_version=model_version,
        )

    @staticmethod
    def _parse_model_result(result: Any) -> tuple[float | None, str]:
        if result is None:
            return None, ""
        if isinstance(result, (int, float)):
            return float(result), "eta_external_model"
        if isinstance(result, dict):
            value = result.get("predicted_eta_minutes", result.get("eta_minutes"))
            if isinstance(value, (int, float)):
                return float(value), str(result.get("model_version", "eta_external_model"))
        return None, ""
