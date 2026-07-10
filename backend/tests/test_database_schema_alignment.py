from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.schema_check import validate_database_schema
from app.models import Base
from app.schemas.bus_schema import BusLineCreateRequest
from app.schemas.vehicle_schema import VehicleCreateRequest
from app.schemas.user_schema import UserFavoriteRequest
from app.services.user_service import (
    FAVORITE_QUERY_TYPE,
    add_user_favorite,
    get_user_favorites,
    get_user_history,
)
from app.models.user import QueryHistory, User


EXPECTED_COLUMNS = {
    "user_account": {
        "user_id", "username", "password_hash", "nickname", "role", "status",
        "created_at", "updated_at", "last_login_at",
    },
    "user_query_history": {
        "history_id", "user_id", "query_type", "origin_name", "origin_longitude",
        "origin_latitude", "destination_name", "destination_longitude",
        "destination_latitude", "selected_route_id", "query_content", "result_summary",
        "created_at",
    },
    "location_poi": {
        "location_id", "location_name", "location_type", "longitude", "latitude",
        "address", "nearest_station_id", "status", "created_at", "updated_at",
    },
    "bus_station": {
        "station_id", "bus_stop_code", "station_name", "road_name", "longitude",
        "latitude", "status", "created_at", "updated_at",
    },
    "bus_line": {
        "line_id", "service_no", "line_name", "operator", "direction", "category",
        "origin_station_id", "origin_stop_code", "destination_station_id",
        "destination_stop_code", "am_peak_freq", "am_offpeak_freq", "pm_peak_freq",
        "pm_offpeak_freq", "avg_service_frequency", "loop_desc", "status",
        "created_at", "updated_at",
    },
    "line_station": {
        "line_station_id", "line_id", "service_no", "line_name", "operator", "direction",
        "station_id", "bus_stop_code", "stop_sequence", "route_distance_km",
        "wd_first_bus", "wd_last_bus", "sat_first_bus", "sat_last_bus", "sun_first_bus",
        "sun_last_bus", "created_at", "updated_at",
    },
    "bus_vehicle": {
        "vehicle_id", "vehicle_code", "line_id", "service_no", "line_name",
        "current_station_id", "next_station_id", "next_station_name", "current_position_text",
        "longitude", "latitude", "speed_kph", "onboard_count", "capacity", "load_level",
        "load_code", "load_score", "operation_status", "delay_minutes", "data_status",
        "last_reported_at", "created_at", "updated_at",
    },
    "bus_eta_status": {
        "eta_status_id", "vehicle_id", "line_id", "target_station_id", "bus_stop_code",
        "query_time", "eta_minutes", "arrival_time", "vehicle_to_stop_distance_m", "speed_kph",
        "confidence", "data_source", "created_at", "updated_at",
    },
    "bus_load_status": {
        "load_status_id", "vehicle_id", "line_id", "station_id", "bus_stop_code", "query_time",
        "load_code", "load_level", "load_score", "load_rate", "onboard_count", "capacity",
        "confidence", "data_source", "created_at", "updated_at",
    },
    "passenger_flow_trend": {
        "flow_record_id", "target_type", "target_id", "bus_stop_code", "record_time", "day_type",
        "tap_in_volume", "tap_out_volume", "total_flow", "flow_level", "data_source", "created_at",
    },
    "passenger_flow_prediction": {
        "prediction_id", "target_type", "target_id", "prediction_time", "predict_time",
        "predicted_flow", "crowd_level", "confidence", "model_version", "created_at",
    },
    "map_road_segment": {
        "segment_id", "segment_name", "line_id", "service_no", "line_name", "direction",
        "stop_sequence", "start_station_id", "start_station_name", "end_station_id",
        "end_station_name", "start_lat", "start_lon", "end_lat", "end_lon",
        "segment_distance_km", "ride_time_minutes", "avg_speed_kph", "delay_minutes",
        "avg_passenger_flow", "flow_level", "path_coordinates", "created_at", "updated_at",
    },
    "lta_bus_arrival": {
        "arrival_record_id", "query_time", "station_id", "bus_stop_code", "service_no", "line_id",
        "line_name", "operator", "visit_order", "origin_stop_code", "destination_stop_code",
        "estimated_arrival", "eta_minutes", "duration_ms", "monitored", "vehicle_id",
        "vehicle_latitude", "vehicle_longitude", "visit_number", "load_code", "load_level",
        "load_score", "load_rate", "onboard_count", "capacity", "bus_type", "feature",
        "vehicle_to_stop_distance_m", "speed_kph", "created_at",
    },
    "traffic_speed_bands": {
        "traffic_record_id", "query_time", "link_id", "road_name", "road_category", "speed_band",
        "minimum_speed_kmh", "maximum_speed_kmh", "congestion_score", "heat_color", "start_lon",
        "start_lat", "end_lon", "end_lat", "line_coordinates", "created_at",
    },
}


def test_all_orm_tables_and_physical_columns_match_final_schema() -> None:
    actual = {
        table.name: {column.name for column in table.columns}
        for table in Base.metadata.sorted_tables
    }
    assert actual == EXPECTED_COLUMNS


def test_all_models_share_one_metadata_and_can_create_together() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("""
            CREATE VIEW v_map_station AS
            SELECT station_id, bus_stop_code, station_name, road_name, longitude, latitude,
                   0 AS line_count, 0 AS service_count, '' AS line_ids,
                   '' AS line_names, '' AS service_nos
            FROM bus_station
        """))
    assert validate_database_schema(engine) == []


def test_legacy_status_inputs_are_normalized_to_database_enums() -> None:
    line = BusLineCreateRequest(
        line_name="测试线",
        line_code="T001",
        start_station="01001",
        end_station="01002",
        status="active",
    )
    vehicle = VehicleCreateRequest(
        vehicle_code="V001",
        line_id=1,
        status="running",
    )
    assert line.status == "running"
    assert vehicle.status == "normal"


def test_favorite_api_uses_reserved_query_history_records() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        user = User(username="tester", password_hash="hash", role="passenger", status="active")
        session.add(user)
        session.commit()
        session.refresh(user)

        history = QueryHistory(
            user_id=user.user_id,
            query_type="route_search",
            query_content="normal history",
        )
        session.add(history)
        session.commit()

        favorite = add_user_favorite(
            session,
            user.user_id,
            UserFavoriteRequest(favorite_type="line", target_id=1, target_name="1号线"),
        )
        assert favorite.target_id == 1

        records = session.query(QueryHistory).order_by(QueryHistory.history_id).all()
        assert records[-1].query_type == FAVORITE_QUERY_TYPE
        assert records[-1].query_content == "line"

        favorites = get_user_favorites(session, user.user_id)
        histories = get_user_history(session, user.user_id)
        assert favorites.total == 1
        assert histories.total == 1
        assert histories.histories[0].query_type == "route_search"
