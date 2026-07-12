from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.schemas.common import StrictModel


class EtaResult(StrictModel):
    """LTA 实时 ETA 查询结果。

    数据来源：LTA Bus Arrival 实时数据（MySQL 缓存）+ 仿真覆盖 + 规则兜底。
    非自研 ETA 预测模型。
    """

    vehicle_id: int = Field(gt=0)
    target_station_id: int = Field(gt=0)
    predicted_eta_minutes: float = Field(
        ge=0,
        description="预计到达分钟数（来自 LTA 实时数据，非自研预测模型；字段名含 predicted 为历史兼容）",
    )
    arrival_time: datetime
    factors: dict[str, Any]
    model_version: str = Field(
        default="eta_mysql_realtime_v1",
        description="ETA 数据版本标识（历史兼容字段，非 ML 模型版本号；实际值如 eta_mysql_realtime_v1 / eta_rule_v1）",
    )