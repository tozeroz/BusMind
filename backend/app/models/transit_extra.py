"""ORM models for the remaining tables in database/schema/init_busmind.sql."""

from sqlalchemy import Column, DateTime, DECIMAL, ForeignKey, Integer, JSON, String, TEXT, text
from sqlalchemy.sql import func

from app.db.base import BIGINT_COMPAT, Base


class LocationPoi(Base):
    __tablename__ = "location_poi"

    location_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    location_name = Column(String(100), nullable=False, index=True)
    location_type = Column(String(30), nullable=False, index=True)
    longitude = Column(DECIMAL(10, 7), nullable=False)
    latitude = Column(DECIMAL(10, 7), nullable=False)
    address = Column(String(255), nullable=True)
    nearest_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    status = Column(String(20), nullable=False, default="active", server_default=text("'active'"))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class MapRoadSegment(Base):
    __tablename__ = "map_road_segment"

    segment_id = Column(String(50), primary_key=True)
    segment_name = Column(String(150), nullable=False)
    line_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_line.line_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    service_no = Column(String(30), nullable=True)
    line_name = Column(String(100), nullable=True)
    direction = Column(Integer, nullable=True)
    stop_sequence = Column(Integer, nullable=True)
    start_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    start_station_name = Column(String(100), nullable=True)
    end_station_id = Column(
        BIGINT_COMPAT,
        ForeignKey("bus_station.station_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    end_station_name = Column(String(100), nullable=True)
    start_lat = Column(DECIMAL(10, 7), nullable=False)
    start_lon = Column(DECIMAL(10, 7), nullable=False)
    end_lat = Column(DECIMAL(10, 7), nullable=False)
    end_lon = Column(DECIMAL(10, 7), nullable=False)
    segment_distance_km = Column(DECIMAL(8, 3), nullable=True)
    ride_time_minutes = Column(DECIMAL(8, 2), nullable=True)
    avg_speed_kph = Column(DECIMAL(6, 2), nullable=True)
    delay_minutes = Column(Integer, nullable=False, default=0, server_default=text("0"))
    avg_passenger_flow = Column(DECIMAL(10, 2), nullable=True)
    flow_level = Column(String(20), nullable=True, index=True)
    path_coordinates = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class LtaBusArrival(Base):
    __tablename__ = "lta_bus_arrival"

    arrival_record_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    query_time = Column(DateTime, nullable=False)
    station_id = Column(BIGINT_COMPAT, nullable=True)
    bus_stop_code = Column(String(30), nullable=True)
    service_no = Column(String(30), nullable=True)
    line_id = Column(BIGINT_COMPAT, nullable=True)
    line_name = Column(String(100), nullable=True)
    operator = Column(String(100), nullable=True)
    visit_order = Column(Integer, nullable=True)
    origin_stop_code = Column(String(30), nullable=True)
    destination_stop_code = Column(String(30), nullable=True)
    estimated_arrival = Column(DateTime, nullable=True)
    eta_minutes = Column(DECIMAL(8, 2), nullable=True)
    duration_ms = Column(BIGINT_COMPAT, nullable=True)
    monitored = Column(Integer, nullable=True)
    vehicle_id = Column(BIGINT_COMPAT, nullable=True)
    vehicle_latitude = Column(DECIMAL(10, 7), nullable=True)
    vehicle_longitude = Column(DECIMAL(10, 7), nullable=True)
    visit_number = Column(Integer, nullable=True)
    load_code = Column(String(10), nullable=True)
    load_level = Column(String(30), nullable=True)
    load_score = Column(DECIMAL(6, 2), nullable=True)
    load_rate = Column(DECIMAL(6, 4), nullable=True)
    onboard_count = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    bus_type = Column(String(30), nullable=True)
    feature = Column(String(30), nullable=True)
    vehicle_to_stop_distance_m = Column(DECIMAL(10, 2), nullable=True)
    speed_kph = Column(DECIMAL(6, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class TrafficSpeedBand(Base):
    __tablename__ = "traffic_speed_bands"

    traffic_record_id = Column(BIGINT_COMPAT, primary_key=True, autoincrement=True)
    query_time = Column(DateTime, nullable=False, index=True)
    link_id = Column(BIGINT_COMPAT, nullable=True)
    road_name = Column(String(150), nullable=True, index=True)
    road_category = Column(String(80), nullable=True)
    speed_band = Column(Integer, nullable=False, index=True)
    minimum_speed_kmh = Column(DECIMAL(6, 2), nullable=True)
    maximum_speed_kmh = Column(DECIMAL(6, 2), nullable=True)
    congestion_score = Column(DECIMAL(6, 4), nullable=True)
    heat_color = Column(String(20), nullable=True)
    start_lon = Column(DECIMAL(10, 7), nullable=False)
    start_lat = Column(DECIMAL(10, 7), nullable=False)
    end_lon = Column(DECIMAL(10, 7), nullable=False)
    end_lat = Column(DECIMAL(10, 7), nullable=False)
    line_coordinates = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


__all__ = ["LocationPoi", "MapRoadSegment", "LtaBusArrival", "TrafficSpeedBand"]
