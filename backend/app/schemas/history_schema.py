from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class PassengerFlowTrendDTO(BaseModel):
    flow_record_id: int
    target_type: str
    target_id: int
    bus_stop_code: Optional[str]
    record_time: Optional[datetime]
    day_type: Optional[str]
    tap_in_volume: int
    tap_out_volume: int
    total_flow: int
    flow_level: Optional[str]
    data_source: Optional[str]

class PassengerFlowSummary(BaseModel):
    total_tap_in: int
    total_tap_out: int
    total_flow: int
    peak_hour: Optional[int]
    peak_flow: Optional[int]
    dominant_flow_level: Optional[str]

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
    confidence: Optional[float]
    model_version: Optional[str]

class EtaPredictionDTO(BaseModel):
    eta_prediction_id: int
    vehicle_id: int
    line_id: int
    target_station_id: int
    prediction_time: Optional[datetime]
    predicted_eta_minutes: float
    arrival_time: Optional[datetime]
    vehicle_to_stop_distance_m: Optional[float]
    speed_kph: Optional[float]
    confidence: Optional[float]
    model_version: Optional[str]
    created_at: datetime

class LoadPredictionDTO(BaseModel):
    load_prediction_id: int
    vehicle_id: int
    line_id: int
    station_id: Optional[int]
    prediction_time: Optional[datetime]
    predicted_load_level: str
    load_score: Optional[float]
    predicted_load_rate: Optional[float]
    onboard_count: Optional[int]
    capacity: Optional[int]
    confidence: Optional[float]
    model_version: Optional[str]
    created_at: datetime