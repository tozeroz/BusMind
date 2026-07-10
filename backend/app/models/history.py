from sqlalchemy import Column, BIGINT, Integer, Float, DateTime, ForeignKey, String, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property

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
    __tablename__ = "bus_eta_status"

    eta_prediction_id = Column("eta_status_id", BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    target_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    bus_stop_code = Column(String(30))
    prediction_time = Column("query_time", DateTime, index=True)
    predicted_eta_minutes = Column("eta_minutes", Float, nullable=False)
    arrival_time = Column(DateTime)
    vehicle_to_stop_distance_m = Column(Float)
    speed_kph = Column(Float)
    confidence = Column(Float)
    data_source = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    model_version = column_property(None)


class LoadPrediction(Base):
    __tablename__ = "bus_load_status"

    load_prediction_id = Column("load_status_id", BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    bus_stop_code = Column(String(30))
    prediction_time = Column("query_time", DateTime, index=True)
    load_code = Column(String(20))
    predicted_load_level = Column("load_level", String(32), nullable=False)
    load_score = Column(Float)
    predicted_load_rate = Column("load_rate", Float)
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(Float)
    data_source = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    model_version = column_property(None)
