from __future__ import annotations


LOAD_TEXT = {
    "seats_available": "预计有座位，车内相对宽松",
    "standing_available": "预计可以站立，拥挤程度中等",
    "limited_standing": "预计较拥挤，站立空间有限",
    "overcrowded": "预计车厢较满，舒适度偏低",
}

FLOW_TEXT = {
    "low": "上月同时段站点客流偏低",
    "medium": "上月同时段站点客流中等",
    "high": "上月同时段站点客流偏高",
}


def build_experience_reason(
    *,
    load_level: str,
    eta_minutes: float | None,
    walk_time_minutes: float,
    transfer_count: int,
    avg_service_frequency: float | None = None,
    station_flow_level: str | None = None,
    congestion_score: float | None = None,
    reliability_score: float | None = None,
) -> str:
    parts: list[str] = []
    if eta_minutes is not None:
        if eta_minutes <= 5:
            parts.append(f"预计等待约 {eta_minutes:.1f} 分钟，上车较快")
        elif eta_minutes <= 12:
            parts.append(f"预计等待约 {eta_minutes:.1f} 分钟")
        else:
            parts.append(f"预计等待约 {eta_minutes:.1f} 分钟，时间成本偏高")

    parts.append(LOAD_TEXT.get(load_level, "实时客载状态未知"))

    if walk_time_minutes <= 6:
        parts.append(f"步行约 {walk_time_minutes:.1f} 分钟，负担较小")
    elif walk_time_minutes <= 12:
        parts.append(f"步行约 {walk_time_minutes:.1f} 分钟，可接受")
    else:
        parts.append(f"步行约 {walk_time_minutes:.1f} 分钟，步行偏长")

    if transfer_count == 0:
        parts.append("无需换乘")
    else:
        parts.append(f"需要换乘 {transfer_count} 次")

    if avg_service_frequency is not None:
        parts.append(f"线路平均发车间隔约 {avg_service_frequency:.1f} 分钟")

    if station_flow_level:
        parts.append(FLOW_TEXT.get(station_flow_level.lower(), "站点客流压力未知"))

    if congestion_score is not None:
        if congestion_score <= 0.25:
            parts.append("沿线道路较通畅")
        elif congestion_score <= 0.55:
            parts.append("沿线路况中等")
        else:
            parts.append("沿线路况偏拥堵")

    if reliability_score is not None:
        if reliability_score >= 80:
            parts.append("实时数据可信度较高")
        elif reliability_score >= 60:
            parts.append("实时数据可信度中等")
        else:
            parts.append("部分特征来自降级估算")

    return "；".join(parts) + "。"


def build_route_reason(
    *,
    line_names: list[str],
    eta_minutes: float | None,
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
    experience_score: float,
    avg_service_frequency: float | None = None,
    station_flow_level: str | None = None,
    congestion_score: float | None = None,
    reliability_score: float | None = None,
) -> str:
    line_text = " -> ".join(line_names)
    detail = build_experience_reason(
        load_level=load_level,
        eta_minutes=eta_minutes,
        walk_time_minutes=walk_time_minutes,
        transfer_count=transfer_count,
        avg_service_frequency=avg_service_frequency,
        station_flow_level=station_flow_level,
        congestion_score=congestion_score,
        reliability_score=reliability_score,
    )
    return f"推荐 {line_text}。{detail} 综合体验分 {experience_score:.1f}。"
