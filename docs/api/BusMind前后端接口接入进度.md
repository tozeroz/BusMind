# BusMind前后端接口接入进度

> 更新时间：2026-07-12。状态依据当前代码静态核查与运行时 OpenAPI；没有测试记录的页面调用不得标为“已验证”。负责人未在仓库中明确，统一记为“待分配”。

## 状态定义

`未开发`、`后端开发中`、`后端已完成未封装`、`前端已封装未接入`、`前端接入中`、`已接入待测试`、`已接入已验证`、`存在问题`、`暂不接入`、`已废弃`。

## 当前进度

| 模块 | 页面 | 前端方法 | 后端路径 | 当前状态 | 请求字段是否一致 | 返回字段是否一致 | Mock | 当前问题 | 下一步任务 | 负责人 | 验证方式 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 用户登录 | LoginView | `loginUser` | `POST /users/login` | 前端已封装未接入 | 否：account/username | 未验证 | 是 | 无条件跳转、无 Token | 接入登录与角色跳转 | 待分配 | 真实账号登录、401/400、刷新保持登录 |
| 用户注册 | RegisterView | `registerUser` | `POST /users/register` | 前端已封装未接入 | 否：name/phone 与 Schema 冲突 | 未验证 | 是 | 提交后直接进首页 | 明确手机号并接入 | 待分配 | 201、409、422 与数据库记录 |
| 当前用户 | 未实现页面 | `getCurrentUser`,`updateCurrentUser` | `GET/PATCH /users/me` | 前端已封装未接入 | 是（封装层） | 未验证 | 否 | 无页面调用 | 建个人中心并验证 Token | 待分配 | Bearer Token、401、字段回显 |
| 收藏/历史 | 未实现页面 | favorites/history 方法 | `/users/me/favorites`,`/query-history` | 前端已封装未接入 | 是（封装层） | 未验证 | 否 | 无页面调用 | 设计页面和分页 | 待分配 | 增删查、page/limit、空列表 |
| 地图站点/线路 | HomeView/BusMap | `getMapStations`,`getMapLines`,`getRoadSegments` | `/map/*` | 前端已封装未接入 | 是 | 否：组件读 Mock GeoJSON | 是 | BusMap 完全使用本地源 | 建地图数据适配器 | 待分配 | 地图真实点线、空数据、重复加载 |
| 位置搜索 | HomeView | `searchLocations`,`getNearbyLocations` | `/locations/search`,`/nearby` | 前端已封装未接入 | 未构造真实请求 | 未验证 | 是 | 搜索和定位都是本地函数 | 接入防抖搜索与浏览器定位 | 待分配 | keyword、坐标、无结果、权限拒绝 |
| 路线推荐 | HomeView | `recommendRoutes` | `POST /recommend-routes` | 存在问题 | 目标偏好枚举不一致 | 否：页面模型未适配 | 是 | 后端只收 low_load，正式口径为 comfort | 先补别名映射，再接页面 | 待分配 | 五种正式偏好、low_load 兼容、结果展示 |
| 首页 AI | HomeView | `askAiTravel` | `POST /ai/travel` | 前端已封装未接入 | 未构造真实请求 | 未验证 | 是 | 本地函数与 API 名称重叠 | 改名并接入 API | 待分配 | qa/suggest/explain、fallback、错误态 |
| 独立 AI | AiAssistantView | `sendAiMessage` | `POST /ai/travel` | 已接入待测试 | 是 | 部分：answer/reminders | 是 | 未注册路由；无成功证据；固定站点 | 注册路由并做联调 | 待分配 | 网络抓包、成功响应、fallback、503 |
| 线路列表 | LineListView | `getLines` | `GET /lines` | 前端已封装未接入 | 页面未请求 | 否：Mock 字段不同 | 是 | 未注册路由 | 接基础列表与分页 | 待分配 | page/limit/filter、空页 |
| 线路详情/站序 | LineDetailView | `getLineDetail`,`getLineStations` | `/lines/{id}`,`/stations` | 前端已封装未接入 | 页面未请求 | 未适配 | 是 | 从 Mock 数组查详情 | 接路由参数及并行加载 | 待分配 | 正常/404、站序方向 |
| 实时车辆 | VehicleView | `getRealtimeVehicles`,`getVehiclesByLine` | `/vehicles/realtime`,`/vehicles/line/{id}` | 前端已封装未接入 | 页面未请求 | 否：视图字段不同 | 是 | 未注册路由、地图占位 | 接列表、刷新和离线态 | 待分配 | line_id 筛选、定时刷新、空车辆 |
| 实时 ETA | Home/Line/Vehicle | `getEta` | `GET /eta` | 前端已封装未接入 | 页面未请求 | 否：eta_minutes/predicted_eta_minutes | 是 | 术语仍像自研预测 | 基于 LTA 实时口径接入并适配字段 | 待分配 | 对照 LTA 到站、时间戳、503 |
| 实时 Load | Home/Line/Vehicle | `predictPassengerLoad` | `POST /passenger-load-prediction` | 存在问题 | 封装一致 | 未验证 | 是 | 路径/Schema仍称 prediction，业务口径为 LTA 实时客载 | 明确是否重命名并保兼容 | 待分配 | 对照 LTA Load 枚举与展示 |
| 历史 Passenger Flow | PassengerFlowView | `getPassengerFlowTrend` | `GET /history/passenger-flow` | 前端已封装未接入 | 页面未请求 | 未验证 | 静态占位 | 页面文案仍写预测预留路径 | 改历史分析页并接趋势 | 待分配 | 时间范围、粒度、图表数据 |
| Passenger Flow prediction | PassengerFlowView | `getPassengerFlowPrediction` | `/history/passenger-flow/prediction` | 暂不接入 | 是（封装层） | 未验证 | 否 | 不属于第一阶段模型 | 从核心页面移除 | 待分配 | 确认无页面请求 |
| 后台基础 CRUD | AdminView | transit/vehicle CRUD | `/lines`,`/stations`,`/vehicles` | 前端已封装未接入 | 页面未请求 | 未验证 | 是 | 后端写接口无 admin 鉴权 | 先定权限再接入 | 待分配 | 权限、CRUD、冲突码 |
| LTA 正式刷新 | AdminView | 无 | `POST /admin/lta/*/refresh` | 后端已完成未封装 | 否 | 未验证 | 否 | 前端缺正式封装 | 新增 admin API 封装 | 待分配 | 配置/未配置密钥、sync_to_db |
| LTA 旧刷新 | 无 | `refreshLtaBusArrival` | `POST /simulation/lta-bus-arrival/refresh` | 已废弃 | 是 | 未验证 | 否 | OpenAPI deprecated，仍被 index 导出 | 停止新增使用，后续移除封装 | 待分配 | 全仓搜索无页面调用 |
| 兼容 bus 路径 | 无 | `getBus*` 多为主函数别名 | `/bus-lines`,`/bus-stations`,`/bus-vehicles` | 前端已封装未接入 | 部分：封装实际打主路径 | 未验证 | 否 | 函数名看似兼容路径，实际调用正式路径 | 文档注明，勿误判 | 待分配 | 网络抓包确认实际 URL |

## 结论

- 当前唯一能确认“页面实际调用”的是独立 AI 页面，但它没有路由入口，也没有联调成功证据，因此状态只能是“已接入待测试”。
- 其余多数项目属于“前端已封装未接入”，不能沿用旧文档的“已接入”表述。
- 当前没有足够证据把任何业务页面接口标为“已接入已验证”。
