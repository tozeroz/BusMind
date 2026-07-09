from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone
from typing import Optional
from app.dependencies.auth import get_db
from app.services.history_service import (
    get_passenger_flow_trend,
    get_passenger_flow_prediction,
    get_eta_prediction,
    get_load_prediction,
    get_eta_predictions_by_line,
    get_load_predictions_by_line
)
from app.schemas.user_schema import ApiResponse
from app.schemas.history_schema import (
    PassengerFlowResponse,
    PassengerFlowPredictionDTO,
    EtaPredictionDTO,
    LoadPredictionDTO
)

router = APIRouter(prefix="/history", tags=["History"])

def get_trace_id() -> str:
    return f"req_{uuid4().hex[:12]}"

def get_timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def build_response(code: int, message: str, data=None) -> ApiResponse:
    return ApiResponse(
        code=code,
        message=message,
        data=data,
        trace_id=get_trace_id(),
        timestamp=get_timestamp()
    )

@router.get(
    "/passenger-flow",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Passenger Flow Trend",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_passenger_flow(
    line_id: Optional[int] = Query(None, ge=1),
    station_id: Optional[int] = Query(None, ge=1),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    granularity: str = Query("hour", regex="^(hour|day|week)$"),
    db: Session = Depends(get_db)
):
    start_datetime = datetime.fromisoformat(start_date) if start_date else None
    end_datetime = datetime.fromisoformat(end_date) if end_date else None
    
    result = get_passenger_flow_trend(
        db=db,
        line_id=line_id,
        station_id=station_id,
        start_date=start_datetime,
        end_date=end_datetime,
        granularity=granularity
    )
    return build_response(0, "success", result.model_dump())

@router.get(
    "/passenger-flow/prediction",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Passenger Flow Prediction",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_passenger_flow_prediction_api(
    target_type: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    start_datetime = datetime.fromisoformat(start_time) if start_time else None
    end_datetime = datetime.fromisoformat(end_time) if end_time else None
    
    result = get_passenger_flow_prediction(
        db=db,
        target_type=target_type,
        target_id=target_id,
        start_time=start_datetime,
        end_time=end_datetime
    )
    return build_response(0, "success", [r.model_dump() for r in result])

@router.get(
    "/eta/{vehicle_id}/{target_station_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get ETA Prediction for Vehicle",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Not found"}
    }
)
async def get_eta(
    vehicle_id: int,
    target_station_id: int,
    line_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    result = get_eta_prediction(
        db=db,
        vehicle_id=vehicle_id,
        target_station_id=target_station_id,
        line_id=line_id
    )
    if result:
        return build_response(0, "success", result.model_dump())
    return build_response(404, "ETA prediction not found")

@router.get(
    "/eta/line/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get ETA Predictions by Line",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_eta_by_line(
    line_id: int,
    target_station_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    result = get_eta_predictions_by_line(
        db=db,
        line_id=line_id,
        target_station_id=target_station_id
    )
    return build_response(0, "success", [r.model_dump() for r in result])

@router.get(
    "/load/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Load Prediction",
    responses={
        200: {"description": "Get success"},
        404: {"description": "Not found"}
    }
)
async def get_load(
    line_id: int,
    station_id: Optional[int] = Query(None, ge=1),
    vehicle_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    result = get_load_prediction(
        db=db,
        line_id=line_id,
        station_id=station_id,
        vehicle_id=vehicle_id
    )
    if result:
        return build_response(0, "success", result.model_dump())
    return build_response(404, "Load prediction not found")

@router.get(
    "/load/line/{line_id}",
    response_model=ApiResponse,
    status_code=200,
    summary="Get Load Predictions by Line",
    responses={
        200: {"description": "Get success"}
    }
)
async def get_load_by_line(
    line_id: int,
    station_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db)
):
    result = get_load_predictions_by_line(
        db=db,
        line_id=line_id,
        station_id=station_id
    )
    return build_response(0, "success", [r.model_dump() for r in result])