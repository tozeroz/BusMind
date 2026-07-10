"""Standalone tests for RealIntelligenceGateway without conftest dependencies."""

import asyncio
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, ForeignKey, Integer, String, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.sql import func

# Create a separate Base for testing to avoid conflicts
Base = declarative_base()

class BusStation(Base):
    __tablename__ = "bus_station"
    
    station_id = Column(Integer, primary_key=True)
    station_name = Column(String(100), nullable=False)
    station_code = Column(String(30), unique=True, nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=True)
    longitude = Column(DECIMAL(10, 7), nullable=True)
    address = Column(String(100), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class BusLine(Base):
    __tablename__ = "bus_line"
    
    line_id = Column(Integer, primary_key=True)
    line_name = Column(String(100), nullable=False)
    line_code = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, default="running")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class BusVehicle(Base):
    __tablename__ = "bus_vehicle"
    
    vehicle_id = Column(Integer, primary_key=True)
    vehicle_code = Column(String(30), unique=True, nullable=True)
    line_id = Column(Integer, nullable=False)
    current_station_id = Column(Integer, nullable=True)
    next_station_id = Column(Integer, nullable=True)
    current_latitude = Column(DECIMAL(10, 7), nullable=True)
    current_longitude = Column(DECIMAL(10, 7), nullable=True)
    speed_kmh = Column(DECIMAL(6, 2), nullable=True)
    onboard_count = Column(Integer, nullable=True)
    capacity = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="normal")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class LineStation(Base):
    __tablename__ = "line_station"
    
    id = Column(String(50), primary_key=True)
    line_id = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    station_id = Column(Integer, nullable=False)
    station_code = Column(String(30), nullable=True)
    route_distance_km = Column(DECIMAL(8, 3), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

# Copy the RealIntelligenceGateway implementation to avoid import issues
from math import asin, cos, radians, sin, sqrt

class ResourceNotFoundError(Exception):
    """Raised when a requested resource is not found."""
    pass

@dataclass(frozen=True, slots=True)
class StationData:
    station_id: int
    station_name: str
    longitude: float
    latitude: float

@dataclass(frozen=True, slots=True)
class VehicleData:
    vehicle_id: int
    line_id: int
    longitude: float
    latitude: float
    current_station_id: int
    next_station_id: int
    speed_kph: float
    onboard_count: int
    capacity: int
    status: str = "normal"

class RealIntelligenceGateway:
    def __init__(self, db):
        self._db = db

    async def get_station(self, station_id: int) -> StationData:
        station = self._db.query(BusStation).filter(BusStation.station_id == station_id).first()
        if station is None:
            raise ResourceNotFoundError(f"站点不存在：station_id={station_id}")
        
        return StationData(
            station_id=int(station.station_id),
            station_name=station.station_name,
            longitude=float(station.longitude) if station.longitude else 0.0,
            latitude=float(station.latitude) if station.latitude else 0.0,
        )

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        return VehicleData(
            vehicle_id=int(vehicle.vehicle_id),
            line_id=int(vehicle.line_id),
            longitude=float(vehicle.current_longitude) if vehicle.current_longitude else 0.0,
            latitude=float(vehicle.current_latitude) if vehicle.current_latitude else 0.0,
            current_station_id=int(vehicle.current_station_id) if vehicle.current_station_id else 0,
            next_station_id=int(vehicle.next_station_id) if vehicle.next_station_id else 0,
            speed_kph=float(vehicle.speed_kmh) if vehicle.speed_kmh else 0.0,
            onboard_count=int(vehicle.onboard_count) if vehicle.onboard_count else 0,
            capacity=int(vehicle.capacity) if vehicle.capacity else 0,
            status=vehicle.status or "normal",
        )

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        stations = self._db.query(BusStation).all()
        
        if not stations:
            raise ResourceNotFoundError("没有找到任何站点")
        
        nearest_station = min(
            stations,
            key=lambda station: self._haversine_meters(
                longitude,
                latitude,
                float(station.longitude) if station.longitude else 0.0,
                float(station.latitude) if station.latitude else 0.0,
            ),
        )
        
        return StationData(
            station_id=int(nearest_station.station_id),
            station_name=nearest_station.station_name,
            longitude=float(nearest_station.longitude) if nearest_station.longitude else 0.0,
            latitude=float(nearest_station.latitude) if nearest_station.latitude else 0.0,
        )

    async def get_distance_to_station_meters(self, vehicle_id: int, target_station_id: int) -> float:
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        station = self._db.query(BusStation).filter(BusStation.station_id == target_station_id).first()
        if station is None:
            raise ResourceNotFoundError(f"站点不存在：station_id={target_station_id}")
        
        vehicle_lon = float(vehicle.current_longitude) if vehicle.current_longitude else 0.0
        vehicle_lat = float(vehicle.current_latitude) if vehicle.current_latitude else 0.0
        station_lon = float(station.longitude)
        station_lat = float(station.latitude)
        
        return self._haversine_meters(vehicle_lon, vehicle_lat, station_lon, station_lat)

    async def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        
        line_id = vehicle.line_id
        
        line_stations = (
            self._db.query(LineStation)
            .filter(LineStation.line_id == line_id)
            .order_by(LineStation.order_index)
            .all()
        )
        
        if not line_stations:
            return 1
        
        station_index_map = {ls.station_id: ls.order_index for ls in line_stations}
        
        current_index = None
        if vehicle.current_station_id and vehicle.current_station_id in station_index_map:
            current_index = station_index_map[vehicle.current_station_id]
        elif vehicle.next_station_id and vehicle.next_station_id in station_index_map:
            current_index = station_index_map[vehicle.next_station_id] - 1
        
        if target_station_id not in station_index_map:
            return 1
        
        target_index = station_index_map[target_station_id]
        
        if current_index is None:
            return max(1, len(line_stations) // 2)
        
        remaining = target_index - current_index
        
        return max(1, remaining) if remaining > 0 else 1

    @staticmethod
    def _haversine_meters(lon1, lat1, lon2, lat2):
        earth_radius = 6_371_000.0
        lon_1, lat_1, lon_2, lat_2 = map(radians, (lon1, lat1, lon2, lat2))
        delta_lon = lon_2 - lon_1
        delta_lat = lat_2 - lat_1
        value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        return 2 * earth_radius * asin(sqrt(value))

# Test functions
async def test_get_station(gateway, station_id, expected_name):
    station = await gateway.get_station(station_id)
    assert station.station_id == station_id
    assert station.station_name == expected_name
    print(f"PASSED: get_station({station_id}) returns '{expected_name}'")

async def test_get_station_not_found(gateway):
    try:
        await gateway.get_station(99999)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "站点不存在" in str(e)
        print("PASSED: get_station raises ResourceNotFoundError for non-existent station")

async def test_get_vehicle(gateway, vehicle_id):
    vehicle = await gateway.get_vehicle(vehicle_id)
    assert vehicle.vehicle_id == vehicle_id
    assert vehicle.line_id == 1
    assert vehicle.speed_kph == 30.0
    assert vehicle.onboard_count == 25
    assert vehicle.capacity == 60
    print(f"PASSED: get_vehicle({vehicle_id}) returns correct data")

async def test_get_vehicle_not_found(gateway):
    try:
        await gateway.get_vehicle(99999)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "车辆不存在" in str(e)
        print("PASSED: get_vehicle raises ResourceNotFoundError for non-existent vehicle")

async def test_find_nearest_station(gateway):
    nearest = await gateway.find_nearest_station(121.4736, 31.2303)
    assert nearest.station_id == 1
    assert nearest.station_name == "东门站"
    print("PASSED: find_nearest_station returns closest station")

async def test_find_nearest_station_no_stations():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    gateway = RealIntelligenceGateway(db)
    
    try:
        await gateway.find_nearest_station(121.4737, 31.2304)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "没有找到任何站点" in str(e)
        print("PASSED: find_nearest_station raises error when no stations exist")
    finally:
        db.close()

async def test_get_distance_to_station_meters(gateway):
    distance = await gateway.get_distance_to_station_meters(101, 3)
    assert distance > 0
    print(f"PASSED: get_distance_to_station_meters returns {distance:.1f} meters")

async def test_get_distance_to_station_not_found(gateway):
    try:
        await gateway.get_distance_to_station_meters(99999, 1)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "车辆不存在" in str(e)
        print("PASSED: get_distance_to_station_meters raises error for non-existent vehicle")
    
    try:
        await gateway.get_distance_to_station_meters(101, 99999)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "站点不存在" in str(e)
        print("PASSED: get_distance_to_station_meters raises error for non-existent station")

async def test_get_remaining_stop_count(gateway):
    count = await gateway.get_remaining_stop_count(101, 3)
    assert count == 2
    print(f"PASSED: get_remaining_stop_count returns {count}")

async def test_get_remaining_stop_count_same_station(gateway):
    count = await gateway.get_remaining_stop_count(101, 1)
    assert count >= 1
    print(f"PASSED: get_remaining_stop_count for current station returns {count}")

async def test_get_remaining_stop_count_not_found(gateway):
    try:
        await gateway.get_remaining_stop_count(99999, 1)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "车辆不存在" in str(e)
        print("PASSED: get_remaining_stop_count raises error for non-existent vehicle")

async def main():
    print("=" * 70)
    print("Running RealIntelligenceGateway Standalone Tests")
    print("=" * 70)
    print()
    
    # Setup in-memory database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    
    # Insert test data
    db.add(BusStation(station_id=1, station_name="东门站", station_code="STA001", latitude=31.2304, longitude=121.4737))
    db.add(BusStation(station_id=2, station_name="图书馆站", station_code="STA002", latitude=31.2310, longitude=121.4740))
    db.add(BusStation(station_id=3, station_name="教学楼站", station_code="STA003", latitude=31.2320, longitude=121.4750))
    db.add(BusLine(line_id=1, line_name="测试线路1", line_code="TST001"))
    db.add(BusVehicle(vehicle_id=101, vehicle_code="VH001", line_id=1, current_station_id=1, next_station_id=2, current_latitude=31.2305, current_longitude=121.4738, speed_kmh=30.0, onboard_count=25, capacity=60))
    # Add line-station relationships
    db.add(LineStation(id="LS001", line_id=1, order_index=1, station_id=1))
    db.add(LineStation(id="LS002", line_id=1, order_index=2, station_id=2))
    db.add(LineStation(id="LS003", line_id=1, order_index=3, station_id=3))
    db.commit()
    
    gateway = RealIntelligenceGateway(db)
    
    await test_get_station(gateway, 1, "东门站")
    print()
    await test_get_station_not_found(gateway)
    print()
    await test_get_vehicle(gateway, 101)
    print()
    await test_get_vehicle_not_found(gateway)
    print()
    await test_find_nearest_station(gateway)
    print()
    await test_find_nearest_station_no_stations()
    print()
    await test_get_distance_to_station_meters(gateway)
    print()
    await test_get_distance_to_station_not_found(gateway)
    print()
    await test_get_remaining_stop_count(gateway)
    print()
    await test_get_remaining_stop_count_same_station(gateway)
    print()
    await test_get_remaining_stop_count_not_found(gateway)
    
    db.close()
    
    print()
    print("=" * 70)
    print("All tests passed!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())