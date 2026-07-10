import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import Base as UserBase
from app.models.bus_line import Base as BusLineBase, BusLine, BusStation, LineStation
from app.models.bus_vehicle import Base as VehicleBase, BusVehicle
from app.models.history import Base as HistoryBase, PassengerFlowTrend
from app.services.bus_service import (
    get_line_list,
    get_line_by_id,
    get_line_stations,
    get_station_list,
    get_station_by_id
)
from app.services.vehicle_service import (
    get_vehicle_list,
    get_vehicle_by_id,
    get_vehicles_by_line
)
from app.services.map_service import (
    get_map_stations,
    get_road_segments,
    get_map_lines
)
from app.services.history_service import get_passenger_flow_trend

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_a_api.db"


@pytest.fixture(scope="function")
def db_engine():
    return create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})


@pytest.fixture(scope="function")
def db_session(db_engine):
    UserBase.metadata.create_all(bind=db_engine)
    BusLineBase.metadata.create_all(bind=db_engine)
    VehicleBase.metadata.create_all(bind=db_engine)
    HistoryBase.metadata.create_all(bind=db_engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    db = TestingSessionLocal()
    
    yield db
    
    db.rollback()
    db.close()
    HistoryBase.metadata.drop_all(bind=db_engine)
    VehicleBase.metadata.drop_all(bind=db_engine)
    BusLineBase.metadata.drop_all(bind=db_engine)
    UserBase.metadata.drop_all(bind=db_engine)


@pytest.fixture(scope="function")
def test_data(db_session):
    line = BusLine(
        line_id=1,
        line_name="测试线路A",
        line_code="TEST001",
        start_station="起点站",
        end_station="终点站",
        total_stations=3,
        distance_km=5.0,
        first_departure_time="06:00",
        last_departure_time="22:00",
        interval_minutes=10,
        status="active"
    )
    db_session.add(line)
    
    station1 = BusStation(
        station_id=1,
        station_name="站点1",
        station_code="ST001",
        latitude=31.2304,
        longitude=121.4737,
        address="地址1",
        zone="ZoneA"
    )
    db_session.add(station1)
    
    station2 = BusStation(
        station_id=2,
        station_name="站点2",
        station_code="ST002",
        latitude=31.2310,
        longitude=121.4740,
        address="地址2",
        zone="ZoneA"
    )
    db_session.add(station2)
    
    station3 = BusStation(
        station_id=3,
        station_name="站点3",
        station_code="ST003",
        latitude=31.2320,
        longitude=121.4750,
        address="地址3",
        zone="ZoneA"
    )
    db_session.add(station3)
    
    ls1 = LineStation(id=1, line_id=1, station_id=1, order_index=1, direction="forward")
    ls2 = LineStation(id=2, line_id=1, station_id=2, order_index=2, direction="forward")
    ls3 = LineStation(id=3, line_id=1, station_id=3, order_index=3, direction="forward")
    db_session.add_all([ls1, ls2, ls3])
    
    vehicle = BusVehicle(
        vehicle_id=1,
        vehicle_code="VH001",
        line_id=1,
        current_latitude=31.2307,
        current_longitude=121.4739,
        current_station_id=1,
        next_station_id=2,
        progress=25.0,
        status="running",
        speed_kmh=30.0,
        direction_deg=90.0,
        onboard_count=25,
        capacity=60
    )
    db_session.add(vehicle)
    
    flow = PassengerFlowTrend(
        flow_record_id=1,
        target_type="station",
        target_id=1,
        bus_stop_code="ST001",
        year_month="2024-01",
        hour=8,
        day_type="workday",
        tap_in_volume=150,
        tap_out_volume=80,
        total_flow=230,
        flow_level="high",
        data_source="metro"
    )
    db_session.add(flow)
    
    db_session.commit()
    
    return {
        "line": line,
        "station1": station1,
        "station2": station2,
        "station3": station3,
        "vehicle": vehicle,
        "flow": flow
    }


class TestLinesService:
    def test_get_line_list(self, db_session):
        result = get_line_list(db_session, page=1, limit=10)
        assert hasattr(result, 'lines')
        assert hasattr(result, 'total')
        assert isinstance(result.lines, list)
    
    def test_get_line_by_id(self, db_session, test_data):
        line_id = test_data["line"].line_id
        result = get_line_by_id(db_session, line_id)
        assert result is not None
        assert result.line_id == line_id
        assert result.line_name == "测试线路A"
    
    def test_get_line_not_found(self, db_session):
        result = get_line_by_id(db_session, 99999)
        assert result is None
    
    def test_get_line_stations(self, db_session, test_data):
        line_id = test_data["line"].line_id
        result = get_line_stations(db_session, line_id)
        assert isinstance(result, list)
        assert len(result) == 3


class TestStationsService:
    def test_get_station_list(self, db_session):
        result = get_station_list(db_session, page=1, limit=10)
        assert hasattr(result, 'stations')
        assert hasattr(result, 'total')
        assert isinstance(result.stations, list)
    
    def test_get_station_by_id(self, db_session, test_data):
        station_id = test_data["station1"].station_id
        result = get_station_by_id(db_session, station_id)
        assert result is not None
        assert result.station_id == station_id
        assert result.station_name == "站点1"
    
    def test_get_station_not_found(self, db_session):
        result = get_station_by_id(db_session, 99999)
        assert result is None
    
    def test_station_search(self, db_session, test_data):
        result = get_station_list(db_session, station_name="站点1")
        assert result.total >= 1


class TestVehiclesService:
    def test_get_vehicle_list(self, db_session):
        result = get_vehicle_list(db_session, page=1, limit=10)
        assert hasattr(result, 'vehicles')
        assert hasattr(result, 'total')
        assert isinstance(result.vehicles, list)
    
    def test_get_vehicle_by_id(self, db_session, test_data):
        vehicle_id = test_data["vehicle"].vehicle_id
        result = get_vehicle_by_id(db_session, vehicle_id)
        assert result is not None
        assert result.vehicle_id == vehicle_id
    
    def test_get_vehicle_not_found(self, db_session):
        result = get_vehicle_by_id(db_session, 99999)
        assert result is None
    
    def test_get_vehicles_by_line(self, db_session, test_data):
        line_id = test_data["line"].line_id
        vehicles = get_vehicles_by_line(db_session, line_id)
        assert isinstance(vehicles, list)
        assert len(vehicles) >= 1


class TestMapService:
    def test_get_map_stations(self, db_session):
        result = get_map_stations(db_session)
        assert hasattr(result, 'stations')
        assert hasattr(result, 'total')
        assert isinstance(result.stations, list)
    
    def test_get_road_segments(self, db_session):
        result = get_road_segments(db_session)
        assert hasattr(result, 'segments')
        assert hasattr(result, 'total')
        assert isinstance(result.segments, list)
        if result.total > 0:
            segment = result.segments[0]
            assert hasattr(segment, 'path_coordinates')
            assert isinstance(segment.path_coordinates, list)
    
    def test_get_map_lines(self, db_session):
        result = get_map_lines(db_session)
        assert hasattr(result, 'lines')
        assert hasattr(result, 'total')
        assert isinstance(result.lines, list)
        if result.total > 0:
            line = result.lines[0]
            assert hasattr(line, 'path_coordinates')


class TestHistoryService:
    def test_get_passenger_flow_trend(self, db_session):
        result = get_passenger_flow_trend(db_session)
        assert hasattr(result, 'items')
        assert hasattr(result, 'summary')
        assert isinstance(result.items, list)
    
    def test_passenger_flow_summary(self, db_session):
        result = get_passenger_flow_trend(db_session)
        assert hasattr(result.summary, 'total_tap_in')
        assert hasattr(result.summary, 'total_tap_out')
        assert hasattr(result.summary, 'total_flow')


class TestDataIntegrity:
    def test_line_station_relationship(self, db_session, test_data):
        line = db_session.query(BusLine).filter(BusLine.line_id == test_data["line"].line_id).first()
        assert line is not None
        assert line.line_name == "测试线路A"
        
        stations = db_session.query(LineStation).filter(LineStation.line_id == line.line_id).all()
        assert len(stations) == 3
    
    def test_vehicle_line_relationship(self, db_session, test_data):
        vehicle = db_session.query(BusVehicle).filter(BusVehicle.vehicle_id == test_data["vehicle"].vehicle_id).first()
        assert vehicle is not None
        assert vehicle.line_id == test_data["line"].line_id
        assert vehicle.status == "running"
    
    def test_flow_station_relationship(self, db_session, test_data):
        flow = db_session.query(PassengerFlowTrend).filter(
            PassengerFlowTrend.target_id == test_data["station1"].station_id
        ).first()
        assert flow is not None
        assert flow.tap_in_volume == 150
        assert flow.tap_out_volume == 80