from __future__ import annotations

from typing import Any

from app.schemas.ai_travel import AiMode, AiTravelRequest, AiTravelResult
from app.schemas.recommendation import RecommendRoutesRequest, RouteRecommendation
from app.services.recommend_service import RecommendationService


class AiTravelService:
    def __init__(
        self,
        recommendation_service: RecommendationService,
        client: Any = None,
    ) -> None:
        self.recommendation_service = recommendation_service
        self.client = client or self._build_default_client()

    @staticmethod
    def _build_default_client():
        return None

    async def answer(self, request: AiTravelRequest) -> AiTravelResult:
        used_tools = []
        related_routes: list[RouteRecommendation] = []
        reminders: list[str] = []
        fallback = True
        answer = "抱歉，暂无法处理该请求"

        if self.client is not None:
            messages = [{"role": "system", "content": "你是一个公交出行助手"}]
            answer = await self.client.chat(messages)
            fallback = False
            used_tools.append("deepseek")
        elif request.mode == AiMode.SUGGEST and request.start_station_id and request.end_station_id:
            try:
                recommend_request = RecommendRoutesRequest(
                    start_station_id=request.start_station_id,
                    end_station_id=request.end_station_id,
                    preference=request.preference,
                )
                result = await self.recommendation_service.recommend(recommend_request)
                related_routes = result.items
                used_tools.append("recommend_routes")
                answer = f"为您推荐了 {len(related_routes)} 条公交线路方案"
            except Exception as e:
                answer = f"获取推荐路线时出错: {str(e)}"

        return AiTravelResult(
            answer=answer,
            mode=request.mode,
            used_tools=used_tools,
            related_routes=related_routes,
            reminders=reminders,
            fallback=fallback,
        )