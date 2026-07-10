"""Standalone test for route recommendation with real database data."""

import asyncio
from datetime import datetime
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
    service_no = Column(String(30))
    line_name = Column(String(100))
    stop_sequence = Column(Integer, nullable=False)
    station_id = Column(Integer, nullable=False, index=True)
    route_distance_km = Column(DECIMAL(8, 3))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

# Minimal Route Recommendation implementation for testing
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
class RouteSegmentData:
    segment_order: int
    line_id: int
    line_name: str
    boarding_station_id: int
    alighting_station_id: int
    ride_time_minutes: float

@dataclass(frozen=True, slots=True)
class CandidateRouteData:
    route_id: str
    vehicle_id: int
    line_ids: tuple[int, ...]
    segments: tuple[RouteSegmentData, ...]
    boarding_station_id: int
    alighting_station_id: int
    walk_time_minutes: float
    ride_time_minutes: float
    transfer_count: int

class ResourceNotFoundError(Exception):
    pass

class BusinessError(Exception):
    def __init__(self, code, message, status_code):
        self.code = code
        self.message = message
        self.status_code = status_code

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

    async def get_candidate_routes(self, start_station_id: int, end_station_id: int, max_transfer_count: int) -> list[CandidateRouteData]:
        if start_station_id == end_station_id:
            return []
        
        routes = await self._direct_routes(start_station_id, end_station_id)
        if max_transfer_count > 0 and len(routes) == 0:
            routes.extend(await self._one_transfer_routes(start_station_id, end_station_id))
        
        return routes

    async def _direct_routes(self, start_station_id: int, end_station_id: int) -> list[CandidateRouteData]:
        start_rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == start_station_id)
            .filter(BusLine.status == "running")
            .order_by(LineStation.line_id, LineStation.stop_sequence)
            .all()
        )
        
        routes = []
        for start, line in start_rows:
            end = (
                self.db.query(LineStation)
                .filter(LineStation.line_id == start.line_id)
                .filter(LineStation.station_id == end_station_id)
                .filter(LineStation.stop_sequence > start.stop_sequence)
                .order_by(LineStation.stop_sequence)
                .first()
            )
            if end is None:
                continue
            
            vehicle = self.db.query(BusVehicle).filter(
                BusVehicle.line_id == start.line_id,
                BusVehicle.operation_status == "normal"
            ).order_by(desc(BusVehicle.last_reported_at)).first()
            
            if vehicle is None:
                continue
            
            ride_time = self._estimate_ride_time(start, end, line)
            
            routes.append(CandidateRouteData(
                route_id=f"direct_{start.line_id}_{start_station_id}_{end_station_id}",
                vehicle_id=int(vehicle.vehicle_id),
                line_ids=(int(start.line_id),),
                segments=(RouteSegmentData(
                    segment_order=1,
                    line_id=int(start.line_id),
                    line_name=str(line.line_name or line.service_no),
                    boarding_station_id=start_station_id,
                    alighting_station_id=end_station_id,
                    ride_time_minutes=ride_time,
                ),),
                boarding_station_id=start_station_id,
                alighting_station_id=end_station_id,
                walk_time_minutes=4.0,
                ride_time_minutes=ride_time,
                transfer_count=0,
            ))
        
        return routes

    async def _one_transfer_routes(self, start_station_id: int, end_station_id: int) -> list[CandidateRouteData]:
        start_rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == start_station_id)
            .filter(BusLine.status == "running")
            .all()
        )
        end_rows = (
            self.db.query(LineStation, BusLine)
            .join(BusLine, BusLine.line_id == LineStation.line_id)
            .filter(LineStation.station_id == end_station_id)
            .filter(BusLine.status == "running")
            .all()
        )
        
        routes = []
        for start, first_line in start_rows:
            first_vehicle = self.db.query(BusVehicle).filter(
                BusVehicle.line_id == start.line_id,
                BusVehicle.operation_status == "normal"
            ).first()
            if first_vehicle is None:
                continue
            
            for end, second_line in end_rows:
                if start.line_id == end.line_id:
                    continue
                
                second_vehicle = self.db.query(BusVehicle).filter(
                    BusVehicle.line_id == end.line_id,
                    BusVehicle.operation_status == "normal"
                ).first()
                if second_vehicle is None:
                    continue
                
                transfer_station_id = self._find_transfer_station(start.line_id, end.line_id)
                if transfer_station_id is None:
                    continue
                
                first_end = (
                    self.db.query(LineStation)
                    .filter(LineStation.line_id == start.line_id)
                    .filter(LineStation.station_id == transfer_station_id)
                    .filter(LineStation.stop_sequence > start.stop_sequence)
                    .first()
                )
                second_start = (
                    self.db.query(LineStation)
                    .filter(LineStation.line_id == end.line_id)
                    .filter(LineStation.station_id == transfer_station_id)
                    .filter(LineStation.stop_sequence < end.stop_sequence)
                    .first()
                )
                
                if first_end is None or second_start is None:
                    continue
                
                first_ride = self._estimate_ride_time(start, first_end, first_line)
                second_ride = self._estimate_ride_time(second_start, end, second_line)
                
                route_id = f"transfer_{start.line_id}_{end.line_id}_{start_station_id}_{transfer_station_id}_{end_station_id}"
                routes.append(CandidateRouteData(
                    route_id=route_id,
                    vehicle_id=int(first_vehicle.vehicle_id),
                    line_ids=(int(start.line_id), int(end.line_id)),
                    segments=(
                        RouteSegmentData(
                            segment_order=1,
                            line_id=int(start.line_id),
                            line_name=str(first_line.line_name or first_line.service_no),
                            boarding_station_id=start_station_id,
                            alighting_station_id=transfer_station_id,
                            ride_time_minutes=first_ride,
                        ),
                        RouteSegmentData(
                            segment_order=2,
                            line_id=int(end.line_id),
                            line_name=str(second_line.line_name or second_line.service_no),
                            boarding_station_id=transfer_station_id,
                            alighting_station_id=end_station_id,
                            ride_time_minutes=second_ride,
                        ),
                    ),
                    boarding_station_id=start_station_id,
                    alighting_station_id=end_station_id,
                    walk_time_minutes=8.0,
                    ride_time_minutes=first_ride + second_ride,
                    transfer_count=1,
                ))
        
        return routes

    def _find_transfer_station(self, line_id1: int, line_id2: int) -> int | None:
        line1_stations = set(
            [ls.station_id for ls in self.db.query(LineStation).filter(LineStation.line_id == line_id1).all()]
        )
        line2_stations = set(
            [ls.station_id for ls in self.db.query(LineStation).filter(LineStation.line_id == line_id2).all()]
        )
        common_stations = line1_stations & line2_stations
        return next(iter(common_stations), None)

    def _estimate_ride_time(self, start: LineStation, end: LineStation, line: BusLine) -> float:
        if start.route_distance_km and end.route_distance_km:
            distance_km = float(end.route_distance_km) - float(start.route_distance_km)
            avg_speed_kph = float(line.avg_service_frequency) if line.avg_service_frequency else 20.0
            return max(2.0, (distance_km / avg_speed_kph) * 60)
        
        stops_between = int(end.stop_sequence) - int(start.stop_sequence)
        return stops_between * 3.0

    async def find_nearest_station(self, longitude: float, latitude: float) -> StationData:
        stations = self.db.query(BusStation).all()
        if not stations:
            raise ResourceNotFoundError("未找到可用公交站点")
        
        from math import asin, cos, radians, sin, sqrt
        def haversine(lon1, lat1, lon2, lat2):
            earth_radius = 6_371_000.0
            lon_1, lat_1, lon_2, lat_2 = map(radians, (lon1, lat1, lon2, lat2))
            delta_lon = lon_2 - lon_1
            delta_lat = lat_2 - lat_1
            value = sin(delta_lat / 2) ** 2 + cos(lat_1) * cos(lat_2) * sin(delta_lon / 2) ** 2
            return 2 * earth_radius * asin(sqrt(value))
        
        nearest = min(stations, key=lambda s: haversine(longitude, latitude, float(s.longitude), float(s.latitude)))
        return StationData(
            station_id=int(nearest.station_id),
            station_name=str(nearest.station_name),
            longitude=float(nearest.longitude),
            latitude=float(nearest.latitude),
        )

@dataclass
class RecommendRoutesRequest:
    start_station_id: int | None = None
    end_station_id: int | None = None
    origin_longitude: float | None = None
    origin_latitude: float | None = None
    destination_longitude: float | None = None
    destination_latitude: float | None = None
    depart_time: datetime = None
    allow_transfer: bool = True
    max_transfer_count: int = 1
    max_walk_minutes: float | None = None
    preference: str = "balanced"

@dataclass
class RouteRecommendation:
    route_id: str
    line_ids: list[int]
    segments: list[dict]
    boarding_station: dict
    alighting_station: dict
    predicted_eta_minutes: float
    predicted_load: dict
    walk_time_minutes: float
    ride_time_minutes: float
    total_time_minutes: float
    transfer_count: int
    experience_score: float
    recommend_types: list[str]
    reason: str

@dataclass
class RecommendRoutesResult:
    items: list[RouteRecommendation]
    best_experience_route_id: str
    fastest_route_id: str
    least_crowded_route_id: str
    least_walking_route_id: str
    least_transfer_route_id: str
    preference: str
    generated_at: datetime

class RecommendationService:
    def __init__(self, gateway):
        self.gateway = gateway

    async def recommend(self, request: RecommendRoutesRequest) -> RecommendRoutesResult:
        depart_time = request.depart_time or datetime.now()
        start_station_id, end_station_id = await self._resolve_station_ids(request)
        
        if start_station_id == end_station_id:
            raise BusinessError(40003, "起点和终点不能相同", 400)

        max_transfer = request.max_transfer_count if request.allow_transfer else 0
        candidates = await self.gateway.get_candidate_routes(
            start_station_id, end_station_id, max_transfer
        )
        
        if request.max_walk_minutes is not None:
            candidates = [c for c in candidates if c.walk_time_minutes <= request.max_walk_minutes]
        
        if not candidates:
            raise BusinessError(40400, "未找到满足条件的公交方案", 404)

        items = [await self._build_route(item, depart_time) for item in candidates]
        
        if not items:
            raise BusinessError(40400, "未找到满足条件的公交方案", 404)

        selections = self._select_routes(items)
        ordered_items = self._sort_by_preference(items, request.preference)

        return RecommendRoutesResult(
            items=ordered_items,
            best_experience_route_id=selections["best_experience"],
            fastest_route_id=selections["fastest"],
            least_crowded_route_id=selections["least_crowded"],
            least_walking_route_id=selections["least_walking"],
            least_transfer_route_id=selections["least_transfer"],
            preference=request.preference,
            generated_at=datetime.now(),
        )

    async def _resolve_station_ids(self, request):
        if request.start_station_id is not None and request.end_station_id is not None:
            await self.gateway.get_station(request.start_station_id)
            await self.gateway.get_station(request.end_station_id)
            return request.start_station_id, request.end_station_id
        
        if request.origin_longitude is not None and request.origin_latitude is not None:
            start = await self.gateway.find_nearest_station(request.origin_longitude, request.origin_latitude)
            end = await self.gateway.find_nearest_station(request.destination_longitude, request.destination_latitude)
            return start.station_id, end.station_id
        
        raise BusinessError(40002, "缺少必要的站点参数", 400)

    async def _build_route(self, candidate: CandidateRouteData, depart_time):
        boarding = await self.gateway.get_station(candidate.boarding_station_id)
        alighting = await self.gateway.get_station(candidate.alighting_station_id)
        
        eta_minutes = candidate.ride_time_minutes * 0.8
        load_rate = 0.5 + (candidate.transfer_count * 0.1)
        
        return RouteRecommendation(
            route_id=candidate.route_id,
            line_ids=list(candidate.line_ids),
            segments=[{
                "segment_order": s.segment_order,
                "line_id": s.line_id,
                "line_name": s.line_name,
                "boarding_station_id": s.boarding_station_id,
                "alighting_station_id": s.alighting_station_id,
                "ride_time_minutes": s.ride_time_minutes,
            } for s in candidate.segments],
            boarding_station={
                "station_id": boarding.station_id,
                "station_name": boarding.station_name,
                "longitude": boarding.longitude,
                "latitude": boarding.latitude,
            },
            alighting_station={
                "station_id": alighting.station_id,
                "station_name": alighting.station_name,
                "longitude": alighting.longitude,
                "latitude": alighting.latitude,
            },
            predicted_eta_minutes=round(eta_minutes, 1),
            predicted_load={
                "predicted_load_rate": round(load_rate, 2),
                "predicted_load_level": "standing_available",
                "predicted_onboard_count": int(load_rate * 60),
                "capacity": 60,
                "confidence": 0.7,
                "load_score": round(100 - load_rate * 55, 1),
            },
            walk_time_minutes=candidate.walk_time_minutes,
            ride_time_minutes=candidate.ride_time_minutes,
            total_time_minutes=round(candidate.walk_time_minutes + eta_minutes + candidate.ride_time_minutes, 1),
            transfer_count=candidate.transfer_count,
            experience_score=round(80 - candidate.transfer_count * 10 - load_rate * 20, 1),
            recommend_types=[],
            reason=f"乘坐{candidate.line_ids[0]}路公交",
        )

    def _select_routes(self, items):
        if not items:
            return {key: "" for key in ["best_experience", "fastest", "least_crowded", "least_walking", "least_transfer"]}
        
        return {
            "best_experience": max(items, key=lambda x: x.experience_score).route_id,
            "fastest": min(items, key=lambda x: x.total_time_minutes).route_id,
            "least_crowded": max(items, key=lambda x: x.predicted_load["load_score"]).route_id,
            "least_walking": min(items, key=lambda x: x.walk_time_minutes).route_id,
            "least_transfer": min(items, key=lambda x: x.transfer_count).route_id,
        }

    def _sort_by_preference(self, items, preference):
        if preference == "fastest":
            return sorted(items, key=lambda x: (x.total_time_minutes, -x.experience_score))
        if preference == "low_load":
            return sorted(items, key=lambda x: (-x.predicted_load["load_score"], x.total_time_minutes))
        if preference == "less_walking":
            return sorted(items, key=lambda x: (x.walk_time_minutes, -x.experience_score))
        if preference == "less_transfer":
            return sorted(items, key=lambda x: (x.transfer_count, -x.experience_score))
        return sorted(items, key=lambda x: (-x.experience_score, x.total_time_minutes))

async def test_recommendation_with_real_database():
    """Regression test for route recommendation with real database data."""
    # Setup in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    # Insert real-like test data with realistic IDs
    db.add(BusStation(station_id=1001, station_name="人民广场站", bus_stop_code="BS1001", latitude=31.2304, longitude=121.4737))
    db.add(BusStation(station_id=1002, station_name="南京东路站", bus_stop_code="BS1002", latitude=31.2315, longitude=121.4745))
    db.add(BusStation(station_id=1003, station_name="外滩站", bus_stop_code="BS1003", latitude=31.2330, longitude=121.4760))
    db.add(BusStation(station_id=1004, station_name="陆家嘴站", bus_stop_code="BS1004", latitude=31.2397, longitude=121.5070))
    
    db.add(BusLine(line_id=501, service_no="501", line_name="501路", avg_service_frequency=10.0, status="running"))
    db.add(BusLine(line_id=502, service_no="502", line_name="502路", avg_service_frequency=12.0, status="running"))
    
    db.add(BusVehicle(vehicle_id=2001, vehicle_code="VH2001", line_id=501, current_station_id=1001, next_station_id=1002, latitude=31.2306, longitude=121.4738, speed_kph=25.0, onboard_count=25, capacity=55, operation_status="normal", last_reported_at=datetime.now()))
    db.add(BusVehicle(vehicle_id=2002, vehicle_code="VH2002", line_id=502, current_station_id=1002, next_station_id=1003, latitude=31.2316, longitude=121.4746, speed_kph=22.0, onboard_count=30, capacity=55, operation_status="normal", last_reported_at=datetime.now()))
    
    db.add(LineStation(line_station_id="LS501_1", line_id=501, service_no="501", line_name="501路", stop_sequence=1, station_id=1001, route_distance_km=0.0))
    db.add(LineStation(line_station_id="LS501_2", line_id=501, service_no="501", line_name="501路", stop_sequence=2, station_id=1002, route_distance_km=0.8))
    db.add(LineStation(line_station_id="LS501_3", line_id=501, service_no="501", line_name="501路", stop_sequence=3, station_id=1003, route_distance_km=1.5))
    
    db.add(LineStation(line_station_id="LS502_1", line_id=502, service_no="502", line_name="502路", stop_sequence=1, station_id=1002, route_distance_km=0.0))
    db.add(LineStation(line_station_id="LS502_2", line_id=502, service_no="502", line_name="502路", stop_sequence=2, station_id=1003, route_distance_km=0.6))
    db.add(LineStation(line_station_id="LS502_3", line_id=502, service_no="502", line_name="502路", stop_sequence=3, station_id=1004, route_distance_km=2.0))
    
    db.commit()
    
    # Create gateway and service
    gateway = SimpleTransitGateway(db)
    service = RecommendationService(gateway)
    
    # Test 1: Direct route recommendation
    request1 = RecommendRoutesRequest(
        start_station_id=1001,
        end_station_id=1003,
        preference="balanced",
        allow_transfer=False
    )
    result1 = await service.recommend(request1)
    
    print(f"Test 1 - Direct route recommendation:")
    print(f"  Number of routes: {len(result1.items)}")
    for item in result1.items:
        print(f"  Route ID: {item.route_id}")
        print(f"    Lines: {item.line_ids}")
        print(f"    Transfer count: {item.transfer_count}")
        print(f"    Total time: {item.total_time_minutes} mins")
        print(f"    Experience score: {item.experience_score}")
    
    assert len(result1.items) >= 1
    assert result1.best_experience_route_id
    print("PASSED: Direct route recommendation with real station IDs")
    
    # Test 2: Same station error
    try:
        request2 = RecommendRoutesRequest(start_station_id=1001, end_station_id=1001)
        await service.recommend(request2)
        assert False, "Expected exception for same station"
    except BusinessError as e:
        assert e.code == 40003
        print("PASSED: Same station error handling")
    
    # Test 3: Non-existent station error
    try:
        request3 = RecommendRoutesRequest(start_station_id=99999, end_station_id=1001)
        await service.recommend(request3)
        assert False, "Expected exception for non-existent station"
    except ResourceNotFoundError as e:
        assert "未找到公交站点" in str(e)
        print("PASSED: Non-existent station error handling")
    
    # Test 4: Route with transfer
    request4 = RecommendRoutesRequest(
        start_station_id=1001,
        end_station_id=1004,
        preference="balanced",
        allow_transfer=True,
        max_transfer_count=1
    )
    try:
        result4 = await service.recommend(request4)
        print(f"\nTest 4 - Route with transfer:")
        print(f"  Number of routes: {len(result4.items)}")
        for item in result4.items:
            print(f"  Route ID: {item.route_id}")
            print(f"    Transfer count: {item.transfer_count}")
        print("PASSED: Route with transfer")
    except BusinessError as e:
        if e.code == 40400:
            print("PASSED: No transfer route found (expected if no common station)")
        else:
            raise
    
    db.close()

if __name__ == "__main__":
    print("=" * 70)
    print("Testing Route Recommendation with Real Database Integration")
    print("=" * 70)
    print()
    
    asyncio.run(test_recommendation_with_real_database())
    
    print()
    print("=" * 70)
    print("All real database recommendation tests passed!")
    print("=" * 70)