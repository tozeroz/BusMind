# BusMind 智行公交系统

BusMind 是一个面向公交出行场景的智能推荐系统。项目围绕公交线路、站点、车辆实时状态、ETA 到站时间、车辆客载状态和出行体验评分，提供路线推荐、地图展示、历史趋势查询和 AI 出行助手等功能。

当前项目使用新加坡 LTA DataMall 数据作为主要数据来源，已经包含原始数据采集、CSV 清洗、MySQL 导入、后端实时采集缓存、ETA/客载/推荐接口和前端页面展示。

## 技术栈

| 模块 | 技术 |
|---|---|
| 前端 | Vue 3、Vite、Axios、MapLibre |
| 后端 | FastAPI、SQLAlchemy、Pydantic |
| 数据库 | MySQL，开发时也可使用 SQLite |
| 数据处理 | Python、Pandas |
| 实时数据 | LTA DataMall Bus Arrival、Traffic Speed Bands |

## 目录结构

```text
frontend/      前端 Vue 项目
backend/       后端 FastAPI 服务
database/      MySQL 建表和导入脚本
data/          LTA 原始数据、清洗后 CSV 和采集脚本
algorithm/     ETA、客载和推荐相关算法
docs/          接口文档、数据库文档和项目文档
postman/       接口测试集合
```

## 环境准备

需要提前安装：

- Python 3.12 左右
- Node.js 18+ 或 20+
- MySQL 8.x，若只看基础页面和部分接口，可先用默认 SQLite

后端 `.env` 放在项目根目录：

```env
DATABASE_URL=mysql+pymysql://busmind_dev:密码@127.0.0.1:3307/busmind?charset=utf8mb4
LTA_ACCOUNT_KEY=你的_LTA_DataMall_AccountKey
```

`.env` 已被 `.gitignore` 忽略，不要把真实密钥提交到仓库。

## 启动后端

```powershell
cd path\to\BusMind\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python start.py
```

也可以直接使用 Uvicorn；项目入口会自动加载根目录下的 `algorithm` 和 `llm` 模块，无需手动设置 `PYTHONPATH`：

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端默认启动在：

```text
http://127.0.0.1:8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 启动前端

```powershell
cd path\to\BusMind\frontend
npm install
npm run dev
```

前端默认启动在：

```text
http://127.0.0.1:5173
```

前端开发环境默认请求：

```text
/api/v1
```

如需修改后端地址，可调整 `frontend/.env.development` 或 Vite 代理配置。

## 初始化数据库和导入数据

先在 MySQL 中创建数据库和用户，然后执行建表 SQL：

```powershell
mysql -u busmind_dev -p busmind < .\database\schema\init_busmind.sql
```

如果需要重新生成 processed CSV：

```powershell
python .\data\processed\process_scripts\build_lta_processed_data.py
```

导入清洗后的 CSV：

```powershell
python .\database\import\import_processed_to_mysql.py --processed-dir .\data\processed --dry-run
python .\database\import\import_processed_to_mysql.py --processed-dir .\data\processed
```

## LTA 实时采集接口

后端提供了第一阶段的手动刷新入口：

```text
POST /api/v1/admin/lta/bus-arrival/refresh
POST /api/v1/admin/lta/traffic-speed-bands/refresh
```

示例：

```json
{
  "bus_stop_code": "83139",
  "service_no": "15",
  "sync_to_db": true
}
```

```json
{
  "sync_to_db": true
}
```

## 常用接口

| 功能 | 接口 |
|---|---|
| 线路查询 | `GET /api/v1/lines` |
| 站点查询 | `GET /api/v1/stations` |
| 实时车辆 | `GET /api/v1/vehicles/realtime` |
| ETA 计算 | `GET /api/v1/eta` |
| 客载预测 | `POST /api/v1/passenger-load-prediction` |
| 路线推荐 | `POST /api/v1/recommend-routes` |
| AI 出行助手 | `POST /api/v1/ai/travel` |

完整接口说明见：

```text
docs/api/BusMind项目接口文档.md
```

## 运行测试

后端目标测试：

```powershell
cd path\to\BusMind\backend
python -m pytest tests\test_lta_refresh_service.py tests\test_admin_lta_refresh_api.py
python -m pytest tests\test_database_schema_alignment.py
```

注意：部分集成测试依赖本地 MySQL 已启动并且数据表已初始化。

## 项目状态

当前已完成第一阶段核心链路：

```text
LTA DataMall
  -> raw 数据采集
  -> processed CSV 清洗
  -> MySQL 导入
  -> FastAPI 查询和推荐接口
  -> 前端页面展示
```

实时链路也已有基础实现：

```text
LTA Bus Arrival / Traffic Speed Bands
  -> MemoryCacheProvider
  -> CacheSyncService
  -> MySQL
  -> ETA / Load / Recommend 服务读取
```

后续主要工作是继续完善真实 MySQL 联调、推荐算法中的路况拥堵分使用，以及生产环境鉴权和部署。
