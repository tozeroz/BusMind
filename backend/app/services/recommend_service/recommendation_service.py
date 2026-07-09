from __future__ import annotations

from algorithm.recommend import build_route_reason, select_route_ids
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
from app.schemas.travel_experience import TravelExperienceRequest
from app.services.eta_service import EtaService
from app.services.intelligence_gateway import (
    CandidateRouteData,
    IntelligenceDataGateway,
)
from app.services.load_service import PassengerLoadService
from app.services.recommend_service.experience_service import TravelExperienceService


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
        depart_time = ensure_local_datetime(request.depart_time)
        start_station_id, end_station_id = await self._resolve_station_ids(request)
        if start_station_id == end_station_id:
            raise BusinessError(40003, "起点和终点不能相同", 400)

        max_transfer = request.max_transfer_count if request.allow_transfer else 0
        candidates = await self.gateway.get_candidate_routes(
            start_station_id,
            end_station_id,
            max_transfer,
        )
        if request.max_walk_minutes is not None:
            candidates = [
                item
                for item in candidates
                if item.walk_time_minutes <= request.max_walk_minutes
            ]
        if not candidates:
            raise BusinessError(40400, "未找到满足条件的公交方案", 404)

        items = [await self._build_route(item, depart_time) for item in candidates]
        selections = select_route_ids(items)

        tags: dict[str, set[RecommendType]] = {item.route_id: set() for item in items}
        tags[selections["best_experience"]].add(RecommendType.BEST_EXPERIENCE)
        tags[selections["fastest"]].add(RecommendType.FASTEST)
        tags[selections["least_crowded"]].add(RecommendType.LEAST_CROWDED)
        tags[selections["least_walking"]].add(RecommendType.LEAST_WALKING)
        tags[selections["least_transfer"]].add(RecommendType.LEAST_TRANSFER)

        tagged_items = [
            item.model_copy(
                update={"recommend_types": sorted(tags[item.route_id], key=str)}
            )
            for item in items
        ]
        ordered_items = self._sort_by_preference(tagged_items, request.preference)

        return RecommendRoutesResult(
            items=ordered_items,
            best_experience_route_id=selections["best_experience"],
            fastest_route_id=selections["fastest"],
            least_crowded_route_id=selections["least_crowded"],
            least_walking_route_id=selections["least_walking"],
            least_transfer_route_id=selections["least_transfer"],
            preference=request.preference,
            generated_at=now_local(),
        )

    async def _resolve_station_ids(
        self, request: RecommendRoutesRequest
    ) -> tuple[int, int]:
        if request.start_station_id is not None and request.end_station_id is not None:
            await self.gateway.get_station(request.start_station_id)
            await self.gateway.get_station(request.end_station_id)
            return request.start_station_id, request.end_station_id

        assert request.origin_longitude is not None and request.origin_latitude is not None
        assert (
            request.destination_longitude is not None
            and request.destination_latitude is not None
        )

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
        self, candidate: CandidateRouteData, depart_time
    ) -> RouteRecommendation:
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
        experience = self.experience_service.evaluate(
            TravelExperienceRequest(
                predicted_load_rate=load.predicted_load_rate,
                predicted_load_level=load.predicted_load_level,
                transfer_count=candidate.transfer_count,
                walk_time_minutes=candidate.walk_time_minutes,
            )
        )

        line_names = [segment.line_name for segment in candidate.segments]
        total_time = round(
            candidate.walk_time_minutes
            + eta.predicted_eta_minutes
            + candidate.ride_time_minutes,
            1,
        )

        return RouteRecommendation(
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
            reason=build_route_reason(
                line_names=line_names,
                eta_minutes=eta.predicted_eta_minutes,
                load_level=load.predicted_load_level.value,
                walk_time_minutes=candidate.walk_time_minutes,
                transfer_count=candidate.transfer_count,
                experience_score=experience.experience_score,
            ),
        )

    @staticmethod
    def _sort_by_preference(
        items: list[RouteRecommendation], preference: Preference
    ) -> list[RouteRecommendation]:
        if preference == Preference.FASTEST:
            return sorted(
                items,
                key=lambda item: (item.total_time_minutes, -item.experience_score),
            )
        if preference == Preference.LOW_LOAD:
            return sorted(
                items,
                key=lambda item: (
                    -item.predicted_load.load_score,
                    item.total_time_minutes,
                ),
            )
        if preference == Preference.LESS_WALKING:
            return sorted(
                items,
                key=lambda item: (item.walk_time_minutes, -item.experience_score),
            )
        if preference == Preference.LESS_TRANSFER:
            return sorted(
                items,
                key=lambda item: (item.transfer_count, -item.experience_score),
            )
        return sorted(
            items,
            key=lambda item: (-item.experience_score, item.total_time_minutes),
        )
