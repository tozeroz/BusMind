from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.admin.router import router
from app.api.v1.dependencies import (
    get_cache_sync_service,
    get_db,
    get_lta_collector_service,
)
from app.core.exception_handlers import register_intelligence_exception_handlers


class FakeCollector:
    async def refresh_bus_arrival(self, bus_stop_code: str, service_no: str | None = None):
        return [
            {
                "bus_stop_code": bus_stop_code,
                "service_no": service_no or "15",
                "eta_minutes": 4.0,
            }
        ]

    async def refresh_traffic_speed_bands(self):
        return [
            {
                "link_id": 103000001,
                "speed_band": 4,
                "congestion_score": 0.5714,
            }
        ]


class FakeSyncService:
    def sync_bus_arrival(self, db, bus_stop_code: str, service_no: str):
        db.synced.append(("bus_arrival", bus_stop_code, service_no))
        return _Result(processed=1, skipped=0)

    def sync_traffic_speed_bands(self, db, bands):
        db.synced.append(("traffic_speed_bands", len(bands)))
        return _Result(processed=len(bands), skipped=0)


class FakeDb:
    def __init__(self):
        self.synced = []
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        self.committed = False

    def close(self):
        pass


class _Result:
    def __init__(self, processed: int, skipped: int):
        self.processed = processed
        self.skipped = skipped


def test_admin_bus_arrival_refresh_triggers_collector_and_sync():
    db = FakeDb()
    client = _client(db)

    response = client.post(
        "/admin/lta/bus-arrival/refresh",
        json={"bus_stop_code": "83139", "service_no": "15", "sync_to_db": True},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dataset"] == "lta_bus_arrival"
    assert data["collected"] == 1
    assert data["synced"] == 1
    assert db.synced == [("bus_arrival", "83139", "15")]
    assert db.committed is True


def test_admin_traffic_speed_bands_refresh_triggers_collector_and_sync():
    db = FakeDb()
    client = _client(db)

    response = client.post(
        "/admin/lta/traffic-speed-bands/refresh",
        json={"sync_to_db": True},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["dataset"] == "traffic_speed_bands"
    assert data["collected"] == 1
    assert data["synced"] == 1
    assert db.synced == [("traffic_speed_bands", 1)]
    assert db.committed is True


def _client(db: FakeDb) -> TestClient:
    app = FastAPI()
    register_intelligence_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_lta_collector_service] = lambda: FakeCollector()
    app.dependency_overrides[get_cache_sync_service] = lambda: FakeSyncService()
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)
