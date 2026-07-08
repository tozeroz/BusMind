from __future__ import annotations


LOAD_TEXT = {
    "seats_available": "预计有座位，车内较宽松",
    "standing_available": "预计可站立，客载压力适中",
    "limited_standing": "预计站立空间有限，车内较拥挤",
}


def build_experience_reason(
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
) -> str:
    load_text = LOAD_TEXT.get(load_level, "客载状态未知")
    walk_text = (
        "步行时间较短"
        if walk_time_minutes <= 6
        else "步行时间可接受"
        if walk_time_minutes <= 12
        else "步行时间较长"
    )
    transfer_text = (
        "无需换乘"
        if transfer_count == 0
        else f"需要换乘 {transfer_count} 次"
    )
    return f"{load_text}，{walk_text}，{transfer_text}。"


def build_route_reason(
    line_names: list[str],
    eta_minutes: float,
    load_level: str,
    walk_time_minutes: float,
    transfer_count: int,
    experience_score: float,
) -> str:
    line_text = " → ".join(line_names)
    detail = build_experience_reason(load_level, walk_time_minutes, transfer_count)
    return (
        f"推荐 {line_text}：预计约 {eta_minutes:.1f} 分钟后到达上车站，"
        f"步行约 {walk_time_minutes:.1f} 分钟。{detail}"
        f"出行体验综合分为 {experience_score:.1f} 分。"
    )
