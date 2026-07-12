# Process Scripts

> 这些脚本用于把 `data/raw/lta` 下的 LTA 原始数据转换为后端接口和数据库导入需要的标准 CSV。当前版本只保留业务接口需要的数据，不再输出 ETA/Load 训练样本

# 零、目录职责

`data/processed` 是从 `data/raw/lta` 到后端数据库和业务查询的标准化中间层。

固定边界：

- 输入只来自 `data/raw/lta` 的原始 LTA 数据。
- 输出是后端数据库导入和业务接口查询使用的标准 CSV。
- 处理脚本可以做字段规范化、ID 生成、基础表构建、实时字段扁平化、历史客流聚合、道路热力整理。
- 本目录 CSV 是“业务数据表口径”，不是最终模型训练样本。
- 推荐模型训练样本统一由 `algorithm/dataset` 基于 processed/raw 再构建。

禁止在本目录承担：

- 保存推荐模型伪标签。
- 保存模型训练产物。
- 承担用户偏好排序逻辑。
- 把 ETA 或 Load 作为训练目标输出。

# 一、运行方式

先安装数据处理依赖，然后在项目根目录运行：

```powershell
D:\Code\Python\anaconda3_data\envs\py311-venv\python.exe .\data\processed\process_scripts\build_lta_processed_data.py --month 202605
```

生成后建议立即运行数据质量校验：

```powershell
D:\Code\Python\anaconda3_data\envs\py311-venv\python.exe .\tools\validate_processed_data.py --report .\docs\data\processed_data_validation.md
```

如果只想验证 CSV 是否满足 MySQL 导入字段要求，可以运行 dry-run：

```powershell
D:\Code\Python\anaconda3_data\envs\py311-venv\python.exe .\database\import\import_processed_to_mysql.py --dry-run
```

# 二、输入

```text
data/raw/lta/api_response/BusStops_full.json
data/raw/lta/api_response/BusRoutes_full.json
data/raw/lta/api_response/BusServices_full.json
data/raw/lta/passenger_volume_stop/<month>/original.zip
data/raw/lta/bus_arrival_samples/YYYY-MM-DD/*.jsonl
data/raw/lta/traffic_speed_bands/YYYY-MM-DD/*.json
```

其中 `traffic_speed_bands` 是可选输入；如果还没有采集，道路速度热力 CSV 会跳过生成

# 三、输出

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

# 四、说明

- `station_id` 和 `line_id` 已转换为后端接口可直接使用的整数 ID，同时保留 LTA 原始编号 `bus_stop_code`、`service_no`
- `bus_eta_status.csv` 直接来自 LTA Bus Arrival 的 `EstimatedArrival`，表示实时到站状态，不是模型预测
- `bus_load_status.csv` 直接来自 LTA Bus Arrival 的 `Load`，表示实时客载状态，不是模型预测
- `bus_vehicle.csv` 由 Bus Arrival 实时车辆坐标和客载状态整理得到，用于车辆列表和智能接口网关
- `map_station.csv` 和 `map_road_segment.csv` 用于地图站点、线路路段展示
- `passenger_flow_trend.csv` 用于历史客流趋势接口
- `traffic_speed_bands.csv` 用于实时道路速度/拥堵热力图

# 五、注意事项

- `eta_prediction.csv` 和 `load_prediction.csv` 属于旧口径遗留文件，不是当前处理脚本的输出，也不应作为当前阶段训练集提交或导入
- 真实 `data/raw` 和 `data/processed` 数据文件默认被 `.gitignore` 排除，仓库只提交采集、处理、导入和校验脚本
