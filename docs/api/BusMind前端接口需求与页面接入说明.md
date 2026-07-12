# BusMind前端接口需求与页面接入说明

> 依据：2026-07-12 当前 `frontend/src`、运行时 OpenAPI v1.2.0。本文描述页面需求与真实调用，不以“API 文件存在”等同于“页面已接入”。原《接口说明.md》当前工作树缺失，本文件沿用其“统一说明—页面清单—核心页面—模块页面—Mock 替换—检查清单”框架重建。

## 一、统一说明

- Axios 位于 `frontend/src/api/request.js`，默认 `baseURL` 为 `/api/v1`（通过 `VITE_API_BASE_URL` 环境变量或硬编码兜底）。
- 响应拦截器返回 `response.data`，所以页面拿到统一外壳，业务数据仍在 `response.data`。
- 当前统一追踪字段为 `trace_id`。页面尚未读取或展示该字段。
- API 封装存在只说明“前端已封装”；只有 Vue 页面实际 import 并执行函数，才算“页面实际调用”。
- 推荐正式偏好为 `balanced`、`fastest`、`comfort`、`less_walking`、`less_transfer`；`low_load` 仅作兼容别名。当前运行时 OpenAPI 已同时接受 `comfort` 和 `low_load`，前端可直接使用正式值 `comfort`。
- **ETA 字段适配层**：`src/utils/eta.js` 提供 `getEtaMinutes(item)` 和 `formatEtaDisplay(item)`，统一从 `predicted_eta_minutes` / `eta_minutes` / `eta` / `total_time_minutes` 中提取 ETA 分钟数。页面应通过适配层访问 ETA，避免直接硬编码字段名。BusMap 的 mock 数据已使用 `predicted_eta_minutes` 作为规范字段名。**注意**：ETA 数据来源为 LTA Bus Arrival 实时数据（MySQL 缓存），非自研 ETA 预测模型；字段 `predicted_eta_minutes` / `model_version` 为历史兼容命名。

## 二、页面总览

| 页面 | 路由现状 | API 实际调用 | Mock/静态数据 | 结论 |
|---|---|---|---|---|
| LoginView | `/login` | 无 | 固定 demo 账号，直接跳转 | 未接入 |
| RegisterView | `/register` | 无 | 提交后直接跳转 | 未接入 |
| HomeView | `/home` | 无 | 地图、搜索、推荐、AI 全为本地数据 | 未接入 |
| AdminView | `/admin` | 无 | `adminStats` 与表格均静态 | 未接入 |
| AiAssistantView | `/ai` | `sendAiMessage` | QA 模式已验证（code=0, fallback=true）；catch 降级提示 | 已接入待测试 |
| LineListView | `/lines` | 无 | `mockData.lines` | 未接入 |
| LineDetailView | `/lines/:id` | 无 | `mockData.lines/vehicles` | 未接入 |
| VehicleView | `/vehicles` | 无 | `mockData.lines/vehicles` | 未接入 |
| PassengerFlowView | `/passenger-flow` | `getPassengerFlowTrend`、`getPassengerFlowPrediction`、`getLoadPredictionsByLine`、`getLoadPrediction` | 真实数据渲染（趋势图、统计卡片、预测卡片、客载卡片） | 已接入 |

## 三、按页面接入说明

### 3.1 LoginView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/login/LoginView.vue` |
| 页面功能 | 账号登录并按角色进入乘客端或管理端 |
| 需要接口 | `POST /api/v1/users/login`，登录后可选 `GET /api/v1/users/me` |
| 触发时机 | 表单提交；成功保存 Token 后拉取用户信息 |
| 请求字段 | `username`、`password`；当前表单字段却是 `account`、`password` |
| 真正使用的返回字段 | 尚未使用；建议 `data.access_token`、`data.token_type`、用户/角色字段以 OpenAPI 和实际响应确认 |
| 当前 API 封装 | `loginUser(data)`、`saveAuthToken(token)`、`getCurrentUser()` |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是，按钮无条件跳转 |
| 当前问题 | 无鉴权、无错误处理、账号字段名不一致、管理员入口可绕过权限 |
| 建议接入方式 | 提交时映射 `account -> username`；校验 `code`；保存 Token；读取用户角色后跳转 |

### 3.2 RegisterView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/login/RegisterView.vue` |
| 页面功能 | 注册账号 |
| 需要接口 | `POST /api/v1/users/register` |
| 触发时机 | 表单提交 |
| 请求字段 | 后端为 `username`、`password`、`nickname?`；页面为 `name`、`phone`、`password` |
| 真正使用的返回字段 | 尚未使用；建议用户标识、用户名、昵称 |
| 当前 API 封装 | `registerUser(data)` |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是，直接跳 `/home` |
| 当前问题 | `name/phone` 与 Schema 不一致；手机号无后端字段 |
| 建议接入方式 | 明确手机号是否进入后端模型；在此之前映射 `name -> username`，成功后跳登录页而非直接登录 |

### 3.3 HomeView.vue 与 BusMap.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/home/HomeView.vue`；`frontend/src/components/map/BusMap.vue` |
| 页面功能 | 地图、位置检索、站点/线路选择、路线推荐、ETA/Load 展示、悬浮 AI |
| 需要接口 | `/map/stations`、`/map/lines`、`/map/road-segments`、`/locations/search`、`/locations/nearby`、`/recommend-routes`、`/eta`、`/passenger-load-prediction`、`/ai/travel` |
| 触发时机 | 地图加载；输入防抖；定位；提交检索；选择路线/站点；打开或提交 AI |
| 请求字段 | 搜索：`keyword,page,limit`；附近：`latitude,longitude,radius_km`；推荐：站点 ID 对或完整坐标对、`preference` 等；ETA：`vehicle_id,target_station_id,line_id?` |
| 真正使用的返回字段 | 当前只使用本地 `title/eta/score/load/id/line_id` 和地图 `stop_id/stop_name/eta_minutes/crowd_level/passing_routes`；与后端推荐的 `items[].predicted_eta_minutes`、`predicted_load`、`experience_score` 尚未适配 |
| 当前 API 封装 | 所需函数均已封装，页面未 import |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是；`mockRoutes`、`mockBusRouteGeoJSON`、`mockBusStopsGeoJSON`、固定定位、固定 AI 回复 |
| 当前问题 | 搜索、推荐、AI 函数均为本地同名逻辑；地图组件完全依赖 Mock；展示字段 `eta_minutes` 与推荐/ETA 现行字段不一致 |
| 建议接入方式 | 先建立页面适配层，把后端 route/station/ETA/load 转成当前视图模型；地图加载三接口并保留明确的演示开关；推荐正式传 `comfort` 前先修复后端兼容映射 |

### 3.4 AiAssistantView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/ai-assistant/AiAssistantView.vue` |
| 页面功能 | AI 出行问答 |
| 需要接口 | `POST /api/v1/ai/travel` |
| 触发时机 | 输入或快捷问题提交 |
| 请求字段 | `mode,question,start_station_id,end_station_id,preference` |
| 真正使用的返回字段 | `data.answer`、`data.reminders` |
| 当前 API 封装 | `sendAiMessage`（`askAiTravel` 别名） |
| 是否实际调用 | 是 |
| 是否仍使用 Mock | 否；实际调用 `POST /api/v1/ai/travel`；`catch` 块展示错误信息作为降级提示 |
| 当前问题 | 固定站点 ID（1→12）；不读取 `fallback`/`used_tools`/`related_routes`/`trace_id`；suggest 模式未验证（需 MySQL） |
| 建议接入方式 | 已联调验证（2026-07-12）：QA 模式成功（code=0, fallback=true），参数校验错误（42200）正常；`answer`/`reminders` 字段正确读取。建议补读 `fallback` 用于区分 AI/本地回答，补读 `trace_id` 用于错误排查。 |

### 3.5 LineListView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/line/LineListView.vue` |
| 页面功能 | 线路列表、搜索、拥挤度展示 |
| 需要接口 | `GET /api/v1/lines`；按需补实时 Load |
| 触发时机 | 页面加载、搜索条件变化/提交、分页 |
| 请求字段 | `page,limit,line_name` |
| 真正使用的返回字段 | 当前 Mock 的 `id,name,start,end,stations,eta,crowd`；后端需适配 `line_id,line_name,start_station,end_station,total_stations` 等 |
| 当前 API 封装 | `getLines(params)` |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是 |
| 当前问题 | `eta/crowd` 不属于线路基础列表稳定字段 |
| 建议接入方式 | 基础列表先接 `/lines`；ETA/Load 按选中线路或可见项异步补充，勿把实时口径写成预测模型 |

### 3.6 LineDetailView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/line/LineDetailView.vue` |
| 页面功能 | 线路信息、站序、关联车辆、ETA/客载 |
| 需要接口 | `/lines/{id}`、`/lines/{id}/stations`、`/vehicles/line/{id}`、`/eta`，必要时 Load |
| 触发时机 | 路由 `line_id` 变化；车辆/目标站选择；实时刷新 |
| 请求字段 | `line_id`；ETA 还需 `vehicle_id,target_station_id` |
| 真正使用的返回字段 | Mock 的线路字段和车辆 `position,next,eta,passengers,capacity,crowd` |
| 当前 API 封装 | `getLineDetail`、`getLineStations`、`getVehiclesByLine`、`getEta` |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是 |
| 当前问题 | 只从 Mock 数组查详情；实时字段与基础车辆字段混杂 |
| 建议接入方式 | 并行加载基础详情、站序、车辆；ETA/Load 单独刷新并在适配层转换 |

### 3.7 VehicleView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/vehicle/VehicleView.vue` |
| 页面功能 | 按线路查看实时车辆、位置、下一站、ETA、客载 |
| 需要接口 | `GET /lines`、`GET /vehicles/realtime`、`GET /vehicles/line/{id}`、`GET /eta` |
| 触发时机 | 页面加载、线路筛选、定时刷新 |
| 请求字段 | 列表 `page,limit`；实时车辆 `line_id?`；ETA 三个标识字段 |
| 真正使用的返回字段 | `id,line,position,next,eta,passengers,capacity,crowd`（当前均来自 Mock） |
| 当前 API 封装 | `getLines`、`getRealtimeVehicles`、`getVehiclesByLine`、`getEta` |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是 |
| 当前问题 | 地图仅占位；`speed_kmh` 与仿真 `speed_kph` 需区分 |
| 建议接入方式 | 线路和车辆分别加载；用 LTA 实时 ETA/Load 更新卡片；设置刷新间隔和离线态 |

### 3.8 AdminView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/admin/AdminView.vue` |
| 页面功能 | 线路、站点、车辆、采集刷新与运行概览 |
| 需要接口 | CRUD `/lines`、`/stations`、`/vehicles`；正式刷新 `/admin/lta/*` |
| 触发时机 | 页面加载、筛选、保存、删除、手动刷新 |
| 请求字段 | 各 CRUD Schema；刷新 `bus_stop_code,service_no?,sync_to_db` 或 `sync_to_db` |
| 真正使用的返回字段 | 当前仅静态统计和表格文本 |
| 当前 API 封装 | CRUD 已封装；正式 admin 刷新 `refreshAdminLtaBusArrival` / `refreshAdminLtaTrafficSpeedBands` 已封装在 `@/api/admin`；旧 simulation 刷新封装（`refreshLtaBusArrival` 等）已标注 @deprecated 并从 index.js 统一导出中移除 |
| 是否实际调用 | 否 |
| 是否仍使用 Mock | 是 |
| 当前问题 | 后端管理写接口已要求 admin 角色（未登录返回 401，已登录但非 admin 返回 403），前端页面入口无额外鉴权门控；旧刷新函数指向废弃路径 |
| 建议接入方式 | 正式 admin 刷新已在 `@/api/admin` 中，直接 import 即可；禁止新页面调用 `@/api/simulation` 已废弃路径 |

### 3.9 PassengerFlowView.vue

| 项目 | 内容 |
|---|---|
| 页面文件 | `frontend/src/views/recommend/PassengerFlowView.vue` |
| 页面功能 | 历史客流分析（趋势图 + 统计卡片 + 近期客流记录 + 线路客载） |
| 需要接口 | `GET /history/passenger-flow`（核心）、`GET /history/passenger-flow/prediction`（兼容/实验）、`GET /history/load/line/{line_id}`（线路客载）、`GET /history/load/{line_id}`（客载回退） |
| 触发时机 | 页面加载（`onMounted`）、粒度切换（hour/day/week）、刷新按钮、线路选择 |
| 请求字段 | `granularity`（hour/day/week），prediction 无参数，load 传 `line_id` |
| 真正使用的返回字段 | trend: `items[].total_flow`、`summary（total_tap_in/total_tap_out/dominant_flow_level）`；prediction: `items[].predicted_flow/predict_time/crowd_level`；load: `predicted_onboard_count/predicted_load_level/predicted_load_rate` |
| 当前 API 封装 | `getPassengerFlowTrend`、`getPassengerFlowPrediction`、`getLoadPredictionsByLine`、`getLoadPrediction` |
| 是否实际调用 | 是，`onMounted` 时并行调用 trend + prediction，选择线路后调用 load |
| 是否仍使用 Mock | 否，全部为真实 API 调用；无数据时展示空状态 |
| 当前问题 | prediction 接口（兼容/实验）在第一阶段页面中直接展示，标题为"近期客流趋势"；客载区域需先选择线路才有数据 |
| 建议接入方式 | 已接入完成；prediction 卡片保留展示但文案不强调"预测"；可将 prediction 区域折叠或加说明标签"近期客流（实验）" |

## 四、组件字段适配重点

| 组件视图字段 | 当前后端字段 | 处理 |
|---|---|---|
| `eta` / `eta_minutes` | `predicted_eta_minutes` | 适配层映射；`predicted_eta_minutes` 为历史兼容命名，实际来自 LTA Bus Arrival 实时数据，非自研预测模型。业务文案统一称"实时 ETA"。 |
| `load` / `crowd` | `predicted_load.predicted_load_level` 或 LTA 客载枚举 | 映射为舒适/可站立/拥挤文案 |
| `score` | `experience_score` | 直接映射并保留数值范围 |
| `id` | `route_id` / `line_id` / `vehicle_id` | 不可用一个通用 `id` 猜测类型 |
| `request_id` | `trace_id` | 统一使用 `trace_id`。注意：`request_id` 仅存在于推荐模型服务内部协议，非 BusMind API 统一外壳。前端页面应读取 `trace_id` 用于错误排查。 |

## 五、替换 Mock 与联调检查清单

1. 页面实际 import 并执行 API 函数后，状态才从“已封装未接入”变为“接入中”。
2. 成功分支读取真实字段并有测试证据后，才可标“已接入已验证”。
3. catch 中固定回答、固定路线或固定车辆仍算存在 Mock。
4. 核对 Axios `baseURL`，避免 `/api` 与 `/api/v1` 错位。
5. 核对 `page/limit`、`trace_id`、`predicted_eta_minutes` 的现行字段。
6. 后端完成 `low_load -> comfort` 映射后，前端统一发送 `comfort`。
7. ETA、Load 页面文案必须标注 LTA 实时来源；Passenger Flow 标注历史分析。
