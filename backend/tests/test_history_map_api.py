from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.bus_line import Base, BusLine, BusStation, LineStation
from app.models.history import PassengerFlowTrend
from app.services.history_service import get_passenger_flow_trend
from app.services.map_service import get_road_segments, get_map_lines, get_map_stations

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_history_map_api.db"


@pytest.fixture(scope="module")
def db_session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def test_data(db_session):
    line = BusLine(
        line_name="测试线路1",
        line_code="TST001",
        start_station="起点站",
        end_station="终点站",
        total_stations=3,
        distance_km=3.0,
        first_departure_time="06:00",
        last_departure_time="22:00",
        interval_minutes=10,
        status="active"
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(line)
    
    station1 = BusStation(
        station_name="站点A",
        station_code="STA001",
        latitude=31.2304,
        longitude=121.4737,
        address="测试地址1",
        zone="Zone1"
    )
    db_session.add(station1)
    db_session.commit()
    db_session.refresh(station1)
    
    station2 = BusStation(
        station_name="站点B",
        station_code="STA002",
        latitude=31.2310,
        longitude=121.4740,
        address="测试地址2",
        zone="Zone1"
    )
    db_session.add(station2)
    db_session.commit()
    db_session.refresh(station2)
    
    station3 = BusStation(
        station_name="站点C",
        station_code="STA003",
        latitude=31.2320,
        longitude=121.4750,
        address="测试地址3",
        zone="Zone1"
    )
    db_session.add(station3)
    db_session.commit()
    db_session.refresh(station3)
    
    ls1 = LineStation(line_id=line.line_id, station_id=station1.station_id, order_index=1, direction="forward")
    ls2 = LineStation(line_id=line.line_id, station_id=station2.station_id, order_index=2, direction="forward")
    ls3 = LineStation(line_id=line.line_id, station_id=station3.station_id, order_index=3, direction="forward")
    db_session.add_all([ls1, ls2, ls3])
    db_session.commit()
    
    flow1 = PassengerFlowTrend(
        target_type="station",
        target_id=station1.station_id,
        bus_stop_code="STA001",
        year_month="2024-01",
        hour=8,
        day_type="workday",
        tap_in_volume=150,
        tap_out_volume=80,
        total_flow=230,
        flow_level="high",
        data_source="metro"
    )
    db_session.add(flow1)
    db_session.commit()
    
    return {
        "line": line,
        "station1": station1,
        "station2": station2,
        "station3": station3
    }


def test_get_passenger_flow_trend(db_session, test_data):
    result = get_passenger_flow_trend(db_session)
    
    assert hasattr(result, 'items')
    assert hasattr(result, 'summary')
    assert isinstance(result.items, list)
    
    if result.items:
        item = result.items[0]
        assert hasattr(item, 'tap_in_volume')
        assert hasattr(item, 'tap_out_volume')
        assert hasattr(item, 'total_flow')
        assert hasattr(item, 'flow_level')
    
    assert hasattr(result.summary, 'total_tap_in')
    assert hasattr(result.summary, 'total_tap_out')
    assert hasattr(result.summary, 'total_flow')
    assert hasattr(result.summary, 'peak_hour')



def test_passenger_flow_uses_latest_month_and_line_station_mapping(db_session, test_data):
    station = test_data["station1"]
    line = test_data["line"]
    db_session.add_all(
        [
            PassengerFlowTrend(
                target_type="station",
                target_id=station.station_id,
                bus_stop_code=station.station_code,
                record_time=datetime(2025, 2, 1, 8),
                day_type="weekday",
                tap_in_volume=40,
                tap_out_volume=20,
                total_flow=60,
                flow_level="medium",
                data_source="test",
            ),
            PassengerFlowTrend(
                target_type="station",
                target_id=station.station_id,
                bus_stop_code=station.station_code,
                record_time=datetime(2025, 2, 1, 9),
                day_type="weekday",
                tap_in_volume=70,
                tap_out_volume=30,
                total_flow=100,
                flow_level="high",
                data_source="test",
            ),
        ]
    )
    db_session.commit()

    result = get_passenger_flow_trend(
        db_session,
        line_id=line.line_id,
        granularity="hour",
    )

    assert len(result.items) == 2
    assert result.summary.total_flow == 160
    assert result.summary.point_count == 2
    assert result.summary.granularity == "hour"
    assert all(item.target_type == "line" for item in result.items)
    assert all(item.record_time.year == 2025 for item in result.items)

def test_get_road_segments(db_session, test_data):
    result = get_road_segments(db_session)
    
    assert hasattr(result, 'segments')
    assert hasattr(result, 'total')
    assert isinstance(result.segments, list)
    
    if result.segments:
        segment = result.segments[0]
        assert hasattr(segment, 'segment_id')
        assert hasattr(segment, 'line_id')
        assert hasattr(segment, 'path_coordinates')
        assert isinstance(segment.path_coordinates, list)
        assert len(segment.path_coordinates) == 2
        assert isinstance(segment.path_coordinates[0], list)
        assert len(segment.path_coordinates[0]) == 2


def test_get_map_lines(db_session, test_data):
    result = get_map_lines(db_session)
    
    assert hasattr(result, 'lines')
    assert hasattr(result, 'total')
    assert isinstance(result.lines, list)
    
    if result.lines:
        line = result.lines[0]
        assert hasattr(line, 'line_id')
        assert hasattr(line, 'line_name')
        assert hasattr(line, 'path_coordinates')
        assert isinstance(line.path_coordinates, list)


def test_get_map_stations(db_session, test_data):
    result = get_map_stations(db_session)
    
    assert hasattr(result, 'stations')
    assert hasattr(result, 'total')
    assert isinstance(result.stations, list)
    
    if result.stations:
        station = result.stations[0]
        assert hasattr(station, 'station_id')
        assert hasattr(station, 'station_name')
        assert hasattr(station, 'latitude')
        assert hasattr(station, 'longitude')


def test_passenger_flow_boundary():
    from app.schemas.history_schema import PassengerFlowTrendDTO, LoadPredictionDTO
    
    flow = PassengerFlowTrendDTO(
        flow_record_id=1,
        target_type="station",
        target_id=1,
        bus_stop_code="S001",
        record_time=None,
        day_type="workday",
        tap_in_volume=100,
        tap_out_volume=80,
        total_flow=180,
        flow_level="medium",
        data_source="metro"
    )
    
    load = LoadPredictionDTO(
        load_prediction_id=1,
        vehicle_id=1,
        line_id=1,
        station_id=1,
        prediction_time=None,
        predicted_load_level="comfortable",
        load_score=0.75,
        predicted_load_rate=75.0,
        onboard_count=45,
        capacity=60,
        confidence=0.9,
        model_version="v1.0",
        created_at=None
    )
    
    assert hasattr(flow, 'tap_in_volume')
    assert hasattr(flow, 'tap_out_volume')
    assert hasattr(flow, 'total_flow')
    
    assert hasattr(load, 'onboard_count')
    assert hasattr(load, 'capacity')
    assert hasattr(load, 'predicted_load_rate')