import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.bus_line import Base, BusLine, BusStation
from app.models.bus_vehicle import BusVehicle
from app.services.vehicle_service import (
    get_vehicle_list,
    get_vehicle_by_id,
    create_vehicle,
    get_vehicles_by_line
)
from app.schemas.vehicle_schema import (
    VehicleCreateRequest
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_vehicle_api.db"


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
        total_stations=5,
        distance_km=5.5,
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
    
    vehicle_request = VehicleCreateRequest(
        vehicle_code="VH001",
        line_id=line.line_id,
        current_latitude=31.2305,
        current_longitude=121.4738,
        current_station_id=station1.station_id,
        next_station_id=station2.station_id,
        progress=25.5,
        status="running",
        speed_kmh=30.0,
        direction_deg=90.0,
        onboard_count=25,
        capacity=60
    )
    vehicle = create_vehicle(db_session, vehicle_request)
    
    return {
        "line": line,
        "station1": station1,
        "station2": station2,
        "vehicle": vehicle
    }


def test_get_vehicle_list(db_session):
    result = get_vehicle_list(db_session, page=1, limit=10)
    assert hasattr(result, 'vehicles')
    assert hasattr(result, 'total')
    assert isinstance(result.vehicles, list)
    assert isinstance(result.total, int)


def test_get_vehicle_by_id(db_session, test_data):
    vehicle_id = test_data["vehicle"].vehicle_id
    result = get_vehicle_by_id(db_session, vehicle_id)
    assert result is not None
    assert result.vehicle_id == vehicle_id
    assert result.vehicle_code == "VH001"
    assert result.line_id == test_data["line"].line_id
    assert result.current_latitude == 31.2305
    assert result.current_longitude == 121.4738
    assert result.latitude == 31.2305
    assert result.longitude == 121.4738
    assert result.current_station_id == test_data["station1"].station_id
    assert result.current_station_name == "站点A"
    assert result.next_station_id == test_data["station2"].station_id
    assert result.next_station_name == "站点B"
    assert result.progress == 25.5
    assert result.status == "running"
    assert result.speed_kmh == 30.0
    assert result.speed == 30.0
    assert result.onboard_count == 25
    assert result.capacity == 60
    assert result.load_rate > 0


def test_get_vehicle_not_found(db_session):
    result = get_vehicle_by_id(db_session, 99999)
    assert result is None


def test_get_vehicles_by_line(db_session, test_data):
    line_id = test_data["line"].line_id
    result = get_vehicles_by_line(db_session, line_id)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert result[0].line_id == line_id
    assert hasattr(result[0], 'latitude')
    assert hasattr(result[0], 'longitude')
    assert hasattr(result[0], 'update_time')


def test_vehicle_list_pagination(db_session, test_data):
    for i in range(15):
        vehicle_request = VehicleCreateRequest(
            vehicle_code=f"VH{i:03d}",
            line_id=test_data["line"].line_id,
            current_latitude=31.2300 + i * 0.0001,
            current_longitude=121.4730 + i * 0.0001
        )
        create_vehicle(db_session, vehicle_request)
    
    result = get_vehicle_list(db_session, page=1, limit=10)
    assert result.total >= 16
    assert len(result.vehicles) == 10
    
    result2 = get_vehicle_list(db_session, page=2, limit=10)
    assert len(result2.vehicles) >= 6


def test_vehicle_compatible_fields(db_session, test_data):
    vehicle_id = test_data["vehicle"].vehicle_id
    result = get_vehicle_by_id(db_session, vehicle_id)
    
    assert hasattr(result, 'latitude')
    assert hasattr(result, 'longitude')
    assert hasattr(result, 'speed')
    assert hasattr(result, 'update_time')
    assert hasattr(result, 'current_station_id')
    assert hasattr(result, 'current_station_name')
    assert hasattr(result, 'progress')