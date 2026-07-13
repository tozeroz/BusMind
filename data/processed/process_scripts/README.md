# Process Scripts

本目录脚本负责把 `data/raw/lta` 下的 LTA 原始数据转换成后端接口和数据库导入需要的标准 CSV。

`data/processed` 是从 `data/raw/lta` 到后端数据库和业务查询的标准化中间层，不是最终模型训练样本目录。推荐模型训练样本统一由 `algorithm/dataset` 基于 processed/raw 再构建。

## 目录职责

允许职责：

- 字段规范化、ID 生成、基础表构建。
- Bus Arrival 的 ETA、Load 实时字段扁平化。
- 历史客流聚合。
- Traffic Speed Bands 当前路况快照整理。

禁止职责：

- 保存推荐模型伪标签。
- 保存模型训练产物。
- 承担用户偏好排序逻辑。
- 把 ETA 或 Load 当成训练目标输出。

## 运行方式

在项目根目录运行：

```powershell
uv run python data\processed\process_scripts\build_lta_processed_data.py --month 202605
```

如果本机 `uv` cache 权限异常，也可以临时使用已有虚拟环境：

```powershell
.\.venv\Scripts\python.exe data\processed\process_scripts\build_lta_processed_data.py --month 202605
```

## 输入

```text
data/raw/lta/api_response/BusStops_full.json
data/raw/lta/api_response/BusRoutes_full.json
data/raw/lta/api_response/BusServices_full.json
data/raw/lta/passenger_volume_stop/<month>/original.zip
data/raw/lta/bus_arrival_samples/YYYY-MM-DD/*.jsonl
data/raw/lta/traffic_speed_bands/YYYY-MM-DD/*.json
```

其中 `traffic_speed_bands` 是可选输入；如果还没有采集，道路速度热力 CSV 会跳过生成。

Traffic Speed Bands 默认只把最新一次快照写入 `data/processed/traffic_speed_bands.csv`，用于后端导入和当前路况查询。这样可以避免多天 5 分钟采样膨胀成千万行 CSV。

如果确实要保留所有历史快照，可以显式使用：

```powershell
uv run python data\processed\process_scripts\build_lta_processed_data.py --traffic-snapshot-mode all
```

`all` 模式主要服务离线分析，会生成很大的 CSV，不建议直接导入 MySQL。

## 输出

```text
data/processed/bus_station.csv
data/processed/bus_line.csv
data/processed/line_station.csv
data/processed/bus_vehicle.csv
data/processed/lta_bus_arrival.csv
data/processed/bus_eta_status.csv
data/processed/bus_load_status.csv
data/processed/map_station.csv
data/processed/map_road_segment.csv
data/processed/passenger_flow_trend.csv
data/processed/traffic_speed_bands.csv
data/processed/processing_summary.csv
```

## 字段口径

- `bus_eta_status.csv` 直接来自 LTA Bus Arrival 的 `EstimatedArrival`，表示实时到站状态，不是模型预测。
- `bus_load_status.csv` 直接来自 LTA Bus Arrival 的 `Load`，表示实时客载状态，不是模型预测。
- `bus_vehicle.csv` 由 Bus Arrival 实时车辆坐标和客载状态整理得到，用于车辆列表和智能接口网关。
- `passenger_flow_trend.csv` 用于历史客流趋势接口。
- `traffic_speed_bands.csv` 用于实时道路速度和拥堵热力图，默认只保留最新快照。

## 校验

生成后建议运行：

```powershell
uv run python tools\validate_processed_data.py --processed-dir data\processed
```

如需验证 CSV 是否满足 MySQL 导入字段要求：

```powershell
uv run python database\import\import_processed_to_mysql.py --processed-dir data\processed --dry-run
```

## 注意事项

- `eta_prediction.csv` 和 `load_prediction.csv` 属于旧口径遗留文件，不是当前处理脚本输出，也不应作为当前阶段训练集提交或导入。
- 真实 `data/raw` 和 `data/processed` 数据文件默认被 `.gitignore` 排除，仓库只提交采集、处理、导入和校验脚本。
