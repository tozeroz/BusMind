# BusMind前后端接口接入进度

> 更新时间：2026-07-12（本轮接口补齐交付）  
> 核对基线：`BusMind(4).zip` 当前代码、运行时 FastAPI OpenAPI v1.2.0、项目接口文档、前端接口需求说明、前端生产构建、隔离 SQLite HTTP 冒烟测试。  
> 状态原则：API 文件存在不等于页面已接入；未取得浏览器 Network/交互记录的页面统一标记为“已接入待浏览器验收”，不虚报为“已验证”。

## 1. 本轮结论

- 运行时 OpenAPI 的 **72 个操作已逐项建立前端处理台账**：45 个页面已接入、11 个兼容接口已显式封装、12 个内部/按需接口已封装、1 个第一阶段暂缓、1 个已废弃、1 个仅返回方法提示、1 个根健康检查仅供后端部署使用。
- 所有当前产品页面要求使用的正式接口已完成封装和页面调用；`frontend/src/api` 继续作为统一接口层。
- 本轮不修改后端算法、数据库模型和他人业务实现，仅补齐前端接口层、页面调用、路由鉴权、响应适配、契约测试和文档。
- `GET /history/passenger-flow/prediction` 按项目口径继续保留封装但不接页面；已废弃的 `POST /simulation/lta-bus-arrival/refresh` 仅保留兼容封装，不新增页面调用。

## 2. 状态定义

`已接入待浏览器验收`：页面已经真实 import 并调用后端接口，已通过构建/契约或 HTTP 冒烟测试，但尚无浏览器 Network 与人工交互记录。  
`已封装按需调用`：接口封装和合约存在，当前页面没有明确触发场景。  
`兼容封装`：旧路径仍由后端运行，为避免漏接已建立独立封装，但新页面继续使用正式主路径。  
`暂不接入`：文档明确当前阶段不应放入页面。  
`已废弃`：后端 OpenAPI 已标记 deprecated，禁止新增调用。

## 3. 页面与模块接入进度

| 模块/页面 | 主要接口 | 本轮完成内容 | 当前状态 | 验收重点 |
|---|---|---|---|---|
| 登录 LoginView | `POST /users/login`、`GET /users/me` | `account -> username`；保存 Token 与用户角色；失败清理会话；按角色跳转 | 已接入待浏览器验收 | 正确/错误密码、管理员跳转、刷新保持 |
| 注册 RegisterView | `POST /users/register` | 请求字段与后端一致；统一错误提示；成功返回登录页 | 已接入待浏览器验收 | 201、409、422 提示 |
| 路由与权限 | 前端路由守卫 | 未登录拦截；管理员页角色校验；访客页重定向 | 已接入待浏览器验收 | 无 Token、乘客访问 `/admin`、退出登录 |
| 个人中心 ProfileView | `/users/me`、收藏、查询历史 | 用户、收藏、历史真实加载；昵称更新同步本地用户；错误统一处理 | 已接入待浏览器验收 | 401、空列表、收藏增删、昵称修改 |
| 首页地图 HomeView/BusMap | `/map/stations`、`/map/lines`、`/map/road-segments` | 三接口均真实调用；路段作为线路几何兜底；移除页面对 Mock 的依赖 | 已接入待浏览器验收 | 空数据、真实折线、重复加载、地图报错 |
| 位置搜索/附近站点 | `/locations/search`、`/locations/nearby` | 搜索与定位请求字段对齐；统一错误处理 | 已接入待浏览器验收 | 无结果、定位拒绝、坐标与半径 |
| 路线推荐 | `POST /recommend-routes` | 原始推荐 items 留存；视图字段适配；舒适偏好按当前后端契约发送 `low_load` | 已接入待浏览器验收 | 两站选择、空结果、后端修复 `comfort` 后回归 |
| 首页 AI | `POST /ai/travel` | 将后端可识别的 `context.items` 传入；有起终点时使用 suggest；保留 fallback 信息 | 已接入待浏览器验收 | QA、建议、无 Key fallback、422 |
| 独立 AI 页面 | `POST /ai/travel` | 去除伪历史对话；展示 fallback/trace；统一错误提示 | 已接入待浏览器验收 | 正常回答、fallback、错误响应 |
| 线路列表 | `GET /lines` | 服务端搜索与分页；修复 `total - 1`；字段适配 | 已接入待浏览器验收 | 搜索、防抖、翻页、空数据 |
| 线路详情/站序 | `/lines/{id}`、`/lines/{id}/stations` | 详情与站序并行读取；修复实时车辆 `data.vehicles` 解包 | 已接入待浏览器验收 | 详情 404、站序、路由参数切换 |
| 实时车辆 | `/vehicles/realtime`、`/vehicles/line/{id}` | 首页、线路详情、车辆页统一读取 `vehicles`；线路接口作为兜底 | 已接入待浏览器验收 | 有/无 line_id、离线车辆、空列表 |
| 实时 ETA | `GET /eta` | 首页、线路详情、车辆详情均已建立真实触发路径 | 已接入待浏览器验收 | 目标站缺失、404/503、LTA 数据时间 |
| 实时客载 | `POST /passenger-load-prediction` | 首页、线路详情、车辆详情均已实际调用并展示 | 已接入待浏览器验收 | 三档客载、容量缺失、车辆线路不一致 |
| 历史客流 | `GET /history/passenger-flow` | 首页、客流页、管理概览真实调用；客流页定位为历史分析 | 已接入待浏览器验收 | hour/day/week、空数据、图表字段 |
| 历史 ETA/Load | `/history/eta/...`、`/history/load/...` | 线路详情与客流页按场景调用；新增通用历史聚合封装 | 已接入待浏览器验收/按需封装 | 时间范围、空记录、分页 |
| Passenger Flow prediction | `/history/passenger-flow/prediction` | 保留 API 封装与契约记录，移除页面调用 | 暂不接入（符合第一阶段口径） | 产品确认后再启用 |
| 管理端基础 CRUD | `/lines`、`/stations`、`/vehicles` | 列表、创建、编辑、删除均接入；站点经过线路查询 | 已接入待浏览器验收 | 建议在测试库做写操作；后端仍缺 admin 鉴权 |
| 管理端线路站序 | `/lines/{id}/stations`、`/lines/stations/{id}` | 增加站点、上下移动、移除站点均接入 | 已接入待浏览器验收 | 顺序冲突、重复站点、方向字段 |
| LTA 管理刷新 | `/admin/lta/*/refresh` | 正式入口已接入；健康状态已接入 `/api/v1/` | 已接入待环境验收 | 需配置 LTA Key；测试库验证 `sync_to_db` |
| 兼容路径 | `/bus-lines`、`/bus-stations`、`/bus-vehicles/realtime`、`/location/*` | 11 个运行中兼容操作建立显式封装 | 兼容封装 | 新页面不得改回旧路径 |
| 仿真/评价/步行 | simulation、evaluate、walking | 保留统一封装；当前页面无明确独立触发入口 | 已封装按需调用 | 由产品场景决定页面入口 |

## 4. 本轮修复的关键问题

1. Axios 默认前缀统一为 `/api/v1`，并支持 `VITE_API_BASE_URL` 与 `VITE_API_TIMEOUT`。
2. 统一处理 `{ code, message, data, trace_id, timestamp }`，业务 `code != 0` 会进入失败分支；同时兼容 FastAPI `detail` 错误。
3. 线路列表不再错误地把 `total` 减 1。
4. 线路详情正确读取实时车辆的 `data.vehicles`。
5. 首页 AI 不再发送后端无法识别的 `visible_routes`，改为 `context.items`。
6. 地图补接 `/map/road-segments`，在主线路缺少几何时作为兜底。
7. ETA 和实时客载不再只是 API 文件中的“已封装”，而是在首页、线路详情、车辆页建立真实调用。
8. Passenger Flow prediction 从页面移除，避免与“第一阶段历史分析、不宣传预测模型”的项目口径冲突。
9. 管理端补齐线路、站点、车辆、线路站序 CRUD，并保留后端权限现状警告。
10. 新增 72 操作契约台账和可重复执行的在线 HTTP 冒烟测试。

## 5. 自动验证结果

| 验证项 | 结果 | 说明 |
|---|---|---|
| OpenAPI 操作映射 | 通过：72/72 有明确处理策略 | `npm run test:api-contract` |
| 前端生产构建 | 通过：118 modules transformed | `npm run build`；仅有包体积 warning，不影响构建 |
| Node 在线 HTTP 冒烟 | 通过：9 PASS、3 SKIP | 隔离空 SQLite；数据依赖项因无站点/车辆而跳过 |
| 项目已有端到端接口冒烟 | 通过：ALL SMOKE TESTS PASSED | 注册、登录、用户、收藏、线路、车辆、历史、位置、地图、ETA、推荐、AI、LTA 共 20 个检查点 |
| 管理端 CRUD 请求体冒烟 | 通过 | 隔离 SQLite 完成线路、站点、车辆、线路站序的创建、查询、修改和删除 |
| 后端全量现有测试 | 76 passed、15 failed、5 errors 后停止 | 失败集中于默认 SQLite 未建表、异步测试插件/夹具缺失、1 个旧兼容测试返回模型假设；本轮未改后端 |
| 后端重点测试组合 | 72 passed、8 failed | 8 个失败均因默认数据库没有 `bus_station`/`bus_vehicle` 表 |
| 差异格式检查 | 通过 | `git diff --check` 无空白错误 |
| 浏览器 Network/人工交互 | 尚未执行 | 需要在有真实数据的本机环境按第 7 节验收 |

## 6. 已新增或修改文件

### 新增

- `frontend/src/api/response.js`
- `frontend/src/api/health.js`
- `frontend/src/api/compatibility.js`
- `frontend/src/api/contract.js`
- `frontend/tests/api-contract.mjs`
- `frontend/tests/live-api-smoke.mjs`
- `docs/api/BusMind前后端接口接入进度.md`
- `docs/api/BusMind前后端接口接入进度.docx`
- `docs/api/BusMind项目运行与接口验收说明.md`

### 修改

- `frontend/package.json`
- `frontend/src/api/request.js`
- `frontend/src/api/index.js`
- `frontend/src/api/history.js`
- `frontend/src/api/user.js`
- `frontend/src/router/index.js`
- `frontend/src/components/map/BusMap.vue`
- `frontend/src/views/login/LoginView.vue`
- `frontend/src/views/login/RegisterView.vue`
- `frontend/src/views/home/HomeView.vue`
- `frontend/src/views/ai-assistant/AiAssistantView.vue`
- `frontend/src/views/line/LineListView.vue`
- `frontend/src/views/line/LineDetailView.vue`
- `frontend/src/views/vehicle/VehicleView.vue`
- `frontend/src/views/recommend/PassengerFlowView.vue`
- `frontend/src/views/profile/ProfileView.vue`
- `frontend/src/views/admin/AdminView.vue`

## 7. 项目使用与完整验收步骤

### 7.1 合并本交付包

交付压缩包是补丁式目录树，只包含上节列出的新增/修改文件。将压缩包解压到原 BusMind 项目根目录并允许覆盖同名文件；不要把压缩包当作完整项目单独运行。

### 7.2 配置后端

在项目根目录创建 `.env`，至少配置：

```env
DATABASE_URL=mysql+pymysql://busmind_dev:你的密码@127.0.0.1:3307/busmind?charset=utf8mb4
LTA_ACCOUNT_KEY=你的_LTA_DataMall_AccountKey
```

只做空库基础测试时可使用 SQLite：

```env
DATABASE_URL=sqlite:///./busmind.db
AUTO_CREATE_TABLES=true
```

正式页面验收建议使用已执行建表和数据导入的 MySQL，否则地图、推荐、ETA、客载只能得到空数据、404 或跳过。

### 7.3 启动后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

打开 `http://127.0.0.1:8000/docs`，确认标题为 BusMind API v1.2.0，并先访问 `http://127.0.0.1:8000/api/v1/`。

### 7.4 启动前端

```bash
cd frontend
npm install
npm run dev
```

默认前端地址：`http://127.0.0.1:5173`。默认 API 前缀是 `/api/v1`，由 Vite 代理到后端。若需要直连其他地址，在 `frontend/.env.development` 设置：

```env
VITE_API_BASE_URL=/api/v1
VITE_API_TIMEOUT=8000
```

### 7.5 自动检查

```bash
cd frontend
npm run test:api-contract
npm run build
```

后端启动后再执行：

```bash
# macOS/Linux
BUSMIND_API_BASE_URL=http://127.0.0.1:8000/api/v1 npm run test:api-live

# Windows PowerShell
$env:BUSMIND_API_BASE_URL="http://127.0.0.1:8000/api/v1"
npm run test:api-live
```

运行项目已有隔离数据库冒烟：

```bash
cd 项目根目录
PYTHONPATH=backend:. python backend/scripts/smoke_frontend_links.py
```

Windows PowerShell 可改为：

```powershell
$env:PYTHONPATH="backend;."
python backend/scripts/smoke_frontend_links.py
```

### 7.6 浏览器验收顺序

1. 在 DevTools → Network 中勾选 Preserve log，清空请求记录。
2. 注册普通用户，确认 `/users/register` 为 201；重复用户名确认 409/422 提示可读。
3. 登录，确认 `/users/login`、必要时 `/users/me`；Application/Storage 中存在 `busmind_access_token` 与 `busmind_current_user`。
4. 刷新页面，确认仍保持登录；删除 Token 后访问 `/home` 应回到 `/login`。
5. 首页确认依次出现 `/map/stations`、`/map/lines`、`/map/road-segments`；搜索触发 `/locations/search`；定位触发 `/locations/nearby`。
6. 选择起终点并推荐，确认 `/recommend-routes` 请求的 preference 使用后端当前可接受值；选择路线/车辆后确认 `/eta` 与 `/passenger-load-prediction`。
7. 首页 AI 与 `/ai` 页面确认调用 `/ai/travel`；无 DeepSeek Key 时应显示后端 fallback，而不是前端伪造答案。
8. `/lines` 验证搜索和分页总数；进入详情验证 `/lines/{id}`、`/lines/{id}/stations`、`/vehicles/realtime` 或 `/vehicles/line/{id}`、ETA/Load。
9. `/vehicles` 选择线路和车辆，确认实时车辆、详情、ETA、Load 请求。
10. `/passenger-flow` 只应调用历史客流/历史 Load，不应调用 `/history/passenger-flow/prediction`。
11. 管理员登录 `/admin`，先在测试库完成线路、站点、车辆、站序 CRUD；确认每个写请求后列表刷新。生产数据库不要直接做删除测试。
12. 配置 LTA Key 后测试两个 `/admin/lta/*/refresh`；先使用 `sync_to_db=false`，确认返回后再在测试库改为 true。

### 7.7 判断“接对了”的标准

- Network 请求 URL、方法、Query/Body 与 OpenAPI 一致。
- HTTP 2xx 且统一响应 `code=0`；错误时页面展示后端 `message/detail`，不会静默使用 Mock。
- 页面展示字段来自 `response.data` 中真实字段；列表能正确处理空数组，总数不被错误修改。
- 401 会清除 Token；乘客不能通过前端路由进入管理端。
- 页面不调用已废弃接口，不调用第一阶段明确暂缓的 Passenger Flow prediction。
- 刷新页面、快速切换条件、空数据和后端断开时无白屏、无未处理 Promise 错误。

## 8. 仍需项目环境或后端负责人处理的事项

1. 默认 SQLite 配置 `AUTO_CREATE_TABLES=false` 且没有业务表，会导致部分接口 500；需要初始化数据库或使用已导入数据的 MySQL。
2. 后端 OpenAPI 当前仍接受 `low_load` 而不接受正式业务值 `comfort`；本轮前端已做兼容，但后端最终应支持 `comfort -> low_load` 映射。
3. 后端线路/站点/车辆写接口当前未绑定 admin 鉴权；前端路由守卫只能改善交互，不能代替服务端授权。
4. LTA 刷新需要真实 `LTA_ACCOUNT_KEY`；无 Key 时无法验证真实采集和入库。
5. 浏览器人工验收需有真实线路、站点、车辆和 LTA 数据，空 SQLite 只能验证合约与空态。
6. 后端全量测试存在默认库、异步插件和测试夹具问题，属于原项目测试环境问题，本轮未改动以避免与后端成员冲突。
