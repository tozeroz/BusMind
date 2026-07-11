# Scheduler Service

后台调度：定期刷新 Bus Arrival 缓存并同步 MySQL。

> MVP 阶段用 `asyncio.create_task` + 自旋循环实现，**不引入 APScheduler**，
> 因此 `backend/requirements.txt` 不需要新增依赖。

## 做了什么

1. 后端启动时根据 `bus_station` / `bus_line` 选出"热门站点 × 热门线路"。
2. 每隔 `BUSMIND_REFRESH_BUS_ARRIVAL_INTERVAL_SECONDS` 秒（默认 60 秒）调用一次
   `LtaCollectorService.refresh_bus_arrival(stop, service_no)`，
   把响应写入进程内内存缓存 `bus_arrival:{stop_code}` 与 `bus_arrival:{stop_code}:{service_no}`。
3. 紧接调用 `CacheSyncService.sync_bus_arrival(db, stop, service_no)`，
   upsert 到 `bus_vehicle / bus_eta_status / bus_load_status / lta_bus_arrival` 四张表。
4. `MySQLTransitGateway` 的下次查询会优先命中缓存，缓存 miss 时回落到数据库表，
   因此 `/api/v1/eta` 和 `/api/v1/passenger-load-prediction` 在演示时始终拿到最新实时状态。

## 启停流程

| 时机 | 动作 |
|---|---|
| FastAPI `lifespan` 启动 | `await _refresh_scheduler.start()`：若 `LTA_ACCOUNT_KEY` 已配置则启动后台 task；否则只打 log、立即返回（dev / CI 友好） |
| FastAPI `lifespan` 关闭 | `await _refresh_scheduler.stop()`：置 stop event → 等当前 tick 退出（最多一个周期 + 5s） |
| 单 tick 异常 | `logger.exception` 后继续下一 tick，不会让循环挂掉 |

## 默认参数

| 参数 | 默认 | 环境变量 |
|---|---|---|
| interval_seconds | 60 | `BUSMIND_REFRESH_BUS_ARRIVAL_INTERVAL_SECONDS` |
| max_stations | 3 | 构造参数 |
| max_lines | 2 | 构造参数 |

> 默认 3 站 × 2 线路 = 6 次/分钟，远低于 LTA 单账号 250 req/min 上限。

## 站点 / 线路选取

`select_hot_stop_codes / select_hot_service_nos` 当前按 `station_id / line_id` 升序
取前 N 条——稳定可预测。等客流热力数据积累到足够稠密再替换为基于
`passenger_flow_trend.total_flow` 的真实热度排序。

## 文件

```text
backend/app/services/scheduler_service/
├── __init__.py        # 公开 API
└── service.py         # Job 定义、Scheduler、工厂

backend/app/main.py    # lifespan 启动 / 停止 scheduler
```

## 测试

```powershell
cd backend
$env:DATABASE_URL="sqlite:///./busmind_test.db"
python -m pytest tests/test_bus_arrival_scheduler.py -v
```

3 个测试：

- `test_build_refresh_jobs_uses_small_hot_pool`：单测 SQL 选择 + Cartesian 拼装
- `test_scheduler_tick_invokes_collector_and_sync`：单测 collector + sync 调用关系
- `test_scheduler_disabled_when_client_missing`：单测"无 LTA key 时 no-op start"
