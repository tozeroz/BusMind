# BusMind 服务端工程师 B 使用说明

## 1. 本代码包含的功能

本压缩包只包含服务端工程师 B 负责的模块，没有实现用户、线路、站点、车辆等服务端 A 接口，也没有实现数据处理工程师负责的模型训练代码。

已实现接口：

```text
GET  /api/v1/eta
POST /api/v1/passenger-load-prediction
POST /api/v1/walking-time-estimation
POST /api/v1/travel-experience/evaluate
POST /api/v1/recommend-routes
POST /api/v1/ai/travel
```

实现内容：

- ETA 模型适配与规则降级
- 客载状态模型适配与规则降级
- 步行时长估算
- 出行体验三指标计算
- 最佳体验、最快、最宽松、最少步行、最少换乘路线选择
- 推荐理由生成
- DeepSeek AI 出行建议与解释
- DeepSeek 不可用时的模板降级
- 统一响应格式、业务错误码和校验错误处理
- 单元测试、集成测试和 Postman Collection

## 2. 目录合并方式

将压缩包解压到 BusMind 项目根目录，选择合并目录。不要删除队友已有文件。

压缩包只会写入以下范围：

```text
backend/app/
backend/tests/
algorithm/recommend/
llm/
tests/integration/
tools/postman/
docs/api/
```

不会修改：

```text
backend/app/api/v1/user/
backend/app/api/v1/line/
backend/app/api/v1/station/
backend/app/api/v1/vehicle/
backend/app/db/
backend/app/models/
backend/app/repositories/
algorithm/eta_prediction/
algorithm/load_prediction/
database/
frontend/
```

## 3. Python 环境准备

建议使用 Python 3.11 或 3.12。Windows PowerShell 示例：

```powershell
cd C:\你的路径\BusMind
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r docs\api\requirements-service-b.txt
```

使用 uv：

```powershell
cd C:\你的路径\BusMind
uv venv --python 3.12
.\.venv\Scripts\Activate.ps1
uv pip install -r docs\api\requirements-service-b.txt
```

如果 Windows 商店版 Python 创建虚拟环境时报错，改用 python.org 安装的 Python 3.12 x64，并在 `uv venv --python 3.12` 中明确指定版本。

## 4. 接入 DeepSeek

### 4.1 获取 API Key

在 DeepSeek 开放平台创建 API Key，并确认账户存在可用额度。不要把 API Key 提交到 GitHub。

当前代码使用 DeepSeek 的 OpenAI 兼容接口：

```text
Base URL: https://api.deepseek.com
Model: deepseek-v4-flash
Endpoint: /chat/completions
```

AI 助手默认关闭思考模式，适合公交建议和路线解释，减少延迟和 Token 消耗。

### 4.2 临时设置环境变量

Windows PowerShell：

```powershell
$env:DEEPSEEK_API_KEY="你的API Key"
$env:DEEPSEEK_BASE_URL="https://api.deepseek.com"
$env:DEEPSEEK_MODEL="deepseek-v4-flash"
```

CMD：

```cmd
set DEEPSEEK_API_KEY=你的API Key
set DEEPSEEK_BASE_URL=https://api.deepseek.com
set DEEPSEEK_MODEL=deepseek-v4-flash
```

Linux/macOS：

```bash
export DEEPSEEK_API_KEY="你的API Key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
export DEEPSEEK_MODEL="deepseek-v4-flash"
```

本模块不自动读取 `.env`，避免与服务端 A 的配置方案冲突。如果团队项目已经使用 `python-dotenv` 或 `pydantic-settings`，由共享入口加载环境变量即可。

### 4.3 未配置 API Key 时

接口不会崩溃。`POST /api/v1/ai/travel` 会返回结构化模板回答：

```json
{
  "fallback": true
}
```

配置正确并成功调用 DeepSeek 后：

```json
{
  "fallback": false
}
```

## 5. 独立运行服务端 B

在项目根目录执行：

```powershell
uvicorn backend.app.intelligence_demo:app --reload --host 127.0.0.1 --port 8000
```

检查：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

独立入口只用于服务端 B 自测，不会替代服务端 A 的正式 `main.py`。

## 6. 合并到服务端 A 的 FastAPI 入口

在团队共享 FastAPI 入口中添加：

```python
from backend.app.api.v1.intelligence_router import router as intelligence_router
from backend.app.core.exception_handlers import register_intelligence_exception_handlers

register_intelligence_exception_handlers(app)
app.include_router(intelligence_router, prefix="/api/v1")
```

注意：

- 如果服务端 A 的总路由已经带 `/api/v1` 前缀，只包含 `intelligence_router`，不要再次添加前缀。
- 如果服务端 A 已经实现统一异常处理，可以不调用 `register_intelligence_exception_handlers(app)`，但返回结构需包含 `code`、`message`、`data`、`trace_id`、`timestamp`。
- 不要同时注册两次相同路由。

## 7. 对接服务端 A 的数据库查询

当前包含 `DemoIntelligenceGateway`，只用于没有数据库时进行 Postman 和答辩演示。正式联调时，服务端 A 编写一个适配器，实现以下读取方法：

```python
from backend.app.services.intelligence_gateway import configure_intelligence_gateway

class MysqlIntelligenceGateway:
    async def get_station(self, station_id): ...
    async def get_vehicle(self, vehicle_id): ...
    async def get_distance_to_station_meters(self, vehicle_id, target_station_id): ...
    async def get_remaining_stop_count(self, vehicle_id, target_station_id): ...
    async def get_station_flow_level(self, station_id, hour): ...
    async def get_candidate_routes(self, start_station_id, end_station_id, max_transfer_count): ...
    async def find_nearest_station(self, longitude, latitude): ...

configure_intelligence_gateway(MysqlIntelligenceGateway())
```

该适配器只读取服务端 A 已有 Repository，不需要修改服务端 B 的接口和算法代码。

## 8. 对接数据处理工程师的 ETA 模型

默认尝试加载：

```text
algorithm.eta_prediction.models.predict_eta:predict_eta
```

数据处理工程师提供：

```python
def predict_eta(features: dict) -> dict:
    return {
        "predicted_eta_minutes": 7.4,
        "model_version": "eta_random_forest_v1"
    }
```

也可以只返回数字：

```python
def predict_eta(features: dict) -> float:
    return 7.4
```

模型路径不同，通过环境变量设置：

```powershell
$env:BUSMIND_ETA_PREDICTOR="你的模块路径:函数名"
```

模型不存在、导入失败或执行异常时，系统自动使用 `eta_rule_v1`，接口仍然可用。

## 9. 对接数据处理工程师的客载状态模型

默认尝试加载：

```text
algorithm.load_prediction.models.predict_load:predict_load
```

建议返回：

```python
def predict_load(features: dict) -> dict:
    return {
        "predicted_onboard_count": 46,
        "predicted_load_rate": 0.77,
        "predicted_load_level": "SDA",
        "confidence": 0.84,
        "model_version": "load_xgb_v1"
    }
```

支持模型标签：

```text
SEA -> seats_available
SDA -> standing_available
LSD -> limited_standing
```

模型路径不同：

```powershell
$env:BUSMIND_LOAD_PREDICTOR="你的模块路径:函数名"
```

模型不可用时自动使用 `load_rule_v1`。

## 10. 出行体验指标口径

按最新图片和接口文档，综合分只包含：

```text
客载量指标
步行时长指标
换乘次数指标
```

默认权重：

```text
experience_score =
0.50 * load_score
+ 0.30 * walk_score
+ 0.20 * transfer_score
```

ETA 不计入 `experience_score`，只用于：

- 页面展示
- 总耗时计算
- `fastest` 路线选择

示例：

```text
predicted_load_rate = 0.77 -> load_score = 58
walk_time_minutes = 6.5 -> walk_score = 84
transfer_count = 0 -> transfer_score = 100
experience_score = 74.2
```

## 11. 使用 Postman

导入：

```text
tools/postman/BusMind-Service-B.postman_collection.json
tools/postman/BusMind-Local.postman_environment.json
```

选择环境 `BusMind Local`，确保：

```text
base_url = http://127.0.0.1:8000/api/v1
```

按文件夹顺序执行：

```text
ETA
Passenger Load
Walking Time
Travel Experience
Recommendation
AI Travel
```

“综合路线推荐”请求会自动把响应 `data` 保存到环境变量 `recommend_context`，后续“AI 路线解释”会直接使用该上下文。

## 12. 运行自动化测试

项目根目录执行：

```powershell
pytest -q backend/tests tests/integration
```

本次交付实测结果：

```text
18 passed
```

## 13. 常见问题

### AI 接口一直 fallback=true

检查：

```powershell
echo $env:DEEPSEEK_API_KEY
```

然后重启 Uvicorn。环境变量必须在启动服务的同一个终端中设置。

### DeepSeek 返回 401

API Key 不正确、已删除或没有正确传入。

### DeepSeek 返回 402

账户余额不足。

### DeepSeek 返回 429

调用过快，稍后重试。

### 推荐接口只有演示数据

这是预期行为。正式数据由服务端 A 的数据库 Gateway 和数据处理工程师模型替换，服务端 B 不负责创建基础线路、站点和车辆数据库接口。

### 模型文件还没有交付

无需阻塞联调。ETA 和客载接口会使用规则降级，`model_version` 分别显示：

```text
eta_rule_v1
load_rule_v1
```
