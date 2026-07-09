import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.bus_line import Base, BusLine, BusStation, LineStation
from app.services.bus_service import (
    get_line_list,
    get_line_by_id,
    get_line_stations,
    get_station_list,
    get_station_by_id,
    create_line,
    create_station,
    add_line_station
)
from app.schemas.bus_schema import (
    BusLineCreateRequest,
    BusStationCreateRequest,
    LineStationCreateRequest
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_bus_api.db"


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
    line_request = BusLineCreateRequest(
        line_name="测试线路1",
        line_code="TST001",
        start_station="起点站",
        end_station="终点站",
        total_stations=5,
        distance_km=5.5,
        first_departure_time="06:00",
        last_departure_time="22:00",
        interval_minutes=10
    )
    line = create_line(db_session, line_request)
    
    station1_request = BusStationCreateRequest(
        station_name="站点A",
        station_code="STA001",
        latitude=31.2304,
        longitude=121.4737,
        address="测试地址1",
        zone="Zone1"
    )
    station1 = create_station(db_session, station1_request)
    
    station2_request = BusStationCreateRequest(
        station_name="站点B",
        station_code="STA002",
        latitude=31.2310,
        longitude=121.4740,
        address="测试地址2",
        zone="Zone1"
    )
    station2 = create_station(db_session, station2_request)
    
    ls_request1 = LineStationCreateRequest(
        line_id=line.line_id,
        station_id=station1.station_id,
        order_index=1,
        direction="forward"
    )
    add_line_station(db_session, ls_request1)
    
    ls_request2 = LineStationCreateRequest(
        line_id=line.line_id,
        station_id=station2.station_id,
        order_index=2,
        direction="forward"
    )
    add_line_station(db_session, ls_request2)
    
    return {
        "line": line,
        "station1": station1,
        "station2": station2
    }


def test_get_line_list(db_session):
    result = get_line_list(db_session, page=1, limit=10)
    assert hasattr(result, 'lines')
    assert hasattr(result, 'total')
    assert isinstance(result.lines, list)
    assert isinstance(result.total, int)


def test_get_line_by_id(db_session, test_data):
    line_id = test_data["line"].line_id
    result = get_line_by_id(db_session, line_id)
    assert result is not None
    assert result.line_id == line_id
    assert result.line_name == "测试线路1"
    assert hasattr(result, 'stations')
    assert isinstance(result.stations, list)


def test_get_line_stations(db_session, test_data):
    line_id = test_data["line"].line_id
    result = get_line_stations(db_session, line_id)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].station.station_name == "站点A"
    assert result[1].station.station_name == "站点B"


def test_get_station_list(db_session):
    result = get_station_list(db_session, page=1, limit=10)
    assert hasattr(result, 'stations')
    assert hasattr(result, 'total')
    assert isinstance(result.stations, list)
    assert isinstance(result.total, int)


def test_get_station_by_id(db_session, test_data):
    station_id = test_data["station1"].station_id
    result = get_station_by_id(db_session, station_id)
    assert result is not None
    assert result.station_id == station_id
    assert result.station_name == "站点A"
    assert hasattr(result, 'latitude')
    assert hasattr(result, 'longitude')


def test_get_station_not_found(db_session):
    result = get_station_by_id(db_session, 99999)
    assert result is None


def test_get_line_not_found(db_session):
    result = get_line_by_id(db_session, 99999)
    assert result is None


def test_line_list_pagination(db_session):
    for i in range(15):
        line_request = BusLineCreateRequest(
            line_name=f"测试线路{i}",
            line_code=f"TST{i:03d}",
            start_station="起点",
            end_station="终点"
        )
        create_line(db_session, line_request)
    
    result = get_line_list(db_session, page=1, limit=10)
    assert result.total == 16
    assert len(result.lines) == 10
    
    result2 = get_line_list(db_session, page=2, limit=10)
    assert len(result2.lines) == 6


def test_station_search(db_session):
    result = get_station_list(db_session, station_name="站点A")
    assert result.total == 1
    assert result.stations[0].station_name == "站点A"


def test_line_search(db_session):
    result = get_line_list(db_session, line_name="测试线路1")
    assert result.total >= 1
    assert any(line.line_name == "测试线路1" for line in result.lines)