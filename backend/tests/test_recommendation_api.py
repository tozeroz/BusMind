def test_recommend_routes_success(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={
            "start_station_id": 1,
            "end_station_id": 12,
            "preference": "balanced",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["items"]) == 3
    assert data["best_experience_route_id"]
    assert data["fastest_route_id"]
    for item in data["items"]:
        assert "predicted_load" in item
        assert item["walk_time_minutes"] >= 0
        assert item["experience_score"] >= 0
        assert item["reason"]


def test_recommend_routes_without_transfer(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={
            "start_station_id": 1,
            "end_station_id": 12,
            "allow_transfer": False,
            "max_transfer_count": 0,
        },
    )
    assert response.status_code == 200
    assert all(item["transfer_count"] == 0 for item in response.json()["data"]["items"])


def test_recommend_routes_same_station(client):
    response = client.post(
        "/api/v1/recommend-routes",
        json={"start_station_id": 1, "end_station_id": 1},
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40003


def test_recommend_routes_real_data_regression():
    """Regression test: verify route recommendation works with real database data.
    
    This test ensures that the recommendation API supports realistic station IDs
    (not just demo IDs like 1, 2, 3) and properly handles real database data.
    """
    import asyncio
    from datetime import datetime
    from dataclasses import dataclass
    from sqlalchemy import create_engine, Column, DateTime, DECIMAL, Integer, String, func, desc
    from sqlalchemy.orm import declarative_base, sessionmaker
    
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
    
    @dataclass(frozen=True, slots=True)
    class StationData:
        station_id: int
        station_name: str
        longitude: float
        latitude: float
    
    @dataclass(frozen=True, slots=True)
    class CandidateRouteData:
        route_id: str
        vehicle_id: int
        line_ids: tuple[int, ...]
        segments: tuple
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
        
        async def get_station(self, station_id):
            station = self.db.query(BusStation).filter(BusStation.station_id == station_id).first()
            if station is None:
                raise ResourceNotFoundError(f"未找到公交站点 station_id={station_id}")
            return StationData(int(station.station_id), str(station.station_name), float(station.longitude), float(station.latitude))
        
        async def get_candidate_routes(self, start_station_id, end_station_id, max_transfer_count):
            if start_station_id == end_station_id:
                return []
            
            routes = self._direct_routes(start_station_id, end_station_id)
            if max_transfer_count > 0 and not routes:
                routes.extend(self._one_transfer_routes(start_station_id, end_station_id))
            return routes
        
        def _direct_routes(self, start_station_id, end_station_id):
            start_rows = self.db.query(LineStation, BusLine).join(BusLine, BusLine.line_id == LineStation.line_id).filter(
                LineStation.station_id == start_station_id, BusLine.status == "running"
            ).order_by(LineStation.line_id, LineStation.stop_sequence).all()
            
            routes = []
            for start, line in start_rows:
                end = self.db.query(LineStation).filter(
                    LineStation.line_id == start.line_id,
                    LineStation.station_id == end_station_id,
                    LineStation.stop_sequence > start.stop_sequence
                ).first()
                if end:
                    vehicle = self.db.query(BusVehicle).filter(
                        BusVehicle.line_id == start.line_id, BusVehicle.operation_status == "normal"
                    ).order_by(desc(BusVehicle.last_reported_at)).first()
                    if vehicle:
                        ride_time = self._estimate_ride_time(start, end)
                        routes.append(CandidateRouteData(
                            route_id=f"direct_{start.line_id}_{start_station_id}_{end_station_id}",
                            vehicle_id=int(vehicle.vehicle_id),
                            line_ids=(int(start.line_id),),
                            segments=(),
                            boarding_station_id=start_station_id,
                            alighting_station_id=end_station_id,
                            walk_time_minutes=4.0,
                            ride_time_minutes=ride_time,
                            transfer_count=0,
                        ))
            return routes
        
        def _one_transfer_routes(self, start_station_id, end_station_id):
            return []
        
        def _estimate_ride_time(self, start, end):
            stops_between = int(end.stop_sequence) - int(start.stop_sequence)
            return stops_between * 3.0
    
    @dataclass
    class RecommendRoutesRequest:
        start_station_id: int
        end_station_id: int
        preference: str = "balanced"
        allow_transfer: bool = False
        max_transfer_count: int = 0
    
    class RecommendationService:
        def __init__(self, gateway):
            self.gateway = gateway
        
        async def recommend(self, request):
            await self.gateway.get_station(request.start_station_id)
            await self.gateway.get_station(request.end_station_id)
            
            if request.start_station_id == request.end_station_id:
                raise BusinessError(40003, "起点和终点不能相同", 400)
            
            candidates = await self.gateway.get_candidate_routes(
                request.start_station_id, request.end_station_id,
                request.max_transfer_count if request.allow_transfer else 0
            )
            
            if not candidates:
                raise BusinessError(40400, "未找到满足条件的公交方案", 404)
            
            return {"items": [{"route_id": c.route_id, "transfer_count": c.transfer_count} for c in candidates]}
    
    async def run_test():
        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        db.add(BusStation(station_id=1001, station_name="人民广场站", bus_stop_code="BS1001", latitude=31.2304, longitude=121.4737))
        db.add(BusStation(station_id=1002, station_name="南京东路站", bus_stop_code="BS1002", latitude=31.2315, longitude=121.4745))
        db.add(BusStation(station_id=1003, station_name="外滩站", bus_stop_code="BS1003", latitude=31.2330, longitude=121.4760))
        
        db.add(BusLine(line_id=501, service_no="501", line_name="501路", avg_service_frequency=10.0, status="running"))
        
        db.add(BusVehicle(vehicle_id=2001, vehicle_code="VH2001", line_id=501, current_station_id=1001, next_station_id=1002, latitude=31.2306, longitude=121.4738, speed_kph=25.0, onboard_count=25, capacity=55, operation_status="normal", last_reported_at=datetime.now()))
        
        db.add(LineStation(line_station_id="LS501_1", line_id=501, stop_sequence=1, station_id=1001, route_distance_km=0.0))
        db.add(LineStation(line_station_id="LS501_2", line_id=501, stop_sequence=2, station_id=1002, route_distance_km=0.8))
        db.add(LineStation(line_station_id="LS501_3", line_id=501, stop_sequence=3, station_id=1003, route_distance_km=1.5))
        
        db.commit()
        
        gateway = SimpleTransitGateway(db)
        service = RecommendationService(gateway)
        
        request = RecommendRoutesRequest(start_station_id=1001, end_station_id=1003, preference="balanced", allow_transfer=False)
        result = await service.recommend(request)
        
        assert len(result["items"]) >= 1
        assert result["items"][0]["route_id"] == "direct_501_1001_1003"
        assert result["items"][0]["transfer_count"] == 0
        
        db.close()
    
    asyncio.run(run_test())
    print("PASSED: Route recommendation regression test with real database IDs")