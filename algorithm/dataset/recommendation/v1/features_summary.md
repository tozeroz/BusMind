# Recommendation Feature Dataset Summary

Input: `algorithm\dataset\recommendation\v1\features.csv`

- Rows: 3000
- Candidate groups: 100
- Average routes per group: 30.0
- Synthetic rows: 3000
- Missing required columns: none
- Missing feature source keys: none

## Numeric Feature Ranges

| feature | non_null | min | median | max |
| --- | --- | --- | --- | --- |
| eta_minutes | 3000 | 0.02 | 16.375 | 44.28 |
| ride_time_minutes | 3000 | 5.0 | 36.0 | 214.7 |
| walk_time_minutes | 3000 | 0.0 | 3.0 | 9.0 |
| walk_distance_meters | 3000 | 0.0 | 240.0 | 720.0 |
| transfer_count | 3000 | 0.0 | 1.0 | 2.0 |
| load_score | 3000 | 70.0 | 100.0 | 100.0 |
| history_flow_score | 3000 | 45.0 | 45.0 | 45.0 |
| congestion_score | 3000 | 43.21 | 58.6 | 94.72 |
| data_freshness_seconds | 3000 | 60.0 | 60.0 | 60.0 |
| monitored_score | 3000 | 75.0 | 100.0 | 100.0 |
| completeness_score | 3000 | 64.0 | 76.0 | 76.0 |
| avg_service_frequency_minutes | 3000 | 4.25 | 11.375 | 45.0 |

## Degraded Field Counts

| field | count |
| --- | --- |
| data_freshness_seconds | 3000 |
| transfer_count | 3000 |
| walk_distance_meters | 3000 |
| walk_time_minutes | 3000 |
| congestion_score | 1025 |
| ride_time_minutes | 26 |
| avg_service_frequency_minutes | 1 |
