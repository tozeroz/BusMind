from __future__ import annotations

from backend.app.core.intelligence_settings import settings
from backend.app.schemas.ai_travel import AiMode, AiTravelRequest, AiTravelResult
from backend.app.schemas.recommendation import RecommendRoutesRequest, RouteRecommendation
from backend.app.services.recommend_service import RecommendationService
from llm.context_builders.travel_context import extract_routes_from_context, routes_to_context
from llm.prompts.travel_assistant import SYSTEM_PROMPT, build_user_prompt
from llm.providers.deepseek import DeepSeekClient, DeepSeekConfig, DeepSeekError


class AiTravelService:
    def __init__(
        self,
        recommendation_service: RecommendationService,
        client: DeepSeekClient | None = None,
    ) -> None:
        self.recommendation_service = recommendation_service
        self.client = client or self._build_default_client()

    async def answer(self, request: AiTravelRequest) -> AiTravelResult:
        routes = extract_routes_from_context(request.context)
        used_tools: list[str] = []

        if request.mode == AiMode.SUGGEST and not routes:
            assert request.start_station_id is not None and request.end_station_id is not None
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
        elif routes:
            used_tools = ["recommend_routes"]

        if request.mode == AiMode.EXPLAIN and request.route_id:
            matched = [route for route in routes if route.route_id == request.route_id]
            if matched:
                routes = matched

        context_text = routes_to_context(routes) if routes else "[]"
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
                                context_text,
                            ),
                        },
                    ]
                )
                return AiTravelResult(
                    answer=answer,
                    mode=request.mode,
                    used_tools=used_tools,
                    related_routes=routes[:5],
                    reminders=reminders,
                    fallback=False,
                )
            except DeepSeekError:
                pass

        return AiTravelResult(
            answer=self._fallback_answer(request, routes),
            mode=request.mode,
            used_tools=used_tools,
            related_routes=routes[:5],
            reminders=reminders,
            fallback=True,
        )

    @staticmethod
    def _build_default_client() -> DeepSeekClient | None:
        if not settings.deepseek_api_key:
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
        }[best.predicted_load.predicted_load_level.value]
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
