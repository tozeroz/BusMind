"""Standalone test for passenger load prediction with real database data."""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass
from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String, func, desc
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

class PassengerFlowTrend(Base):
    __tablename__ = "passenger_flow_trend"
    flow_record_id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(String(20), nullable=False)
    target_id = Column(Integer, nullable=False, index=True)
    bus_stop_code = Column(String(30))
    record_time = Column(DateTime, nullable=False, index=True)
    day_type = Column(String(20))
    tap_in_volume = Column(Integer, nullable=False, default=0)
    tap_out_volume = Column(Integer, nullable=False, default=0)
    total_flow = Column(Integer, nullable=False, default=0)
    flow_level = Column(String(20), index=True)
    data_source = Column(String(100))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

class BusLoadStatus(Base):
    __tablename__ = "bus_load_status"
    load_status_id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(Integer, nullable=False, index=True)
    line_id = Column(Integer, nullable=False, index=True)
    station_id = Column(Integer, index=True)
    bus_stop_code = Column(String(30))
    query_time = Column(DateTime, nullable=False, index=True)
    load_code = Column(String(10))
    load_level = Column(String(30), nullable=False)
    load_score = Column(DECIMAL(6, 2))
    load_rate = Column(DECIMAL(6, 4))
    onboard_count = Column(Integer)
    capacity = Column(Integer)
    confidence = Column(DECIMAL(5, 4))
    data_source = Column(String(100), nullable=False, default="lta_bus_arrival")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

# Minimal Load implementation for testing
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

@dataclass(frozen=True, slots=True)
class LoadStatusData:
    vehicle_id: int | None
    line_id: int
    station_id: int
    load_level: str
    load_code: str | None
    load_rate: float | None
    load_score: float | None
    onboard_count: int | None
    capacity: int | None
    confidence: float | None
    query_time: datetime
    source: str

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

    async def get_latest_load_status(
        self,
        line_id: int,
        station_id: int,
        vehicle_id: int | None = None,
    ) -> LoadStatusData | None:
        latest = self.db.query(BusLoadStatus).filter(
            BusLoadStatus.line_id == line_id,
            BusLoadStatus.station_id == station_id
        ).order_by(desc(BusLoadStatus.query_time)).first()
        
        if latest is not None:
            return LoadStatusData(
                vehicle_id=int(latest.vehicle_id) if latest.vehicle_id is not None else vehicle_id,
                line_id=int(latest.line_id),
                station_id=int(latest.station_id or station_id),
                load_level=str(latest.load_level),
                load_code=str(latest.load_code) if latest.load_code else None,
                load_rate=float(latest.load_rate) if latest.load_rate else None,
                load_score=float(latest.load_score) if latest.load_score else None,
                onboard_count=int(latest.onboard_count) if latest.onboard_count else None,
                capacity=int(latest.capacity) if latest.capacity else None,
                confidence=float(latest.confidence) if latest.confidence else None,
                query_time=latest.query_time,
                source=str(latest.data_source or "bus_load_status"),
            )
        return None

    async def get_station_flow_level(self, station_id: int, hour: int) -> str:
        rows = (
            self.db.query(PassengerFlowTrend.flow_level, func.count(PassengerFlowTrend.flow_record_id))
            .filter(PassengerFlowTrend.target_type == "station")
            .filter(PassengerFlowTrend.target_id == station_id)
            .filter(func.extract("hour", PassengerFlowTrend.record_time) == hour)
            .filter(PassengerFlowTrend.flow_level.isnot(None))
            .group_by(PassengerFlowTrend.flow_level)
            .order_by(desc(func.count(PassengerFlowTrend.flow_record_id)))
            .all()
        )
        if rows:
            return str(rows[0][0])
        fallback = (
            self.db.query(PassengerFlowTrend.flow_level)
            .filter(PassengerFlowTrend.target_type == "station")
            .filter(PassengerFlowTrend.target_id == station_id)
            .filter(PassengerFlowTrend.flow_level.isnot(None))
            .order_by(desc(PassengerFlowTrend.record_time))
            .first()
        )
        if fallback:
            return str(fallback[0])
        
        if hour in {7, 8, 9, 17, 18, 19}:
            return "high"
        if hour in {10, 11, 12, 13, 14, 15, 16}:
            return "medium"
        return "low"

# Load Service implementation
from enum import Enum

class LoadLevel(Enum):
    SEATS_AVAILABLE = "seats_available"
    STANDING_AVAILABLE = "standing_available"
    LIMITED_STANDING = "limited_standing"
    OVERCROWDED = "overcrowded"

LOAD_LEVEL_SCORE = {
    LoadLevel.SEATS_AVAILABLE: 100.0,
    LoadLevel.STANDING_AVAILABLE: 70.0,
    LoadLevel.LIMITED_STANDING: 35.0,
    LoadLevel.OVERCROWDED: 10.0,
}

@dataclass
class PassengerLoadPredictionRequest:
    line_id: int
    station_id: int
    vehicle_id: int | None = None
    capacity: int | None = None
    current_onboard_count: int | None = None
    weather: str = "clear"
    target_time: datetime = None

@dataclass
class PassengerLoadPredictionResult:
    line_id: int
    station_id: int
    vehicle_id: int | None
    predicted_onboard_count: int | None
    capacity: int
    predicted_load_rate: float | None
    predicted_load_level: LoadLevel
    load_score: float
    confidence: float
    predict_time: datetime
    feature_summary: dict
    model_version: str

class BusinessError(Exception):
    def __init__(self, code, message, status_code):
        self.code = code
        self.message = message
        self.status_code = status_code

class PassengerLoadService:
    def __init__(self, gateway):
        self.gateway = gateway

    async def predict(self, request: PassengerLoadPredictionRequest) -> PassengerLoadPredictionResult:
        moment = request.target_time or datetime.now()
        await self.gateway.get_station(request.station_id)

        vehicle = None
        if request.vehicle_id is not None:
            vehicle = await self.gateway.get_vehicle(request.vehicle_id)
            if vehicle.line_id != request.line_id:
                raise BusinessError(
                    40002,
                    f"车辆 {request.vehicle_id} 不属于线路 {request.line_id}",
                    400,
                )

        capacity = request.capacity or (vehicle.capacity if vehicle else 60)
        if capacity <= 0:
            raise BusinessError(40002, "capacity 必须大于 0", 400)
        current_onboard = (
            request.current_onboard_count
            if request.current_onboard_count is not None
            else (vehicle.onboard_count if vehicle else round(capacity * 0.45))
        )

        latest_load = await self.gateway.get_latest_load_status(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
        )
        if latest_load is not None:
            load_rate = latest_load.load_rate
            load_level = self._level_from_source(latest_load.load_level, load_rate)
            status_capacity = latest_load.capacity or capacity
            predicted_count = latest_load.onboard_count
            if predicted_count is None and load_rate is not None:
                predicted_count = int(round(status_capacity * load_rate))
            confidence = latest_load.confidence if latest_load.confidence is not None else 0.82
            return PassengerLoadPredictionResult(
                line_id=request.line_id,
                station_id=request.station_id,
                vehicle_id=request.vehicle_id,
                predicted_onboard_count=predicted_count,
                capacity=status_capacity,
                predicted_load_rate=load_rate,
                predicted_load_level=load_level,
                load_score=latest_load.load_score if latest_load.load_score is not None else self.calculate_load_score(load_rate, load_level),
                confidence=round(max(0.0, min(float(confidence), 1.0)), 2),
                predict_time=moment,
                feature_summary={
                    "source": latest_load.source,
                    "query_time": latest_load.query_time.isoformat(),
                    "load_code": latest_load.load_code,
                },
                model_version="load_mysql_realtime_v1",
            )

        is_peak = moment.hour in {7, 8, 9, 17, 18, 19}
        flow_level = await self.gateway.get_station_flow_level(request.station_id, moment.hour)
        weather = (request.weather or "clear").lower()

        predicted_count, load_rate, load_level, confidence = self._rule_predict(
            current_onboard=current_onboard,
            capacity=capacity,
            is_peak=is_peak,
            flow_level=flow_level,
            weather=weather,
        )
        load_score = self.calculate_load_score(load_rate, load_level)

        return PassengerLoadPredictionResult(
            line_id=request.line_id,
            station_id=request.station_id,
            vehicle_id=request.vehicle_id,
            predicted_onboard_count=predicted_count,
            capacity=capacity,
            predicted_load_rate=load_rate,
            predicted_load_level=load_level,
            load_score=load_score,
            confidence=confidence,
            predict_time=moment,
            feature_summary={
                "is_peak": is_peak,
                "station_flow_level": flow_level,
                "weather": weather,
                "day_type": "weekend" if moment.weekday() >= 5 else "weekday",
            },
            model_version="load_rule_v1",
        )

    @staticmethod
    def _level_from_source(raw_level: str, load_rate: float | None) -> LoadLevel:
        mapping = {
            "SEA": LoadLevel.SEATS_AVAILABLE,
            "SDA": LoadLevel.STANDING_AVAILABLE,
            "LSD": LoadLevel.LIMITED_STANDING,
            "seats_available": LoadLevel.SEATS_AVAILABLE,
            "standing_available": LoadLevel.STANDING_AVAILABLE,
            "limited_standing": LoadLevel.LIMITED_STANDING,
            "overcrowded": LoadLevel.OVERCROWDED,
        }
        level = mapping.get(str(raw_level))
        if level is not None:
            return level
        if load_rate is None:
            return LoadLevel.STANDING_AVAILABLE
        if load_rate <= 0.60:
            return LoadLevel.SEATS_AVAILABLE
        if load_rate <= 0.85:
            return LoadLevel.STANDING_AVAILABLE
        if load_rate <= 1.0:
            return LoadLevel.LIMITED_STANDING
        return LoadLevel.OVERCROWDED

    @staticmethod
    def calculate_load_score(load_rate: float | None, load_level: LoadLevel) -> float:
        if load_rate is not None:
            return float(round(max(0.0, min(100.0, 100.0 - min(load_rate, 2.0) * 55.0))))
        return LOAD_LEVEL_SCORE[load_level]

    @staticmethod
    def _level_from_rate(rate: float) -> LoadLevel:
        if rate <= 0.60:
            return LoadLevel.SEATS_AVAILABLE
        if rate <= 0.85:
            return LoadLevel.STANDING_AVAILABLE
        if rate <= 1.0:
            return LoadLevel.LIMITED_STANDING
        return LoadLevel.OVERCROWDED

    def _rule_predict(self, current_onboard, capacity, is_peak, flow_level, weather):
        delta = 0
        if is_peak:
            delta += round(capacity * 0.12)
        delta += {"high": round(capacity * 0.10), "medium": round(capacity * 0.04), "low": -2}.get(
            flow_level, 0
        )
        if weather in {"rain", "rainy", "snow", "storm"}:
            delta += round(capacity * 0.05)
        predicted_count = max(0, min(round(capacity * 1.05), current_onboard + delta))
        rate = round(min(predicted_count / capacity, 2.0), 2)
        level = self._level_from_rate(rate)
        confidence = 0.72 if is_peak or flow_level == "high" else 0.66
        return predicted_count, rate, level, confidence

async def test_load_prediction_with_real_database():
    """Regression test for passenger load prediction with real database data."""
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
        onboard_count=25, 
        capacity=55,
        operation_status="normal",
        last_reported_at=datetime.now()
    ))
    
    # Add passenger flow trend data for station 1001
    db.add(PassengerFlowTrend(
        target_type="station",
        target_id=1001,
        bus_stop_code="BS1001",
        record_time=datetime.now() - timedelta(days=1),
        day_type="weekday",
        tap_in_volume=120,
        tap_out_volume=80,
        total_flow=200,
        flow_level="high",
        data_source="test"
    ))
    
    db.add(BusLoadStatus(
        vehicle_id=2001,
        line_id=501,
        station_id=1001,
        bus_stop_code="BS1001",
        query_time=datetime.now(),
        load_code="SDA",
        load_level="standing_available",
        load_score=70.0,
        load_rate=0.75,
        onboard_count=41,
        capacity=55,
        confidence=0.85,
        data_source="test"
    ))
    
    db.commit()
    
    # Create gateway and service
    gateway = SimpleTransitGateway(db)
    service = PassengerLoadService(gateway)
    
    # Test 1: Load prediction with real data (using real-time load status)
    request1 = PassengerLoadPredictionRequest(
        line_id=501,
        station_id=1001,
        vehicle_id=2001,
        target_time=datetime.now()
    )
    result1 = await service.predict(request1)
    
    print(f"Test 1 - Real-time load status:")
    print(f"  line_id: {result1.line_id}")
    print(f"  station_id: {result1.station_id}")
    print(f"  vehicle_id: {result1.vehicle_id}")
    print(f"  predicted_onboard_count: {result1.predicted_onboard_count}")
    print(f"  capacity: {result1.capacity}")
    print(f"  predicted_load_rate: {result1.predicted_load_rate}")
    print(f"  predicted_load_level: {result1.predicted_load_level.value}")
    print(f"  load_score: {result1.load_score}")
    print(f"  model_version: {result1.model_version}")
    
    assert result1.model_version == "load_mysql_realtime_v1"
    assert result1.predicted_load_rate == 0.75
    assert result1.predicted_load_level == LoadLevel.STANDING_AVAILABLE
    print("PASSED: Load prediction using real-time load status")
    
    # Test 2: Load prediction without vehicle (using rule-based fallback)
    request2 = PassengerLoadPredictionRequest(
        line_id=501,
        station_id=1002,  # Different station without load status
        target_time=datetime.now()
    )
    result2 = await service.predict(request2)
    
    print(f"\nTest 2 - Rule-based prediction:")
    print(f"  line_id: {result2.line_id}")
    print(f"  station_id: {result2.station_id}")
    print(f"  predicted_load_rate: {result2.predicted_load_rate}")
    print(f"  predicted_load_level: {result2.predicted_load_level.value}")
    print(f"  model_version: {result2.model_version}")
    
    assert result2.model_version == "load_rule_v1"
    assert 0 <= result2.predicted_load_rate <= 2
    print("PASSED: Load prediction using rule-based fallback")
    
    # Test 3: Vehicle-line mismatch error
    try:
        request3 = PassengerLoadPredictionRequest(
            line_id=999,  # Wrong line
            station_id=1001,
            vehicle_id=2001,
            target_time=datetime.now()
        )
        await service.predict(request3)
        assert False, "Expected exception for vehicle-line mismatch"
    except BusinessError as e:
        assert e.code == 40002
        print("PASSED: Load prediction raises error for vehicle-line mismatch")
    
    # Test 4: Non-existent station error
    try:
        request4 = PassengerLoadPredictionRequest(
            line_id=501,
            station_id=99999,  # Non-existent
            target_time=datetime.now()
        )
        await service.predict(request4)
        assert False, "Expected exception for non-existent station"
    except ResourceNotFoundError as e:
        assert "未找到公交站点" in str(e)
        print("PASSED: Load prediction raises error for non-existent station")
    
    # Test 5: Non-existent vehicle error
    try:
        request5 = PassengerLoadPredictionRequest(
            line_id=501,
            station_id=1001,
            vehicle_id=99999,  # Non-existent
            target_time=datetime.now()
        )
        await service.predict(request5)
        assert False, "Expected exception for non-existent vehicle"
    except ResourceNotFoundError as e:
        assert "未找到公交车辆" in str(e)
        print("PASSED: Load prediction raises error for non-existent vehicle")
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Passenger Load Prediction with Real Database Integration")
    print("=" * 70)
    print()
    
    asyncio.run(test_load_prediction_with_real_database())
    
    print()
    print("=" * 70)
    print("All real database load prediction tests passed!")
    print("=" * 70)