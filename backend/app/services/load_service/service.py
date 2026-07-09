from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.app.core.intelligence_exceptions import BusinessError
from backend.app.core.intelligence_settings import settings
from backend.app.core.time_utils import ensure_local_datetime
from backend.app.schemas.passenger_load import (
    LoadLevel,
    PassengerLoadPredictionRequest,
    PassengerLoadPredictionResult,
)
from backend.app.services.intelligence_gateway import IntelligenceDataGateway
from backend.app.services.model_adapter import OptionalPredictor
from backend.app.services.simulation_service.store import (
    SimulationStateStore,
    simulation_state_store,
)


LOAD_LEVEL_SCORE: dict[LoadLevel, float] = {
    LoadLevel.SEATS_AVAILABLE: 100.0,
    LoadLevel.STANDING_AVAILABLE: 70.0,
    LoadLevel.LIMITED_STANDING: 35.0,
}


class PassengerLoadService:
    def __init__(
        self,
        gateway: IntelligenceDataGateway,
        predictor: OptionalPredictor | None = None,
        state_store: SimulationStateStore | None = None,
    ) -> None:
        self.gateway = gateway
        self.predictor = predictor or OptionalPredictor(settings.load_predictor_path)
        self.state_store = state_store or simulation_state_store

    async def predict(
        self, request: PassengerLoadPredictionRequest
    ) -> PassengerLoadPredictionResult:
        moment = ensure_local_datetime(request.target_time)
        await self.gateway.get_station(request.station_id)

        vehicle = None
        if request.vehicle_id is not None:
            vehicle = await self.gateway.get_vehicle(request.vehicle_id)
            if vehicle.line_id != request.line_id:
                raise BusinessError(
                    40002,
                    f"车辆 {request.vehicle_id} 不属于线路 {request.line_id}",
                    400,
                )

        capacity = request.capacity or (vehicle.capacity if vehicle else settings.default_vehicle_capacity)
        if capacity <= 0:
            raise BusinessError(40002, "capacity 必须大于 0", 400)
        current_onboard = (
            request.current_onboard_count
            if request.current_onboard_count is not None
            else (vehicle.onboard_count if vehicle else round(capacity * 0.45))
        )

        override = self.state_store.get_load(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
        )
        if override is not None:
            raw_level = str(override.payload.get("predicted_load_level", ""))
            try:
                load_level = LoadLevel(raw_level)
            except ValueError:
                load_level = self._level_from_rate(
                    float(override.payload.get("predicted_load_rate", 0.72))
                )
            load_rate_raw = override.payload.get("predicted_load_rate")
            load_rate = (
                round(float(load_rate_raw), 2)
                if isinstance(load_rate_raw, (int, float))
                else None
            )
            override_capacity = override.payload.get("capacity")
            if isinstance(override_capacity, int) and override_capacity > 0:
                capacity = override_capacity
            predicted_count = override.payload.get("predicted_onboard_count")
            if not isinstance(predicted_count, int):
                predicted_count = (
                    int(round(capacity * load_rate))
                    if load_rate is not None
                    else None
                )
            confidence_raw = override.payload.get("confidence", 0.9)
            confidence = (
                round(max(0.0, min(float(confidence_raw), 1.0)), 2)
                if isinstance(confidence_raw, (int, float))
                else 0.9
            )
            return PassengerLoadPredictionResult(
                line_id=request.line_id,
                station_id=request.station_id,
                vehicle_id=request.vehicle_id,
                predicted_onboard_count=predicted_count,
                capacity=capacity,
                predicted_load_rate=load_rate,
                predicted_load_level=load_level,
                load_score=self.calculate_load_score(load_rate, load_level),
                confidence=confidence,
                predict_time=moment,
                feature_summary={
                    "source": override.source,
                    "metadata": override.payload.get("metadata", {}),
                    "expires_at": override.expires_at.isoformat(),
                },
                model_version=str(
                    override.payload.get("model_version", "simulation_load_override")
                ),
            )

        is_peak = moment.hour in {7, 8, 9, 17, 18, 19}
        flow_level = await self.gateway.get_station_flow_level(request.station_id, moment.hour)
        weather = (request.weather or "clear").lower()
        features: dict[str, Any] = {
            "line_id": request.line_id,
            "station_id": request.station_id,
            "vehicle_id": request.vehicle_id,
            "hour": moment.hour,
            "day_type": "weekend" if moment.weekday() >= 5 else "weekday",
            "is_peak": is_peak,
            "station_flow_level": flow_level,
            "weather": weather,
            "current_onboard_count": current_onboard,
            "capacity": capacity,
        }

        model_result = await self.predictor.predict(features)
        parsed = self._parse_model_result(model_result, capacity)
        if parsed is None:
            predicted_count, load_rate, load_level, confidence = self._rule_predict(
                current_onboard=current_onboard,
                capacity=capacity,
                is_peak=is_peak,
                flow_level=flow_level,
                weather=weather,
            )
            model_version = "load_rule_v1"
        else:
            predicted_count, load_rate, load_level, confidence, model_version = parsed

        load_score = self.calculate_load_score(load_rate, load_level)
        return PassengerLoadPredictionResult(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
            predicted_onboard_count=predicted_count,
            capacity=capacity,
            predicted_load_rate=load_rate,
            predicted_load_level=load_level,
            load_score=load_score,
            confidence=confidence,
            predict_time=moment,
            feature_summary={
                "is_peak": is_peak,
                "station_flow_level": flow_level,
                "weather": weather,
                "day_type": features["day_type"],
            },
            model_version=model_version,
        )

    @staticmethod
    def calculate_load_score(
        load_rate: float | None,
        load_level: LoadLevel,
    ) -> float:
        # The current interface example maps 0.77 to 58.0.  Rounding the
        # monotonic formula below gives that result while retaining level-only
        # compatibility with LTA SEA/SDA/LSD labels.
        if load_rate is not None:
            return float(round(max(0.0, min(100.0, 100.0 - load_rate * 55.0))))
        return LOAD_LEVEL_SCORE[load_level]

    @staticmethod
    def _level_from_rate(rate: float) -> LoadLevel:
        if rate <= 0.60:
            return LoadLevel.SEATS_AVAILABLE
        if rate <= 0.85:
            return LoadLevel.STANDING_AVAILABLE
        return LoadLevel.LIMITED_STANDING

    def _rule_predict(
        self,
        current_onboard: int,
        capacity: int,
        is_peak: bool,
        flow_level: str,
        weather: str,
    ) -> tuple[int, float, LoadLevel, float]:
        delta = 0
        if is_peak:
            delta += round(capacity * 0.12)
        delta += {"high": round(capacity * 0.10), "medium": round(capacity * 0.04), "low": -2}.get(
            flow_level, 0
        )
        if weather in {"rain", "rainy", "snow", "storm"}:
            delta += round(capacity * 0.05)
        predicted_count = max(0, min(round(capacity * 1.05), current_onboard + delta))
        rate = round(min(predicted_count / capacity, 1.0), 2)
        level = self._level_from_rate(rate)
        confidence = 0.72 if is_peak or flow_level == "high" else 0.66
        return predicted_count, rate, level, confidence

    def _parse_model_result(
        self, result: Any, capacity: int
    ) -> tuple[int | None, float | None, LoadLevel, float, str] | None:
        if not isinstance(result, dict):
            return None
        raw_level = result.get("predicted_load_level", result.get("predicted_load"))
        mapping = {
            "SEA": LoadLevel.SEATS_AVAILABLE,
            "SDA": LoadLevel.STANDING_AVAILABLE,
            "LSD": LoadLevel.LIMITED_STANDING,
            "seats_available": LoadLevel.SEATS_AVAILABLE,
            "standing_available": LoadLevel.STANDING_AVAILABLE,
            "limited_standing": LoadLevel.LIMITED_STANDING,
        }
        level = mapping.get(str(raw_level))
        count = result.get("predicted_onboard_count")
        rate = result.get("predicted_load_rate")
        if isinstance(count, (int, float)):
            count = max(0, int(round(count)))
        else:
            count = None
        if isinstance(rate, (int, float)):
            rate = round(max(0.0, min(float(rate), 1.0)), 2)
        elif count is not None:
            rate = round(min(count / capacity, 1.0), 2)
        else:
            rate = None
        if level is None and rate is not None:
            level = self._level_from_rate(rate)
        if level is None:
            return None
        confidence_raw = result.get("confidence", 0.8)
        confidence = (
            max(0.0, min(float(confidence_raw), 1.0))
            if isinstance(confidence_raw, (int, float))
            else 0.8
        )
        return (
            count,
            rate,
            level,
            round(confidence, 2),
            str(result.get("model_version", result.get("model_name", "load_external_model"))),
        )
