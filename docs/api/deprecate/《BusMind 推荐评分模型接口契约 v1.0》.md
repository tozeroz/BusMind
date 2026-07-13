# BusMind 后端与推荐模型数据契约

> 契约版本：`1.0.0`  
> 当前模型入口：`algorithm.model.predictor.predict_recommendation(payload)`  
> 模型名称：`busmind-route-scorer`  
> 模型版本：`0.1.0`

## 1. 责任边界

模型只负责给候选路线打分，不负责：

- 调用 LTA API；
- 查询 MySQL 或缓存；
- 生成候选路线；
- 预测 ETA 或 Load；
- 生成最终自然语言解释；
- 决定公开 HTTP API 响应格式。

后端负责：

- 起终点匹配；
- 候选路线生成；
- ETA / Load / 客流 / 路况 / 可靠性特征组装；
- 缺失值降级；
- 调用模型；
- 根据模型分数排序和打标签；
- 组织公开响应。

## 2. 模型请求

一次请求最多评分 10 条路线。

```json
{
  "contract_version": "1.0.0",
  "request_id": "rec_01J2ABCDEF",
  "preference": "comfort",
  "routes": []
}
```

模型不接受 `weights`。如果 payload 中出现 `weights`，模型会返回契约错误。用户偏好只通过 `preference` 表达。

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

## 3. 单条路线特征

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `route_id` | string | 是 | 请求内唯一 |
| `service_nos` | string[] | 是 | 候选路线包含的公交线路号 |
| `eta_minutes` | float | 是 | LTA Bus Arrival 计算出的 ETA |
| `ride_time_minutes` | float | 是 | 车内时间 |
| `walk_time_minutes` | float | 是 | 步行时间 |
| `walk_distance_meters` | float | 是 | 步行距离 |
| `transfer_count` | int | 是 | 换乘次数 |
| `load_code` | string | 是 | `SEA` / `SDA` / `LSD` / `UNKNOWN` |
| `load_score` | float | 是 | 客载分，0-100，越高越舒适 |
| `history_flow_score` | float | 是 | 历史客流分，0-100，越高压力越低 |
| `congestion_score` | float | 是 | 路况分，0-100，越高越通畅 |
| `data_freshness_seconds` | float | 是 | 实时数据年龄 |
| `monitored_score` | float | 是 | 实时监控可信度，0-100 |
| `completeness_score` | float | 是 | 特征完整度，0-100 |
| `avg_service_frequency_minutes` | float | 是 | 平均发车间隔 |
| `feature_sources` | object | 是 | 各特征来源 |
| `degraded_fields` | string[] | 是 | 降级字段列表 |

其中 12 个数值特征是模型真正训练和推理使用的输入：

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

## 4. 请求示例

```json
{
  "contract_version": "1.0.0",
  "request_id": "rec_01J2ABCDEF",
  "preference": "comfort",
  "routes": [
    {
      "route_id": "route_002",
      "service_nos": ["36"],
      "eta_minutes": 8.0,
      "ride_time_minutes": 15.0,
      "walk_time_minutes": 5.0,
      "walk_distance_meters": 360.0,
      "transfer_count": 0,
      "load_code": "SDA",
      "load_score": 70.0,
      "history_flow_score": 70.0,
      "congestion_score": 75.0,
      "data_freshness_seconds": 35,
      "monitored_score": 100.0,
      "completeness_score": 100.0,
      "avg_service_frequency_minutes": 10.0,
      "feature_sources": {
        "eta": "lta_realtime",
        "load": "lta_realtime",
        "flow": "historical",
        "traffic": "cache"
      },
      "degraded_fields": []
    }
  ]
}
```

## 5. 模型响应

```json
{
  "contract_version": "1.0.0",
  "request_id": "rec_01J2ABCDEF",
  "model_name": "busmind-route-scorer",
  "model_version": "0.1.0",
  "results": [
    {
      "route_id": "route_002",
      "time_score": 76.0,
      "comfort_score": 72.5,
      "walk_score": 60.0,
      "transfer_score": 100.0,
      "reliability_score": 88.0,
      "recommend_score": 79.8,
      "feature_contributions": {
        "eta_minutes": -0.08,
        "load_score": 0.19
      }
    }
  ],
  "warnings": [],
  "duration_ms": 12,
  "generated_at": "2026-07-11T12:00:00+00:00"
}
```

## 6. 模型内部计算

```text
12 个数值特征
    ↓
标准化：(x - mean) / std
    ↓
5 个 sigmoid 子评分头
    ↓
time_score / comfort_score / walk_score / transfer_score / reliability_score
    ↓
根据 preference 选择模型内置偏好模板
    ↓
recommend_score
```

偏好模板由模型内部维护，后端不传 `weights`。

## 7. 错误和降级

模型契约错误包括：

- 缺少必填字段；
- 路线数超过 10；
- 分数不是有限数；
- `contract_version` 不匹配；
- payload 中出现 `weights`。

后端接入时，如果模型不可用或响应不合法，应整批回退规则评分，不能部分采用模型结果。
