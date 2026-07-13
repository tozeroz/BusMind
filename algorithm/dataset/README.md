# Algorithm Dataset

`algorithm/dataset` 是推荐模型的离线训练数据层，只服务于 `algorithm/model` 的训练、验证和数据审计。

## 目录职责

本目录负责把本地 `data/processed` 中的公交网络、到站样本、历史客流和路况数据，整理成与线上后端 `routes[]` payload 对齐的训练数据。

固定边界：

- 优先读取 `data/processed/*.csv`。
- 不直接调用 LTA API，不查询 MySQL，不依赖 SSH 隧道。
- 输出推荐模型训练用的 `features.csv` 和 `pseudo_labels.csv`。
- `features.csv` 保存业务字段，不保存模型内部映射分。
- 训练前统一通过 `algorithm/model/preprocessing.py` 转成 12 维数值特征。
- 记录 `is_synthetic`、`feature_sources` 和 `degraded_fields`，用于后续审计。

本目录不负责：

- 采集 LTA 原始数据。
- 写入 MySQL 或缓存。
- 线上后端实时刷新逻辑。
- 保存模型权重或模型推理产物。

## 当前链路

```text
data/raw/lta
  -> data/processed/*.csv
  -> algorithm/dataset/scripts/build_features.py
  -> algorithm/dataset/features.csv
  -> algorithm/dataset/scripts/build_labels.py
  -> algorithm/dataset/pseudo_labels.csv
  -> algorithm/model/train_ranker.py
  -> algorithm/model/artifacts/route_scorer_v1.json
```

## 文件说明

| 文件或目录 | 用途 |
|---|---|
| `scripts/recommendation_data.py` | 只负责读取 raw / processed 数据，并提供站点客流、线路拥堵等查表能力 |
| `scripts/recommendation_feature_contract.py` | 冻结 `features.csv` 字段、JSON 字段解析、业务字段转模型输入 |
| `scripts/build_features.py` | 单一特征构建入口；从本地 CSV 构建候选路线并输出 `features.csv` |
| `scripts/build_labels.py` | 组装同款模型 payload，基于规则评分生成伪标签 |
| `scripts/summarize_features.py` | 汇总训练特征的数据质量、来源覆盖和降级字段分布 |
| `features.csv` / `pseudo_labels.csv` | 推荐模型离线训练数据产物 |

候选路线搜索核心算法位于 `algorithm/routing/transit_graph.py`，后端和离线训练数据构建共用同一套图搜索逻辑。

## features.csv 冻结字段

`features.csv` 必须只保存线上后端 route payload 对齐字段，以及离线训练管理字段：

```text
candidate_group_id
route_id
service_nos
eta_minutes
ride_time_minutes
walk_time_minutes
walk_distance_meters
transfer_count
avg_service_frequency_minutes
load_code
station_flow_level
route_speed_band
source_updated_at
monitored
degraded_fields
feature_sources
is_synthetic
```

其中：

- `candidate_group_id`：离线候选路线组 ID，线上后端不需要传。
- `is_synthetic`：离线训练样本标记，线上后端不需要传。
- 其余字段与线上后端传入模型的单条 `routes[]` 字段对齐。

`features.csv` 不允许保存这些模型内部字段：

```text
load_score
history_flow_score
congestion_score
data_freshness_seconds
monitored_score
completeness_score
```

这些字段只能由 `algorithm/model/preprocessing.py` 根据业务字段统一映射得到。

## JSON 字段格式

CSV 中复杂字段统一保存为 JSON 字符串：

```text
service_nos      -> ["105","88"]
degraded_fields -> ["walk_distance_meters"]
feature_sources -> {"eta_minutes":"lta_realtime","transfer_count":"backend_graph"}
```

训练脚本读取时必须先把这些字段恢复为 `list` / `dict`，再组装成和 `predict_recommendation(payload)` 相同的结构。

## 模型实际使用的 12 维特征

训练和推理时，模型内部固定使用下列 12 个数值特征：

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

字段来源分层：

| 内部特征 | `features.csv` 业务字段 | 处理口径 |
|---|---|---|
| `load_score` | `load_code` | `SEA=100`，`SDA=70`，`LSD=35`，`UNKNOWN=60` |
| `history_flow_score` | `station_flow_level` | `low=90`，`medium=70`，`high=45` |
| `congestion_score` | `route_speed_band` | LTA `SpeedBand=1..8` 映射为通畅分 |
| `data_freshness_seconds` | `source_updated_at` | 当前时间减数据更新时间 |
| `monitored_score` | `monitored` | `1 -> 100`，`0 -> 75` |
| `completeness_score` | `degraded_fields` | 降级字段越多，完整度越低 |

## 快速验证

临时小样本建议写到 `D:\SummerTraining\.tmp`：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 20 --output D:\SummerTraining\.tmp\frozen_features_20.csv
python .\algorithm\dataset\scripts\summarize_features.py --input D:\SummerTraining\.tmp\frozen_features_20.csv
python .\algorithm\dataset\scripts\build_labels.py --input D:\SummerTraining\.tmp\frozen_features_20.csv --output D:\SummerTraining\.tmp\frozen_labels_20.csv
python .\algorithm\model\train_ranker.py --features D:\SummerTraining\.tmp\frozen_features_20.csv --labels D:\SummerTraining\.tmp\frozen_labels_20.csv --output D:\SummerTraining\.tmp\route_scorer_test.json
```

生成正式 v1 数据集：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 1000
python .\algorithm\dataset\scripts\summarize_features.py --output .\algorithm\dataset\features_summary.md
python .\algorithm\dataset\scripts\build_labels.py
python .\algorithm\model\train_ranker.py
```
