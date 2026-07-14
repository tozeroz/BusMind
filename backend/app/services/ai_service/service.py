from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.intelligence_settings import settings
from app.schemas.ai_travel import (
    AiMode,
    AiTravelRequest,
    AiTravelResult,
    AiTravelStatus,
)
from app.schemas.recommendation import RecommendRoutesRequest, RouteRecommendation
from app.services.recommend_service import RecommendationService
from llm.prompts.travel_assistant import SYSTEM_PROMPT, build_user_prompt
from llm.providers.deepseek import DeepSeekClient, DeepSeekConfig, DeepSeekError

logger = logging.getLogger(__name__)


class AiTravelService:
    def __init__(
        self,
        recommendation_service: RecommendationService,
        client: DeepSeekClient | Any | None = None,
    ) -> None:
        self.recommendation_service = recommendation_service
        self.client = client if client is not None else self._build_default_client()

    async def answer(self, request: AiTravelRequest) -> AiTravelResult:
        routes = _extract_routes_from_context(request.context)
        used_tools: list[str] = []
        evidence_source = "request_context" if routes else "none"

        if request.mode == AiMode.SUGGEST and not routes:
            missing_fields = _missing_station_fields(request)
            if missing_fields:
                return self._clarification_result(
                    request,
                    missing_fields,
                    "请提供完整的起点和终点，我才能查询候选路线、预计到站时间和客载情况。",
                )
            recommendation = await self.recommendation_service.recommend(
                RecommendRoutesRequest(
                    start_station_id=request.start_station_id,
                    end_station_id=request.end_station_id,
                    preference=request.preference,
                )
            )
            routes = recommendation.items
            used_tools = [
                "eta",
                "passenger_load_prediction",
                "travel_experience_evaluate",
                "recommend_routes",
            ]
            evidence_source = "recommendation_service"
        elif routes:
            used_tools = ["provided_route_context"]

        if request.mode == AiMode.EXPLAIN and request.route_id:
            matched = [route for route in routes if route.route_id == request.route_id]
            if not matched:
                return self._clarification_result(
                    request,
                    ["route_id"],
                    "当前推荐结果中没有找到指定路线，请重新选择一条候选路线后再询问。",
                    related_routes=routes[:5],
                )
            routes = matched

        if request.mode == AiMode.QA and not routes:
            return self._clarification_result(
                request,
                ["context.items"],
                "当前没有可核验的路线、ETA 或客载数据。请先提供起点和终点并查询路线。",
            )

        evidence_context = _build_evidence_context(
            request,
            routes,
            source=evidence_source,
        )
        reminders = self._build_reminders(routes)

        if self.client is not None:
            try:
                answer = await self.client.chat(
                    [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": build_user_prompt(
                                request.mode.value,
                                request.question,
                                evidence_context,
                            ),
                        },
                    ]
                )
                return AiTravelResult(
                    answer=answer,
                    mode=request.mode,
                    status=AiTravelStatus.COMPLETED,
                    used_tools=[*used_tools, "deepseek"],
                    related_routes=routes[:5],
                    reminders=reminders,
                    fallback=False,
                )
            except DeepSeekError as exc:
                # Do not expose credentials or raw request data.  The exception
                # contains only a bounded provider error message.
                logger.warning("DeepSeek call failed; using local fallback: %s", exc)
                reminders.append(f"AI 服务调用失败，已使用本地结果：{exc}")

        return AiTravelResult(
            answer=self._fallback_answer(request, routes),
            mode=request.mode,
            status=AiTravelStatus.DEGRADED,
            used_tools=used_tools,
            related_routes=routes[:5],
            reminders=reminders,
            fallback=True,
        )

    @staticmethod
    def _clarification_result(
        request: AiTravelRequest,
        missing_fields: list[str],
        answer: str,
        *,
        related_routes: list[RouteRecommendation] | None = None,
    ) -> AiTravelResult:
        return AiTravelResult(
            answer=answer,
            mode=request.mode,
            status=AiTravelStatus.NEEDS_CLARIFICATION,
            missing_fields=missing_fields,
            used_tools=[],
            related_routes=related_routes or [],
            reminders=[],
            fallback=False,
        )

    @staticmethod
    def _build_default_client() -> DeepSeekClient | None:
        if not settings.deepseek_api_key:
            logger.info("DeepSeek client disabled: DEEPSEEK_API_KEY is not configured")
            return None
        return DeepSeekClient(
            DeepSeekConfig(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
                model=settings.deepseek_model,
                timeout_seconds=settings.deepseek_timeout_seconds,
                max_tokens=settings.deepseek_max_tokens,
                temperature=settings.deepseek_temperature,
            )
        )

    @staticmethod
    def _fallback_answer(
        request: AiTravelRequest,
        routes: list[RouteRecommendation],
    ) -> str:
        if not routes:
            if request.mode == AiMode.QA:
                return "当前没有可核验的线路、ETA 或客载数据。请先查询路线，或在 context 中传入推荐结果。"
            if request.mode == AiMode.EXPLAIN:
                return "未找到该路线的结构化结果，暂时无法解释。请把 recommend-routes 的返回结果放入 context。"
            return "暂未获得候选路线，请检查起终点或数据服务后重试。"

        best = max(routes, key=lambda item: item.experience_score)
        line_names = " → ".join(segment.line_name for segment in best.segments)
        load_text = {
            "seats_available": "预计有座位",
            "standing_available": "预计可站立",
            "limited_standing": "预计较拥挤",
        }.get(best.predicted_load.predicted_load_level.value, "客载状态未知")
        return (
            f"建议选择 {line_names}。预计约 {best.predicted_eta_minutes:.1f} 分钟后到达上车站，"
            f"{load_text}，步行约 {best.walk_time_minutes:.1f} 分钟，"
            f"换乘 {best.transfer_count} 次，出行体验分 {best.experience_score:.1f}。"
        )

    @staticmethod
    def _build_reminders(routes: list[RouteRecommendation]) -> list[str]:
        reminders: list[str] = []
        if any(
            route.predicted_load.predicted_load_level.value == "limited_standing"
            for route in routes
        ):
            reminders.append("部分方案预计较拥挤，建议预留候车时间或选择宽松方案")
        if any(route.walk_time_minutes > 12 for route in routes):
            reminders.append("部分方案步行时间较长，请结合天气和体力选择")
        if any(route.transfer_count > 0 for route in routes):
            reminders.append("换乘方案需关注下车站点和下一段线路")
        return reminders


def _routes_to_evidence(routes: list[RouteRecommendation]) -> list[dict[str, Any]]:
    return [
        {
            "route_id": route.route_id,
            "line_names": [segment.line_name for segment in route.segments],
            "boarding_station": route.boarding_station.station_name,
            "alighting_station": route.alighting_station.station_name,
            "predicted_eta_minutes": route.predicted_eta_minutes,
            "predicted_load_level": route.predicted_load.predicted_load_level.value,
            "predicted_load_rate": route.predicted_load.predicted_load_rate,
            "walk_time_minutes": route.walk_time_minutes,
            "transfer_count": route.transfer_count,
            "total_time_minutes": route.total_time_minutes,
            "experience_score": route.experience_score,
            "recommend_types": [item.value for item in route.recommend_types],
            "reason": route.reason,
        }
        for route in routes
    ]


def _build_evidence_context(
    request: AiTravelRequest,
    routes: list[RouteRecommendation],
    *,
    source: str,
) -> dict[str, Any]:
    return {
        "contract_version": "1.0",
        "mode": request.mode.value,
        "query": {
            "preference": request.preference.value,
            "start_station_id": request.start_station_id,
            "end_station_id": request.end_station_id,
            "route_id": request.route_id,
        },
        "evidence": {
            "source": source,
            "routes": _routes_to_evidence(routes),
        },
        "missing_information": [],
        "constraints": {
            "route_facts_are_authoritative": True,
            "model_must_not_recalculate_metrics": True,
            "model_must_not_invent_realtime_data": True,
        },
    }


def _missing_station_fields(request: AiTravelRequest) -> list[str]:
    missing: list[str] = []
    if request.start_station_id is None:
        missing.append("start_station_id")
    if request.end_station_id is None:
        missing.append("end_station_id")
    return missing


def _extract_routes_from_context(
    context: dict[str, Any] | None,
) -> list[RouteRecommendation]:
    if not context:
        return []

    candidate: Any = context
    if isinstance(candidate, dict) and isinstance(candidate.get("data"), dict):
        candidate = candidate["data"]
    items = candidate.get("items") if isinstance(candidate, dict) else None
    if not isinstance(items, list):
        return []

    routes: list[RouteRecommendation] = []
    for item in items[:10]:
        try:
            routes.append(RouteRecommendation.model_validate(item))
        except Exception:
            continue
    return routes
