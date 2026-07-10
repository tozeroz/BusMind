from __future__ import annotations

from sqlalchemy import BIGINT, DECIMAL, JSON, Column, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.user import Base


class BusStation(Base):
    __tablename__ = "bus_station"

    station_id = Column(BIGINT, primary_key=True)
    bus_stop_code = Column(String(30), unique=True, index=True)
    station_name = Column(String(100), nullable=False, index=True)
    road_name = Column(String(100))
    latitude = Column(DECIMAL(10, 7), nullable=False)
    longitude = Column(DECIMAL(10, 7), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class BusLine(Base):
    __tablename__ = "bus_line"

    line_id = Column(BIGINT, primary_key=True)
    service_no = Column(String(30), nullable=False, index=True)
    line_name = Column(String(100), nullable=False, index=True)
    operator = Column(String(100))
    direction = Column(Integer, nullable=False, default=1)
    category = Column(String(50))
    origin_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"))
    origin_stop_code = Column(String(30))
    destination_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"))
    destination_stop_code = Column(String(30))
    am_peak_freq = Column(String(20))
    am_offpeak_freq = Column(String(20))
    pm_peak_freq = Column(String(20))
    pm_offpeak_freq = Column(String(20))
    avg_service_frequency = Column(DECIMAL(6, 2))
    loop_desc = Column(String(255))
    status = Column(String(20), nullable=False, default="running", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    origin_station = relationship("BusStation", foreign_keys=[origin_station_id])
    destination_station = relationship("BusStation", foreign_keys=[destination_station_id])


class LineStation(Base):
    __tablename__ = "line_station"

    line_station_id = Column(String(50), primary_key=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    service_no = Column(String(30))
    line_name = Column(String(100))
    operator = Column(String(100))
    direction = Column(Integer)
    stop_sequence = Column(Integer, nullable=False)
    station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    bus_stop_code = Column(String(30))
    route_distance_km = Column(DECIMAL(8, 3))
    wd_first_bus = Column(Time)
    wd_last_bus = Column(Time)
    sat_first_bus = Column(Time)
    sat_last_bus = Column(Time)
    sun_first_bus = Column(Time)
    sun_last_bus = Column(Time)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine")
    station = relationship("BusStation")


class BusVehicle(Base):
    __tablename__ = "bus_vehicle"

    vehicle_id = Column(BIGINT, primary_key=True)
    vehicle_code = Column(String(30), unique=True, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    service_no = Column(String(30))
    line_name = Column(String(100))
    current_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    next_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    next_station_name = Column(String(100))
    current_position_text = Column(String(150))
    longitude = Column(DECIMAL(10, 7))
    latitude = Column(DECIMAL(10, 7))
    speed_kph = Column(DECIMAL(6, 2))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    load_level = Column(String(30))
    load_code = Column(String(10))
    load_score = Column(DECIMAL(6, 2))
    operation_status = Column(String(20), nullable=False, default="normal", index=True)
    delay_minutes = Column(Integer, nullable=False, default=0)
    data_status = Column(String(20), nullable=False, default="estimated")
    last_reported_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine")
    current_station = relationship("BusStation", foreign_keys=[current_station_id])
    next_station = relationship("BusStation", foreign_keys=[next_station_id])


class BusEtaStatus(Base):
    __tablename__ = "bus_eta_status"

    eta_status_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    target_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    bus_stop_code = Column(String(30))
    query_time = Column(DateTime, nullable=False, index=True)
    eta_minutes = Column(DECIMAL(8, 2), nullable=False)
    arrival_time = Column(DateTime, index=True)
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2))
    speed_kph = Column(DECIMAL(6, 2))
    confidence = Column(DECIMAL(5, 4))
    data_source = Column(String(100), nullable=False, default="lta_bus_arrival")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine")
    target_station = relationship("BusStation")


class BusLoadStatus(Base):
    __tablename__ = "bus_load_status"

    load_status_id = Column(BIGINT, primary_key=True, autoincrement=True)
    vehicle_id = Column(BIGINT, nullable=False, index=True)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), index=True)
    bus_stop_code = Column(String(30))
    query_time = Column(DateTime, nullable=False, index=True)
    load_code = Column(String(10))
    load_level = Column(String(30), nullable=False)
    load_score = Column(DECIMAL(6, 2))
    load_rate = Column(DECIMAL(6, 4))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(DECIMAL(5, 4))
    data_source = Column(String(100), nullable=False, default="lta_bus_arrival")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine")
    station = relationship("BusStation")


class PassengerFlowTrend(Base):
    __tablename__ = "passenger_flow_trend"

    flow_record_id = Column(BIGINT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False)
    target_id = Column(BIGINT, nullable=False, index=True)
    bus_stop_code = Column(String(30))
    record_time = Column(DateTime, nullable=False, index=True)
    day_type = Column(String(20))
    tap_in_volume = Column(Integer, nullable=False, default=0)
    tap_out_volume = Column(Integer, nullable=False, default=0)
    total_flow = Column(Integer, nullable=False, default=0)
    flow_level = Column(String(20), index=True)
    data_source = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class PassengerFlowPrediction(Base):
    __tablename__ = "passenger_flow_prediction"

    prediction_id = Column(BIGINT, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False)
    target_id = Column(String(50), nullable=False, index=True)
    prediction_time = Column(DateTime, nullable=False, index=True)
    predict_time = Column(DateTime, nullable=False, index=True)
    predicted_flow = Column(Integer, nullable=False)
    crowd_level = Column(String(20), nullable=False)
    confidence = Column(DECIMAL(5, 4))
    model_version = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class MapRoadSegment(Base):
    __tablename__ = "map_road_segment"

    segment_id = Column(String(50), primary_key=True)
    segment_name = Column(String(150), nullable=False)
    line_id = Column(BIGINT, ForeignKey("bus_line.line_id"), nullable=False, index=True)
    service_no = Column(String(30))
    line_name = Column(String(100))
    direction = Column(Integer)
    stop_sequence = Column(Integer)
    start_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    start_station_name = Column(String(100))
    end_station_id = Column(BIGINT, ForeignKey("bus_station.station_id"), nullable=False, index=True)
    end_station_name = Column(String(100))
    start_lat = Column(DECIMAL(10, 7), nullable=False)
    start_lon = Column(DECIMAL(10, 7), nullable=False)
    end_lat = Column(DECIMAL(10, 7), nullable=False)
    end_lon = Column(DECIMAL(10, 7), nullable=False)
    segment_distance_km = Column(DECIMAL(8, 3))
    ride_time_minutes = Column(DECIMAL(8, 2))
    avg_speed_kph = Column(DECIMAL(6, 2))
    delay_minutes = Column(Integer, nullable=False, default=0)
    avg_passenger_flow = Column(DECIMAL(10, 2))
    flow_level = Column(String(20), index=True)
    path_coordinates = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    line = relationship("BusLine")
    start_station = relationship("BusStation", foreign_keys=[start_station_id])
    end_station = relationship("BusStation", foreign_keys=[end_station_id])


class LtaBusArrival(Base):
    __tablename__ = "lta_bus_arrival"

    arrival_record_id = Column(BIGINT, primary_key=True, autoincrement=True)
    query_time = Column(DateTime, nullable=False, index=True)
    station_id = Column(BIGINT, index=True)
    bus_stop_code = Column(String(30), index=True)
    service_no = Column(String(30), index=True)
    line_id = Column(BIGINT, index=True)
    line_name = Column(String(100))
    operator = Column(String(100))
    visit_order = Column(Integer)
    origin_stop_code = Column(String(30))
    destination_stop_code = Column(String(30))
    estimated_arrival = Column(DateTime)
    eta_minutes = Column(DECIMAL(8, 2))
    duration_ms = Column(BIGINT)
    monitored = Column(Integer)
    vehicle_id = Column(BIGINT, index=True)
    vehicle_latitude = Column(DECIMAL(10, 7))
    vehicle_longitude = Column(DECIMAL(10, 7))
    visit_number = Column(Integer)
    load_code = Column(String(10))
    load_level = Column(String(30))
    load_score = Column(DECIMAL(6, 2))
    load_rate = Column(DECIMAL(6, 4))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    bus_type = Column(String(30))
    feature = Column(String(30))
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2))
    speed_kph = Column(DECIMAL(6, 2))
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class TrafficSpeedBand(Base):
    __tablename__ = "traffic_speed_bands"

    traffic_record_id = Column(BIGINT, primary_key=True, autoincrement=True)
    query_time = Column(DateTime, nullable=False, index=True)
    link_id = Column(BIGINT, index=True)
    road_name = Column(String(150), index=True)
    road_category = Column(String(80))
    speed_band = Column(Integer, nullable=False, index=True)
    minimum_speed_kmh = Column(DECIMAL(6, 2))
    maximum_speed_kmh = Column(DECIMAL(6, 2))
    congestion_score = Column(DECIMAL(6, 4))
    heat_color = Column(String(20))
    start_lon = Column(DECIMAL(10, 7), nullable=False)
    start_lat = Column(DECIMAL(10, 7), nullable=False)
    end_lon = Column(DECIMAL(10, 7), nullable=False)
    end_lat = Column(DECIMAL(10, 7), nullable=False)
    line_coordinates = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
