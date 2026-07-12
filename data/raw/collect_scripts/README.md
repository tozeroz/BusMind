# Collect Scripts

这些脚本用于采集 BusMind 项目需要的 LTA DataMall 原始数据。不要把 AccountKey 写入仓库，运行时用参数传入，或先设置环境变量 `LTA_ACCOUNT_KEY`。

## 目录职责

`data/raw` 是项目的原始数据层，只负责保存从 LTA DataMall 获取到的原始响应、ZIP、JSONL 快照和采集脚本。

固定边界：

- `data/raw/lta` 保存 LTA 原始数据，不做字段清洗、不改业务口径。
- `collect_scripts` 只负责拉取或采样数据，不生成模型特征。
- Bus Arrival、Passenger Volume、Traffic Speed Bands 的采集脚本只负责“拿数据”。
- 原始数据可以作为 `data/processed` 的输入，但不直接作为推荐模型训练入口。

禁止在本目录承担：

- 清洗字段或生成数据库标准 CSV。
- 生成推荐模型 `features.csv` 或 `pseudo_labels.csv`。
- 保存模型训练产物或推荐排序结果。

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

本地采样默认优先使用热门站点列表：

```text
data/raw/collect_scripts/hot_bus_stops.txt
```

该文件和服务器采集使用的热门站点列表保持同一口径，每行一个 Bus Stop Code。若不传 `-BusStopCodes` 或 `-BusStopFile`，脚本会先读取该文件；如果文件不存在，才回退到 `data/raw/lta/api_response/BusStops_full.json` 的前 `MaxStops` 个站点。

```powershell
.\data\raw\collect_scripts\sample_lta_bus_arrival.ps1 -MaxStops 100
```

也可以显式指定站点列表文件：

```powershell
.\data\raw\collect_scripts\sample_lta_bus_arrival.ps1 -BusStopFile .\data\raw\collect_scripts\hot_bus_stops.txt -MaxStops 100
```

或临时指定少量站点：

```powershell
.\data\raw\collect_scripts\sample_lta_bus_arrival.ps1 -BusStopCodes 46009,22009,75009
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

## 7. Linux 服务器实时采集

服务器部署时，推荐把 Python 采集脚本放在：

```text
/root/BusMind/data/raw/collect_lta_realtime_server.py
```

采集结果默认写入：

```text
/root/BusMind/data/raw/lta
```

脚本只依赖 Python 标准库，`AccountKey` 通过环境变量配置，不写入代码

启动命令：

```bash
python collect_lta_realtime_server.py --mode both --account-key 你的AccountKey --bus-stop-file hot_bus_stops.txt --bus-poll-seconds 30 --traffic-poll-seconds 300
```

采集口径：

- Bus Arrival：官方 20 秒更新；服务器默认每 30 秒采一次热门站点。
- Traffic Speed Bands：官方 5 分钟更新；服务器每 5 分钟采一次。
- Bus Arrival 只在四个时间窗采集：
  - `morning_peak`：07:00-09:00
  - `midday`：12:00-14:00
  - `evening_peak`：17:00-19:00
  - `night`：21:00-23:00

建议准备热门站点文件：

```text
/root/BusMind/data/raw/hot_bus_stops.txt
```

每行一个站点编号，例如：

```text
83139
04167
01112
```

Bus Arrival 的每条 JSONL 会额外保存：

- `collection_window`
- `collection_round`
- `query_time`
- `bus_stop_code`

这样后续构建推荐模型训练集时，可以按早高峰、平峰、晚高峰、夜间区分动态样本。
