from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# 默认配置：可直接在这里改起点、终点和偏好。Aft Braddell Rd
# 运行命令：
# cd ./backend
# uv run python ./scripts/inspect_recommendation_chain.py
DEFAULT_START_STATION_NAME = "Aft Braddell Rd"
DEFAULT_END_STATION_NAME = "New Tech Pk"
DEFAULT_PREFERENCE = "balanced"
DEFAULT_ALLOW_TRANSFER = True
DEFAULT_MAX_TRANSFER_COUNT = 2


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
for path in (PROJECT_ROOT, BACKEND_ROOT):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

# 当前后端运行配置统一放在 backend/.env。
load_dotenv(BACKEND_ROOT / ".env", override=False)

from app.core.time_utils import ensure_local_datetime, now_local
from app.db.session import SessionLocal
from app.models.bus_line import BusStation
from app.schemas.recommendation import Preference, RecommendRoutesRequest
from app.services.eta_service import EtaService
from app.services.intelligence_gateway_mysql import MySQLTransitGateway
from app.services.load_service import PassengerLoadService
from app.services.recommend_service.experience_service import TravelExperienceService
from app.services.recommend_service.recommendation_service import (
    MODEL_SCORE_LIMIT,
    RecommendationService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="打印真实数据库推荐链路：前端请求体、后端候选路径、算法评分、最终响应。"
    )
    parser.add_argument("--start", default=DEFAULT_START_STATION_NAME)
    parser.add_argument("--end", default=DEFAULT_END_STATION_NAME)
    parser.add_argument("--preference", default=DEFAULT_PREFERENCE)
    parser.add_argument(
        "--allow-transfer",
        action=argparse.BooleanOptionalAction,
        default=DEFAULT_ALLOW_TRANSFER,
    )
    parser.add_argument("--max-transfer-count", type=int, default=DEFAULT_MAX_TRANSFER_COUNT)
    return parser.parse_args()


def print_section(title: str, data: Any) -> None:
    print(f"\n========== {title} ==========")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def station_to_dict(station: BusStation) -> dict[str, Any]:
    return {
        "station_id": int(station.station_id),
        "station_name": station.station_name,
        "bus_stop_code": getattr(station, "bus_stop_code", None),
        "longitude": float(station.longitude),
        "latitude": float(station.latitude),
    }


def resolve_station(db, station_name: str, label: str) -> BusStation:
    exact = (
        db.query(BusStation)
        .filter(BusStation.station_name == station_name)
        .order_by(BusStation.station_id)
        .first()
    )
    if exact is not None:
        return exact

    matches = (
        db.query(BusStation)
        .filter(BusStation.station_name.like(f"%{station_name}%"))
        .order_by(BusStation.station_id)
        .limit(10)
        .all()
    )
    if not matches:
        raise RuntimeError(f"{label} station not found: {station_name}")

    print_section(
        f"{label} station fuzzy matches; using first",
        [station_to_dict(station) for station in matches],
    )
    return matches[0]


def candidate_to_dict(candidate) -> dict[str, Any]:
    return {
        "route_id": candidate.route_id,
        "vehicle_id": candidate.vehicle_id,
        "line_ids": list(candidate.line_ids),
        "boarding_station_id": candidate.boarding_station_id,
        "alighting_station_id": candidate.alighting_station_id,
        "walk_time_minutes": candidate.walk_time_minutes,
        "ride_time_minutes": candidate.ride_time_minutes,
        "transfer_count": candidate.transfer_count,
        "segments": [
            {
                "segment_order": segment.segment_order,
                "line_id": segment.line_id,
                "line_name": segment.line_name,
                "boarding_station_id": segment.boarding_station_id,
                "alighting_station_id": segment.alighting_station_id,
                "ride_time_minutes": segment.ride_time_minutes,
            }
            for segment in candidate.segments
        ],
    }


def final_route_to_dict(route) -> dict[str, Any]:
    return {
        "route_id": route.route_id,
        "line_ids": route.line_ids,
        "segments": [segment.model_dump(mode="json") for segment in route.segments],
        "boarding_station": route.boarding_station.model_dump(mode="json"),
        "alighting_station": route.alighting_station.model_dump(mode="json"),
        "predicted_eta_minutes": route.predicted_eta_minutes,
        "predicted_load": route.predicted_load.model_dump(mode="json"),
        "walk_time_minutes": route.walk_time_minutes,
        "ride_time_minutes": route.ride_time_minutes,
        "total_time_minutes": route.total_time_minutes,
        "transfer_count": route.transfer_count,
        "experience_score": route.experience_score,
        "recommend_types": [item.value for item in route.recommend_types],
        "reason": route.reason,
    }


async def inspect_chain(args: argparse.Namespace) -> None:
    db = SessionLocal()
    try:
        gateway = MySQLTransitGateway(db)
        service = RecommendationService(
            gateway=gateway,
            eta_service=EtaService(gateway),
            load_service=PassengerLoadService(gateway),
            experience_service=TravelExperienceService(),
        )

        start_station = resolve_station(db, args.start, "start")
        end_station = resolve_station(db, args.end, "end")
        frontend_payload = {
            "start_station_id": int(start_station.station_id),
            "end_station_id": int(end_station.station_id),
            "preference": args.preference,
            "allow_transfer": bool(args.allow_transfer),
            "max_transfer_count": int(args.max_transfer_count) if args.allow_transfer else 0,
        }

        print_section(
            "1. 前端模拟请求体 /recommend-routes",
            {
                "start_station": station_to_dict(start_station),
                "end_station": station_to_dict(end_station),
                "payload": frontend_payload,
            },
        )

        candidates = await gateway.get_candidate_routes(
            frontend_payload["start_station_id"],
            frontend_payload["end_station_id"],
            frontend_payload["max_transfer_count"],
        )
        print_section(
            "2. 后端生成的候选路径",
            {
                "count": len(candidates),
                "items": [candidate_to_dict(candidate) for candidate in candidates],
            },
        )

        if not candidates:
            print_section(
                "诊断",
                "候选路径为空，所以后端不会调用算法评分。请检查方向、line_station 站序或换乘图。",
            )
            return

        depart_time = ensure_local_datetime(None)
        weights = service._weights_for_preference(Preference(args.preference))
        built_routes = [
            await service._build_route(candidate, depart_time, weights)
            for candidate in candidates[:MODEL_SCORE_LIMIT]
        ]
        model_payload = {
            "contract_version": "1.0.0",
            "request_id": (
                f"inspect:{start_station.station_id}:{end_station.station_id}:"
                f"{now_local().isoformat()}"
            ),
            "preference": service._model_preference(Preference(args.preference)),
            "routes": [route.model_payload for route in built_routes],
        }
        print_section("3. 后端传给算法的模型 payload", model_payload)

        model_result = service._predict_with_route_model(model_payload)
        print_section("4. 算法返回的路径评分", model_result)

        backend_result = await service.recommend(RecommendRoutesRequest(**frontend_payload))
        print_section(
            "5. 后端最终返回给前端的信息",
            {
                "best_experience_route_id": backend_result.best_experience_route_id,
                "fastest_route_id": backend_result.fastest_route_id,
                "least_crowded_route_id": backend_result.least_crowded_route_id,
                "least_walking_route_id": backend_result.least_walking_route_id,
                "least_transfer_route_id": backend_result.least_transfer_route_id,
                "preference": backend_result.preference.value,
                "generated_at": backend_result.generated_at,
                "items": [final_route_to_dict(route) for route in backend_result.items],
            },
        )
    finally:
        db.close()


def main() -> None:
    asyncio.run(inspect_chain(parse_args()))


if __name__ == "__main__":
    main()
