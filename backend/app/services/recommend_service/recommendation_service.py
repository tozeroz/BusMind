from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from app.cache import memory_cache_provider
from app.cache.cache_keys import recommend_route
from app.core.intelligence_exceptions import BusinessError
from app.core.time_utils import ensure_local_datetime, now_local
from app.schemas.common import RouteSegment, StationSummary
from app.schemas.passenger_load import PassengerLoadPredictionRequest
from app.schemas.recommendation import (
    PredictedLoadSummary,
    Preference,
    RecommendRoutesRequest,
    RecommendRoutesResult,
    RecommendType,
    RouteRecommendation,
)
from app.schemas.travel_experience import ExperienceWeights, TravelExperienceRequest
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import CandidateRouteData, IntelligenceDataGateway
from app.services.load_service import PassengerLoadService
from app.services.recommend_service.experience_service import TravelExperienceService


logger = logging.getLogger(__name__)
MODEL_SCORE_LIMIT = 6
RECOMMENDATION_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True, slots=True)
class BuiltRoute:
    item: RouteRecommendation
    model_payload: dict[str, Any]
    line_names: list[str]
    avg_service_frequency: float | None
    station_flow_level: str | None
    congestion_score: float | None
    reliability_score: float | None


class RecommendationService:
    def __init__(
        self,
        gateway: IntelligenceDataGateway,
        eta_service: EtaService,
        load_service: PassengerLoadService,
        experience_service: TravelExperienceService,
    ) -> None:
        self.gateway = gateway
        self.eta_service = eta_service
        self.load_service = load_service
        self.experience_service = experience_service

    async def recommend(
        self, request: RecommendRoutesRequest
    ) -> RecommendRoutesResult:
        trace_id = f"recommend:{now_local().timestamp():.6f}"
        total_started = perf_counter()
        depart_time = ensure_local_datetime(request.depart_time)
        started = perf_counter()
        start_station_id, end_station_id = await self._resolve_station_ids(request)
        logger.info(
            "recommend station_resolve trace_id=%s elapsed_ms=%.1f",
            trace_id,
            (perf_counter() - started) * 1000,
        )
        if start_station_id == end_station_id:
            raise BusinessError(40003, "start and end station must be different", 400)

        max_transfer = request.max_transfer_count if request.allow_transfer else 0
        cache_key = recommend_route(
            start_station_id,
            end_station_id,
            request.preference.value,
            depart_time,
            request.allow_transfer,
            max_transfer,
        )
        cache_key = f"{cache_key}:{id(type(self)._predict_with_route_model)}"
        if request.max_walk_minutes is None:
            cached = memory_cache_provider.get(cache_key)
            if isinstance(cached, RecommendRoutesResult):
                logger.info(
                    "recommend cache_hit trace_id=%s elapsed_ms=%.1f",
                    trace_id,
                    (perf_counter() - total_started) * 1000,
                )
                return cached

        started = perf_counter()
        candidates = await self.gateway.get_candidate_routes(
            start_station_id,
            end_station_id,
            max_transfer,
        )
        candidates = candidates[:MODEL_SCORE_LIMIT]
        logger.info(
            "recommend candidates trace_id=%s count=%s elapsed_ms=%.1f",
            trace_id,
            len(candidates),
            (perf_counter() - started) * 1000,
        )
        if request.max_walk_minutes is not None:
            candidates = [
                item for item in candidates if item.walk_time_minutes <= request.max_walk_minutes
            ]
        if not candidates:
            raise BusinessError(40400, "no route recommendation found", 404)

        weights = self._weights_for_preference(request.preference)
        started = perf_counter()
        built_routes = [
            await self._build_route(item, depart_time, weights) for item in candidates
        ]
        logger.info(
            "recommend build_routes trace_id=%s count=%s elapsed_ms=%.1f",
            trace_id,
            len(built_routes),
            (perf_counter() - started) * 1000,
        )
        started = perf_counter()
        built_routes, model_scores = await self._apply_model_scores(
            built_routes,
            request.preference,
            start_station_id,
            end_station_id,
        )
        logger.info(
            "recommend model_score trace_id=%s scored=%s elapsed_ms=%.1f",
            trace_id,
            len(model_scores),
            (perf_counter() - started) * 1000,
        )
        items = [route.item for route in built_routes]
        selections = self._select_route_ids(items, model_scores)

        tags: dict[str, set[RecommendType]] = {item.route_id: set() for item in items}
        tags[selections["best_experience"]].add(RecommendType.BEST_EXPERIENCE)
        tags[selections["fastest"]].add(RecommendType.FASTEST)
        tags[selections["least_crowded"]].add(RecommendType.LEAST_CROWDED)
        tags[selections["least_walking"]].add(RecommendType.LEAST_WALKING)
        tags[selections["least_transfer"]].add(RecommendType.LEAST_TRANSFER)

        tagged_items = [
            item.model_copy(update={"recommend_types": sorted(tags[item.route_id], key=str)})
            for item in items
        ]
        ordered_items = self._sort_by_preference(
            tagged_items,
            request.preference,
            model_scores,
        )

        result = RecommendRoutesResult(
            items=ordered_items,
            best_experience_route_id=selections["best_experience"],
            fastest_route_id=selections["fastest"],
            least_crowded_route_id=selections["least_crowded"],
            least_walking_route_id=selections["least_walking"],
            least_transfer_route_id=selections["least_transfer"],
            preference=request.preference,
            generated_at=now_local(),
        )
        if request.max_walk_minutes is None:
            memory_cache_provider.set(
                cache_key,
                result,
                ttl_seconds=RECOMMENDATION_CACHE_TTL_SECONDS,
            )
        logger.info(
            "recommend total trace_id=%s count=%s elapsed_ms=%.1f",
            trace_id,
            len(result.items),
            (perf_counter() - total_started) * 1000,
        )
        return result

    async def _resolve_station_ids(
        self, request: RecommendRoutesRequest
    ) -> tuple[int, int]:
        if request.start_station_id is not None and request.end_station_id is not None:
            await self.gateway.get_station(request.start_station_id)
            await self.gateway.get_station(request.end_station_id)
            return request.start_station_id, request.end_station_id

        assert request.origin_longitude is not None and request.origin_latitude is not None
        assert request.destination_longitude is not None and request.destination_latitude is not None

        start = await self.gateway.find_nearest_station(
            request.origin_longitude,
            request.origin_latitude,
        )
        end = await self.gateway.find_nearest_station(
            request.destination_longitude,
            request.destination_latitude,
        )
        return start.station_id, end.station_id

    async def _build_route(
        self,
        candidate: CandidateRouteData,
        depart_time,
        weights: ExperienceWeights | None,
    ) -> BuiltRoute:
        boarding = await self.gateway.get_station(candidate.boarding_station_id)
        alighting = await self.gateway.get_station(candidate.alighting_station_id)
        first_line_id = candidate.line_ids[0]

        eta = await self.eta_service.calculate_eta(
            candidate.vehicle_id,
            candidate.boarding_station_id,
            first_line_id,
            depart_time,
        )
        load = await self.load_service.predict(
            PassengerLoadPredictionRequest(
                line_id=first_line_id,
                station_id=candidate.boarding_station_id,
                vehicle_id=candidate.vehicle_id,
                target_time=depart_time,
            )
        )

        avg_service_frequency = await self._get_route_frequency(candidate)
        station_flow_level = await self.gateway.get_station_flow_level(
            candidate.boarding_station_id,
            depart_time.hour,
        )
        station_flow_mean = await self.gateway.get_station_flow_average(
            candidate.boarding_station_id,
            depart_time.hour,
        )
        congestion_score = await self._get_route_congestion(candidate)
        reliability_score = self._derive_reliability_score(eta, load)

        experience = self.experience_service.evaluate(
            TravelExperienceRequest(
                eta_minutes=eta.predicted_eta_minutes,
                predicted_load_rate=load.predicted_load_rate,
                predicted_load_level=load.predicted_load_level,
                transfer_count=candidate.transfer_count,
                walk_time_minutes=candidate.walk_time_minutes,
                avg_service_frequency=avg_service_frequency,
                station_flow_level=station_flow_level,
                station_flow_mean=station_flow_mean,
                congestion_score=congestion_score,
                reliability_score=reliability_score,
                weights=weights,
            )
        )

        line_names = [segment.line_name for segment in candidate.segments]
        total_time = round(
            candidate.walk_time_minutes + eta.predicted_eta_minutes + candidate.ride_time_minutes,
            1,
        )

        route_item = RouteRecommendation(
            route_id=candidate.route_id,
            line_ids=list(candidate.line_ids),
            segments=[
                RouteSegment(
                    segment_order=segment.segment_order,
                    line_id=segment.line_id,
                    line_name=segment.line_name,
                    boarding_station_id=segment.boarding_station_id,
                    alighting_station_id=segment.alighting_station_id,
                    ride_time_minutes=segment.ride_time_minutes,
                )
                for segment in candidate.segments
            ],
            boarding_station=StationSummary(
                station_id=boarding.station_id,
                station_name=boarding.station_name,
                longitude=boarding.longitude,
                latitude=boarding.latitude,
            ),
            alighting_station=StationSummary(
                station_id=alighting.station_id,
                station_name=alighting.station_name,
                longitude=alighting.longitude,
                latitude=alighting.latitude,
            ),
            predicted_eta_minutes=eta.predicted_eta_minutes,
            predicted_load=PredictedLoadSummary(
                predicted_load_rate=load.predicted_load_rate,
                predicted_load_level=load.predicted_load_level,
                predicted_onboard_count=load.predicted_onboard_count,
                capacity=load.capacity,
                confidence=load.confidence,
                load_score=load.load_score,
            ),
            walk_time_minutes=candidate.walk_time_minutes,
            ride_time_minutes=candidate.ride_time_minutes,
            total_time_minutes=total_time,
            transfer_count=candidate.transfer_count,
            experience_score=experience.experience_score,
            recommend_types=[],
            reason=self._build_route_reason(
                line_names=line_names,
                eta_minutes=eta.predicted_eta_minutes,
                load_level=load.predicted_load_level.value,
                walk_time_minutes=candidate.walk_time_minutes,
                transfer_count=candidate.transfer_count,
                experience_score=experience.experience_score,
                avg_service_frequency=avg_service_frequency,
                station_flow_level=station_flow_level,
                congestion_score=congestion_score,
                reliability_score=reliability_score,
            ),
        )

        return BuiltRoute(
            item=route_item,
            model_payload=self._build_model_route_payload(
                candidate=candidate,
                item=route_item,
                eta=eta,
                load=load,
                avg_service_frequency=avg_service_frequency,
                station_flow_level=station_flow_level,
                congestion_score=congestion_score,
            ),
            line_names=line_names,
            avg_service_frequency=avg_service_frequency,
            station_flow_level=station_flow_level,
            congestion_score=congestion_score,
            reliability_score=reliability_score,
        )

    async def _apply_model_scores(
        self,
        built_routes: list[BuiltRoute],
        preference: Preference,
        start_station_id: int,
        end_station_id: int,
    ) -> tuple[list[BuiltRoute], dict[str, dict[str, float]]]:
        """调用推荐模型给候选路线打分；失败时保留旧规则分数作为兜底。"""

        scoreable_routes = built_routes[:MODEL_SCORE_LIMIT]
        if not scoreable_routes:
            return built_routes, {}

        payload = {
            "contract_version": "1.0.0",
            "request_id": f"recommend:{start_station_id}:{end_station_id}:{now_local().isoformat()}",
            "preference": self._model_preference(preference),
            "routes": [route.model_payload for route in scoreable_routes],
        }
        try:
            model_result = await asyncio.to_thread(self._predict_with_route_model, payload)
        except Exception:
            return built_routes, {}

        model_scores: dict[str, dict[str, float]] = {}
        for raw_score in model_result.get("results", []):
            route_id = str(raw_score.get("route_id") or "")
            if not route_id:
                continue
            model_scores[route_id] = {
                "time_score": float(raw_score.get("time_score", 0.0)),
                "comfort_score": float(raw_score.get("comfort_score", 0.0)),
                "walk_score": float(raw_score.get("walk_score", 0.0)),
                "transfer_score": float(raw_score.get("transfer_score", 0.0)),
                "reliability_score": float(raw_score.get("reliability_score", 0.0)),
                "recommend_score": float(raw_score.get("recommend_score", 0.0)),
            }

        if not model_scores:
            return built_routes, {}

        updated_routes: list[BuiltRoute] = []
        for route in built_routes:
            score = model_scores.get(route.item.route_id)
            if not score:
                updated_routes.append(route)
                continue
            recommend_score = round(score["recommend_score"], 1)
            item = route.item.model_copy(
                update={
                    "experience_score": recommend_score,
                    "reason": self._build_route_reason(
                        line_names=route.line_names,
                        eta_minutes=route.item.predicted_eta_minutes,
                        load_level=route.item.predicted_load.predicted_load_level.value,
                        walk_time_minutes=route.item.walk_time_minutes,
                        transfer_count=route.item.transfer_count,
                        experience_score=recommend_score,
                        avg_service_frequency=route.avg_service_frequency,
                        station_flow_level=route.station_flow_level,
                        congestion_score=route.congestion_score,
                        reliability_score=route.reliability_score,
                    ),
                }
            )
            updated_routes.append(
                BuiltRoute(
                    item=item,
                    model_payload=route.model_payload,
                    line_names=route.line_names,
                    avg_service_frequency=route.avg_service_frequency,
                    station_flow_level=route.station_flow_level,
                    congestion_score=route.congestion_score,
                    reliability_score=route.reliability_score,
                )
            )

        return updated_routes, model_scores

    @staticmethod
    def _predict_with_route_model(payload: dict[str, Any]) -> dict[str, Any]:
        """从项目根目录加载推荐模型，兼容 backend 目录下启动 Uvicorn 的场景。"""

        project_root = Path(__file__).resolve().parents[4]
        project_root_text = str(project_root)
        if project_root_text not in sys.path:
            sys.path.insert(0, project_root_text)

        from algorithm.model.predictor import predict_recommendation

        return predict_recommendation(payload)

    @staticmethod
    def _build_model_route_payload(
        *,
        candidate: CandidateRouteData,
        item: RouteRecommendation,
        eta,
        load,
        avg_service_frequency: float | None,
        station_flow_level: str | None,
        congestion_score: float | None,
    ) -> dict[str, Any]:
        degraded_fields: list[str] = ["walk_distance_meters"]
        if avg_service_frequency is None:
            degraded_fields.append("avg_service_frequency_minutes")
        if station_flow_level is None:
            degraded_fields.append("station_flow_level")
        if congestion_score is None:
            degraded_fields.append("route_speed_band")
        if "rule" in str(eta.model_version).lower():
            degraded_fields.append("eta_minutes")
        if "rule" in str(load.model_version).lower():
            degraded_fields.append("load_code")

        load_source = RecommendationService._source_from_version(str(load.model_version))
        eta_source = RecommendationService._source_from_version(str(eta.model_version))
        congestion_source = "cache" if congestion_score is not None else "default"

        return {
            "route_id": item.route_id,
            "service_nos": [str(line_id) for line_id in item.line_ids],
            "eta_minutes": item.predicted_eta_minutes,
            "ride_time_minutes": item.ride_time_minutes,
            "walk_time_minutes": item.walk_time_minutes,
            # 后端暂未给步行距离，模型侧 v1 先按 1.2m/s 由步行时间估算，并标记降级字段。
            "walk_distance_meters": round(item.walk_time_minutes * 60.0 * 1.2, 1),
            "transfer_count": item.transfer_count,
            "avg_service_frequency_minutes": avg_service_frequency or 12.0,
            "load_code": RecommendationService._load_code_from_level(
                item.predicted_load.predicted_load_level.value
            ),
            "station_flow_level": station_flow_level or "medium",
            "route_speed_band": RecommendationService._speed_band_from_congestion(
                congestion_score
            ),
            "source_updated_at": now_local().isoformat(),
            "monitored": 1 if eta_source in {"lta_realtime", "cache", "database"} else 0,
            "degraded_fields": degraded_fields,
            "feature_sources": {
                "eta_minutes": eta_source,
                "ride_time_minutes": "database",
                "walk_time_minutes": "database",
                "walk_distance_meters": "rule_estimate",
                "transfer_count": "database",
                "avg_service_frequency_minutes": "database"
                if avg_service_frequency is not None
                else "default",
                "load_code": load_source,
                "station_flow_level": "historical"
                if station_flow_level is not None
                else "default",
                "route_speed_band": congestion_source,
                "source_updated_at": "cache",
                "monitored": eta_source,
                "degraded_fields": "rule_estimate",
            },
        }

    @staticmethod
    def _model_preference(preference: Preference) -> str:
        if preference == Preference.LOW_LOAD:
            return "comfort"
        return preference.value

    @staticmethod
    def _load_code_from_level(load_level: str) -> str:
        mapping = {
            "seats_available": "SEA",
            "standing_available": "SDA",
            "limited_standing": "LSD",
            "overcrowded": "LSD",
        }
        return mapping.get(str(load_level).lower(), "UNKNOWN")

    @staticmethod
    def _speed_band_from_congestion(congestion_score: float | None) -> int:
        if congestion_score is None:
            return 5
        value = max(0.0, float(congestion_score))
        pressure = min(value, 1.0) if value <= 1.0 else min(value / 100.0, 1.0)
        smoothness_score = 100.0 - pressure * 70.0
        return max(1, min(8, int(round((smoothness_score - 30.0) / 10.0 + 1.0))))

    @staticmethod
    def _source_from_version(model_version: str) -> str:
        text = model_version.lower()
        if "mysql_realtime" in text or "lta" in text:
            return "lta_realtime"
        if "cache" in text:
            return "cache"
        if "rule" in text:
            return "rule_estimate"
        return "model"

    @staticmethod
    def _select_route_ids(
        items: list[RouteRecommendation],
        model_scores: dict[str, dict[str, float]] | None = None,
    ) -> dict[str, str]:
        model_scores = model_scores or {}
        best = max(
            items,
            key=lambda item: (
                model_scores.get(item.route_id, {}).get("recommend_score", item.experience_score),
                -item.total_time_minutes,
            ),
        )
        fastest = max(
            items,
            key=lambda item: (
                model_scores.get(item.route_id, {}).get("time_score", -item.total_time_minutes),
                -item.total_time_minutes,
            ),
        )
        least_crowded = max(
            items,
            key=lambda item: (
                model_scores.get(item.route_id, {}).get("comfort_score", item.predicted_load.load_score),
                -item.total_time_minutes,
            ),
        )
        least_walking = max(
            items,
            key=lambda item: (
                model_scores.get(item.route_id, {}).get("walk_score", -item.walk_time_minutes),
                -item.walk_time_minutes,
            ),
        )
        least_transfer = max(
            items,
            key=lambda item: (
                model_scores.get(item.route_id, {}).get("transfer_score", -item.transfer_count),
                -item.transfer_count,
            ),
        )
        return {
            "best_experience": best.route_id,
            "fastest": fastest.route_id,
            "least_crowded": least_crowded.route_id,
            "least_walking": least_walking.route_id,
            "least_transfer": least_transfer.route_id,
        }

    @staticmethod
    def _build_route_reason(
        *,
        line_names: list[str],
        eta_minutes: float | None,
        load_level: str,
        walk_time_minutes: float,
        transfer_count: int,
        experience_score: float,
        avg_service_frequency: float | None,
        station_flow_level: str | None,
        congestion_score: float | None,
        reliability_score: float | None,
    ) -> str:
        line_text = " -> ".join(line_names) if line_names else "候选线路"
        parts = [
            f"推荐线路 {line_text}",
            "预计等待未知" if eta_minutes is None else f"预计等待约 {eta_minutes:.1f} 分钟",
            f"客载状态为 {load_level}",
            f"步行约 {walk_time_minutes:.1f} 分钟",
            "无需换乘" if transfer_count == 0 else f"需要换乘 {transfer_count} 次",
        ]
        if avg_service_frequency is not None:
            parts.append(f"平均发车间隔约 {avg_service_frequency:.1f} 分钟")
        if station_flow_level:
            parts.append(f"历史客流等级为 {station_flow_level}")
        if congestion_score is not None:
            parts.append("已结合道路拥堵特征")
        if reliability_score is not None:
            parts.append(f"可靠性约 {reliability_score:.1f} 分")
        parts.append(f"综合体验分 {experience_score:.1f}")
        return "；".join(parts) + "。"

    async def _get_route_frequency(self, candidate: CandidateRouteData) -> float | None:
        values: list[float] = []
        for line_id in candidate.line_ids:
            value = await self.gateway.get_line_frequency_minutes(line_id)
            if value is not None and value > 0:
                values.append(value)
        if not values:
            return None
        return round(sum(values) / len(values), 2)

    async def _get_route_congestion(self, candidate: CandidateRouteData) -> float | None:
        weighted_total = 0.0
        total_weight = 0.0
        for segment in candidate.segments:
            value = await self.gateway.get_route_congestion_score(
                segment.line_id,
                segment.boarding_station_id,
                segment.alighting_station_id,
            )
            if value is None:
                continue
            weight = max(float(segment.ride_time_minutes), 1.0)
            weighted_total += value * weight
            total_weight += weight
        if total_weight <= 0:
            return None
        return round(weighted_total / total_weight, 4)

    @staticmethod
    def _derive_reliability_score(eta, load) -> float:
        eta_conf = RecommendationService._resolve_eta_confidence(eta)
        load_conf = RecommendationService._resolve_load_confidence(load)
        return round(((eta_conf + load_conf) / 2.0) * 100.0, 1)

    @staticmethod
    def _resolve_eta_confidence(eta) -> float:
        raw = eta.factors.get("confidence")
        if isinstance(raw, (int, float)):
            return max(0.0, min(float(raw), 1.0))
        source = str(eta.factors.get("source", "")).lower()
        model_version = str(eta.model_version).lower()
        if "mysql_realtime" in model_version or "lta" in source:
            return 0.88
        if "cache" in source:
            return 0.80
        if "rule" in model_version:
            return 0.64
        return 0.72

    @staticmethod
    def _resolve_load_confidence(load) -> float:
        if load.confidence is not None:
            return max(0.0, min(float(load.confidence), 1.0))
        model_version = str(load.model_version).lower()
        if "mysql_realtime" in model_version:
            return 0.84
        if "rule" in model_version:
            return 0.66
        return 0.74

    @staticmethod
    def _weights_for_preference(preference: Preference) -> ExperienceWeights | None:
        if preference == Preference.FASTEST:
            return ExperienceWeights(
                w_eta=0.32,
                w_load=0.12,
                w_walk=0.12,
                w_transfer=0.10,
                w_frequency=0.14,
                w_flow=0.06,
                w_congestion=0.06,
                w_reliability=0.08,
            )
        if preference in (Preference.COMFORT, Preference.LOW_LOAD):
            return ExperienceWeights(
                w_eta=0.12,
                w_load=0.28,
                w_walk=0.08,
                w_transfer=0.08,
                w_frequency=0.10,
                w_flow=0.16,
                w_congestion=0.10,
                w_reliability=0.08,
            )
        if preference == Preference.LESS_WALKING:
            return ExperienceWeights(
                w_eta=0.16,
                w_load=0.16,
                w_walk=0.28,
                w_transfer=0.08,
                w_frequency=0.10,
                w_flow=0.08,
                w_congestion=0.06,
                w_reliability=0.08,
            )
        if preference == Preference.LESS_TRANSFER:
            return ExperienceWeights(
                w_eta=0.16,
                w_load=0.14,
                w_walk=0.10,
                w_transfer=0.24,
                w_frequency=0.10,
                w_flow=0.08,
                w_congestion=0.08,
                w_reliability=0.10,
            )
        return None

    @staticmethod
    def _sort_by_preference(
        items: list[RouteRecommendation],
        preference: Preference,
        model_scores: dict[str, dict[str, float]] | None = None,
    ) -> list[RouteRecommendation]:
        model_scores = model_scores or {}
        if preference == Preference.FASTEST:
            return sorted(
                items,
                key=lambda item: (
                    -model_scores.get(item.route_id, {}).get("time_score", -item.total_time_minutes),
                    item.total_time_minutes,
                ),
            )
        if preference in (Preference.COMFORT, Preference.LOW_LOAD):
            return sorted(
                items,
                key=lambda item: (
                    -model_scores.get(item.route_id, {}).get(
                        "comfort_score",
                        item.predicted_load.load_score,
                    ),
                    item.total_time_minutes,
                ),
            )
        if preference == Preference.LESS_WALKING:
            return sorted(
                items,
                key=lambda item: (
                    -model_scores.get(item.route_id, {}).get("walk_score", -item.walk_time_minutes),
                    item.walk_time_minutes,
                ),
            )
        if preference == Preference.LESS_TRANSFER:
            return sorted(
                items,
                key=lambda item: (
                    -model_scores.get(item.route_id, {}).get(
                        "transfer_score",
                        -item.transfer_count,
                    ),
                    item.transfer_count,
                ),
            )
        return sorted(
            items,
            key=lambda item: (
                -model_scores.get(item.route_id, {}).get("recommend_score", item.experience_score),
                item.total_time_minutes,
            ),
        )
