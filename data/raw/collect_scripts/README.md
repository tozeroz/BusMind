# Collect Scripts

这些脚本用于采集 BusMind 项目需要的 LTA DataMall 原始数据。不要把 AccountKey 写入仓库，运行时用参数传入，或先设置环境变量 `LTA_ACCOUNT_KEY`。

## 1. 设置 AccountKey

```powershell
$env:LTA_ACCOUNT_KEY = "你的AccountKey"
```

## 2. 拉取静态公交数据

```powershell
.\data\raw\collect_scripts\fetch_lta_static.ps1
```

输出：

```text
data/raw/lta/api_response/BusStops_full.json
data/raw/lta/api_response/BusRoutes_full.json
data/raw/lta/api_response/BusServices_full.json
```

## 3. 拉取 Passenger Volume 月度数据

```powershell
.\data\raw\collect_scripts\fetch_lta_passenger_volume.ps1 -Month 202605
```

输出：

```text
data/raw/lta/api_response/PassengerVolumeByBusStops_202605.json
data/raw/lta/api_response/PassengerVolumeByOriginDestinationBusStops_202605.json
data/raw/lta/passenger_volume_stop/202605/original.zip
data/raw/lta/passenger_volume_od/202605/original.zip
```

## 4. 采样 Bus Arrival 动态数据

```powershell
.\data\raw\collect_scripts\sample_lta_bus_arrival.ps1 -MaxStops 50
```

输出：

```text
data/raw/lta/bus_arrival_samples/YYYY-MM-DD/bus_arrival_sample.jsonl
```

Bus Arrival 可以直接提供：

- `EstimatedArrival`：用于计算 ETA。
- `Load`：用于客载状态，取值为 `SEA`、`SDA`、`LSD`。
- `Latitude` / `Longitude`：用于展示实时车辆位置。

## 5. 采集 Traffic Speed Bands 道路热力数据

```powershell
.\data\raw\collect_scripts\fetch_lta_traffic_speed_bands.ps1
```

输出：

```text
data/raw/lta/traffic_speed_bands/YYYY-MM-DD/traffic_speed_bands_YYYYMMDD_HHMMSS.json
```

Traffic Speed Bands 可以直接提供道路分段热力图所需字段：

- `SpeedBand`：道路速度等级，用于映射拥堵颜色。
- `MinimumSpeed` / `MaximumSpeed`：速度范围。
- `StartLat` / `StartLon` / `EndLat` / `EndLon`：道路分段起终点坐标。

## 6. 检查原始数据是否齐全

```powershell
.\data\raw\collect_scripts\check_lta_raw_data.ps1
```
