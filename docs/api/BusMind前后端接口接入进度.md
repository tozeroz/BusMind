# BusMind前后端接口接入进度

> 更新时间：2026-07-12（重点联调后）。状态依据 `BusMind(2).zip` 当前代码、真实 Uvicorn HTTP、隔离数据库数据和前端生产构建。没有浏览器 Network/交互记录的页面仍标为“已接入待测试”，不误标“已接入已验证”。

## 状态定义

`未开发`、`后端开发中`、`后端已完成未封装`、`前端已封装未接入`、`前端接入中`、`已接入待测试`、`已接入已验证`、`存在问题`、`暂不接入`、`已废弃`。

## 当前进度

| 模块 | 页面 | 前端方法 | 后端路径 | 当前状态 | 请求字段是否一致 | 返回字段是否一致 | Mock | 当前问题 | 下一步任务 | 负责人 | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 用户登录 | LoginView | `loginUser` | `POST /users/login` | 已接入待测试 | 是：页面将 account 映射为 username | 是：读取 access_token/user.role | 否 | 后端 400 错误仍嵌套 detail；缺浏览器记录 | 浏览器验证登录、角色跳转、刷新保持 | 待分配 | HTTP 200/400 已验证；待 Network/交互 |
| 用户注册 | RegisterView | `registerUser` | `POST /users/register` | 已接入待测试 | 是：username/password/nickname/role | 是 | 否 | 409 错误嵌套 detail；缺浏览器记录 | 浏览器验证成功跳转和错误提示 | 待分配 | HTTP 201/409/422 与数据库记录已验证 |
| 当前用户 | ProfileView | `getCurrentUser`,`updateCurrentUser` | `GET/PATCH /users/me` | 已接入待测试 | 是 | GET 已验证；PATCH 未复测 | 否 | 页面已存在并注册，但本轮未测修改昵称 | 复测 PATCH、401、Token 失效 | 待分配 | Bearer GET 200 已验证 |
| 收藏/历史 | ProfileView | favorites/history 方法 | `/users/me/favorites`,`/query-history` | 已接入待测试 | 是 | 是（目标 pytest 通过） | 否 | 缺浏览器交互记录 | 验证增删收藏、分页和空列表 | 待分配 | 后端目标测试通过；待页面 Network |
| 地图站点/线路 | HomeView/BusMap | `getMapStations`,`getMapLines`,`getRoadSegments` | `/map/*` | 已接入待测试 | 是 | 是：stations/lines/path_coordinates | 否 | 默认数据库零表导致 500；尚未浏览器验图 | 初始化真实数据后检查点线、空数据、重复加载 | 待分配 | 隔离库 HTTP 200 非空；前端构建通过 |
| 位置搜索 | HomeView | `searchLocations`,`getNearbyLocations` | `/locations/search`,`/nearby` | 已接入待测试 | 是（页面已构造 keyword/坐标） | 静态核查一致，未复测 | 否 | 依赖真实站点数据和定位权限 | 复测关键词、坐标、无结果、权限拒绝 | 待分配 | 代码静态核查；本轮非重点未 HTTP 复测 |
| 路线推荐 | HomeView | `recommendRoutes` | `POST /recommend-routes` | 存在问题 | balanced 可用；comfort 仍 422 | 是：items 适配完整 | 否 | 正式偏好 comfort 与 OpenAPI 冲突；依赖线路数据 | 后端增加 comfort 兼容后做浏览器验收 | 待分配 | balanced/low_load 200；comfort 422 已复现 |
| 首页 AI | HomeView | `askAiTravel` | `POST /ai/travel` | 存在问题 | qa/question 一致；context 字段不一致 | answer 可读；related_routes 常为空 | 否 | 页面传 visible_routes，后端只识别 items/data.items | 传原始推荐 items 或改 suggest+站点 ID | 待分配 | QA fallback 200 已验证；页面待修改 |
| 独立 AI | AiAssistantView | `sendAiMessage` | `POST /ai/travel` | 已接入待测试 | 是 | 是：answer/reminders/fallback | 有初始静态会话 | 路由已注册；无 Key 时为本地 fallback 200 | 浏览器验证问答、fallback 和 422 | 待分配 | HTTP 200 fallback=true、422 已验证 |
| 线路列表 | LineListView | `getLines` | `GET /lines` | 存在问题 | 是：page/limit | lines 字段一致；total 被前端减 1 | 否 | 默认数据库零表 500；页面 total 算法错误 | 初始化数据并移除 total - 1 | 待分配 | HTTP 200 非空、422 已验证；待页面修复 |
| 线路详情/站序 | LineDetailView | `getLineDetail` | `GET /lines/{id}` | 存在问题 | 是 | 详情/站序一致；实时车辆解析错误 | 否 | 页面只认车辆 data/items，后端返回 data.vehicles | 修正车辆解包并浏览器验收 | 待分配 | 详情 200/404、stations 顺序已验证 |
| 实时车辆 | VehicleView/LineDetailView | `getRealtimeVehicles`,`getVehiclesByLine` | `/vehicles/realtime`,`/vehicles/line/{id}` | 存在问题 | 是 | VehicleView 一致；LineDetailView 不一致 | 否 | 同一响应在详情页被错误解包 | 统一复用 unwrapList(response,'vehicles') | 待分配 | 字段静态核查；本轮未单独计入重点接口 |
| 实时 ETA | LineDetailView | `getEta` | `GET /eta` | 已接入待测试 | 是 | 是：predicted_eta_minutes 等 | 否 | 依赖车辆、ETA/LTA 数据；默认库为空 | 用真实 LTA 时间戳复测 | 待分配 | 页面静态核查；本轮非重点 |
| 实时 Load | Home/Line/Vehicle | `predictPassengerLoad` | `POST /passenger-load-prediction` | 存在问题 | 封装一致 | 页面已兼容主要枚举，未复测 | 否 | 路径/Schema仍称 prediction，业务口径为 LTA 实时客载 | 明确版本化命名并保兼容 | 待分配 | 本轮非重点未 HTTP 复测 |
| 历史 Passenger Flow | Home/PassengerFlowView/AdminView | `getPassengerFlowTrend` | `GET /history/passenger-flow` | 已接入待测试 | 是 | 是：items/summary | 否 | 默认库无历史数据 | 导入数据后验证时间范围、粒度和图表 | 待分配 | 页面静态核查；隔离库确认有数据可存 |
| Passenger Flow prediction | PassengerFlowView | `getPassengerFlowPrediction` | `/history/passenger-flow/prediction` | 存在问题 | 是 | 静态核查一致 | 否 | 页面当前实际调用，但第一阶段口径要求暂不接入 | 产品确认后移除调用或调整定位 | 待分配 | 全仓搜索确认页面调用；本轮未 HTTP 复测 |
| 后台基础 CRUD | AdminView | transit/vehicle 查询与 CRUD 封装 | `/lines`,`/stations`,`/vehicles` | 已接入待测试 | 查询一致 | 概览字段静态核查一致 | 否 | 写接口仍无 admin 鉴权；本轮未做破坏性 CRUD | 先加权限，再用测试库验证 CRUD | 待分配 | 概览代码静态核查；未做写操作 |
| LTA 正式刷新 | AdminView | `refreshAdminLtaBusArrival`,`refreshAdminLtaTrafficSpeedBands` | `POST /admin/lta/*/refresh` | 存在问题 | 是 | 503 结构已验证 | 否 | 缺 LTA_ACCOUNT_KEY；真实刷新未验证 | 配置 Key 后在测试库复测 sync_to_db | 待分配 | 无 Key 返回 HTTP 503/code 50320 |
| LTA 旧刷新 | 无 | `refreshLtaBusArrival` | `POST /simulation/lta-bus-arrival/refresh` | 已废弃 | 是 | 未复测 | 否 | OpenAPI deprecated，仍由 index 导出 | 停止新增使用，后续版本移除封装 | 待分配 | 全仓搜索无页面调用 |
| 兼容 bus 路径 | 无 | `getBus*` 仍为主函数别名 | `/bus-lines`,`/bus-stations`,`/bus-vehicles` | 前端已封装未接入 | 部分：函数实际打主路径 | 未复测 | 否 | 函数名易让审计误判真实 URL | 文档继续按真实 URL 记录 | 待分配 | 代码静态核查 |

## 本轮联调交付

| 交付项 | 结果 |
|---|---|
| 已联调接口数量 | 11 个唯一接口 |
| 当天重点接口数量 | 8 个 |
| 当天重点后端合约验证 | 8/8 通过 |
| 页面已接入已验证 | 0；缺浏览器 Network/交互记录，不虚报 |
| 配置阻塞 | 1；LTA 刷新缺少 Key，返回 503 |
| 后端目标测试 | 25 passed、4 failed；失败均指向空默认数据库/依赖覆盖问题 |
| 前端生产构建 | 通过，114 modules transformed |

## 当前问题摘要

1. P0：默认数据库没有表和可展示数据，线路与地图在默认启动下返回 500。
2. P1：推荐正式偏好 `comfort` 返回 422，仅 `low_load` 可用。
3. P1：LineDetailView 错读 `data.vehicles`；LineListView 错减 total。
4. P1：首页 AI 的 `context.visible_routes` 不被后端识别。
5. P1：错误响应外壳和时间戳时区不统一。
6. P1：没有配置 LTA/DeepSeek Key；LTA 是 503，AI 则正常降级为 fallback 200。

详细请求、字段和修复清单见 `docs/api/BusMind重点接口联调报告.md`。
