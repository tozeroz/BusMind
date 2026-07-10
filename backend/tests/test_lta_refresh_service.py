from datetime import timedelta

import pytest

from backend.app.cache.cache_keys import traffic_speed_band_link, traffic_speed_bands_latest
from backend.app.cache.memory_cache_provider import MemoryCacheProvider
from backend.app.core.time_utils import now_local
from backend.app.schemas.simulation import LtaBusArrivalRefreshRequest
from backend.app.services.intelligence_gateway import DemoIntelligenceGateway
from backend.app.services.collector_service.service import LtaCollectorService
from backend.app.services.lta_service import LtaBusArrival, LtaTrafficSpeedBand
from backend.app.services.sync_service.service import CacheSyncService
from backend.app.services.simulation_service import SimulationService, SimulationStateStore


class FakeLtaClient:
    async def get_bus_arrivals(self, bus_stop_code: str, service_no: str | None = None):
        return [
            LtaBusArrival(
                bus_stop_code=bus_stop_code,
                service_no=service_no or "15",
                operator="GAS",
                estimated_arrival=now_local() + timedelta(minutes=4),
                eta_minutes=4.0,
                monitored=True,
                latitude=1.31549,
                longitude=103.90591,
                load_code="SDA",
                feature="WAB",
                bus_type="SD",
            )
        ]


@pytest.mark.asyncio
async def test_lta_refresh_writes_eta_load_and_vehicle_state():
    gateway = DemoIntelligenceGateway()
    store = SimulationStateStore()
    service = SimulationService(gateway, store, FakeLtaClient())

    result = await service.refresh_from_lta(
        LtaBusArrivalRefreshRequest(
            bus_stop_code="83139",
            service_no="15",
            vehicle_id=101,
            line_id=1,
            station_id=3,
            capacity=60,
        )
    )
    assert result.predicted_eta_minutes == 4.0
    assert result.predicted_load_level.value == "standing_available"
    assert store.get_eta(vehicle_id=101, target_station_id=3, line_id=1) is not None
    assert store.get_load(line_id=1, station_id=3, vehicle_id=101) is not None
    vehicle = await gateway.get_vehicle(101)
    assert vehicle.longitude == 103.90591
    assert vehicle.onboard_count == 43


class FakeTrafficLtaClient(FakeLtaClient):
    async def get_traffic_speed_bands(self):
        return [
            LtaTrafficSpeedBand(
                query_time=now_local(),
                link_id=103000001,
                road_name="PIE",
                road_category="Expressway",
                speed_band=4,
                minimum_speed_kmh=30.0,
                maximum_speed_kmh=39.0,
                congestion_score=0.5714,
                heat_color="#fb8c00",
                start_lon=103.9,
                start_lat=1.31,
                end_lon=103.91,
                end_lat=1.32,
                line_coordinates=[[103.9, 1.31], [103.91, 1.32]],
            )
        ]


@pytest.mark.asyncio
async def test_traffic_speed_bands_refresh_writes_latest_and_link_cache():
    cache = MemoryCacheProvider()
    service = LtaCollectorService(FakeTrafficLtaClient(), cache=cache)

    result = await service.refresh_traffic_speed_bands()

    assert result[0]["link_id"] == 103000001
    assert cache.get(traffic_speed_bands_latest()) == result
    assert cache.get(traffic_speed_band_link(103000001)) == result[0]


def test_sync_traffic_speed_bands_accepts_cached_payloads():
    class FakeDb:
        def __init__(self):
            self.params = []

        def execute(self, statement, params):
            self.params.append(params)

    db = FakeDb()
    cache = MemoryCacheProvider()
    cache.set(
        traffic_speed_bands_latest(),
        [
            {
                "query_time": now_local().isoformat(),
                "link_id": 103000001,
                "road_name": "PIE",
                "road_category": "Expressway",
                "speed_band": 4,
                "minimum_speed_kmh": 30,
                "maximum_speed_kmh": 39,
                "start_lon": 103.9,
                "start_lat": 1.31,
                "end_lon": 103.91,
                "end_lat": 1.32,
            }
        ],
    )

    result = CacheSyncService(cache).sync_traffic_speed_bands(db)

    assert result.processed == 1
    assert result.skipped == 0
    assert db.params[0]["congestion_score"] == 0.5714
    assert db.params[0]["line_coordinates"] == "[[103.9, 1.31], [103.91, 1.32]]"
