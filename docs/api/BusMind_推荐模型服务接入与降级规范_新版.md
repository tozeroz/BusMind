# BusMind 推荐模型服务接入与降级规范

> 状态：当前实施版  
> 规范版本：`1.0.0`  
> 对应数据契约：`BusMind 推荐评分模型输入输出契约 v1.0.0`  
> 当前模型名称：`busmind-route-scorer`  
> 当前模型版本：`0.1.0`  
> 当前模型入口：`algorithm.model.predictor.predict_recommendation(payload)`  
> 适用对象：后端、算法/模型、测试与部署人员  
> 最后更新：2026-07-11

## 1. 文档目标

本文规定 BusMind 后端如何接入推荐评分模型，以及模型不可用、响应异常或契约不兼容时如何回退到规则评分。

模型请求与响应字段、字段类型、偏好枚举和模型输出结构，以《BusMind 推荐评分模型输入输出契约》为唯一依据。本文不重复定义另一套字段体系，只负责说明：

- 后端与模型的调用方式；
- `RouteScoringGateway` 接入边界；
- 本地模型、规则模型和后续 HTTP 模型的切换方式；
- 响应校验、异常处理和整批降级策略；
- 日志、测试、部署和联调要求。

## 2. 当前总体架构

```text
POST /api/v1/recommend-routes
        ↓
RecommendationService
        ├── 起终点匹配
        ├── CandidateRouteService
        ├── 实时 ETA / Load 特征获取
        ├── 历史客流与道路热力特征获取
        ├── 缺失值降级与来源标注
        ↓
RouteScoringGateway
        ├── LocalModelScoringGateway   当前主模式
        ├── RuleBasedScoringGateway    永久降级模式
        └── HttpModelScoringGateway    后续扩展模式
        ↓
后端校验模型结果
        ↓
Top-K 排序、业务标签、结构化推荐理由
        ↓
大模型自然语言解释
        ↓
公开 API 响应
```

后端业务层只能依赖统一的 `RouteScoringGateway`，不得在 Controller 中直接导入算法代码，也不得在路由层拼装模型请求。

## 3. 责任边界

| 能力 | 后端 | 推荐模型 |
|---|:---:|:---:|
| 参数校验、鉴权 | ✅ | - |
| 起终点匹配 | ✅ | - |
| 候选路线生成 | ✅ | - |
| 调用 LTA、MySQL、缓存 | ✅ | - |
| ETA、Load、客流、路况特征组装 | ✅ | - |
| 缺失值降级与来源标注 | ✅ | - |
| 请求契约校验 | ✅ | ✅ |
| 五维子评分计算 | 规则降级 | ✅ |
| 根据 `preference` 选择内部偏好模板 | - | ✅ |
| 综合推荐分计算 | 规则降级 | ✅ |
| Top-K 排序和业务标签 | ✅ | - |
| 结构化推荐理由 | ✅ | - |
| 自然语言解释 | ✅ / LLM | - |
| 公开 HTTP 响应格式 | ✅ | - |
| 模型版本与推理耗时 | 透传 | ✅ |

特别约定：

```text
后端不向模型传递 weights。
模型只接收 preference，并在模型内部选择偏好模板。
payload 中出现 weights 时，模型应返回契约错误。
```

## 4. 接入模式

### 4.1 当前默认：本地模型模式

```env
MODEL_PROVIDER=local
MODEL_FALLBACK_ENABLED=true
MODEL_TIMEOUT_SECONDS=3.0
```

本地模型入口：

```python
algorithm.model.predictor.predict_recommendation(payload)
```

推荐调用关系：

```text
LocalModelScoringGateway
        ↓
predict_recommendation(payload)
        ↓
ModelScoringResponse
```

即使采用本地 Python 调用，也必须复用正式数据契约，不得直接传临时字典或另建字段名称。

### 4.2 规则降级模式

```env
MODEL_PROVIDER=rule
```

规则模式用于：

- 模型尚未完成；
- 模型模块无法导入；
- 模型调用超时；
- 模型返回结果不合法；
- 契约版本不兼容；
- 演示环境需要快速恢复。

规则模式必须与公开推荐接口保持相同输出结构，前端不应感知模型切换。

### 4.3 后续扩展：HTTP 模型服务

```env
MODEL_PROVIDER=http
MODEL_SERVICE_BASE_URL=http://model-service:9000
MODEL_SCORE_PATH=/v1/score-routes
MODEL_TIMEOUT_SECONDS=3.0
MODEL_FALLBACK_ENABLED=true
```

HTTP 模式属于后续扩展。当前项目以本地模型接入为主，但 HTTP 模式仍须复用同一份数据契约。

## 5. Gateway 接口约定

建议统一协议：

```python
from typing import Protocol

class RouteScoringGateway(Protocol):
    async def score_routes(self, payload: dict) -> dict:
        ...
```

实现类：

```text
LocalModelScoringGateway
RuleBasedScoringGateway
HttpModelScoringGateway
```

`RecommendationService` 只调用：

```python
result = await scoring_gateway.score_routes(payload)
```

不得根据 Provider 在业务代码中大量写 `if/else`。Provider 切换应通过配置和依赖注入完成。

## 6. 模型请求构建

一次请求最多评分 10 条候选路线。

顶层请求只包含：

```json
{
  "contract_version": "1.0.0",
  "request_id": "rec_01J2ABCDEF",
  "preference": "comfort",
  "routes": []
}
```

支持的偏好：

```text
balanced
fastest
comfort
less_walking
less_transfer
```

兼容别名：

```text
low_load -> comfort
```

后端在调用模型前必须完成：

1. 候选路线生成；
2. ETA、Load、历史客流、道路热力和可靠性特征组装；
3. 缺失值降级；
4. `feature_sources` 标注；
5. `degraded_fields` 标注；
6. 路线数量限制；
7. 数值范围与有限性校验。

禁止传递：

```text
weights
NaN
Infinity
-Infinity
空字符串作为数值
-1 作为缺失占位
```

## 7. 单条路线特征要求

模型真正使用的 12 个数值特征为：

```text
eta_minutes
ride_time_minutes
walk_time_minutes
walk_distance_meters
transfer_count
load_score
history_flow_score
congestion_score
data_freshness_seconds
monitored_score
completeness_score
avg_service_frequency_minutes
```

后端必须保证这些字段在进入模型前已经成为有效数值。

建议范围：

| 字段 | 约束 |
|---|---|
| `eta_minutes` | `>= 0` |
| `ride_time_minutes` | `>= 0` |
| `walk_time_minutes` | `>= 0` |
| `walk_distance_meters` | `>= 0` |
| `transfer_count` | `0-5` |
| `load_score` | `0-100` |
| `history_flow_score` | `0-100` |
| `congestion_score` | `0-100` |
| `data_freshness_seconds` | `>= 0` |
| `monitored_score` | `0-100` |
| `completeness_score` | `0-100` |
| `avg_service_frequency_minutes` | `> 0` |

若平均发车间隔缺失，后端必须先使用时段平均值、线路默认值或系统默认值完成降级，并将字段名加入：

```json
"degraded_fields": ["avg_service_frequency_minutes"]
```

## 8. 本地模型调用

建议将同步模型调用放入线程池，避免阻塞 FastAPI 事件循环：

```python
import asyncio
from algorithm.model.predictor import predict_recommendation

class LocalModelScoringGateway:
    async def score_routes(self, payload: dict) -> dict:
        return await asyncio.wait_for(
            asyncio.to_thread(predict_recommendation, payload),
            timeout=3.0,
        )
```

若模型本身已经是异步函数，可直接 `await`，不需要 `to_thread`。

本地模型调用也必须应用超时和降级策略，不能因为“同进程调用”就跳过保护。

## 9. 模型响应校验

后端收到模型结果后必须校验：

1. 返回值是合法对象；
2. `contract_version` 与请求兼容；
3. `request_id` 与请求一致；
4. `model_name` 和 `model_version` 非空；
5. `results` 数量与输入路线数量一致；
6. `route_id` 无重复、无遗漏、无额外值；
7. 所有分数均为有限数；
8. 所有分数均位于 `0-100`；
9. `warnings` 为数组；
10. `duration_ms` 为非负整数；
11. `generated_at` 是合法时间字符串。

注意：

```text
后端不再根据 weights 重算 recommend_score，
因为偏好权重由模型内部维护。
```

后端只校验 `recommend_score` 的类型、有限性和范围，不校验模型内部权重公式。

模型输出顺序允许与输入顺序不同，后端必须按 `route_id` 重新关联。

## 10. 整批降级原则

任何一项模型结果校验失败，都不得部分采用模型结果。

必须执行：

```text
整批候选路线统一回退规则评分
```

原因是不同评分方式可能具有不同尺度，部分路线使用模型、部分路线使用规则会造成排序不公平。

降级触发条件包括：

- 模型模块导入失败；
- 模型调用异常；
- 调用超时；
- 返回值不是合法 JSON / dict；
- 契约版本不匹配；
- `request_id` 不一致；
- 路线结果缺失、重复或多出；
- 分数出现 NaN、Infinity 或超出 0-100；
- payload 被模型拒绝；
- 模型未就绪；
- HTTP 模式返回 429 或 5xx。

## 11. 规则评分基线

规则评分作为永久降级方案。

```text
total_time_minutes =
    walk_time_minutes
    + eta_minutes
    + ride_time_minutes
```

```text
time_score =
    max(0, 100 - total_time_minutes × 2)
```

```text
comfort_score =
    0.5 × load_score
    + 0.3 × history_flow_score
    + 0.2 × congestion_score
```

```text
walk_score =
    max(0, 100 - walk_time_minutes × 8)
```

```text
transfer_score:
0 次 = 100
1 次 = 75
2 次 = 50
3 次及以上 = 30
```

```text
reliability_score =
    0.5 × freshness_score
    + 0.3 × monitored_score
    + 0.2 × completeness_score
```

数据新鲜度：

| 数据年龄 | `freshness_score` |
|---|---:|
| `<= 60s` | 100 |
| `61-180s` | 80 |
| `181-300s` | 60 |
| `> 300s` | 40 |

规则模式内部可根据 `preference` 使用与模型一致的偏好模板，确保模型与规则的业务语义一致。

## 12. 降级结果标记

公开推荐响应建议增加评分来源信息：

```json
{
  "provider": "rule_based",
  "model_name": null,
  "model_version": "rules-1.0.0",
  "fallback": true,
  "fallback_reason": "model_timeout",
  "duration_ms": 3012
}
```

正常使用本地模型时：

```json
{
  "provider": "local_model",
  "model_name": "busmind-route-scorer",
  "model_version": "0.1.0",
  "fallback": false,
  "fallback_reason": null,
  "duration_ms": 12
}
```

`fallback_reason` 建议枚举：

```text
model_timeout
model_unavailable
model_not_ready
model_invalid_response
model_contract_mismatch
model_route_mismatch
model_score_invalid
model_inference_failed
model_rate_limited
```

内部异常写入日志，不向前端返回堆栈、文件路径、模型服务地址或敏感配置。

## 13. 错误处理

本地模型抛出的契约错误应转换为统一内部错误类型。

建议错误码：

| 错误码 | 说明 |
|---|---|
| `INVALID_REQUEST` | 请求结构错误 |
| `INVALID_FEATURE` | 特征值非法 |
| `UNEXPECTED_FIELD` | 出现不允许字段，例如 `weights` |
| `CONTRACT_VERSION_UNSUPPORTED` | 不支持当前契约版本 |
| `TOO_MANY_ROUTES` | 路线数量超过 10 |
| `MODEL_NOT_READY` | 模型尚未加载 |
| `INFERENCE_FAILED` | 模型推理失败 |

对于公开推荐接口，除非业务请求本身非法，否则模型错误不应直接导致整个推荐接口失败，而应优先触发规则降级。

## 14. 超时与重试

建议配置：

| 项目 | 建议值 |
|---|---:|
| 本地模型总超时 | 3 秒 |
| HTTP 连接超时 | 500 毫秒 |
| HTTP 总请求超时 | 3 秒 |
| 单批路线数 | 最多 10 条 |
| 在线自动重试 | 0 次 |
| 是否允许规则降级 | true |

在线推荐不建议自动重试模型，因为重试会增加用户等待时间。一次失败后直接规则降级，保证主链路可用。

## 15. 日志与监控

后端每次模型调用至少记录：

```text
request_id
contract_version
provider
model_name
model_version
route_count
preference
duration_ms
success
fallback
fallback_reason
```

不得在普通日志记录：

- 用户精确起终点坐标；
- 用户访问令牌；
- LTA AccountKey；
- 数据库密码；
- 完整模型输入中的敏感用户信息。

建议统计：

```text
模型调用成功率
P50 / P95 / P99 推理耗时
超时率
契约失败率
整批规则降级率
不同 preference 的分数分布
route_id 不一致次数
```

## 16. 配置建议

```env
MODEL_PROVIDER=local
MODEL_FALLBACK_ENABLED=true
MODEL_TIMEOUT_SECONDS=3.0

MODEL_NAME=busmind-route-scorer
MODEL_VERSION=0.1.0
MODEL_CONTRACT_VERSION=1.0.0

RULES_VERSION=rules-1.0.0
```

后续使用 HTTP 服务时再增加：

```env
MODEL_SERVICE_BASE_URL=http://model-service:9000
MODEL_SCORE_PATH=/v1/score-routes
MODEL_CONNECT_TIMEOUT_SECONDS=0.5
```

## 17. 联调验收用例

| 编号 | 场景 | 预期 |
|---|---|---|
| M01 | 一条合法路线 | 返回完整五维分数和综合分 |
| M02 | 十条合法路线 | 每条路线只出现一次 |
| M03 | 模型调整输出顺序 | 后端按 `route_id` 正确关联 |
| M04 | `load_code=UNKNOWN` | 使用降级分正常评分 |
| M05 | payload 包含 `weights` | 模型拒绝，后端整批规则降级 |
| M06 | 模型超时 | 公开推荐接口仍成功，标记 fallback |
| M07 | 返回 NaN、Infinity 或 101 | 整批规则降级 |
| M08 | 遗漏或多出路线 | 整批规则降级 |
| M09 | `request_id` 不一致 | 整批规则降级 |
| M10 | 契约主版本不兼容 | 整批规则降级 |
| M11 | 模型模块导入失败 | 自动切换规则评分 |
| M12 | `avg_service_frequency_minutes` 缺失 | 后端先降级填充后再调用 |
| M13 | `low_load` 偏好 | 规范化为 `comfort` |
| M14 | 模型返回 warnings | 正常返回并记录日志 |
| M15 | 规则模式启动 | 不加载模型也能完成推荐 |

## 18. 双方交付清单

算法/模型负责人交付：

1. `algorithm.model.predictor.predict_recommendation(payload)`；
2. 模型名称、模型版本、契约版本；
3. 输入输出契约；
4. 依赖和启动说明；
5. 至少 5 组固定输入输出样例；
6. 最大批量和性能基线；
7. 已知限制；
8. 契约错误类型说明。

后端负责人交付：

1. 请求和响应 Pydantic Schema；
2. `RouteScoringGateway` 协议；
3. Local、Rule 两种实现；
4. Provider 配置和依赖注入；
5. 超时、校验、整批降级和日志；
6. 固定响应或 Mock Gateway；
7. 公开响应中的评分来源字段；
8. 联调测试用例。

## 19. 实施顺序

1. 以后端现有候选路线和特征组装为基础，统一字段名称；
2. 落地正式请求与响应 Schema；
3. 实现 `RouteScoringGateway`；
4. 实现并验证 `RuleBasedScoringGateway`；
5. 实现 `LocalModelScoringGateway`；
6. 接入 `predict_recommendation(payload)`；
7. 使用固定样例完成契约测试；
8. 验证超时、非法响应和版本不匹配降级；
9. 将 `MODEL_PROVIDER` 切换为 `local`；
10. 保留一键切回 `rule` 的能力；
11. 后续有部署需要时，再扩展 HTTP 模型服务。

## 20. 最终约定

当前项目统一采用以下方案：

```text
后端负责生成候选路线与整理特征
        ↓
后端只传 preference，不传 weights
        ↓
本地推荐模型计算五维分数与 recommend_score
        ↓
后端校验结果、排序和生成业务标签
        ↓
模型失败时整批回退规则评分
        ↓
大模型只负责自然语言解释
```

模型升级、部署方式调整或后续拆分为独立 HTTP 服务时，必须保持公开推荐接口和正式数据契约稳定。
