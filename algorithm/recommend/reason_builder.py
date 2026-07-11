"""Reason builders for recommendation explanations."""

from __future__ import annotations

from typing import Any

from algorithm.recommend.contracts import ReasonFactors, RouteFeature


LOAD_REASON_TEXT = {
    "SEA": "车内大概率有座位，舒适度更好",
    "SDA": "车内允许站立，舒适度中等",
    "LSD": "车内偏拥挤，站立空间有限",
}

FLOW_REASON_TEXT = {
    "low": "上月同小时客流压力较低",
    "medium": "上月同小时客流处于中等水平",
    "high": "上月同小时客流偏高，上车压力会更明显",
}


def _eta_reason(route: RouteFeature, time_score: float) -> str:
    total_time = route.total_time_minutes
    if route.eta_minutes is None:
        return f"缺少实时 ETA，时间评分按兜底值处理（{time_score:.1f}）"
    if total_time <= 20:
        return f"等待加乘车总时间约 {total_time:.1f} 分钟，时间效率较好"
    if total_time <= 35:
        return f"等待加乘车总时间约 {total_time:.1f} 分钟，整体可接受"
    return f"等待加乘车总时间约 {total_time:.1f} 分钟，时间成本偏高"


def _comfort_reason(route: RouteFeature, comfort_score: float) -> str:
    if route.load_code:
        base = LOAD_REASON_TEXT.get(route.load_code.upper(), "实时客载状态未知")
        return f"{base}（舒适度评分 {comfort_score:.1f}）"
    return f"缺少实时客载状态，舒适度评分按兜底值处理（{comfort_score:.1f}）"


def _walk_reason(route: RouteFeature, walk_score: float) -> str:
    walk_time = route.walk_time_minutes
    if walk_time <= 5:
        return f"步行约 {walk_time:.1f} 分钟，步行负担较轻（评分 {walk_score:.1f}）"
    if walk_time <= 10:
        return f"步行约 {walk_time:.1f} 分钟，步行负担中等（评分 {walk_score:.1f}）"
    return f"步行约 {walk_time:.1f} 分钟，步行成本偏高（评分 {walk_score:.1f}）"


def _transfer_reason(route: RouteFeature, transfer_score: float) -> str:
    if route.transfer_count == 0:
        return f"全程无需换乘，复杂度最低（评分 {transfer_score:.1f}）"
    return f"需要换乘 {route.transfer_count} 次，换乘复杂度评分 {transfer_score:.1f}"


def _frequency_reason(route: RouteFeature, frequency_score: float) -> str:
    if route.avg_service_frequency is None:
        return f"缺少发车频率，频率评分按兜底值处理（{frequency_score:.1f}）"
    return (
        f"平均发车间隔约 {route.avg_service_frequency:.1f} 分钟，"
        f"频率评分 {frequency_score:.1f}"
    )


def _flow_reason(route: RouteFeature, flow_score: float) -> str:
    level = (route.station_flow_level or "").strip().lower()
    if level:
        base = FLOW_REASON_TEXT.get(level, "站点客流等级未知")
        return f"{base}（客流评分 {flow_score:.1f}）"
    if route.station_flow_mean is not None:
        return f"站点历史平均客流约 {route.station_flow_mean:.1f}，客流评分 {flow_score:.1f}"
    return f"缺少站点客流数据，客流评分按兜底值处理（{flow_score:.1f}）"


def _congestion_reason(route: RouteFeature, congestion_score: float) -> str:
    if route.congestion_score is None:
        return f"缺少实时路况，拥堵评分按兜底值处理（{congestion_score:.1f}）"
    raw = route.normalized_congestion_pressure
    if raw <= 0.25:
        return f"沿线道路较通畅，拥堵影响较小（评分 {congestion_score:.1f}）"
    if raw <= 0.55:
        return f"沿线路况中等，拥堵影响可控（评分 {congestion_score:.1f}）"
    return f"沿线拥堵偏明显，可能拖累通行体验（评分 {congestion_score:.1f}）"


def _reliability_reason(route: RouteFeature, reliability_score: float) -> str:
    if route.confidence is not None and route.confidence < 0.8:
        return f"部分特征来自降级估计，可靠性评分 {reliability_score:.1f}"
    if route.reliability_score is None:
        return f"缺少可靠性字段，评分按兜底值处理（{reliability_score:.1f}）"
    if reliability_score >= 80:
        return f"实时数据覆盖较完整，可靠性评分 {reliability_score:.1f}"
    if reliability_score >= 60:
        return f"实时数据可用但有部分降级，可靠性评分 {reliability_score:.1f}"
    return f"实时数据不够稳定，可靠性评分 {reliability_score:.1f}"


def build_reason_factors(
    route: RouteFeature,
    *,
    time_score: float,
    comfort_score: float,
    walk_score: float,
    transfer_score: float,
    frequency_score: float,
    flow_score: float,
    congestion_score: float,
    reliability_score: float,
) -> ReasonFactors:
    return ReasonFactors(
        eta_reason=_eta_reason(route, time_score),
        comfort_reason=_comfort_reason(route, comfort_score),
        walk_reason=_walk_reason(route, walk_score),
        transfer_reason=_transfer_reason(route, transfer_score),
        frequency_reason=_frequency_reason(route, frequency_score),
        flow_reason=_flow_reason(route, flow_score),
        congestion_reason=_congestion_reason(route, congestion_score),
        reliability_reason=_reliability_reason(route, reliability_score),
    )


def _legacy_build_experience_reason(**kwargs: Any) -> str:
    eta_minutes = kwargs.get("eta_minutes")
    load_level = str(kwargs.get("load_level") or "").upper()
    walk_time_minutes = float(kwargs.get("walk_time_minutes", 0.0))
    transfer_count = int(kwargs.get("transfer_count", 0))
    avg_service_frequency = kwargs.get("avg_service_frequency")
    station_flow_level = kwargs.get("station_flow_level")
    congestion_score = kwargs.get("congestion_score")
    reliability_score = kwargs.get("reliability_score")

    route = RouteFeature(
        route_id="legacy",
        service_no="legacy",
        eta_minutes=eta_minutes,
        load_code=load_level if load_level in {"SEA", "SDA", "LSD"} else None,
        walk_time_minutes=walk_time_minutes,
        ride_time_minutes=0.0,
        transfer_count=transfer_count,
        avg_service_frequency=avg_service_frequency,
        station_flow_level=station_flow_level,
        congestion_score=congestion_score,
        reliability_score=reliability_score,
        data_source="legacy",
    )
    factors = build_reason_factors(
        route,
        time_score=60.0,
        comfort_score=60.0,
        walk_score=60.0,
        transfer_score=60.0,
        frequency_score=60.0,
        flow_score=60.0,
        congestion_score=60.0,
        reliability_score=60.0,
    )
    return build_experience_reason(route, factors)


def build_experience_reason(route: RouteFeature | None = None, factors: ReasonFactors | None = None, **kwargs: Any) -> str:
    if route is None or factors is None:
        return _legacy_build_experience_reason(**kwargs)
    return "；".join(
        [
            factors.eta_reason,
            factors.comfort_reason,
            factors.walk_reason,
            factors.transfer_reason,
            factors.frequency_reason,
            factors.flow_reason,
            factors.congestion_reason,
            factors.reliability_reason,
        ]
    )


def build_route_reason(
    route: RouteFeature | None = None,
    factors: ReasonFactors | None = None,
    recommend_score: float | None = None,
    **kwargs: Any,
) -> str:
    if route is None or factors is None or recommend_score is None:
        line_names = kwargs.get("line_names") or []
        line_text = " -> ".join(str(name) for name in line_names) if line_names else "线路"
        detail = _legacy_build_experience_reason(**kwargs)
        experience_score = float(kwargs.get("experience_score", 0.0))
        return f"推荐线路 {line_text}。{detail}。综合推荐分 {experience_score:.1f}。"
    line_text = route.service_no or "/".join(route.line_ids) or route.route_id
    detail = build_experience_reason(route, factors)
    return f"推荐线路 {line_text}。{detail}。综合推荐分 {recommend_score:.1f}。"
