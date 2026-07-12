# Directed Transit Graph + 0-1 BFS 换乘路由

模块路径: `app.services.recommend_service.transit_graph`

## 直接调

from app.services.recommend_service.transit_graph import TransitGraphService

*# 1. 实例化(一次就够,内部已经缓存快照)*

service = TransitGraphService(db_session_or_repository)

*# 2. 查询*

results = await service.find_candidates(

​    start_station_id=1,

​    end_station_id=12,

​    max_transfer=2,        *# 用户允许的最大换乘次数,默认 2*

​    max_candidates=8,     *# 最多返回几条候选,默认 8,建议给 5~10*

)

*# results 已经是 list[CandidateRouteData] 类型,直接用*

## 数据契约(返回值是 `CandidateRouteData`)

| 字段                   | 类型                           | 说明                                         |
| :--------------------- | :----------------------------- | :------------------------------------------- |
| `route_id`             | `str`                          | 自动生成,例如 `graph_(1,2,3)_101_108_0`      |
| `vehicle_id`           | `int`                          | 0(由你自己的 eta/load 服务再填)              |
| `line_ids`             | `tuple[int, ...]`              | 乘坐的线路顺序,例如 `(1, 2, 3)` 代表三次换乘 |
| `segments`             | `tuple[RouteSegmentData, ...]` | 详细分段,每段一条线路                        |
| `boarding_station_id`  | `int`                          | 起点站                                       |
| `alighting_station_id` | `int`                          | 终点站                                       |
| `walk_time_minutes`    | `float`                        | 估算步行时间(4 + 2 × 换乘次数)               |
| `ride_time_minutes`    | `float`                        | 估算乘车时间(站数 × 2 分钟)                  |
| `transfer_count`       | `int`                          | 换乘次数                                     |

## 行为保证

- 0 换乘最优:同线路直达的路径一定最先返回
- 禁环:同一 `line_id` 不会重复出现(不会让人坐同一趟车来回)
- 去重:`(line_ids, transfer_count)` 唯一签名,不会返回重复候选
- 候选数量:上限 8 条(可调),保留少换乘的优先

## 异常 / 边界

- 起点 == 终点 → 返回 `[]`
- 起点或终点不在数据库 → 返回 `[]`
- 完全不可达(`max_transfer` 内都到不了)→ 返回 `[]`