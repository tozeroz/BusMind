# Algorithm Dataset

`algorithm/dataset` 是推荐模型的离线训练数据层，只服务 `algorithm/model` 的训练和验证。

## 1. 目录职责

本目录负责把后端业务数据口径转换成推荐模型训练口径。

固定边界：

- 优先读取 `data/processed` 下的标准 CSV。
- 如果 processed 数据缺失，则从 `data/raw/lta` 按同一处理口径重建。
- 输出推荐模型训练用的 `features.csv` 和 `pseudo_labels.csv`。
- 构造 12 维模型输入特征。
- 标记 `is_synthetic`，记录 `feature_sources` 和 `degraded_fields`。

禁止在本目录承担：

- 调用 LTA API。
- 写入 MySQL 或缓存。
- 承担线上后端实时刷新逻辑。
- 保存模型权重或模型推理产物。

## 2. 当前链路

```text
data/raw/lta
    ↓
data/processed/*.csv
    ↓
algorithm/dataset/build_features.py
    ↓
algorithm/dataset/recommendation/v1/features.csv
    ↓
algorithm/dataset/build_labels.py
    ↓
algorithm/dataset/recommendation/v1/pseudo_labels.csv
    ↓
algorithm/model/train_ranker.py
```

## 3. 文件说明

| 文件或目录 | 用途 |
|---|---|
| `recommendation_data.py` | 数据读取、字段转换、12 维特征构建 |
| `build_features.py` | 生成模型输入数据 `features.csv` |
| `build_labels.py` | 基于规则基线生成伪标签 `pseudo_labels.csv` |
| `summarize_features.py` | 汇总训练特征的数据质量、来源覆盖和降级字段分布 |
| `recommendation/v1/` | 推荐模型 v1 的离线训练数据输出目录 |

## 4. 输出字段要求

`features.csv` 必须包含模型 12 个数值特征：

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

同时必须保留：

```text
candidate_group_id
route_id
service_nos
load_code
feature_sources
degraded_fields
is_synthetic
```

## 5. 当前数据口径

真实来源字段：

- `eta_minutes`：LTA Bus Arrival 的 `EstimatedArrival - query_time`。
- `load_score`：LTA Bus Arrival 的 `Load` 映射。
- `history_flow_score`：Passenger Volume by Bus Stops 的历史客流映射。
- `congestion_score`：Traffic Speed Bands 的 `SpeedBand` 映射。
- `avg_service_frequency_minutes`：Bus Services 的发车频率字段解析。

估算或过渡字段：

- `ride_time_minutes`：当前按线路剩余距离和默认速度估算。
- `walk_time_minutes`：当前离线阶段缺少真实步行路径，必要时模拟。
- `walk_distance_meters`：当前由步行时间反推。
- `transfer_count`：当前离线阶段必要时模拟。
- `data_freshness_seconds`：当前离线阶段使用默认值。
- `completeness_score`：当前按 `degraded_fields` 的字段数量计算。

估算或模拟字段必须通过 `feature_sources` 和 `degraded_fields` 显式标记。

## 6. 快速验证

```powershell
python .\algorithm\dataset\build_features.py --max-groups 3
python .\algorithm\dataset\summarize_features.py
python .\algorithm\dataset\build_labels.py
```

生成完整训练集时可以直接输出到 v1 目录：

```powershell
python .\algorithm\dataset\build_features.py --min-groups 500
python .\algorithm\dataset\summarize_features.py --output .\algorithm\dataset\recommendation\v1\features_summary.md
python .\algorithm\dataset\build_labels.py
```

`--min-groups` 会在真实候选组不足时用可控扰动生成补充候选组。补充样本会保留 `is_synthetic=true`，并把 `feature_sources` 标为 `model`，避免和真实来源混淆。

如果只想临时验证，建议把输出写到 `D:\SummerTraining\.tmp`，避免把训练样本提交到仓库。
