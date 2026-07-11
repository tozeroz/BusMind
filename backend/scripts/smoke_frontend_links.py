"""端到端 HTTP 冒烟测试：仅验证本轮接入的接口契约与字段，不依赖 MySQL。"""
from __future__ import annotations

import os
import sys

# Make project root + backend importable.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "backend"))

# Force SQLite file under /tmp before importing the app.
import tempfile  # noqa: E402

_smoke_db = os.path.join(tempfile.gettempdir(), "smoke_frontend_links.sqlite")
if os.path.exists(_smoke_db):
    os.remove(_smoke_db)
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_smoke_db}")
os.environ.setdefault("AUTO_CREATE_TABLES", "true")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db.session import engine  # noqa: E402
from app.dependencies.auth import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402

# Pre-create schema once before the TestClient lifespan runs.
Base.metadata.create_all(bind=engine)

from app.api.v1.dependencies import (  # noqa: E402
    get_cache_sync_service,
    get_lta_collector_service,
)

class _FakeCollector:
    async def refresh_bus_arrival(self, bus_stop_code, service_no=None):
        return [{
            "bus_stop_code": bus_stop_code,
            "service_no": service_no or "15",
            "eta_minutes": 4.0,
        }]

    async def refresh_traffic_speed_bands(self):
        return [{"link_id": "X", "speed_band": 3}]


class _FakeSyncService:
    def sync_bus_arrival(self, db, bus_stop_code, service_no):
        from app.schemas.sync_results import SyncProcessResult  # noqa: E402
        return SyncProcessResult(processed=0, skipped=0, errors=0)

    def sync_traffic_speed_bands(self, db, payloads):
        from app.schemas.sync_results import SyncProcessResult  # noqa: E402
        return SyncProcessResult(processed=0, skipped=0, errors=0)


# Prevent real LTA network calls inside the smoke run.
app.dependency_overrides[get_lta_collector_service] = lambda: _FakeCollector()
app.dependency_overrides[get_cache_sync_service] = lambda: _FakeSyncService()

client = TestClient(app)


def fail(msg: str) -> None:
    raise AssertionError(msg)


def check(condition: bool, msg: str) -> None:
    if not condition:
        fail(msg)


def main() -> None:
    # 1. 用户注册
    r = client.post("/api/v1/users/register", json={
        "username": "smoke_user",
        "password": "smoke_password",
        "nickname": "Smoke"
    })
    check(r.status_code == 201, f"register status={r.status_code} body={r.text}")
    data = r.json()
    check(data["code"] == 0, f"register code={data}")
    check(data["data"]["username"] == "smoke_user", f"register username={data}")
    print("PASS register")

    # 2. 用户登录
    r = client.post("/api/v1/users/login", json={
        "username": "smoke_user",
        "password": "smoke_password"
    })
    check(r.status_code == 200, f"login status={r.status_code} body={r.text}")
    login = r.json()
    check(login["code"] == 0, f"login code={login}")
    token = login["data"]["access_token"]
    check(bool(token), "missing access_token")
    headers = {"Authorization": f"Bearer {token}"}
    print("PASS login")

    # 3. 获取当前用户
    r = client.get("/api/v1/users/me", headers=headers)
    check(r.status_code == 200, f"me status={r.status_code}")
    me = r.json()["data"]
    check(me["user"]["username"] == "smoke_user", f"me={me}")
    check("favorite_count" in me and "history_count" in me, f"me missing counts={me}")
    print("PASS me")

    # 4. 修改昵称
    r = client.patch("/api/v1/users/me", json={"nickname": "新昵称"}, headers=headers)
    check(r.status_code == 200, f"patch me status={r.status_code}")
    me2 = r.json()["data"]
    check(me2["nickname"] == "新昵称", f"nickname={me2}")
    print("PASS patch me")

    # 5. 添加收藏
    r = client.post("/api/v1/users/me/favorites", json={
        "favorite_type": "line",
        "target_id": 1,
        "target_name": "测试线路"
    }, headers=headers)
    check(r.status_code == 201, f"add fav status={r.status_code} body={r.text}")
    fav = r.json()["data"]
    fav_id = fav["favorite_id"]
    print("PASS add favorite")

    # 6. 获取收藏
    r = client.get("/api/v1/users/me/favorites", headers=headers)
    check(r.status_code == 200, f"get fav status={r.status_code}")
    favs = r.json()["data"]
    check(favs["total"] == 1 and favs["favorites"][0]["favorite_id"] == fav_id, f"favs={favs}")
    print("PASS get favorites")

    # 7. 删除收藏
    r = client.delete(f"/api/v1/users/me/favorites/{fav_id}", headers=headers)
    check(r.status_code == 200, f"del fav status={r.status_code}")
    print("PASS delete favorite")

    # 8. 查询历史
    r = client.get("/api/v1/users/me/query-history", headers=headers)
    check(r.status_code == 200, f"history status={r.status_code}")
    hist = r.json()["data"]
    check("histories" in hist and "total" in hist, f"history={hist}")
    print("PASS query history")

    # 9. 线路列表
    r = client.get("/api/v1/lines", params={"page": 1, "limit": 5})
    check(r.status_code == 200, f"lines status={r.status_code}")
    lines = r.json()["data"]
    check("lines" in lines and "total" in lines, f"lines={lines}")
    print("PASS lines list (empty ok)")

    # 10. 车辆列表
    r = client.get("/api/v1/vehicles", params={"page": 1, "limit": 5})
    check(r.status_code == 200, f"vehicles status={r.status_code}")
    print("PASS vehicles list")

    # 11. 实时车辆
    r = client.get("/api/v1/vehicles/realtime")
    check(r.status_code == 200, f"realtime status={r.status_code}")
    rt = r.json()["data"]
    check("vehicles" in rt, f"realtime missing vehicles={rt}")
    print("PASS realtime vehicles")

    # 12. 客流趋势
    r = client.get("/api/v1/history/passenger-flow", params={"granularity": "hour"})
    check(r.status_code == 200, f"flow status={r.status_code}")
    flow = r.json()["data"]
    check("items" in flow and "summary" in flow, f"flow={flow}")
    print("PASS passenger flow trend")

    # 13. 客流预测
    r = client.get("/api/v1/history/passenger-flow/prediction")
    check(r.status_code == 200, f"prediction status={r.status_code}")
    pred = r.json()["data"]
    check(isinstance(pred, list), f"prediction not list: {pred}")
    print("PASS passenger flow prediction (empty list ok)")

    # 14. 附近站点
    r = client.get("/api/v1/locations/nearby", params={
        "latitude": 1.3, "longitude": 103.8, "radius_km": 5
    })
    check(r.status_code == 200, f"nearby status={r.status_code}")
    nb = r.json()["data"]
    check("stations" in nb, f"nearby missing stations={nb}")
    print("PASS nearby stations")

    # 15. 位置搜索
    r = client.get("/api/v1/locations/search", params={"keyword": "乌节"})
    check(r.status_code == 200, f"search status={r.status_code}")
    print("PASS location search")

    # 16. 地图线路
    r = client.get("/api/v1/map/lines")
    check(r.status_code == 200, f"map lines status={r.status_code}")
    print("PASS map lines")

    # 17. ETA (没有车辆数据时，返回 404 是预期)
    r = client.get("/api/v1/eta", params={"vehicle_id": 1, "target_station_id": 1})
    check(r.status_code in (200, 404, 503), f"eta unexpected status={r.status_code}")
    print(f"PASS eta status={r.status_code}")

    # 18. 推荐（在没有站点数据时应返回 404）
    r = client.post("/api/v1/recommend-routes", json={
        "start_station_id": 1, "end_station_id": 2, "preference": "balanced"
    })
    check(r.status_code in (200, 404, 503), f"recommend status={r.status_code}")
    print(f"PASS recommend-routes status={r.status_code}")

    # 19. AI（没配置 key 时返回 503）
    r = client.post("/api/v1/ai/travel", json={"mode": "qa", "question": "你好"})
    check(r.status_code in (200, 503), f"ai status={r.status_code}")
    print(f"PASS ai/travel status={r.status_code}")

    # 20. 管理员 LTA 刷新（无 LTA key 时返回 503）
    r = client.post("/api/v1/admin/lta/bus-arrival/refresh", json={
        "bus_stop_code": "01012", "service_no": "15", "sync_to_db": False
    })
    check(r.status_code in (200, 503), f"lta refresh status={r.status_code}")
    print(f"PASS admin lta refresh status={r.status_code}")

    print("\nALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()