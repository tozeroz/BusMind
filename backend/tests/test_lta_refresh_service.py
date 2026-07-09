from datetime import timedelta

import pytest

from backend.app.core.time_utils import now_local
from backend.app.schemas.simulation import LtaBusArrivalRefreshRequest
from backend.app.services.intelligence_gateway import DemoIntelligenceGateway
from backend.app.services.lta_service import LtaBusArrival
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
