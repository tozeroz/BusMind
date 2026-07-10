from sqlalchemy import Column, BIGINT, Integer, Float, DateTime, ForeignKey, String, DECIMAL
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import column_property

Base = declarative_base()


class PassengerFlowTrend(Base):
    __tablename__ = "passenger_flow_trend"

    flow_record_id = Column("id", BIGINT, primary_key=True, autoincrement=True)
    year_month = Column(String(7))
    hour = Column(Integer)
    target_id = Column("station_id", BIGINT, nullable=False, index=True)
    day_type = Column(String(20))
    tap_in_volume = Column(Integer, nullable=False, default=0)
    tap_out_volume = Column(Integer, nullable=False, default=0)
    total_flow = Column(Integer, nullable=False, default=0)
    flow_level = Column(String(20))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    target_type = column_property("station")
    bus_stop_code = column_property(None)
    record_time = column_property(None)
    data_source = column_property(None)


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

    eta_prediction_id = Column("id", BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, nullable=False, index=True)
    target_station_id = Column(BIGINT, nullable=False, index=True)
    predicted_eta_minutes = Column(Float, nullable=False)
    arrival_time = Column(DateTime)
    vehicle_to_stop_distance_m = Column(Float)
    speed_kph = Column(Float)
    model_version = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    prediction_time = column_property(None)
    confidence = column_property(None)


class LoadPrediction(Base):
    __tablename__ = "load_prediction"

    load_prediction_id = Column("id", BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, nullable=False, index=True)
    station_id = Column(BIGINT, index=True)
    predicted_load_level = Column(String(32), nullable=False)
    load_score = Column(Float)
    predicted_load_rate = Column(Float)
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(Float)
    model_version = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    prediction_time = column_property(None)