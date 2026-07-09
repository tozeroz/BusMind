from sqlalchemy import Column, BIGINT, Integer, Float, DateTime, ForeignKey, String, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PassengerFlowTrend(Base):
    __tablename__ = "passenger_flow_trend"

    flow_record_id = Column(BIGINT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(BIGINT, nullable=False, index=True)
    bus_stop_code = Column(String(30))
    record_time = Column(DateTime, nullable=False, index=True)
    day_type = Column(String(20))
    tap_in_volume = Column(Integer, nullable=False, default=0)
    tap_out_volume = Column(Integer, nullable=False, default=0)
    total_flow = Column(Integer, nullable=False, default=0)
    flow_level = Column(String(20))
    data_source = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class PassengerFlowPrediction(Base):
    __tablename__ = "passenger_flow_prediction"

    prediction_id = Column(BIGINT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False, index=True)
    target_id = Column(String(50), nullable=False, index=True)
    prediction_time = Column(DateTime, nullable=False, index=True)
    predict_time = Column(DateTime, nullable=False, index=True)
    predicted_flow = Column(Integer, nullable=False)
    crowd_level = Column(String(20), nullable=False)
    confidence = Column(DECIMAL(5, 4))
    model_version = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class EtaPrediction(Base):
    __tablename__ = "eta_prediction"

    eta_prediction_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, ForeignKey("bus_vehicles.vehicle_id"), nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_lines.line_id"), nullable=False, index=True)
    target_station_id = Column(BIGINT, ForeignKey("bus_stations.station_id"), nullable=False, index=True)
    prediction_time = Column(DateTime, nullable=False, index=True)
    predicted_eta_minutes = Column(DECIMAL(8, 2), nullable=False)
    arrival_time = Column(DateTime, index=True)
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2))
    speed_kph = Column(DECIMAL(6, 2))
    confidence = Column(DECIMAL(5, 4))
    model_version = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class LoadPrediction(Base):
    __tablename__ = "load_prediction"

    load_prediction_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, ForeignKey("bus_vehicles.vehicle_id"), nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_lines.line_id"), nullable=False, index=True)
    station_id = Column(BIGINT, ForeignKey("bus_stations.station_id"), index=True)
    prediction_time = Column(DateTime, nullable=False, index=True)
    predicted_load_level = Column(String(30), nullable=False)
    load_score = Column(DECIMAL(6, 2))
    predicted_load_rate = Column(DECIMAL(6, 4))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(DECIMAL(5, 4))
    model_version = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())