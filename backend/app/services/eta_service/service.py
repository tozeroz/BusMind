from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.core.intelligence_exceptions import BusinessError
from app.core.intelligence_settings import settings
from app.core.time_utils import ensure_local_datetime
from app.schemas.eta import EtaResult
from app.services.intelligence_gateway import IntelligenceDataGateway
from app.services.model_adapter import OptionalPredictor
from app.services.simulation_service.store import (
    SimulationStateStore,
    simulation_state_store,
)


class EtaService:
    def __init__(
        self,
        gateway: IntelligenceDataGateway,
        predictor: OptionalPredictor | None = None,
        state_store: SimulationStateStore | None = None,
    ) -> None:
        self.gateway = gateway
        self.predictor = predictor or OptionalPredictor(settings.eta_predictor_path)
        self.state_store = state_store or simulation_state_store

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

        override = self.state_store.get_eta(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            line_id=line_id or vehicle.line_id,
        )
        if override is not None:
            eta_minutes = round(
                max(0.0, min(float(override.payload["predicted_eta_minutes"]), 240.0)),
                1,
            )
            arrival_time = override.payload.get("arrival_time")
            if not isinstance(arrival_time, datetime):
                arrival_time = moment + timedelta(minutes=eta_minutes)
            metadata = override.payload.get("metadata") or {}
            return EtaResult(
                vehicle_id=vehicle_id,
                target_station_id=target_station_id,
                predicted_eta_minutes=eta_minutes,
                arrival_time=arrival_time,
                factors={
                    "source": override.source,
                    "distance_meters": metadata.get("distance_meters"),
                    "speed_kph": metadata.get("speed_kph"),
                    "confidence": override.payload.get("confidence"),
                    "remaining_stop_count": metadata.get("remaining_stop_count"),
                    "metadata": metadata,
                    "expires_at": override.expires_at.isoformat(),
                },
                model_version=str(
                    override.payload.get("model_version", "simulation_eta_override")
                ),
            )

        latest_eta = await self.gateway.get_latest_eta_status(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            line_id=line_id or vehicle.line_id,
        )
        if latest_eta is not None:
            eta_minutes = round(max(0.0, min(float(latest_eta.eta_minutes), 240.0)), 1)
            return EtaResult(
                vehicle_id=vehicle_id,
                target_station_id=target_station_id,
                predicted_eta_minutes=eta_minutes,
                arrival_time=latest_eta.arrival_time,
                factors={
                    "source": latest_eta.source,
                    "query_time": latest_eta.query_time.isoformat(),
                    "distance_meters": latest_eta.vehicle_to_stop_distance_m,
                    "speed_kph": latest_eta.speed_kph,
                    "confidence": latest_eta.confidence,
                },
                model_version="eta_mysql_realtime_v1",
            )


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
                "source": "rule_fallback",
                "distance_meters": round(distance_meters, 1),
                "remaining_stop_count": stop_count,
                "speed_kph": round(effective_speed_kph, 1),
                "is_peak": is_peak,
                "time_factor": time_factor,
                "day_type": features["day_type"],
                "confidence": None,
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

