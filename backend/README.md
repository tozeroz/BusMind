# BusMind 后端目录说明

后端采用 FastAPI + SQLAlchemy。为减少多人协作时的合并冲突，本次整理不批量移动既有业务文件，只明确目录职责，并把新增道路拥堵热力能力收口到独立服务包。

```text
backend/
├── app/
│   ├── api/v1/                     # HTTP 路由，仅做参数校验与响应封装
│   ├── cache/                      # 缓存键和缓存实现
│   ├── core/                       # 配置、统一响应、异常、时间工具
│   ├── db/                         # 数据库连接与结构检查
│   ├── dependencies/               # 鉴权和数据库依赖
│   ├── models/                     # SQLAlchemy ORM，文件使用 snake_case
│   ├── repositories/               # 数据访问封装
│   ├── schemas/                    # Pydantic 请求/响应模型
│   └── services/                   # 业务服务
│       └── traffic_heatmap_service/ # 推荐路线道路拥堵匹配与分段着色
├── scripts/
│   ├── legacy/                     # 历史排查脚本，不作为正式入口
│   └── README.md                   # 正式脚本用途和执行方式
├── tests/                          # Pytest 测试
└── start.py                        # 本地启动入口
```

## 正式启动

在项目根目录执行：

```powershell
uv sync
Copy-Item .env.example .env
uv run python backend\start.py
```

后端固定读取仓库根目录 `.env`。该文件也是 algorithm、数据脚本和本地工具共用的唯一真实配置；不要再维护 `backend/.env` 的第二份配置。

也可以进入后端目录后直接启动 Uvicorn：

```powershell
Set-Location backend
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```


## 数据库连接自检

在项目根目录执行：

```powershell
uv run python backend\scripts\check_database_connection.py
```

脚本只显示脱敏后的数据库目标，不会输出用户名或密码。成功时显示 `database_connection: ok`。

## 测试

```powershell
uv run pytest backend\tests -q
```

新增功能的重点测试：

```powershell
uv run pytest backend\tests\test_history_map_api.py backend\tests\test_traffic_heatmap_api.py -q
```

## 目录维护规则

- Python 包、模块、函数和变量使用 `snake_case`。
- API 路径使用小写短横线，例如 `/api/v1/map/traffic-heatmap`。
- 路由层不直接编写复杂 SQL 或空间匹配逻辑；业务逻辑放入 `services`。
- 临时排查脚本放入 `scripts/legacy`，正式自动化脚本保留在 `scripts` 根目录并在 `scripts/README.md` 登记。
- 不提交 `.env`、本地数据库、日志、缓存和测试产物。
