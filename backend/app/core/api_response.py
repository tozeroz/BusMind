from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from app.core.time_utils import now_local


class ApiResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    code: int = 0
    message: str = "success"
    data: Any = None
    trace_id: str
    timestamp: datetime


def new_trace_id(prefix: str = "req") -> str:
    return f"{prefix}_{now_local():%Y%m%d%H%M%S}_{uuid4().hex[:8]}"


def success_response(data: Any, trace_prefix: str = "req") -> ApiResponse:
    if isinstance(data, BaseModel):
        payload = data.model_dump(mode="json")
    else:
        payload = data
    return ApiResponse(
        code=0,
        message="success",
        data=payload,
        trace_id=new_trace_id(trace_prefix),
        timestamp=now_local(),
    )


def error_response(code: int, message: str, trace_prefix: str = "req") -> ApiResponse:
    return ApiResponse(
        code=code,
        message=message,
        data=None,
        trace_id=new_trace_id(trace_prefix),
        timestamp=now_local(),
    )
