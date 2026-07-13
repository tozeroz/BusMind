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
| `scripts/build_features.py` | 单一特征构建入口；默认用 `data/raw/collect_scripts/hot_bus_stops.txt` 筛选 OD，从本地 CSV 构建候选路线并输出 `features.csv` |
| `scripts/build_labels.py` | 基于独立规则生成排序伪标签，不调用当前模型 scorer |
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

如需绕开热门站筛选，临时加 `--ignore-hot-stops`。如需调整换乘 OD 占比，可调 `--transfer-pair-ratio`；脚本还会用 `--candidate-search-multiplier` 先多搜候选，再保留 `--max-candidates` 条，以尽量让同一 OD 内同时出现直达和换乘路线。

## 伪标签策略

当前阶段没有足够真实用户点击、选择、取消、满意度等行为数据，不能直接训练真实排序模型。`build_labels.py` 使用独立业务规则为候选路线生成伪标签，作为第一版模型的冷启动弱监督标准。

伪标签只依赖 `features.csv` 中的候选路线业务字段，并在训练前通过 `algorithm/model/preprocessing.py` 映射到 12 维数值特征。它不调用当前模型 scorer，也不把模型已有输出重新当作标签，避免形成“模型自己教自己”的闭环。

当前规则会先计算五类子目标：

| 子目标 | 主要依据 |
|---|---|
| `time_score` | ETA、乘车时间、平均发车间隔、换乘惩罚 |
| `comfort_score` | 实时客载、历史站点客流、线路道路拥堵、是否受实时监控 |
| `walk_score` | 步行时间、步行距离 |
| `transfer_score` | 换乘次数，采用非线性惩罚 |
| `reliability_score` | 数据完整度、数据新鲜度、监控状态、字段来源可信度 |

随后按 `balanced`、`fastest`、`comfort`、`less_walking`、`less_transfer` 五种偏好模板混合为 `recommend_score`，并在每个 `candidate_group_id` 内生成排序位置、硬标签、软标签、分数间隔和置信度。

这套伪标签的意义是让模型先学习一套可解释、可复用的排序方法论。后续如果积累了真实推荐曝光、用户点击、最终选择或满意度反馈，可以保留当前 `features.csv` 字段和训练链路，把伪标签替换为真实标签，或用真实标签校准伪标签权重。

## pseudo_labels.csv 字段

`build_labels.py` 会为每个 `candidate_group_id` 和每种 preference 生成排序标签：

```text
candidate_group_id
preference
route_id
rank_position
label
label_gain
soft_label
score_margin
label_confidence
time_score
comfort_score
walk_score
transfer_score
reliability_score
recommend_score
is_synthetic
```

其中 `time_score`、`comfort_score`、`walk_score`、`transfer_score`、`reliability_score` 是当前 `train_ranker.py` 的训练目标；`rank_position`、`label_gain`、`soft_label`、`score_margin`、`label_confidence` 用于后续升级排序损失或样本权重。

生成正式 v1 数据集：

```powershell
python .\algorithm\dataset\scripts\build_features.py --groups 1000
python .\algorithm\dataset\scripts\summarize_features.py --output .\algorithm\dataset\features_summary.md
python .\algorithm\dataset\scripts\build_labels.py
python .\algorithm\model\train_ranker.py
```
