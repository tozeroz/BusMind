# 候选路线特征数据摘要

输入文件：`D:\SummerTraining\BusMind\algorithm\dataset\features\features.csv`

- 行数：10000
- 候选路线组数：1000
- 平均每组路线数：10.0
- 合成样本行数：10000
- 缺失冻结字段：无
- 缺失特征来源字段：无

## 预处理后的数值特征范围

| 特征 | 非空数 | 最小值 | 中位数 | 最大值 |
| --- | --- | --- | --- | --- |
| eta_minutes | 10000 | 0.0 | 12.195 | 43.22 |
| ride_time_minutes | 10000 | 3.0 | 77.0 | 320.0 |
| walk_time_minutes | 10000 | 4.0 | 6.0 | 8.0 |
| walk_distance_meters | 10000 | 320.0 | 480.0 | 640.0 |
| transfer_count | 10000 | 0.0 | 1.0 | 2.0 |
| load_score | 10000 | 35.0 | 100.0 | 100.0 |
| history_flow_score | 10000 | 45.0 | 45.0 | 45.0 |
| congestion_score | 10000 | 40.0 | 60.0 | 90.0 |
| data_freshness_seconds | 10000 | 48624.34 | 48654.58 | 139875.62 |
| monitored_score | 10000 | 75.0 | 100.0 | 100.0 |
| completeness_score | 10000 | 58.0 | 82.0 | 82.0 |
| avg_service_frequency_minutes | 10000 | 3.5 | 11.812 | 117.167 |

## 降级字段统计

| 字段 | 次数 |
| --- | --- |
| ride_time_minutes | 10000 |
| walk_distance_meters | 10000 |
| walk_time_minutes | 10000 |
| route_speed_band | 1086 |
| eta_minutes | 596 |
| load_code | 596 |
| source_updated_at | 109 |
| avg_service_frequency_minutes | 17 |
