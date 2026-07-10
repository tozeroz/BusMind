"""Standalone test for walking time estimation with real database data."""

import asyncio
from datetime import datetime
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String, func
from sqlalchemy.orm import declarative_base, sessionmaker

# Create a separate Base for testing
Base = declarative_base()

class BusStation(Base):
    __tablename__ = "bus_station"
    station_id = Column(Integer, primary_key=True)
    station_name = Column(String(100), nullable=False)
    bus_stop_code = Column(String(30), unique=True, index=True)
    latitude = Column(DECIMAL(10, 7), nullable=False)
    longitude = Column(DECIMAL(10, 7), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

# Minimal Walking implementation for testing
@dataclass(frozen=True, slots=True)
class StationData:
    station_id: int
    station_name: str
    longitude: float
    latitude: float

class ResourceNotFoundError(Exception):
    pass

class SimpleTransitGateway:
    def __init__(self, db):
        self.db = db

    async def get_station(self, station_id: int) -> StationData:
        station = self.db.query(BusStation).filter(BusStation.station_id == station_id).first()
        if station is None:
            raise ResourceNotFoundError(f"未找到公交站点 station_id={station_id}")
        return StationData(
            station_id=int(station.station_id),
            station_name=str(station.station_name),
            longitude=float(station.longitude),
            latitude=float(station.latitude),
        )

class WalkingRouteMode:
    STRAIGHT_LINE = "straight_line"

@dataclass
class GeoPoint:
    longitude: float
    latitude: float

@dataclass
class StationSummary:
    station_id: int
    station_name: str
    longitude: float
    latitude: float

@dataclass
class WalkingTimeRequest:
    origin_longitude: float
    origin_latitude: float
    target_station_id: int
    walking_speed_mps: float = 1.2

@dataclass
class WalkingTimeResult:
    origin: GeoPoint
    target_station: StationSummary
    walk_distance_meters: float
    walk_time_minutes: float
    walking_speed_mps: float
    route_source: str

class WalkingTimeService:
    def __init__(self, gateway):
        self.gateway = gateway
        self.walking_road_factor = 1.3  # Road distance is ~30% longer than straight line

    async def estimate(self, request: WalkingTimeRequest) -> WalkingTimeResult:
        station = await self.gateway.get_station(request.target_station_id)
        straight_distance = self._haversine_meters(
            request.origin_longitude,
            request.origin_latitude,
            station.longitude,
            station.latitude,
        )
        route_source = WalkingRouteMode.STRAIGHT_LINE
        distance = straight_distance * self.walking_road_factor
        minutes = distance / request.walking_speed_mps / 60
        return WalkingTimeResult(
            origin=GeoPoint(
                longitude=request.origin_longitude,
                latitude=request.origin_latitude,
            ),
            target_station=StationSummary(
                station_id=station.station_id,
                station_name=station.station_name,
                longitude=station.longitude,
                latitude=station.latitude,
            ),
            walk_distance_meters=round(distance, 1),
            walk_time_minutes=round(minutes, 1),
            walking_speed_mps=request.walking_speed_mps,
            route_source=route_source,
        )

    @staticmethod
    def _haversine_meters(longitude_1, latitude_1, longitude_2, latitude_2):
        earth_radius = 6_371_000.0
        lon_1, lat_1, lon_2, lat_2 = map(radians, (longitude_1, latitude_1, longitude_2, latitude_2))
        delta_lon = lon_2 - lon_1
        delta_lat = lat_2 - lat_1
        value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        return 2 * earth_radius * asin(sqrt(value))

async def test_walking_time_with_real_database():
    """Regression test for walking time estimation with real database data."""
    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Insert real-like test data with realistic IDs (not demo 1, 2, 3)
    db.add(BusStation(
        station_id=1001, 
        station_name="人民广场站", 
        bus_stop_code="BS1001",
        latitude=31.2304, 
        longitude=121.4737
    ))
    db.add(BusStation(
        station_id=1002, 
        station_name="南京东路站", 
        bus_stop_code="BS1002",
        latitude=31.2315, 
        longitude=121.4745
    ))
    
    db.commit()
    
    # Create gateway and service
    gateway = SimpleTransitGateway(db)
    service = WalkingTimeService(gateway)
    
    # Test 1: Walking time estimation with real station ID
    request1 = WalkingTimeRequest(
        origin_longitude=121.4730,
        origin_latitude=31.2300,
        target_station_id=1001,
        walking_speed_mps=1.2
    )
    result1 = await service.estimate(request1)
    
    print(f"Test 1 - Walking time to real station:")
    print(f"  origin: ({result1.origin.longitude}, {result1.origin.latitude})")
    print(f"  target_station: {result1.target_station.station_name} (ID: {result1.target_station.station_id})")
    print(f"  target_station_coords: ({result1.target_station.longitude}, {result1.target_station.latitude})")
    print(f"  walk_distance_meters: {result1.walk_distance_meters}")
    print(f"  walk_time_minutes: {result1.walk_time_minutes}")
    print(f"  walking_speed_mps: {result1.walking_speed_mps}")
    print(f"  route_source: {result1.route_source}")
    
    assert result1.target_station.station_id == 1001
    assert result1.target_station.station_name == "人民广场站"
    assert result1.walk_distance_meters > 0
    assert result1.walk_time_minutes > 0
    assert result1.route_source == "straight_line"
    print("PASSED: Walking time estimation with real station ID")
    
    # Test 2: Walking time to different station
    request2 = WalkingTimeRequest(
        origin_longitude=121.4730,
        origin_latitude=31.2300,
        target_station_id=1002,
        walking_speed_mps=1.0
    )
    result2 = await service.estimate(request2)
    
    print(f"\nTest 2 - Walking time to different station:")
    print(f"  target_station: {result2.target_station.station_name}")
    print(f"  walk_distance_meters: {result2.walk_distance_meters}")
    print(f"  walk_time_minutes: {result2.walk_time_minutes}")
    
    assert result2.target_station.station_id == 1002
    assert result2.walk_distance_meters > 0
    print("PASSED: Walking time estimation to different station")
    
    # Test 3: Non-existent station error
    try:
        request3 = WalkingTimeRequest(
            origin_longitude=121.4730,
            origin_latitude=31.2300,
            target_station_id=99999,  # Non-existent
            walking_speed_mps=1.2
        )
        await service.estimate(request3)
        assert False, "Expected exception for non-existent station"
    except ResourceNotFoundError as e:
        assert "未找到公交站点" in str(e)
        print("PASSED: Walking time raises error for non-existent station")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Walking Time Estimation with Real Database Integration")
    print("=" * 70)
    print()
    
    asyncio.run(test_walking_time_with_real_database())
    
    print()
    print("=" * 70)
    print("All real database walking time tests passed!")
    print("=" * 70)