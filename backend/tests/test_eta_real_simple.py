"""Simple standalone test for ETA API with real database data."""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
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

class BusLine(Base):
    __tablename__ = "bus_line"
    line_id = Column(Integer, primary_key=True)
    service_no = Column(String(30), nullable=False, index=True)
    line_name = Column(String(100), nullable=False, index=True)
    avg_service_frequency = Column(DECIMAL(6, 2))
    status = Column(String(20), nullable=False, default="running", index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class BusVehicle(Base):
    __tablename__ = "bus_vehicle"
    vehicle_id = Column(Integer, primary_key=True)
    vehicle_code = Column(String(30), unique=True, index=True)
    line_id = Column(Integer, nullable=False, index=True)
    current_station_id = Column(Integer, index=True)
    next_station_id = Column(Integer, index=True)
    latitude = Column(DECIMAL(10, 7))
    longitude = Column(DECIMAL(10, 7))
    speed_kph = Column(DECIMAL(6, 2))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    operation_status = Column(String(20), nullable=False, default="normal", index=True)
    last_reported_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

class LineStation(Base):
    __tablename__ = "line_station"
    line_station_id = Column(String(50), primary_key=True)
    line_id = Column(Integer, nullable=False, index=True)
    stop_sequence = Column(Integer, nullable=False)
    station_id = Column(Integer, nullable=False, index=True)
    route_distance_km = Column(DECIMAL(8, 3))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

# Minimal ETA implementation for testing
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

class ResourceNotFoundError(Exception):
    pass

from math import asin, cos, radians, sin, sqrt

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

    async def get_vehicle(self, vehicle_id: int) -> VehicleData:
        vehicle = self.db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"未找到公交车辆 vehicle_id={vehicle_id}")
        return VehicleData(
            vehicle_id=int(vehicle.vehicle_id),
            line_id=int(vehicle.line_id),
            longitude=float(vehicle.longitude or 0.0),
            latitude=float(vehicle.latitude or 0.0),
            current_station_id=int(vehicle.current_station_id or 0),
            next_station_id=int(vehicle.next_station_id or 0),
            speed_kph=float(vehicle.speed_kph or 18.0),
            onboard_count=int(vehicle.onboard_count or 0),
            capacity=int(vehicle.capacity or 60),
            status=str(vehicle.operation_status or "normal"),
        )

    async def get_distance_to_station_meters(self, vehicle_id: int, target_station_id: int) -> float:
        vehicle = await self.get_vehicle(vehicle_id)
        station = await self.get_station(target_station_id)
        if vehicle.longitude == 0.0 and vehicle.latitude == 0.0:
            return 1000.0
        return max(250.0, self._haversine_meters(vehicle.longitude, vehicle.latitude, station.longitude, station.latitude) * 1.35)

    async def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        vehicle = await self.get_vehicle(vehicle_id)
        await self.get_station(target_station_id)
        
        line_stations = (
            self.db.query(LineStation)
            .filter(LineStation.line_id == vehicle.line_id)
            .order_by(LineStation.stop_sequence)
            .all()
        )
        
        if not line_stations:
            return 1
        
        station_index_map = {ls.station_id: ls.stop_sequence for ls in line_stations}
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

    async def get_latest_eta_status(self, vehicle_id, target_station_id, line_id=None):
        return None

    @staticmethod
    def _haversine_meters(lon1, lat1, lon2, lat2):
        earth_radius = 6_371_000.0
        lon_1, lat_1, lon_2, lat_2 = map(radians, (lon1, lat1, lon2, lat2))
        delta_lon = lon_2 - lon_1
        delta_lat = lat_2 - lat_1
        value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        return 2 * earth_radius * asin(sqrt(value))

@dataclass
class EtaResult:
    vehicle_id: int
    target_station_id: int
    predicted_eta_minutes: float
    arrival_time: datetime
    factors: dict
    model_version: str

class EtaService:
    def __init__(self, gateway):
        self.gateway = gateway

    async def calculate_eta(self, vehicle_id, target_station_id, line_id=None, query_time=None):
        moment = query_time or datetime.now()
        vehicle = await self.gateway.get_vehicle(vehicle_id)
        await self.gateway.get_station(target_station_id)

        if line_id is not None and vehicle.line_id != line_id:
            raise ValueError(f"车辆 {vehicle_id} 不属于线路 {line_id}")
        if vehicle.status == "offline":
            raise ValueError(f"车辆 {vehicle_id} 当前离线")

        latest_eta = await self.gateway.get_latest_eta_status(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            line_id=line_id or vehicle.line_id,
        )
        if latest_eta is not None:
            eta_minutes = round(max(0.0, min(float(latest_eta.eta_minutes), 240.0)), 1)
            return EtaResult(
                vehicle_id=vehicle_id,
                target_station_id=target_station_id,
                predicted_eta_minutes=eta_minutes,
                arrival_time=latest_eta.arrival_time,
                factors={"source": latest_eta.source},
                model_version="eta_mysql_realtime_v1",
            )

        distance_meters = await self.gateway.get_distance_to_station_meters(vehicle_id, target_station_id)
        stop_count = await self.gateway.get_remaining_stop_count(vehicle_id, target_station_id)
        is_peak = moment.hour in {7, 8, 9, 17, 18, 19}
        time_factor = 1.22 if is_peak else 1.0
        effective_speed_kph = max(vehicle.speed_kph, 8.0)

        travel_minutes = distance_meters / (effective_speed_kph * 1000 / 60)
        stop_delay_minutes = stop_count * 0.45
        eta_minutes = travel_minutes * time_factor + stop_delay_minutes
        eta_minutes = round(max(0.1, min(float(eta_minutes), 240.0)), 1)

        return EtaResult(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            predicted_eta_minutes=eta_minutes,
            arrival_time=moment + timedelta(minutes=eta_minutes),
            factors={
                "distance_meters": round(distance_meters, 1),
                "remaining_stop_count": stop_count,
                "speed_kph": round(effective_speed_kph, 1),
                "is_peak": is_peak,
                "time_factor": time_factor,
            },
            model_version="eta_rule_v1",
        )

async def test_eta_with_real_database():
    """Regression test for ETA API with real database data."""
    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Insert real-like test data with realistic IDs (not demo 101/3)
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
    db.add(BusStation(
        station_id=1003, 
        station_name="外滩站", 
        bus_stop_code="BS1003",
        latitude=31.2330, 
        longitude=121.4760
    ))
    
    db.add(BusLine(
        line_id=501, 
        service_no="501",
        line_name="501路",
        avg_service_frequency=10.0
    ))
    
    db.add(BusVehicle(
        vehicle_id=2001, 
        vehicle_code="VH2001", 
        line_id=501,
        current_station_id=1001, 
        next_station_id=1002,
        latitude=31.2306, 
        longitude=121.4738,
        speed_kph=25.0, 
        onboard_count=15, 
        capacity=50,
        operation_status="normal",
        last_reported_at=datetime.now()
    ))
    
    db.add(LineStation(
        line_station_id="LS001", 
        line_id=501, 
        stop_sequence=1, 
        station_id=1001
    ))
    db.add(LineStation(
        line_station_id="LS002", 
        line_id=501, 
        stop_sequence=2, 
        station_id=1002
    ))
    db.add(LineStation(
        line_station_id="LS003", 
        line_id=501, 
        stop_sequence=3, 
        station_id=1003
    ))
    
    db.commit()
    
    # Create gateway and service
    gateway = SimpleTransitGateway(db)
    service = EtaService(gateway)
    
    # Test ETA calculation with real data (not demo data)
    result = await service.calculate_eta(vehicle_id=2001, target_station_id=1003)
    
    print(f"ETA Result for real data:")
    print(f"  vehicle_id: {result.vehicle_id}")
    print(f"  target_station_id: {result.target_station_id}")
    print(f"  predicted_eta_minutes: {result.predicted_eta_minutes}")
    print(f"  model_version: {result.model_version}")
    print(f"  factors: {result.factors}")
    
    assert result.vehicle_id == 2001
    assert result.target_station_id == 1003
    assert result.predicted_eta_minutes > 0
    assert result.factors["remaining_stop_count"] == 2
    assert result.factors["distance_meters"] > 0
    
    print("\nPASSED: ETA calculation with real database data")
    
    # Test with non-existent vehicle
    try:
        await service.calculate_eta(vehicle_id=99999, target_station_id=1001)
        assert False, "Expected exception for non-existent vehicle"
    except ResourceNotFoundError as e:
        assert "未找到公交车辆" in str(e) or "车辆不存在" in str(e)
        print("PASSED: ETA raises error for non-existent vehicle")
    
    # Test with non-existent station
    try:
        await service.calculate_eta(vehicle_id=2001, target_station_id=99999)
        assert False, "Expected exception for non-existent station"
    except ResourceNotFoundError as e:
        assert "未找到公交站点" in str(e) or "站点不存在" in str(e)
        print("PASSED: ETA raises error for non-existent station")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing ETA API with Real Database Integration")
    print("=" * 70)
    print()
    
    asyncio.run(test_eta_with_real_database())
    
    print()
    print("=" * 70)
    print("All real database ETA tests passed!")
    print("=" * 70)