# BusMind 重点接口联调检查结果

> 目标：`http://127.0.0.1:8000`；生成时间：2026-07-12T10:18:29+08:00

通过 9，失败 0，阻塞 1。

| 模块 | 检查 | 请求 | 状态 | HTTP | 说明 |
|---|---|---|---|---:|---|
| 环境 | API v1 健康检查 | `GET /api/v1/` | PASS | 200 | code=0 且包含 trace_id |
| 登录注册 | 注册 | `POST /api/v1/users/register` | PASS | 201 | 返回 user_id/username |
| 登录注册 | 登录 | `POST /api/v1/users/login` | PASS | 200 | 返回 access_token/user |
| 登录注册 | Bearer Token | `GET /api/v1/users/me` | PASS | 200 | code=0 且包含 trace_id |
| 线路列表 | 列表与分页 | `GET /api/v1/lines?page=1&limit=20` | PASS | 200 | data.lines=20 |
| 线路详情 | 详情与站序 | `GET /api/v1/lines/797` | PASS | 200 | line_id=797，stations=0 |
| 地图 | 站点坐标 | `GET /api/v1/map/stations` | PASS | 200 | data.stations=5205 |
| 地图 | 线路折线 | `GET /api/v1/map/lines` | PASS | 200 | data.lines=796 |
| AI 助手 | QA 与 fallback | `POST /api/v1/ai/travel` | PASS | 200 | answer 已返回，fallback=False |
| 路线推荐 | 综合推荐 | `POST /api/v1/recommend-routes` | BLOCKED | - | 线路详情不足两个站点 |
