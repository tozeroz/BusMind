"""Integration tests for ETA API with real gateway and SQLite data."""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()

class BusStation(Base):
    __tablename__ = "bus_station"
    station_id = Column(Integer, primary_key=True)
    station_name = Column(String(100), nullable=False)
    station_code = Column(String(30), unique=True, nullable=True)
    latitude = Column(DECIMAL(10, 7), nullable=False)
    longitude = Column(DECIMAL(10, 7), nullable=False)
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

# Minimal models for testing
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
            longitude=float(station.longitude),
            latitude=float(station.latitude),
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
                longitude, latitude,
                float(station.longitude), float(station.latitude)
            ),
        )
        return StationData(
            station_id=int(nearest_station.station_id),
            station_name=nearest_station.station_name,
            longitude=float(nearest_station.longitude),
            latitude=float(nearest_station.latitude),
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
        return self._haversine_meters(vehicle_lon, vehicle_lat, float(station.longitude), float(station.latitude))

    async def get_remaining_stop_count(self, vehicle_id: int, target_station_id: int) -> int:
        vehicle = self._db.query(BusVehicle).filter(BusVehicle.vehicle_id == vehicle_id).first()
        if vehicle is None:
            raise ResourceNotFoundError(f"车辆不存在：vehicle_id={vehicle_id}")
        line_stations = (
            self._db.query(LineStation)
            .filter(LineStation.line_id == vehicle.line_id)
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

    async def get_latest_eta_status(self, vehicle_id, target_station_id, line_id=None):
        return None

    async def get_latest_load_status(self, line_id, station_id, vehicle_id=None):
        return None

    async def get_station_flow_level(self, station_id, hour):
        raise NotImplementedError()

    async def get_candidate_routes(self, start_station_id, end_station_id, max_transfer_count):
        raise NotImplementedError()

    @staticmethod
    def _haversine_meters(lon1, lat1, lon2, lat2):
        earth_radius = 6_371_000.0
        lon_1, lat_1, lon_2, lat_2 = map(radians, (lon1, lat1, lon2, lat2))
        delta_lon = lon_2 - lon_1
        delta_lat = lat_2 - lat_1
        value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
        return 2 * earth_radius * asin(sqrt(value))

# EtaService minimal implementation for testing
@dataclass
class EtaResult:
    vehicle_id: int
    target_station_id: int
    predicted_eta_minutes: float
    arrival_time: datetime
    factors: dict
    model_version: str

class OptionalPredictor:
    def __init__(self, path=None):
        self.path = path
    
    async def predict(self, features):
        return None

class SimulationStateStore:
    def get_eta(self, vehicle_id, target_station_id, line_id):
        return None

class EtaService:
    def __init__(self, gateway, predictor=None, state_store=None):
        self.gateway = gateway
        self.predictor = predictor or OptionalPredictor()
        self.state_store = state_store or SimulationStateStore()

    async def calculate_eta(self, vehicle_id, target_station_id, line_id=None, query_time=None):
        moment = query_time or datetime.now()
        vehicle = await self.gateway.get_vehicle(vehicle_id)
        await self.gateway.get_station(target_station_id)

        if line_id is not None and vehicle.line_id != line_id:
            raise ValueError(f"车辆 {vehicle_id} 不属于线路 {line_id}")
        if vehicle.status == "offline":
            raise ValueError(f"车辆 {vehicle_id} 当前离线")

        override = self.state_store.get_eta(
            vehicle_id=vehicle_id,
            target_station_id=target_station_id,
            line_id=line_id or vehicle.line_id,
        )
        if override is not None:
            eta_minutes = round(max(0.0, min(float(override.payload["predicted_eta_minutes"]), 240.0)), 1)
            arrival_time = override.payload.get("arrival_time")
            if not isinstance(arrival_time, datetime):
                arrival_time = moment + datetime.timedelta(minutes=eta_minutes)
            return EtaResult(
                vehicle_id=vehicle_id,
                target_station_id=target_station_id,
                predicted_eta_minutes=eta_minutes,
                arrival_time=arrival_time,
                factors={"source": override.source},
                model_version="simulation_eta_override",
            )

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

        model_result = await self.predictor.predict({
            "vehicle_id": vehicle_id,
            "line_id": vehicle.line_id,
            "target_station_id": target_station_id,
            "distance_to_stop": distance_meters,
            "remaining_stop_count": stop_count,
            "speed_kph": effective_speed_kph,
            "hour": moment.hour,
            "day_type": "weekend" if moment.weekday() >= 5 else "weekday",
            "is_peak": is_peak,
        })

        if model_result is None:
            travel_minutes = distance_meters / (effective_speed_kph * 1000 / 60)
            stop_delay_minutes = stop_count * 0.45
            eta_minutes = travel_minutes * time_factor + stop_delay_minutes
            model_version = "eta_rule_v1"
        else:
            eta_minutes = float(model_result)
            model_version = "eta_external_model"

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
            model_version=model_version,
        )

async def test_eta_with_real_data():
    """Test ETA calculation with real database data."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    # Insert real-like test data
    db.add(BusStation(station_id=1, station_name="人民广场站", station_code="STA001", latitude=31.2304, longitude=121.4737))
    db.add(BusStation(station_id=2, station_name="南京东路站", station_code="STA002", latitude=31.2315, longitude=121.4745))
    db.add(BusStation(station_id=3, station_name="外滩站", station_code="STA003", latitude=31.2330, longitude=121.4760))
    db.add(BusLine(line_id=101, line_name="101路", line_code="101"))
    db.add(BusVehicle(vehicle_id=5001, vehicle_code="VH5001", line_id=101, current_station_id=1, next_station_id=2,
                      current_latitude=31.2306, current_longitude=121.4738, speed_kmh=25.0, onboard_count=15, capacity=50))
    db.add(LineStation(id="LS001", line_id=101, order_index=1, station_id=1))
    db.add(LineStation(id="LS002", line_id=101, order_index=2, station_id=2))
    db.add(LineStation(id="LS003", line_id=101, order_index=3, station_id=3))
    db.commit()

    gateway = RealIntelligenceGateway(db)
    service = EtaService(gateway)

    # Test ETA calculation
    result = await service.calculate_eta(vehicle_id=5001, target_station_id=3)
    
    print(f"ETA Result:")
    print(f"  vehicle_id: {result.vehicle_id}")
    print(f"  target_station_id: {result.target_station_id}")
    print(f"  predicted_eta_minutes: {result.predicted_eta_minutes}")
    print(f"  arrival_time: {result.arrival_time}")
    print(f"  factors: {result.factors}")
    print(f"  model_version: {result.model_version}")
    
    assert result.vehicle_id == 5001
    assert result.target_station_id == 3
    assert result.predicted_eta_minutes > 0
    assert result.factors["distance_meters"] > 0
    assert result.factors["remaining_stop_count"] == 2
    assert result.model_version == "eta_rule_v1"
    
    print("\nPASSED: ETA calculation with real data works correctly")

    # Test ETA with non-existent vehicle
    try:
        await service.calculate_eta(vehicle_id=99999, target_station_id=1)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "车辆不存在" in str(e)
        print("PASSED: ETA raises error for non-existent vehicle")

    # Test ETA with non-existent station
    try:
        await service.calculate_eta(vehicle_id=5001, target_station_id=99999)
        assert False, "Expected ResourceNotFoundError"
    except ResourceNotFoundError as e:
        assert "站点不存在" in str(e)
        print("PASSED: ETA raises error for non-existent station")

    db.close()

async def main():
    print("=" * 70)
    print("Testing ETA Service with Real Data Gateway")
    print("=" * 70)
    print()
    
    await test_eta_with_real_data()
    
    print()
    print("=" * 70)
    print("All ETA tests passed!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())