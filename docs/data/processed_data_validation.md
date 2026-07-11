# BusMind processed data validation

## Row counts

| **Dataset** | **Rows** |
|---|---:|
| `bus_eta_status` | 4727 |
| `bus_line` | 796 |
| `bus_load_status` | 4727 |
| `bus_station` | 5205 |
| `bus_vehicle` | 495 |
| `line_station` | 26799 |
| `lta_bus_arrival` | 4727 |
| `map_road_segment` | 26004 |
| `map_station` | 5205 |
| `passenger_flow_trend` | 203044 |
| `traffic_speed_bands` | 143787 |

## Findings

| **Severity** | **Dataset** | **Message** |
|---|---|---|
| WARN | `eta_prediction` | Unexpected CSV in processed dir: eta_prediction.csv. Keep only if it is a deliberate local artifact. |
| WARN | `load_prediction` | Unexpected CSV in processed dir: load_prediction.csv. Keep only if it is a deliberate local artifact. |
| WARN | `traffic_speed_bands` | 51 rows have speed_band=0, treated as unknown |

Result: 0 error(s), 3 warning(s).
