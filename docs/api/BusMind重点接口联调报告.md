# BusMind 重点接口联调报告

> 联调日期：2026-07-12。代码基线：用户提供的 `BusMind(2).zip`。本轮只做环境启动、接口联调、故障定位、字段/数据核查与文档更新，没有新增或修改业务接口。

## 1. 本轮结论

| 统计项 | 数量 | 口径 |
|---|---:|---|
| 实际联调的唯一接口 | 11 | 健康检查、注册、登录、当前用户、线路列表、线路详情、地图站点、地图线路、AI、推荐、LTA 刷新 |
| 当天重点接口 | 8 | 注册、登录、线路列表、线路详情、地图站点、地图线路、AI、推荐 |
| 当天重点后端合约验证通过 | 8 | 使用隔离 SQLite 测试库，通过真实 Uvicorn HTTP 请求验证 |
| 额外验证接口 | 2 | `GET /api/v1/`、`GET /users/me` |
| 配置阻塞接口 | 1 | LTA 刷新按预期返回 503，缺少 `LTA_ACCOUNT_KEY` |
| 重点页面浏览器验收 | 0 | 本轮完成生产构建和静态字段核查，但没有浏览器 Network/视觉操作记录，不标为页面已验证 |

## 2. 环境和数据库检查

1. 后端可正常启动，`GET /` 与 `GET /api/v1/` 均返回 200。
2. 项目默认 `DATABASE_URL=sqlite:///./busmind.db`，同时 `AUTO_CREATE_TABLES=False`。
3. 压缩包内没有 `.env`、可用数据库文件、processed CSV 或种子业务数据。
4. 默认启动后生成的 `backend/busmind.db` 为 0 字节、0 张表；`GET /lines`、`GET /map/stations`、`GET /map/lines` 均返回 500，日志根因为 `sqlite3.OperationalError: no such table: bus_line`。
5. 使用隔离 SQLite 数据库创建完整 ORM 表并加入 1 条线路、3 个站点、1 辆车、ETA/Load/客流/地图路段记录后，六个重点模块均可返回可展示数据。

结论：当前业务 500 不是路由 404，也不是字段 422，而是数据库未初始化、无数据。部署联调前必须配置 MySQL 并执行建表、processed 数据生成和导入。

## 3. 重点接口结果

| 模块 | 请求 | 成功验证 | 异常验证 | 字段核查 |
|---|---|---|---|---|
| 注册 | `POST /api/v1/users/register` | 201，返回 `user_id/username/role` | 重复用户名 409；短用户名 422 | 前端已传 `username/password/nickname/role`，一致 |
| 登录 | `POST /api/v1/users/login` | 200，返回 `access_token/token_type/expires_in/user` | 错误密码 400 | LoginView 已把 `account` 转为 `username` 并保存 Token，一致 |
| 线路列表 | `GET /api/v1/lines?page=1&limit=20` | 200，`data.lines` 非空，`total=1` | `limit=101` 返回 422 | 列表字段一致；前端错误地把 `total` 减 1 |
| 线路详情 | `GET /api/v1/lines/1` | 200，返回线路和 3 条 `stations` | 不存在 ID 返回 404 | 主详情字段一致；详情页实时车辆读取字段不一致 |
| 地图站点 | `GET /api/v1/map/stations` | 200，3 个站点，含经纬度和线路关联 | 默认空库返回 500 | BusMap 使用 `data.stations`，字段一致 |
| 地图线路 | `GET /api/v1/map/lines` | 200，返回非空 `path_coordinates` | 默认空库返回 500 | BusMap 使用 `data.lines/path_coordinates`，字段一致 |
| AI 助手 | `POST /api/v1/ai/travel` | 无 DeepSeek Key 时仍返回 200，`fallback=true` | QA 缺 question 返回 422 | `answer/reminders/related_routes/fallback` 契约正常 |
| 路线推荐 | `POST /api/v1/recommend-routes` | `balanced`、`low_load` 返回 200 和 `data.items` | 正式值 `comfort` 返回 422 | 页面当前 balanced 可用；正式偏好仍冲突 |

## 4. 404、422、500、503 定位

| 状态码 | 已复现场景 | 定位结论 |
|---:|---|---|
| 404 | `GET /lines/999999` | 正常资源不存在，返回体目前嵌套在 `detail` 内 |
| 422 | 注册字段过短、`limit=101`、AI QA 缺问题、推荐传 `comfort` | 前三项是正确参数校验；`comfort` 是文档与 OpenAPI 冲突 |
| 500 | 默认数据库下访问线路/地图 | 数据库零表，`no such table: bus_line`；响应为纯文本 Internal Server Error |
| 503 | 未配置 Key 调用 `/admin/lta/bus-arrival/refresh` | 正确返回业务码 50320；配置 `LTA_ACCOUNT_KEY` 后才能联调真实 LTA |

## 5. 存在问题列表

### 后端待修复

1. P0：明确联调环境 `.env`，初始化 MySQL 表并导入可展示数据；当前压缩包不能直接展示线路和地图。
2. P1：推荐请求接受正式偏好 `comfort`，并把旧值 `low_load` 作为兼容别名。
3. P1：统一 400/404/409 错误外壳；用户和线路模块当前返回 `detail.{code,message...}`，与统一错误响应不一致。
4. P1：统一时区。用户/线路响应记录为运行机器本地 `-05:00`，智能模块为 `+08:00`。
5. P1：数据库异常应转换为带 `trace_id` 的统一 500 响应，并在启动期给出“表未初始化”的明确检查结果。
6. P2：修复推荐与主程序集成测试的数据库依赖覆盖。本轮相关测试结果为 25 passed、4 failed，4 个失败均由空默认数据库引起。

### 前端待修改

1. P1：`LineDetailView.vue` 的实时车辆解析需要读取 `response.data.vehicles`；当前只读取数组或 `data.items`，会把后端真实车辆显示为空。
2. P1：`LineListView.vue` 不应执行 `response.data.total - 1`，应直接使用后端 total。
3. P1：首页 AI 当前传 `context.visible_routes`，后端只识别 `context.items` 或 `context.data.items`；需要传原始推荐结果，或改用 suggest 模式并传站点 ID。
4. P1：在浏览器完成六个重点页面的 Network 和交互验收，再把状态从“已接入待测试”提升为“已接入已验证”。
5. P2：抽取统一错误解析，兼容标准错误外壳、`detail` 嵌套和纯文本 500。

## 6. 测试证据

- 真实 Uvicorn HTTP：重点接口 8/8 后端合约通过。
- 错误分支：201/200/400/404/409/422/500/503 均有实际响应记录。
- 后端目标测试：25 passed、4 failed；失败原因已列入后端待修复。
- 前端生产构建：Vite 114 modules transformed，构建成功；仅有既有的大 chunk 警告。

## 7. 复测命令

后端启动且数据库准备完成后，在 `backend/` 目录执行：

```bash
python scripts/verify_priority_integration.py \
  --base-url http://127.0.0.1:8000 \
  --report priority-integration-result.md
```

脚本会创建一个唯一测试用户，仅应对开发或测试数据库执行。全部检查为 PASS 时退出码为 0；失败或数据不足时退出码为 1，并在报告中注明原因。
