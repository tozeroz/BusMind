# BusMind前后端接口接入进度

> 更新时间：2026-07-12（最终接口核验、重复目录清理与完整项目交付）
> 核对基线：本次上传的 `BusMind (2)(1).zip`、`tyy` 分支 HEAD、运行时 FastAPI OpenAPI v1.2.0、前端契约表、页面真实调用、Vue 单文件组件编译检查、隔离 SQLite HTTP 冒烟测试。
> 状态原则：API 文件存在不等于页面已接入；只有页面源码中存在真实函数调用才标记为“已接入”。兼容、内部、暂缓、废弃接口不为凑数量强行加入业务页面。

## 1. 本轮结论

- 运行时 OpenAPI 共 **72 个操作**，与 `frontend/src/api/contract.js` 的 72 条记录逐项一致，没有发现新增或遗漏操作。
- 其中 **45 个产品页面操作已接入**，静态审计确认共有 61 个真实页面调用点；所有标记为 `connected` 的接口都在 Vue 页面/组件中实际执行。
- 本轮没有发现仍需补接的产品页面接口，因此未改动后端业务、算法、数据库模型或其他成员负责的模块。
- 其余操作均有明确边界：11 个旧路径兼容封装、12 个内部/按需封装、1 个第一阶段暂缓、1 个已废弃、1 个只返回方法提示、1 个后端根健康检查。它们不是漏接，不应为了“全调用”而强行放进业务页面。
- 已删除上一轮误复制出的 `backend/frontend/` 不完整前端镜像，以及 `backend/docs/api/` 的三份完全重复文档；唯一有效前端为根目录 `frontend/`，唯一项目文档目录为根目录 `docs/`。
- 已增强 `frontend/tests/api-contract.mjs`：除检查 72 个操作和封装函数外，还会检查所有 `connected` 接口必须存在页面调用，并阻止兼容、暂缓、废弃接口被现行页面误用。

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
| 运行时 OpenAPI 核对 | 通过：72/72 | 直接导入 `app.main:app` 并读取 `app.openapi()` |
| 前端契约与页面调用 | 通过：72/72；45 个 connected、61 个调用点 | `npm run test:api-contract`；同时检查禁用状态接口未被页面调用 |
| Vue 单文件组件编译 | 通过：14/14 | 使用 `@vue/compiler-sfc` 逐个解析并编译 `<script>` 与 `<template>` |
| 前端生产构建 | 本轮环境未复跑 | 上传包内 `node_modules` 是 Windows 依赖，当前 Linux 容器缺少 Rollup 对应原生可选模块，且无法从依赖源重新安装；本轮未改动 Vue 业务源码。请在目标机器执行 `npm install` 后运行 `npm run build` |
| 项目端到端接口冒烟 | 通过：ALL SMOKE TESTS PASSED | 隔离 SQLite，覆盖注册、登录、用户、收藏、线路、车辆、历史、位置、地图、ETA、推荐、AI、LTA 共 20 个检查点 |
| 精确重复文件审计 | 通过 | 排除依赖、虚拟环境、构建产物后，不再存在需要删除的“同名且内容相同”业务文件组 |
| 差异格式检查 | 通过 | `git diff --check` 无空白错误 |
| 浏览器 Network/人工交互 | 尚未执行 | 需要在有真实数据的本机环境按第 7 节验收 |

## 6. 本轮文件变更

### 删除的完全重复目录

- `backend/frontend/`：上一轮误复制出的不完整前端镜像；项目入口、README、Vite 配置均只使用根目录 `frontend/`。
- `backend/docs/api/`：其中三份文档与根目录 `docs/api/` 对应文件逐字节相同；统一保留根目录文档。

### 修改

- `frontend/tests/api-contract.mjs`：新增“页面真实调用”与“禁止误用兼容/暂缓/废弃接口”检查。
- `docs/api/BusMind前后端接口接入进度.md`
- `docs/api/BusMind前后端接口接入进度.docx`
- `README.md`：明确唯一前端和文档目录，防止再次产生镜像副本。

> 未修改后端接口实现、算法、数据库模型、数据脚本和其他成员业务代码。

## 7. 项目使用与完整验收步骤

### 7.1 解压完整项目包

交付压缩包是可独立使用的完整项目源码，不是补丁包。解压后进入最外层 `BusMind/` 目录即可。为避免跨平台污染和压缩包过大，交付包不包含 `.git/`、虚拟环境、`node_modules/`、`dist/`、缓存和 IDE 配置；这些目录都可按下文命令重新生成。

目录约定：

- 前端只使用 `frontend/`，不要再创建 `backend/frontend/`。
- 项目文档只使用 `docs/`，不要再创建 `backend/docs/`。
- 后端入口为 `backend/app/main.py`，启动目录为 `backend/`。

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

## 8. 最终接口与重复文件判定

### 8.1 是否还有前后端接口没接

没有发现仍需补接的产品页面接口。72 个运行时操作均已进入契约台账；45 个产品页面操作存在真实页面调用。以下状态不计为漏接：

- `compatibility`：旧路径别名，仅用于兼容历史客户端，新页面继续使用正式路径。
- `encapsulated`：内部仿真、辅助查询或暂无明确产品触发场景的按需能力，已有统一封装。
- `deferred`：Passenger Flow prediction 按第一阶段口径暂不进入页面。
- `deprecated`：已废弃路径，禁止新增页面调用。
- `unsupported/backend_only`：方法提示或部署健康检查，不属于业务页面。

### 8.2 重复文件清理结果

已删除 29 个重复文件组成的两个冗余目录树：`backend/frontend/` 和 `backend/docs/api/`。重新按“文件名相同 + SHA-256 内容相同”审计后，业务源码和项目文档中不再有需要合并的重复组。仍保留的同内容文件只有以下合理类型：不同 Python 包必须各自存在的 `__init__.py`、用于保留空目录的 `.gitkeep`、以及 Postman 各集合自身需要的 `definition.yaml`。

## 9. 仍需项目环境或后端负责人处理的事项

1. 默认 SQLite 配置 `AUTO_CREATE_TABLES=false` 且没有业务表，会导致部分接口 500；需要初始化数据库或使用已导入数据的 MySQL。
2. 后端 OpenAPI 当前仍接受 `low_load` 而不接受正式业务值 `comfort`；本轮前端已做兼容，但后端最终应支持 `comfort -> low_load` 映射。
3. 后端线路/站点/车辆写接口当前未绑定 admin 鉴权；前端路由守卫只能改善交互，不能代替服务端授权。
4. LTA 刷新需要真实 `LTA_ACCOUNT_KEY`；无 Key 时无法验证真实采集和入库。
5. 浏览器人工验收需有真实线路、站点、车辆和 LTA 数据，空 SQLite 只能验证合约与空态。
6. 后端全量测试存在默认库、异步插件和测试夹具问题，属于原项目测试环境问题，本轮未改动以避免与后端成员冲突。
