# Recommendation Feature Dataset Summary

Input: `D:\SummerTraining\BusMind\algorithm\dataset\features.csv`

- Rows: 10000
- Candidate groups: 1000
- Average routes per group: 10.0
- Synthetic rows: 10000
- Missing frozen columns: none
- Missing feature source keys: none

## Numeric Feature Ranges After Preprocessing

| feature | non_null | min | median | max |
| --- | --- | --- | --- | --- |
| eta_minutes | 10000 | 0.0 | 12.195 | 43.22 |
| ride_time_minutes | 10000 | 3.0 | 77.0 | 320.0 |
| walk_time_minutes | 10000 | 4.0 | 6.0 | 8.0 |
| walk_distance_meters | 10000 | 320.0 | 480.0 | 640.0 |
| transfer_count | 10000 | 0.0 | 1.0 | 2.0 |
| load_score | 10000 | 35.0 | 100.0 | 100.0 |
| history_flow_score | 10000 | 45.0 | 45.0 | 45.0 |
| congestion_score | 10000 | 40.0 | 60.0 | 90.0 |
| data_freshness_seconds | 10000 | 0.0 | 0.0 | 70807.36 |
| monitored_score | 10000 | 75.0 | 100.0 | 100.0 |
| completeness_score | 10000 | 58.0 | 82.0 | 82.0 |
| avg_service_frequency_minutes | 10000 | 3.5 | 11.812 | 117.167 |

## Degraded Field Counts

| field | count |
| --- | --- |
| ride_time_minutes | 10000 |
| walk_distance_meters | 10000 |
| walk_time_minutes | 10000 |
| route_speed_band | 1086 |
| eta_minutes | 596 |
| load_code | 596 |
| source_updated_at | 109 |
| avg_service_frequency_minutes | 17 |
