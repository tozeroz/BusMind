# BusMind项目运行与接口验收说明

本说明是本轮前后端接口接入补丁的操作手册。完整进度、文件清单和遗留问题见同目录《BusMind前后端接口接入进度》文档。

## 一、如何合并

1. 备份当前工作分支并提交未提交代码。
2. 将交付压缩包解压到原 BusMind 项目根目录。
3. 允许覆盖同名文件；压缩包只含本轮新增/修改文件，不含完整项目。
4. 执行 `git status` 和 `git diff --check`，再按团队流程处理冲突。主要改动范围仅为 `frontend` 接口接入和 `docs/api` 文档。

## 二、安装与启动

### 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

根目录 `.env` 示例：

```env
DATABASE_URL=mysql+pymysql://busmind_dev:你的密码@127.0.0.1:3307/busmind?charset=utf8mb4
LTA_ACCOUNT_KEY=你的_LTA_DataMall_AccountKey
```

仅做空库检查时：

```env
DATABASE_URL=sqlite:///./busmind.db
AUTO_CREATE_TABLES=true
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器打开 `http://127.0.0.1:5173`，后端 Swagger 为 `http://127.0.0.1:8000/docs`。

## 三、自动验证

```bash
cd frontend
npm run test:api-contract
npm run build
```

后端启动后：

```bash
BUSMIND_API_BASE_URL=http://127.0.0.1:8000/api/v1 npm run test:api-live
```

项目已有隔离数据库接口冒烟：

```bash
cd 项目根目录
PYTHONPATH=backend:. python backend/scripts/smoke_frontend_links.py
```

预期：契约测试显示 72 个操作全部有策略；前端构建成功；在线冒烟在空库下通过基础接口，数据依赖项可能显示 SKIP；项目已有冒烟最后输出 `ALL SMOKE TESTS PASSED`。

## 四、浏览器验收

按以下顺序在 DevTools Network 中检查：

1. 注册/登录：`/users/register`、`/users/login`、`/users/me`。
2. 首页地图：`/map/stations`、`/map/lines`、`/map/road-segments`。
3. 搜索/定位：`/locations/search`、`/locations/nearby`。
4. 推荐/智能：`/recommend-routes`、`/eta`、`/passenger-load-prediction`、`/ai/travel`。
5. 线路/车辆：`/lines`、`/lines/{id}`、`/lines/{id}/stations`、`/vehicles/realtime`、`/vehicles/line/{id}`。
6. 历史：`/history/passenger-flow`、`/history/eta/...`、`/history/load/...`；页面不应请求 `/history/passenger-flow/prediction`。
7. 个人中心：`/users/me/favorites`、`/users/me/query-history`。
8. 管理端：线路、站点、车辆、站序 CRUD；LTA 刷新先用 `sync_to_db=false`。

每个请求需要满足：URL/方法/字段符合 Swagger；成功响应 `code=0`；页面读取真实 `data`；错误时显示后端 message/detail；没有继续展示伪 Mock 结果。

## 五、常见问题

- **接口 404**：检查 `VITE_API_BASE_URL` 是否重复或缺少 `/api/v1`，以及 Vite proxy。
- **接口 500/no such table**：数据库没有初始化；空 SQLite 需 `AUTO_CREATE_TABLES=true`，完整页面需导入真实数据。
- **地图空白但接口 200**：确认站点经纬度、线路 path_coordinates 或 road segments 有数据。
- **推荐 comfort 返回 422**：当前后端枚举仍使用 `low_load`；本补丁前端已兼容，后端后续应补 `comfort` 映射。
- **LTA 503**：配置 `LTA_ACCOUNT_KEY`，并确认网络可访问 DataMall。
- **管理员能否真正防越权**：前端已做路由守卫，但后端写接口仍需服务端 admin 鉴权。
