from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class PassengerFlowTrendDTO(BaseModel):
    flow_record_id: int
    target_type: str
    target_id: int
    bus_stop_code: Optional[str] = None
    record_time: Optional[datetime] = None
    day_type: Optional[str] = None
    tap_in_volume: int
    tap_out_volume: int
    total_flow: int
    flow_level: Optional[str] = None
    data_source: Optional[str] = None


class PassengerFlowSummary(BaseModel):
    total_tap_in: int
    total_tap_out: int
    total_flow: int
    peak_hour: Optional[int] = None
    peak_flow: Optional[int] = None
    dominant_flow_level: Optional[str] = None


class PassengerFlowResponse(BaseModel):
    items: List[PassengerFlowTrendDTO]
    summary: PassengerFlowSummary


class PassengerFlowPredictionDTO(BaseModel):
    prediction_id: int
    target_type: str
    target_id: str
    prediction_time: datetime
    predict_time: datetime
    predicted_flow: int
    crowd_level: str
    confidence: Optional[float] = None
    model_version: Optional[str] = None


class EtaPredictionDTO(BaseModel):
    eta_prediction_id: int
    vehicle_id: int
    line_id: int
    target_station_id: int
    bus_stop_code: Optional[str] = None
    prediction_time: Optional[datetime] = None
    predicted_eta_minutes: float
    arrival_time: Optional[datetime] = None
    vehicle_to_stop_distance_m: Optional[float] = None
    speed_kph: Optional[float] = None
    confidence: Optional[float] = None
    data_source: Optional[str] = None
    model_version: Optional[str] = None
    created_at: Optional[datetime] = None


class LoadPredictionDTO(BaseModel):
    load_prediction_id: int
    vehicle_id: int
    line_id: int
    station_id: Optional[int] = None
    bus_stop_code: Optional[str] = None
    prediction_time: Optional[datetime] = None
    load_code: Optional[str] = None
    predicted_load_level: str
    load_score: Optional[float] = None
    predicted_load_rate: Optional[float] = None
    onboard_count: Optional[int] = None
    capacity: Optional[int] = None
    confidence: Optional[float] = None
    data_source: Optional[str] = None
    model_version: Optional[str] = None
    created_at: Optional[datetime] = None
