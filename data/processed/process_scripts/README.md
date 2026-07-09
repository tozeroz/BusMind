# Processed Data Scripts

这些脚本用于把 `data/raw/lta` 下的 LTA 原始数据转换为后端接口和数据库初始化需要的标准 CSV。当前版本只保留接口需要的数据，不再输出 ETA/Load 训练样本。

## 运行方式

先安装数据处理依赖，然后在项目根目录运行：

```powershell
D:\Code\Python\anaconda3_data\envs\py311-venv\python.exe .\data\processed\process_scripts\build_lta_processed_data.py --month 202605
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

## 说明

- `station_id` 和 `line_id` 已转为后端接口可直接使用的整数 ID，同时保留 LTA 原始编号 `bus_stop_code`、`service_no`。
- `bus_eta_status.csv` 直接来自 LTA Bus Arrival 的 `EstimatedArrival`，表示实时到站状态，不是模型预测。
- `bus_load_status.csv` 直接来自 LTA Bus Arrival 的 `Load`，表示实时客载状态，不是模型预测。
- `bus_vehicle.csv` 由 Bus Arrival 实时车辆坐标和客载状态整理得到，用于车辆列表和智能接口网关。
- `map_station.csv` 和 `map_road_segment.csv` 用于地图站点、线路路段展示。
- `passenger_flow_trend.csv` 用于历史客流趋势接口。
- `traffic_speed_bands.csv` 用于实时道路速度/拥堵热力图。
