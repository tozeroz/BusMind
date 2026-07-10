# BusMind项目接口文档

# 目录

**一、文档结论与接口规模**

**二、统一接口规范**

**三、接口总览**

**四、各模块接口说明**

**五、兼容别名接口**

**六、核心数据模型**

**七、枚举、错误码与联调注意事项**

附录：典型请求示例

# 一、文档结论与接口规模

|**统计项**|**数量**|**说明**|
|---|---|---|
|业务路由路径|48|不含根路径健康检查；同一路径可有多个 HTTP 方法。|
|业务接口操作|61|GET/POST/PATCH/DELETE   操作总数。|
|主接口操作|56|含 2 个后台管理触发接口；其余主接口均有 frontend/src/api 中的对应方法。|
|兼容别名操作|5|/bus\-lines   与 /bus\-stations，仅为旧路径兼容。|
|健康检查|1|GET   /，返回简单对象，不使用统一 ApiResponse 外壳。|



关键口径变更：

- 统一前缀为 /api/v1；前端 VITE\_API\_BASE\_URL=/api/v1。

- 分页参数使用 page、limit，不再使用旧文档中的 page\_size。

- 主线路/站点路径为 /lines、/stations；同时保留 /bus\-lines、/bus\-stations 只读别名。

- 实时车辆路径为 /vehicles/realtime，不存在旧文档中的 /bus\-vehicles/realtime。

- 历史预测拆分为 /history/eta/\.\.\.、/history/load/\.\.\. 和 /history/passenger\-flow/prediction。

- Passenger Flow 表示站点/线路客流；Passenger Load 表示车辆内客载，文档中严格区分。

# 二、统一接口规范

## 2\.1 基础约定

|**规范项**|**当前项目约定**|
|---|---|
|**本地服务地址**|http://127\.0\.0\.1:8000|
|**统一接口前缀**|/api/v1|
|**协议与编码**|HTTP/HTTPS；UTF\-8|
|**请求格式**|GET   使用 Path/Query；POST/PATCH 使用 application/json|
|**字段命名**|请求与响应字段使用 snake\_case；路径使用小写短横线|
|**时间格式**|ISO   8601；示例 2026\-07\-10T09:00:00\+08:00|
|**分页**|page 从 1 开始；limit 默认 20，最大 100（各接口以参数表为准）|
|**坐标**|longitude   经度，latitude 纬度；WGS84/项目统一坐标系|
|**前端超时**|Axios   timeout=8000ms|
|**令牌存储**|busmind\_access\_token   或 access\_token（localStorage/sessionStorage）|



## 2\.2 统一成功响应

|\{<br>    "code": 0,<br>    "message": "success",<br>    "data": \{\},<br>    "trace\_id": "req\_xxx",<br>    "timestamp": "2026\-07\-10T09:00:00\+08:00"<br>\}|
|---|



## 2\.3 统一失败响应

|\{<br>    "code": 42200,<br>    "message": "参数校验失败: station\_id Input should be greater   than 0",<br>    "data": null,<br>    "trace\_id": "req\_xxx",<br>    "timestamp": "2026\-07\-10T09:00:01\+08:00"<br>\}|
|---|

|**说明：**智能与仿真模块的业务异常、参数校验已注册统一处理器。用户模块的 OAuth2   Token 校验失败目前可能仍返回 FastAPI 标准 detail 结构；联调时应同时兼容 HTTP 401。|
|---|



## 2\.4 鉴权与权限现状

|**接口类别**|**当前鉴权**|**说明**|
|---|---|---|
|注册、登录|否|匿名调用。|
|当前用户、收藏、查询历史|是|Authorization:   Bearer \<access\_token\>。|
|线路、站点、车辆、地图、位置、历史查询|否|便于演示和前端联调。|
|ETA、客载、步行、推荐、AI|否|当前代码未绑定用户；AI   可使用请求 context。|
|线路/站点/车辆写接口|否|当前代码可直接调用；生产环境建议增加 admin 权限。|
|后台 LTA 采集刷新|否|当前代码未绑定鉴权；建议仅内部或管理员调用。|
|仿真与预测更新|否|建议部署时限制为内部服务或 admin。|

## 2\.5 主要枚举

|**枚举/字段**|**允许值**|**说明**|
|---|---|---|
|role|passenger   / admin|用户角色。|
|direction|forward   / backward|线路站点方向。|
|车辆   CRUD status|running   / stopped / maintenance|数据库车辆运行状态。|
|仿真   VehicleRunStatus|normal   / delayed / offline|智能/仿真模块运行状态。|
|LoadLevel|seats\_available   / standing\_available / limited\_standing|有座位 / 可站立 / 站立空间有限。|
|preference|balanced   / low\_load / less\_walking / less\_transfer / fastest|推荐偏好。|
|ai   mode|qa   / suggest / explain|问答   / 建议 / 路线解释。|
|route\_mode|straight\_line   / map\_api|步行估算模式。|
|prediction\_type|eta   / passenger\_load / passenger\_flow|写入的预测结果类别。|
|granularity|hour   / day / week|客流趋势粒度。|





# 三、接口总览

下表列出正式 FastAPI 应用中的全部 62 个操作（61 个业务接口 \+ 1 个健康检查）。

|**序号**|**模块**|**方法**|**路径**|**功能**|**鉴权**|**前端方法**|
|---|---|---|---|---|---|---|
|1|用户与鉴权|POST|/api/v1/users/login|用户登录|无需鉴权（按当前代码）|loginUser\(data\)|
|2|用户与鉴权|GET|/api/v1/users/me|获取当前用户信息|Bearer   Token|getCurrentUser\(\)|
|3|用户与鉴权|PATCH|/api/v1/users/me|修改当前用户信息|Bearer   Token|updateCurrentUser\(data\)|
|4|用户与鉴权|GET|/api/v1/users/me/favorites|查询用户收藏|Bearer   Token|getUserFavorites\(params\)|
|5|用户与鉴权|POST|/api/v1/users/me/favorites|新增用户收藏|Bearer   Token|addUserFavorite\(data\)|
|6|用户与鉴权|DELETE|/api/v1/users/me/favorites/\{favorite\_id\}|取消用户收藏|Bearer   Token|deleteUserFavorite\(favoriteId\)|
|7|用户与鉴权|GET|/api/v1/users/me/query\-history|查询用户搜索/调用历史|Bearer   Token|getUserQueryHistory\(params\)|
|8|用户与鉴权|POST|/api/v1/users/register|用户注册|无需鉴权（按当前代码）|registerUser\(data\)|
|9|线路管理|GET|/api/v1/bus\-lines|查询线路列表（兼容别名）|无需鉴权（按当前代码）|后端兼容/无直接调用|
|10|线路管理|GET|/api/v1/bus\-lines/\{line\_id\}|查询线路详情（兼容别名）|无需鉴权（按当前代码）|后端兼容/无直接调用|
|11|线路管理|GET|/api/v1/bus\-lines/\{line\_id\}/stations|查询线路站点（兼容别名）|无需鉴权（按当前代码）|后端兼容/无直接调用|
|12|线路管理|GET|/api/v1/lines|查询线路列表|无需鉴权（按当前代码）|getLines\(params\)|
|13|线路管理|POST|/api/v1/lines|创建线路|无需鉴权（按当前代码）|createLine\(data\)|
|14|线路管理|PATCH|/api/v1/lines/stations/\{line\_station\_id\}|修改线路站点顺序或方向|无需鉴权（按当前代码）|updateLineStation\(lineStationId,   data\)|
|15|线路管理|DELETE|/api/v1/lines/stations/\{line\_station\_id\}|从线路移除站点|无需鉴权（按当前代码）|removeStationFromLine\(lineStationId\)|
|16|线路管理|GET|/api/v1/lines/\{line\_id\}|查询线路详情|无需鉴权（按当前代码）|getLineDetail\(lineId\)|
|17|线路管理|PATCH|/api/v1/lines/\{line\_id\}|修改线路|无需鉴权（按当前代码）|updateLine\(lineId,   data\)|
|18|线路管理|DELETE|/api/v1/lines/\{line\_id\}|删除线路|无需鉴权（按当前代码）|deleteLine\(lineId\)|
|19|线路管理|GET|/api/v1/lines/\{line\_id\}/stations|查询线路站点顺序|无需鉴权（按当前代码）|getLineStations\(lineId\)|
|20|线路管理|POST|/api/v1/lines/\{line\_id\}/stations|向线路添加站点|无需鉴权（按当前代码）|addStationToLine\(lineId,   data\)|
|21|站点管理|GET|/api/v1/bus\-stations|查询站点列表（兼容别名）|无需鉴权（按当前代码）|后端兼容/无直接调用|
|22|站点管理|GET|/api/v1/bus\-stations/\{station\_id\}|查询站点详情（兼容别名）|无需鉴权（按当前代码）|后端兼容/无直接调用|
|23|站点管理|GET|/api/v1/stations|查询站点列表|无需鉴权（按当前代码）|getStations\(params\)|
|24|站点管理|POST|/api/v1/stations|创建站点|无需鉴权（按当前代码）|createStation\(data\)|
|25|站点管理|GET|/api/v1/stations/coordinates/all|查询全部站点坐标|无需鉴权（按当前代码）|getAllStationCoordinates\(\)|
|26|站点管理|POST|/api/v1/stations/nearby|查询附近站点|无需鉴权（按当前代码）|searchNearbyStations\(data\)|
|27|站点管理|GET|/api/v1/stations/\{station\_id\}|查询站点详情|无需鉴权（按当前代码）|getStationDetail\(stationId\)|
|28|站点管理|PATCH|/api/v1/stations/\{station\_id\}|修改站点|无需鉴权（按当前代码）|updateStation\(stationId,   data\)|
|29|站点管理|DELETE|/api/v1/stations/\{station\_id\}|删除站点|无需鉴权（按当前代码）|deleteStation\(stationId\)|
|30|站点管理|GET|/api/v1/stations/\{station\_id\}/lines|查询站点经过线路|无需鉴权（按当前代码）|getStationLines\(stationId\)|
|31|车辆管理|GET|/api/v1/vehicles|查询车辆列表|无需鉴权（按当前代码）|getVehicles\(params\)|
|32|车辆管理|POST|/api/v1/vehicles|创建车辆|无需鉴权（按当前代码）|createVehicle\(data\)|
|33|车辆管理|GET|/api/v1/vehicles/line/\{line\_id\}|查询指定线路车辆|无需鉴权（按当前代码）|getVehiclesByLine\(lineId\)|
|34|车辆管理|GET|/api/v1/vehicles/realtime|查询车辆实时位置与状态|无需鉴权（按当前代码）|getRealtimeVehicles\(params\)|
|35|车辆管理|GET|/api/v1/vehicles/\{vehicle\_id\}|查询车辆详情|无需鉴权（按当前代码）|getVehicleDetail\(vehicleId\)|
|36|车辆管理|PATCH|/api/v1/vehicles/\{vehicle\_id\}|修改车辆|无需鉴权（按当前代码）|updateVehicle\(vehicleId,   data\)|
|37|车辆管理|DELETE|/api/v1/vehicles/\{vehicle\_id\}|删除车辆|无需鉴权（按当前代码）|deleteVehicle\(vehicleId\)|
|38|地图数据|GET|/api/v1/map/lines|查询地图线路折线|无需鉴权（按当前代码）|getMapLines\(\)|
|39|地图数据|GET|/api/v1/map/road\-segments|查询地图路段连线|无需鉴权（按当前代码）|getRoadSegments\(\)|
|40|地图数据|GET|/api/v1/map/stations|查询地图站点|无需鉴权（按当前代码）|getMapStations\(params\)|
|41|位置搜索|GET|/api/v1/locations/map/stations|查询地图所需全部站点|无需鉴权（按当前代码）|getLocationMapStations\(\)|
|42|位置搜索|GET|/api/v1/locations/nearby|按坐标查询附近站点|无需鉴权（按当前代码）|getNearbyLocations\(params\)|
|43|位置搜索|GET|/api/v1/locations/search|搜索位置/站点|无需鉴权（按当前代码）|searchLocations\(params\)|
|44|位置搜索|GET|/api/v1/locations/\{location\_id\}|查询位置/站点详情|无需鉴权（按当前代码）|getLocationDetail\(locationId\)|
|45|历史与预测查询|GET|/api/v1/history/eta/line/\{line\_id\}|查询线路 ETA 预测记录|无需鉴权（按当前代码）|getEtaPredictionsByLine\(lineId,   params\)|
|46|历史与预测查询|GET|/api/v1/history/eta/\{vehicle\_id\}/\{target\_station\_id\}|查询车辆到目标站的最新 ETA|无需鉴权（按当前代码）|getEtaPredictionForVehicle\(vehicleId,   targetStationId, params\)|
|47|历史与预测查询|GET|/api/v1/history/load/line/\{line\_id\}|查询线路客载预测记录|无需鉴权（按当前代码）|getLoadPredictionsByLine\(lineId,   params\)|
|48|历史与预测查询|GET|/api/v1/history/load/\{line\_id\}|查询最新客载预测|无需鉴权（按当前代码）|getLoadPrediction\(lineId,   params\)|
|49|历史与预测查询|GET|/api/v1/history/passenger\-flow|查询历史客流趋势|无需鉴权（按当前代码）|getPassengerFlowTrend\(params\)|
|50|历史与预测查询|GET|/api/v1/history/passenger\-flow/prediction|查询客流预测记录|无需鉴权（按当前代码）|getPassengerFlowPrediction\(params\)|
|51|ETA   预测|GET|/api/v1/eta|计算车辆预计到站时间|无需鉴权（按当前代码）|getEta\(params\)|
|52|车辆客载预测|POST|/api/v1/passenger\-load\-prediction|预测车辆客载状态|无需鉴权（按当前代码）|predictPassengerLoad\(data\)|
|53|步行、体验评价与路线推荐|POST|/api/v1/recommend\-routes|生成公交出行推荐方案|无需鉴权（按当前代码）|recommendRoutes\(data\)|
|54|步行、体验评价与路线推荐|POST|/api/v1/travel\-experience/evaluate|计算出行体验评分|无需鉴权（按当前代码）|evaluateTravelExperience\(data\)|
|55|步行、体验评价与路线推荐|POST|/api/v1/walking\-time\-estimation|估算前往上车站的步行时间|无需鉴权（按当前代码）|estimateWalkingTime\(data\)|
|56|AI   出行助手|POST|/api/v1/ai/travel|AI 出行问答、建议与路线解释|无需鉴权（按当前代码）|askAiTravel\(data\)|
|57|后台 LTA 采集刷新|POST|/api/v1/admin/lta/bus\-arrival/refresh|手动刷新 LTA 公交到站并可同步入库|无需鉴权（按当前代码）|后端管理/无直接调用|
|58|后台 LTA 采集刷新|POST|/api/v1/admin/lta/traffic\-speed\-bands/refresh|手动刷新 LTA 路况速度带并可同步入库|无需鉴权（按当前代码）|后端管理/无直接调用|
|59|仿真与预测更新|POST|/api/v1/simulation/lta\-bus\-arrival/refresh|刷新   LTA 公交到站数据（兼容旧入口，已废弃）|无需鉴权（按当前代码）|refreshLtaBusArrival\(data\)|
|60|仿真与预测更新|POST|/api/v1/simulation/prediction\-results|写入/刷新预测结果|无需鉴权（按当前代码）|updatePredictionResult\(data\)|
|61|仿真与预测更新|PATCH|/api/v1/simulation/vehicle\-status/\{vehicle\_id\}|更新仿真车辆状态|无需鉴权（按当前代码）|updateVehicleStatus\(vehicleId,   data\)|
|62|健康检查|GET|/|服务健康检查|无需鉴权（按当前代码）|后端兼容/无直接调用|





# 四、各模块接口说明

本章详细说明 56 个主接口。兼容别名接口在第五章单独列出，避免重复。

## 4\.1 用户与鉴权

完成用户注册登录、当前用户、收藏与查询历史；仅“我的”相关接口需要登录。

### 4\.1\.1 POST /api/v1/users/login

|**项目**|**内容**|
|---|---|
|**接口名称**|用户登录|
|**模块**|用户与鉴权|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|loginUser\(data\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|username|Body|string|是|登录账号，4\-32 个字符，系统内唯一。|
|password|Body|string|是|密码，8\-64   个字符。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 400 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LoginResponse|字段明细见“核心数据模型”。|



### 4\.1\.2 GET /api/v1/users/me

|**项目**|**内容**|
|---|---|
|**接口名称**|获取当前用户信息|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|getCurrentUser\(\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



请求参数：无。

**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 401|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|UserMeResponse|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|



### 4\.1\.3 PATCH /api/v1/users/me

|**项目**|**内容**|
|---|---|
|**接口名称**|修改当前用户信息|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|updateCurrentUser\(data\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|nickname|Body|string（可空）|否|用户昵称，最长 32 个字符。|
|old\_password|Body|string（可空）|否|修改密码时提供的原密码。|
|new\_password|Body|string（可空）|否|新密码，至少   8 个字符；提供时必须同时提供 old\_password。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 400 / 401 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|UserDTO|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|



### 4\.1\.4 GET /api/v1/users/me/favorites

|**项目**|**内容**|
|---|---|
|**接口名称**|查询用户收藏|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|getUserFavorites\(params\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|页码，从 1 开始。 默认 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 401 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|UserFavoriteResponse|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|

### 4\.1\.5 POST /api/v1/users/me/favorites

|**项目**|**内容**|
|---|---|
|**接口名称**|新增用户收藏|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|addUserFavorite\(data\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|favorite\_type|Body|string|是|收藏对象类型，例如   line、route。|
|target\_id|Body|int|是|收藏目标编号，必须为正整数。|
|target\_name|Body|string（可空）|否|收藏目标显示名称。 默认 ""。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 401 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|UserFavoriteDTO|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|



### 4\.1\.6 DELETE /api/v1/users/me/favorites/\{favorite\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|取消用户收藏|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|deleteUserFavorite\(favoriteId\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|favorite\_id|Path|int|是|收藏记录编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 401 / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|null|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|



### 4\.1\.7 GET /api/v1/users/me/query\-history

|**项目**|**内容**|
|---|---|
|**接口名称**|查询用户搜索/调用历史|
|**模块**|用户与鉴权|
|**当前鉴权**|Bearer   Token|
|**前端方法**|getUserQueryHistory\(params\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|页码，从 1 开始。 默认 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 401 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|QueryHistoryResponse|字段明细见“核心数据模型”。|



|**说明：**需要 Authorization: Bearer \<access\_token\>。|
|---|



### 4\.1\.8 POST /api/v1/users/register

|**项目**|**内容**|
|---|---|
|**接口名称**|用户注册|
|**模块**|用户与鉴权|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|registerUser\(data\)|
|**数据来源/实现**|SQLAlchemy   用户、收藏与历史表；JWT。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|username|Body|string|是|登录账号，4\-32 个字符，系统内唯一。|
|password|Body|string|是|密码，8\-64   个字符。|
|nickname|Body|string（可空）|否|用户昵称，最长 32 个字符。 默认   ""。|
|role|Body|string（可空）|否|用户角色：passenger   或 admin；默认 passenger。 默认 "passenger"。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|UserDTO|字段明细见“核心数据模型”。|



## 4\.2 线路管理

提供线路 CRUD、线路站点关系维护及 /bus\-lines 兼容别名。

### 4\.2\.1 GET /api/v1/lines

|**项目**|**内容**|
|---|---|
|**接口名称**|查询线路列表|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLines\(params\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|页码，从 1 开始。 默认 1；\>= 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20；\>= 1；\<= 100。|
|line\_name|Query|string（可空）|否|线路名称；查询时用于模糊筛选。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LineListResponse|字段明细见“核心数据模型”。|



### 4\.2\.2 POST /api/v1/lines

|**项目**|**内容**|
|---|---|
|**接口名称**|创建线路|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|createLine\(data\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_name|Body|string|是|线路名称；查询时用于模糊筛选。|
|line\_code|Body|string|是|线路唯一编码，最长 20 个字符。|
|start\_station|Body|string|是|起点站编码或名称。|
|end\_station|Body|string|是|终点站编码或名称。|
|total\_stations|Body|int（可空）|否|线路站点总数。 默认 0。|
|distance\_km|Body|float（可空）|否|线路总距离，单位 km。 默认 0\.0。|
|first\_departure\_time|Body|string（可空）|否|首班时间，当前代码使用字符串。|
|last\_departure\_time|Body|string（可空）|否|末班时间，当前代码使用字符串。|
|interval\_minutes|Body|int（可空）|否|发车间隔，单位分钟。 默认 10。|
|status|Body|string（可空）|否|运行/资源状态；具体枚举随模块而定。 默认   "active"。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusLineDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.2\.3 PATCH /api/v1/lines/stations/\{line\_station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|修改线路站点顺序或方向|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updateLineStation\(lineStationId,   data\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_station\_id|Path|int|是|线路与站点关系记录编号。|
|order\_index|Body|int（可空）|否|站点在线路中的顺序号。|
|direction|Body|string（可空）|否|线路方向：forward   或 backward。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LineStationDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.2\.4 DELETE /api/v1/lines/stations/\{line\_station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|从线路移除站点|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|removeStationFromLine\(lineStationId\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_station\_id|Path|int|是|线路与站点关系记录编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|null|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.2\.5 GET /api/v1/lines/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询线路详情|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLineDetail\(lineId\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusLineWithStationsDTO|字段明细见“核心数据模型”。|



### 4\.2\.6 PATCH /api/v1/lines/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|修改线路|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updateLine\(lineId,   data\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|
|line\_name|Body|string（可空）|否|线路名称；查询时用于模糊筛选。|
|start\_station|Body|string（可空）|否|起点站编码或名称。|
|end\_station|Body|string（可空）|否|终点站编码或名称。|
|total\_stations|Body|int（可空）|否|线路站点总数。|
|distance\_km|Body|float（可空）|否|线路总距离，单位 km。|
|first\_departure\_time|Body|string（可空）|否|首班时间，当前代码使用字符串。|
|last\_departure\_time|Body|string（可空）|否|末班时间，当前代码使用字符串。|
|interval\_minutes|Body|int（可空）|否|发车间隔，单位分钟。|
|status|Body|string（可空）|否|运行/资源状态；具体枚举随模块而定。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusLineDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|

### 4\.2\.7 DELETE /api/v1/lines/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|删除线路|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|deleteLine\(lineId\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|null|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.2\.8 GET /api/v1/lines/\{line\_id\}/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|查询线路站点顺序|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLineStations\(lineId\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|\{   stations: LineStationDTO\[\] \}|字段明细见“核心数据模型”。|



### 4\.2\.9 POST /api/v1/lines/\{line\_id\}/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|向线路添加站点|
|**模块**|线路管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|addStationToLine\(lineId,   data\)|
|**数据来源/实现**|SQLAlchemy 线路、站点、线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|
|line\_id|Body|int|是|线路编号。|
|station\_id|Body|int|是|站点编号。|
|order\_index|Body|int|是|站点在线路中的顺序号。|
|direction|Body|string|否|线路方向：forward   或 backward。 默认 "forward"。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LineStationDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。 Path 中的 line\_id 会覆盖请求体中的 line\_id；调用时建议保持二者一致。|
|---|



## 4\.3 站点管理

提供站点 CRUD、站点经过线路、附近站点、坐标查询及 /bus\-stations 兼容别名。

### 4\.3\.1 GET /api/v1/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|查询站点列表|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getStations\(params\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|页码，从 1 开始。 默认 1；\>= 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20；\>= 1；\<= 100。|
|station\_name|Query|string（可空）|否|站点名称；查询时用于模糊筛选。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|StationListResponse|字段明细见“核心数据模型”。|



### 4\.3\.2 POST /api/v1/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|创建站点|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|createStation\(data\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_name|Body|string|是|站点名称；查询时用于模糊筛选。|
|station\_code|Body|string|是|站点唯一编码，最长 20 个字符。|
|latitude|Body|float|是|纬度，范围   \-90 至 90。|
|longitude|Body|float|是|经度，范围   \-180 至 180。|
|address|Body|string（可空）|否|站点地址。|
|zone|Body|string（可空）|否|站点所属区域。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusStationDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|

### 4\.3\.3 GET /api/v1/stations/coordinates/all

|**项目**|**内容**|
|---|---|
|**接口名称**|查询全部站点坐标|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getAllStationCoordinates\(\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



请求参数：无。

**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|\{   stations: BusStationDTO\[\] \}|字段明细见“核心数据模型”。|



### 4\.3\.4 POST /api/v1/stations/nearby

|**项目**|**内容**|
|---|---|
|**接口名称**|查询附近站点|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|searchNearbyStations\(data\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|latitude|Body|float|是|纬度，范围   \-90 至 90。|
|longitude|Body|float|是|经度，范围   \-180 至 180。|
|radius\_km|Body|float|否|搜索半径，单位 km。 默认 1\.0。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|NearbyStationResponse|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.3\.5 GET /api/v1/stations/\{station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询站点详情|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getStationDetail\(stationId\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_id|Path|int|是|站点编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusStationDTO|字段明细见“核心数据模型”。|



### 4\.3\.6 PATCH /api/v1/stations/\{station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|修改站点|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updateStation\(stationId,   data\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_id|Path|int|是|站点编号。|
|station\_name|Body|string（可空）|否|站点名称；查询时用于模糊筛选。|
|latitude|Body|float（可空）|否|纬度，范围   \-90 至 90。|
|longitude|Body|float（可空）|否|经度，范围   \-180 至 180。|
|address|Body|string（可空）|否|站点地址。|
|zone|Body|string（可空）|否|站点所属区域。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusStationDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.3\.7 DELETE /api/v1/stations/\{station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|删除站点|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|deleteStation\(stationId\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_id|Path|int|是|站点编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|null|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.3\.8 GET /api/v1/stations/\{station\_id\}/lines

|**项目**|**内容**|
|---|---|
|**接口名称**|查询站点经过线路|
|**模块**|站点管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getStationLines\(stationId\)|
|**数据来源/实现**|SQLAlchemy 站点与线路站点关系表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_id|Path|int|是|站点编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|StationLinesResponse|字段明细见“核心数据模型”。|

## 4\.4 车辆管理

提供车辆 CRUD、按线路查询和实时位置/客载状态查询。

### 4\.4\.1 GET /api/v1/vehicles

|**项目**|**内容**|
|---|---|
|**接口名称**|查询车辆列表|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getVehicles\(params\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|页码，从 1 开始。 默认 1；\>= 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20；\>= 1；\<= 100。|
|line\_id|Query|int（可空）|否|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|VehicleListResponse|字段明细见“核心数据模型”。|



### 4\.4\.2 POST /api/v1/vehicles

|**项目**|**内容**|
|---|---|
|**接口名称**|创建车辆|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|createVehicle\(data\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_code|Body|string|是|车辆唯一编码，最长 20 个字符。|
|line\_id|Body|int|是|线路编号。|
|current\_latitude|Body|float|是|车辆当前纬度。|
|current\_longitude|Body|float|是|车辆当前经度。|
|current\_station\_id|Body|int（可空）|否|车辆当前站点编号。|
|next\_station\_id|Body|int（可空）|否|车辆下一站编号。|
|progress|Body|float（可空）|否|车辆在当前路段的进度。 默认 0\.0。|
|status|Body|string（可空）|否|运行/资源状态；具体枚举随模块而定。 默认   "running"。|
|speed\_kmh|Body|float（可空）|否|车辆速度，单位 km/h（车辆 CRUD 字段）。   默认 0\.0。|
|direction\_deg|Body|float（可空）|否|行驶方向角，单位度。 默认 0\.0。|
|onboard\_count|Body|int（可空）|否|当前车上人数。 默认 0。|
|capacity|Body|int（可空）|否|车辆核定容量。 默认 60。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|201   / 400 / 409 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusVehicleDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.4\.3 GET /api/v1/vehicles/line/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询指定线路车辆|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getVehiclesByLine\(lineId\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|\{   vehicles: BusVehicleDTO\[\] \}|字段明细见“核心数据模型”。|



### 4\.4\.4 GET /api/v1/vehicles/realtime

|**项目**|**内容**|
|---|---|
|**接口名称**|查询车辆实时位置与状态|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getRealtimeVehicles\(params\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int（可空）|否|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|\{   vehicles: BusVehicleDTO\[\] \}|字段明细见“核心数据模型”。|



### 4\.4\.5 GET /api/v1/vehicles/\{vehicle\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询车辆详情|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getVehicleDetail\(vehicleId\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Path|int|是|车辆编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusVehicleDTO|字段明细见“核心数据模型”。|



### 4\.4\.6 PATCH /api/v1/vehicles/\{vehicle\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|修改车辆|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updateVehicle\(vehicleId,   data\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Path|int|是|车辆编号。|
|current\_latitude|Body|float（可空）|否|车辆当前纬度。|
|current\_longitude|Body|float（可空）|否|车辆当前经度。|
|current\_station\_id|Body|int（可空）|否|车辆当前站点编号。|
|next\_station\_id|Body|int（可空）|否|车辆下一站编号。|
|progress|Body|float（可空）|否|车辆在当前路段的进度。|
|status|Body|string（可空）|否|运行/资源状态；具体枚举随模块而定。|
|speed\_kmh|Body|float（可空）|否|车辆速度，单位 km/h（车辆 CRUD 字段）。|
|direction\_deg|Body|float（可空）|否|行驶方向角，单位度。|
|onboard\_count|Body|int（可空）|否|当前车上人数。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusVehicleDTO|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



### 4\.4\.7 DELETE /api/v1/vehicles/\{vehicle\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|删除车辆|
|**模块**|车辆管理|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|deleteVehicle\(vehicleId\)|
|**数据来源/实现**|SQLAlchemy 车辆与线路/站点数据。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Path|int|是|车辆编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|null|字段明细见“核心数据模型”。|



|**说明：**当前代码未增加管理员鉴权；生产部署建议限制为 admin。|
|---|



## 4\.5 地图数据

面向前端地图渲染，输出站点标记、路段连线和线路折线。

### 4\.5\.1 GET /api/v1/map/lines

|**项目**|**内容**|
|---|---|
|**接口名称**|查询地图线路折线|
|**模块**|地图数据|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getMapLines\(\)|
|**数据来源/实现**|由线路、站点、线路站点关系组合生成。|



请求参数：无。

**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|MapLineResponse|字段明细见“核心数据模型”。|



### 4\.5\.2 GET /api/v1/map/road\-segments

|**项目**|**内容**|
|---|---|
|**接口名称**|查询地图路段连线|
|**模块**|地图数据|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getRoadSegments\(\)|
|**数据来源/实现**|由线路、站点、线路站点关系组合生成。|



请求参数：无。

**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|RoadSegmentResponse|字段明细见“核心数据模型”。|



### 4\.5\.3 GET /api/v1/map/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|查询地图站点|
|**模块**|地图数据|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getMapStations\(params\)|
|**数据来源/实现**|由线路、站点、线路站点关系组合生成。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int（可空）|否|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|MapStationResponse|字段明细见“核心数据模型”。|



## 4\.6 位置搜索

复用站点数据，提供搜索、附近站点、地图站点和详情。

### 4\.6\.1 GET /api/v1/locations/map/stations

|**项目**|**内容**|
|---|---|
|**接口名称**|查询地图所需全部站点|
|**模块**|位置搜索|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLocationMapStations\(\)|
|**数据来源/实现**|复用站点查询与距离计算。|



请求参数：无。

**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|\{   stations: BusStationDTO\[\], total: int \}|字段明细见“核心数据模型”。|



### 4\.6\.2 GET /api/v1/locations/nearby

|**项目**|**内容**|
|---|---|
|**接口名称**|按坐标查询附近站点|
|**模块**|位置搜索|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getNearbyLocations\(params\)|
|**数据来源/实现**|复用站点查询与距离计算。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|latitude|Query|float|是|纬度，范围   \-90 至 90。 \>= \-90；\<= 90。|
|longitude|Query|float|是|经度，范围   \-180 至 180。 \>= \-180；\<= 180。|
|radius\_km|Query|float|否|搜索半径，单位 km。 默认 1\.0；\>=   0\.1；\<= 10\.0。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|NearbyStationResponse|字段明细见“核心数据模型”。|



### 4\.6\.3 GET /api/v1/locations/search

|**项目**|**内容**|
|---|---|
|**接口名称**|搜索位置/站点|
|**模块**|位置搜索|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|searchLocations\(params\)|
|**数据来源/实现**|复用站点查询与距离计算。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|keyword|Query|string（可空）|否|站点名称搜索关键字。|
|page|Query|int|否|页码，从 1 开始。 默认 1；\>= 1。|
|limit|Query|int|否|每页数量，通常默认 20，最大 100。 默认   20；\>= 1；\<= 100。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|StationListResponse|字段明细见“核心数据模型”。|



### 4\.6\.4 GET /api/v1/locations/\{location\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询位置/站点详情|
|**模块**|位置搜索|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLocationDetail\(locationId\)|
|**数据来源/实现**|复用站点查询与距离计算。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|location\_id|Path|int|是|位置编号；当前实现等同站点编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|BusStationDTO|字段明细见“核心数据模型”。|



## 4\.7 历史与预测查询

查询历史客流以及已写入的 ETA、车辆客载和客流预测记录。

### 4\.7\.1 GET /api/v1/history/eta/line/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询线路 ETA 预测记录|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getEtaPredictionsByLine\(lineId,   params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|
|target\_station\_id|Query|int（可空）|否|目标到站/上车站编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|EtaPredictionDTO\[\]|字段明细见“核心数据模型”。|



### 4\.7\.2 GET /api/v1/history/eta/\{vehicle\_id\}/\{target\_station\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询车辆到目标站的最新 ETA|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getEtaPredictionForVehicle\(vehicleId,   targetStationId, params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Path|int|是|车辆编号。|
|target\_station\_id|Path|int|是|目标到站/上车站编号。|
|line\_id|Query|int（可空）|否|线路编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|EtaPredictionDTO|字段明细见“核心数据模型”。|



### 4\.7\.3 GET /api/v1/history/load/line/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询线路客载预测记录|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLoadPredictionsByLine\(lineId,   params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|
|station\_id|Query|int（可空）|否|站点编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LoadPredictionDTO\[\]|字段明细见“核心数据模型”。|



### 4\.7\.4 GET /api/v1/history/load/\{line\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|查询最新客载预测|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getLoadPrediction\(lineId,   params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号。|
|station\_id|Query|int（可空）|否|站点编号。|
|vehicle\_id|Query|int（可空）|否|车辆编号。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 404 / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LoadPredictionDTO|字段明细见“核心数据模型”。|



### 4\.7\.5 GET /api/v1/history/passenger\-flow

|**项目**|**内容**|
|---|---|
|**接口名称**|查询历史客流趋势|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getPassengerFlowTrend\(params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int（可空）|否|线路编号。|
|station\_id|Query|int（可空）|否|站点编号。|
|start\_date|Query|string（可空）|否|开始日期时间，ISO 8601 字符串。|
|end\_date|Query|string（可空）|否|结束日期时间，ISO 8601 字符串。|
|granularity|Query|string|否|聚合粒度：hour   / day / week。 默认 "hour"；格式 ^\(hour\|day\|week\)$。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|PassengerFlowResponse|字段明细见“核心数据模型”。|



### 4\.7\.6 GET /api/v1/history/passenger\-flow/prediction

|**项目**|**内容**|
|---|---|
|**接口名称**|查询客流预测记录|
|**模块**|历史与预测查询|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getPassengerFlowPrediction\(params\)|
|**数据来源/实现**|历史客流、ETA、客载预测记录表。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|target\_type|Query|string（可空）|否|目标类型，例如   line、station。|
|target\_id|Query|string（可空）|否|收藏目标编号，必须为正整数。|
|start\_time|Query|string（可空）|否|查询起始时间，ISO 8601 字符串。|
|end\_time|Query|string（可空）|否|查询结束时间，ISO 8601 字符串。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|PassengerFlowPredictionDTO\[\]|字段明细见“核心数据模型”。|

## 4\.8 ETA 预测

计算指定车辆到目标站点的预计到站时间。

### 4\.8\.1 GET /api/v1/eta

|**项目**|**内容**|
|---|---|
|**接口名称**|计算车辆预计到站时间|
|**模块**|ETA   预测|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|getEta\(params\)|
|**数据来源/实现**|实时网关/仿真状态 \+ 规则或可选模型。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Query|int|是|车辆编号。   \> 0。|
|target\_station\_id|Query|int|是|目标到站/上车站编号。 \> 0。|
|line\_id|Query|int（可空）|否|线路编号。|
|query\_time|Query|datetime（可空）|否|ETA 查询时间；省略时使用当前时间。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|EtaResult|字段明细见“核心数据模型”。|



## 4\.9 车辆客载预测

根据线路、站点、车辆和时段等信息预测车辆客载。

### 4\.9\.1 POST /api/v1/passenger\-load\-prediction

|**项目**|**内容**|
|---|---|
|**接口名称**|预测车辆客载状态|
|**模块**|车辆客载预测|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|predictPassengerLoad\(data\)|
|**数据来源/实现**|实时网关/仿真状态 \+ 规则或可选模型。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Body|int|是|线路编号。   \> 0。|
|station\_id|Body|int|是|站点编号。   \> 0。|
|vehicle\_id|Body|int（可空）|否|车辆编号。|
|target\_time|Body|datetime（可空）|否|客载预测目标时间；省略时使用当前时间。|
|current\_onboard\_count|Body|int（可空）|否|预测输入中的当前车上人数。|
|capacity|Body|int（可空）|否|车辆核定容量。|
|weather|Body|string（可空）|否|天气特征，最长 32 个字符。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|PassengerLoadPredictionResult|字段明细见“核心数据模型”。|



|**说明：**该接口预测车辆 Passenger Load，不是站点 Passenger Flow。|
|---|



## 4\.10 步行、体验评价与路线推荐

覆盖步行估算、体验评分和完整路线推荐。

### 4\.10\.1 POST /api/v1/recommend\-routes

|**项目**|**内容**|
|---|---|
|**接口名称**|生成公交出行推荐方案|
|**模块**|步行、体验评价与路线推荐|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|recommendRoutes\(data\)|
|**数据来源/实现**|步行估算、体验评分与路线候选组合。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|start\_station\_id|Body|int（可空）|否|起点站编号。|
|end\_station\_id|Body|int（可空）|否|终点站编号。|
|origin\_longitude|Body|float（可空）|否|出发位置经度。|
|origin\_latitude|Body|float（可空）|否|出发位置纬度。|
|destination\_longitude|Body|float（可空）|否|目的地经度。|
|destination\_latitude|Body|float（可空）|否|目的地纬度。|
|depart\_time|Body|datetime（可空）|否|出发时间；省略时使用当前时间。|
|preference|Body|Preference|否|偏好：balanced   / low\_load / less\_walking / less\_transfer / fastest。 默认 "balanced"。|
|allow\_transfer|Body|bool|否|是否允许换乘，默认 true。 默认 true。|
|max\_transfer\_count|Body|int|否|最大换乘次数，默认 2，范围 0\-5。 默认   2；\>= 0；\<= 5。|
|max\_walk\_minutes|Body|float（可空）|否|可接受的最大步行时间，单位分钟。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|RecommendRoutesResult|字段明细见“核心数据模型”。|



|**说明：**必须提供起终点站编号，或完整的起点/终点坐标；两套输入方式至少满足一套。|
|---|



### 4\.10\.2 POST /api/v1/travel\-experience/evaluate

|**项目**|**内容**|
|---|---|
|**接口名称**|计算出行体验评分|
|**模块**|步行、体验评价与路线推荐|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|evaluateTravelExperience\(data\)|
|**数据来源/实现**|步行估算、体验评分与路线候选组合。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|predicted\_load\_rate|Body|float（可空）|否|预计客载率；当前模型允许 0\-2。|
|predicted\_load\_level|Body|LoadLevel（可空）|否|客载等级：seats\_available   / standing\_available / limited\_standing。|
|transfer\_count|Body|int|是|换乘次数，最小   0。 \>= 0。|
|walk\_time\_minutes|Body|float|是|步行时间，单位分钟。 \>= 0。|
|weights|Body|ExperienceWeights（可空）|否|体验评分权重对象：w\_load、w\_walk、w\_transfer，三者之和必须为   1。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|TravelExperienceResult|字段明细见“核心数据模型”。|



### 4\.10\.3 POST /api/v1/walking\-time\-estimation

|**项目**|**内容**|
|---|---|
|**接口名称**|估算前往上车站的步行时间|
|**模块**|步行、体验评价与路线推荐|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|estimateWalkingTime\(data\)|
|**数据来源/实现**|步行估算、体验评分与路线候选组合。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|origin\_longitude|Body|float|是|出发位置经度。   \>= \-180；\<= 180。|
|origin\_latitude|Body|float|是|出发位置纬度。   \>= \-90；\<= 90。|
|target\_station\_id|Body|int|是|目标到站/上车站编号。 \> 0。|
|walking\_speed\_mps|Body|float|否|步行速度，默认 1\.2 m/s，范围 0\.6\-2\.0。   默认 1\.2；\>= 0\.6；\<= 2\.0。|
|route\_mode|Body|WalkingRouteMode|否|步行路径模式：straight\_line   或 map\_api。 默认 "straight\_line"。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|WalkingTimeResult|字段明细见“核心数据模型”。|



## 4\.11 AI 出行助手

提供问答、建议与路线解释，支持外部大模型与本地回退。

### 4\.11\.1 POST /api/v1/ai/travel

|**项目**|**内容**|
|---|---|
|**接口名称**|AI 出行问答、建议与路线解释|
|**模块**|AI   出行助手|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|askAiTravel\(data\)|
|**数据来源/实现**|DeepSeek   可选；不可用时使用本地结构化回退。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|mode|Body|AiMode|是|AI   模式：qa / suggest / explain。|
|question|Body|string（可空）|否|用户问题；qa 模式必填。|
|route\_id|Body|string（可空）|否|待解释的路线编号；explain   模式可使用。|
|start\_station\_id|Body|int（可空）|否|起点站编号。|
|end\_station\_id|Body|int（可空）|否|终点站编号。|
|preference|Body|Preference|否|偏好：balanced   / low\_load / less\_walking / less\_transfer / fastest。 默认 "balanced"。|
|context|Body|object（可空）|否|AI 上下文对象，可包含页面状态、路线或其他业务数据。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|AiTravelResult|字段明细见“核心数据模型”。|



|**说明：**不同 mode 的必填条件不同：qa 需要 question；suggest 需要站点对或 context；explain 需要   route\_id 或 context。|
|---|



## 4\.12 仿真与预测更新

供联调/仿真程序更新车辆状态、预测结果和 LTA 到站数据。

### 4\.12\.1 POST /api/v1/simulation/lta\-bus\-arrival/refresh

|**项目**|**内容**|
|---|---|
|**接口名称**|刷新   LTA 公交到站数据|
|**模块**|仿真与预测更新|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|refreshLtaBusArrival\(data\)|
|**数据来源/实现**|仿真存储、预测结果缓存及 LTA 刷新。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|bus\_stop\_code|Body|string|是|LTA 公交站编码。 格式 ^\\d\{5\}$。|
|service\_no|Body|string|是|LTA 公交服务号/线路号。 最短 1；最长 12。|
|vehicle\_id|Body|int|是|车辆编号。   \> 0。|
|line\_id|Body|int|是|线路编号。   \> 0。|
|station\_id|Body|int|是|站点编号。   \> 0。|
|capacity|Body|int|否|车辆核定容量。 默认 60；\> 0；\<= 300。|
|expires\_in\_seconds|Body|int|否|缓存/结果有效期，单位秒。 默认 60；\>=   20；\<= 600。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|LtaBusArrivalRefreshResult|字段明细见“核心数据模型”。|



|**说明：**用于仿真、数据刷新和模型结果写入，不等同于普通查询接口。|
|---|



### 4\.12\.2 POST /api/v1/simulation/prediction\-results

|**项目**|**内容**|
|---|---|
|**接口名称**|写入/刷新预测结果|
|**模块**|仿真与预测更新|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updatePredictionResult\(data\)|
|**数据来源/实现**|仿真存储、预测结果缓存及 LTA 刷新。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|prediction\_type|Body|PredictionType|是|预测类型：eta   / passenger\_load / passenger\_flow。|
|vehicle\_id|Body|int（可空）|否|车辆编号。|
|line\_id|Body|int（可空）|否|线路编号。|
|station\_id|Body|int（可空）|否|站点编号。|
|target\_station\_id|Body|int（可空）|否|目标到站/上车站编号。|
|predicted\_eta\_minutes|Body|float（可空）|否|预计到站时间，单位分钟。|
|arrival\_time|Body|datetime（可空）|否|预计到站时间点。|
|predicted\_load\_rate|Body|float（可空）|否|预计客载率；当前模型允许 0\-2。|
|predicted\_load\_level|Body|LoadLevel（可空）|否|客载等级：seats\_available   / standing\_available / limited\_standing。|
|predicted\_onboard\_count|Body|int（可空）|否|预计车上人数。|
|capacity|Body|int（可空）|否|车辆核定容量。|
|load\_score|Body|float（可空）|否|客载体验得分，通常范围 0\-100。|
|confidence|Body|float|否|预测置信度，通常范围 0\-1。 默认 0\.9；\>=   0；\<= 1。|
|prediction\_time|Body|datetime（可空）|否|预测结果对应的业务时间。|
|model\_version|Body|string|否|模型或规则版本。   默认 "manual\_update\_v1"；最短 1；最长 80。|
|source|Body|string|否|数据来源标识。   默认 "simulation"；最短 1；最长 40。|
|expires\_in\_seconds|Body|int|否|缓存/结果有效期，单位秒。 默认 300；\>=   20；\<= 86400。|
|metadata|Body|object|否|附加元数据对象。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|PredictionResultUpdateResult|字段明细见“核心数据模型”。|



|**说明：**用于仿真、数据刷新和模型结果写入，不等同于普通查询接口。|
|---|



### 4\.12\.3 PATCH /api/v1/simulation/vehicle\-status/\{vehicle\_id\}

|**项目**|**内容**|
|---|---|
|**接口名称**|更新仿真车辆状态|
|**模块**|仿真与预测更新|
|**当前鉴权**|无需鉴权（按当前代码）|
|**前端方法**|updateVehicleStatus\(vehicleId,   data\)|
|**数据来源/实现**|仿真存储、预测结果缓存及 LTA 刷新。|



**请求参数**

|**字段**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Path|int|是|车辆编号。   \> 0。|
|longitude|Body|float（可空）|否|经度，范围   \-180 至 180。|
|latitude|Body|float（可空）|否|纬度，范围   \-90 至 90。|
|current\_station\_id|Body|int（可空）|否|车辆当前站点编号。|
|next\_station\_id|Body|int（可空）|否|车辆下一站编号。|
|speed\_kph|Body|float（可空）|否|车辆速度，单位 km/h（仿真接口字段）。|
|onboard\_count|Body|int（可空）|否|当前车上人数。|
|capacity|Body|int（可空）|否|车辆核定容量。|
|status|Body|VehicleRunStatus（可空）|否|运行/资源状态；具体枚举随模块而定。|



**响应结构**

|**响应项**|**类型/结构**|**说明**|
|---|---|---|
|**HTTP 状态**|200   / 422|OpenAPI 中声明的响应状态；业务成功 code=0。|
|**统一外壳**|ApiResponse|code、message、data、trace\_id、timestamp。|
|**data**|VehicleStatusUpdateResult|字段明细见“核心数据模型”。|



|**说明：**用于仿真、数据刷新和模型结果写入，不等同于普通查询接口。|
|---|



# 五、兼容别名接口

以下 5 个只读接口由后端保留，用于兼容早期 /bus\-lines、/bus\-stations 路径。新前端代码调用 /lines、/stations 主路径。

|**序号**|**方法**|**兼容路径**|**对应主接口**|**响应 data**|
|---|---|---|---|---|
|1|GET|/api/v1/bus\-lines|GET   /api/v1/lines|LineListResponse（同   /lines）|
|2|GET|/api/v1/bus\-lines/\{line\_id\}|GET   /api/v1/lines/\{line\_id\}|BusLineWithStationsDTO（同   /lines/\{line\_id\}）|
|3|GET|/api/v1/bus\-lines/\{line\_id\}/stations|GET   /api/v1/lines/\{line\_id\}/stations|\{   stations: LineStationDTO\[\] \}（同主路径）|
|4|GET|/api/v1/bus\-stations|GET   /api/v1/stations|StationListResponse（同   /stations）|
|5|GET|/api/v1/bus\-stations/\{station\_id\}|GET   /api/v1/stations/\{station\_id\}|BusStationDTO（同   /stations/\{station\_id\}）|



# 六、核心数据模型

所有业务响应均放在统一外壳的 data 字段内。以下为各接口实际使用的核心 DTO/Result 字段。

### UserDTO

用户基础信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|user\_id|用户编号|int|是|用户编号。|
|username|username|string|是|登录账号，4\-32 个字符，系统内唯一。|
|nickname|nickname|string|是|用户昵称，最长 32 个字符。|
|role|role|string|是|用户角色：passenger   或 admin；默认 passenger。|
|created\_at|创建时间|datetime|是|创建时间。|



### UserMeResponse

当前用户及统计信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|user|用户信息|UserDTO|是|用户信息。|
|favorite\_count|收藏数量|int|否|收藏数量。   默认 0。|
|history\_count|历史数量|int|否|历史数量。   默认 0。|



### LoginResponse

登录令牌与用户信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|access\_token|访问令牌|string|是|访问令牌。|
|token\_type|令牌类型|string|否|令牌类型。   默认 "Bearer"。|
|expires\_in|有效期秒数|int|是|有效期秒数。|
|user|用户信息|UserDTO|是|用户信息。|



### QueryHistoryDTO

用户查询历史记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|history\_id|历史记录编号|int|是|历史记录编号。|
|user\_id|用户编号|int|是|用户编号。|
|query\_type|查询类型|string|是|查询类型。|
|query\_params|查询参数|string|是|查询参数。|
|result\_summary|结果摘要|string|是|结果摘要。|
|created\_at|创建时间|datetime|是|创建时间。|



### QueryHistoryResponse

用户查询历史列表。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|histories|历史记录列表|QueryHistoryDTO\[\]|是|历史记录列表。|
|total|总数|int|是|总数。|



### UserFavoriteDTO

用户收藏记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|favorite\_id|收藏编号|int|是|收藏记录编号。|
|user\_id|用户编号|int|是|用户编号。|
|favorite\_type|favorite\_type|string|是|收藏对象类型，例如   line、route。|
|target\_id|目标编号|int|是|收藏目标编号，必须为正整数。|
|target\_name|target\_name|string|是|收藏目标显示名称。|
|created\_at|创建时间|datetime|是|创建时间。|



### UserFavoriteResponse

用户收藏列表。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|favorites|收藏列表|UserFavoriteDTO\[\]|是|收藏列表。|
|total|总数|int|是|总数。|



### BusLineDTO

线路基础信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|line\_id|线路编号|int|是|线路编号。|
|line\_name|线路名称|string|是|线路名称；查询时用于模糊筛选。|
|line\_code|线路编码|string|是|线路唯一编码，最长 20 个字符。|
|start\_station|起点站|string|是|起点站编码或名称。|
|end\_station|终点站|string|是|终点站编码或名称。|
|total\_stations|站点总数|int|是|线路站点总数。|
|distance\_km|距离\(km\)|float|是|线路总距离，单位 km。|
|first\_departure\_time|首班时间|string（可空）|是|首班时间，当前代码使用字符串。|
|last\_departure\_time|末班时间|string（可空）|是|末班时间，当前代码使用字符串。|
|interval\_minutes|班次间隔\(分钟\)|int|是|发车间隔，单位分钟。|
|status|状态|string|是|运行/资源状态；具体枚举随模块而定。|
|created\_at|创建时间|datetime|是|创建时间。|



### BusLineWithStationsDTO

包含站点顺序的线路详情。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|line\_id|线路编号|int|是|线路编号。|
|line\_name|线路名称|string|是|线路名称；查询时用于模糊筛选。|
|line\_code|线路编码|string|是|线路唯一编码，最长 20 个字符。|
|start\_station|起点站|string|是|起点站编码或名称。|
|end\_station|终点站|string|是|终点站编码或名称。|
|total\_stations|站点总数|int|是|线路站点总数。|
|distance\_km|距离\(km\)|float|是|线路总距离，单位 km。|
|first\_departure\_time|首班时间|string（可空）|是|首班时间，当前代码使用字符串。|
|last\_departure\_time|末班时间|string（可空）|是|末班时间，当前代码使用字符串。|
|interval\_minutes|班次间隔\(分钟\)|int|是|发车间隔，单位分钟。|
|status|状态|string|是|运行/资源状态；具体枚举随模块而定。|
|created\_at|创建时间|datetime|是|创建时间。|
|stations|站点列表|LineStationDTO\[\]|否|站点列表。   默认 \[\]。|



### LineStationDTO

线路\-站点关系及站点详情。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|id|关系编号|string|是|关系编号。|
|line\_id|线路编号|int|是|线路编号。|
|station\_id|站点编号|int|是|站点编号。|
|order\_index|顺序号|int|是|站点在线路中的顺序号。|
|direction|方向|string|是|线路方向：forward   或 backward。|
|station|站点对象|BusStationDTO|是|站点对象。|



### LineListResponse

线路列表结果。

|**说明：**线路分页结果；当前响应字段为 lines、total，分页参数由请求中的 page/limit 表示。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|lines|线路列表|BusLineDTO\[\]|是|线路列表。|
|total|总数|int|是|总数。|



### BusStationDTO

站点基础信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|station\_id|站点编号|int|是|站点编号。|
|station\_name|站点名称|string|是|站点名称；查询时用于模糊筛选。|
|station\_code|站点编码|string|是|站点唯一编码，最长 20 个字符。|
|latitude|纬度|float|是|纬度，范围   \-90 至 90。|
|longitude|经度|float|是|经度，范围   \-180 至 180。|
|address|地址|string（可空）|是|站点地址。|
|zone|区域|string（可空）|是|站点所属区域。|
|created\_at|创建时间|datetime|是|创建时间。|



### StationListResponse

站点列表结果。

|**说明：**站点分页结果；当前响应字段为 stations、total。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|stations|站点列表|BusStationDTO\[\]|是|站点列表。|
|total|总数|int|是|总数。|



### NearbyStationDTO

附近站点及距离信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|station\_id|站点编号|int|是|站点编号。|
|station\_name|站点名称|string|是|站点名称；查询时用于模糊筛选。|
|station\_code|站点编码|string|是|站点唯一编码，最长 20 个字符。|
|latitude|纬度|float|是|纬度，范围   \-90 至 90。|
|longitude|经度|float|是|经度，范围   \-180 至 180。|
|address|地址|string（可空）|是|站点地址。|
|zone|区域|string（可空）|是|站点所属区域。|
|created\_at|创建时间|datetime|是|创建时间。|
|distance\_km|距离\(km\)|float|是|线路总距离，单位 km。|



### NearbyStationResponse

附近站点结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|stations|站点列表|NearbyStationDTO\[\]|是|站点列表。|
|total|总数|int|是|总数。|



### StationLinesResponse

站点及其经过线路。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|station\_id|站点编号|int|是|站点编号。|
|station\_name|站点名称|string|是|站点名称；查询时用于模糊筛选。|
|lines|线路列表|BusLineDTO\[\]|是|线路列表。|
|total\_lines|total\_lines|int|是|total\_lines   字段。|



### BusVehicleDTO

车辆位置、运行与客载信息。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|vehicle\_id|车辆编号|int|是|车辆编号。|
|vehicle\_code|车辆编码|string|是|车辆唯一编码，最长 20 个字符。|
|line\_id|线路编号|int|是|线路编号。|
|line\_name|线路名称|string（可空）|否|线路名称；查询时用于模糊筛选。|
|current\_latitude|当前纬度|float|是|车辆当前纬度。|
|current\_longitude|当前经度|float|是|车辆当前经度。|
|latitude|纬度|float|否|纬度，范围 \-90 至 90。 默认 0\.0。|
|longitude|经度|float|否|经度，范围 \-180 至 180。 默认 0\.0。|
|current\_station\_id|当前站编号|int（可空）|否|车辆当前站点编号。|
|current\_station\_name|当前站名称|string（可空）|否|当前站名称。|
|next\_station\_id|下一站编号|int（可空）|否|车辆下一站编号。|
|next\_station\_name|下一站名称|string（可空）|否|下一站名称。|
|progress|路段进度|float（可空）|否|车辆在当前路段的进度。 默认 0\.0。|
|status|状态|string|是|运行/资源状态；具体枚举随模块而定。|
|speed\_kmh|速度\(km/h\)|float|是|车辆速度，单位 km/h（车辆 CRUD 字段）。|
|speed|速度|float|否|速度。   默认 0\.0。|
|direction\_deg|方向角|float|是|行驶方向角，单位度。|
|onboard\_count|车上人数|int|是|当前车上人数。|
|capacity|容量|int|是|车辆核定容量。|
|load\_rate|客载率|float|是|客载率。|
|last\_updated\_at|最后更新时间|datetime|是|最后更新时间。|
|update\_time|更新时间|string|否|更新时间。   默认 ""。|
|created\_at|创建时间|datetime|是|创建时间。|

### VehicleListResponse

车辆列表结果。

|**说明：**车辆分页结果；当前响应字段为 vehicles、total。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|vehicles|车辆列表|BusVehicleDTO\[\]|是|车辆列表。|
|total|总数|int|是|总数。|



### MapStationDTO

地图站点标记数据。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|station\_id|站点编号|int|是|站点编号。|
|station\_name|站点名称|string|是|站点名称；查询时用于模糊筛选。|
|station\_code|站点编码|string|是|站点唯一编码，最长 20 个字符。|
|latitude|纬度|float|是|纬度，范围   \-90 至 90。|
|longitude|经度|float|是|经度，范围   \-180 至 180。|
|address|地址|string（可空）|否|站点地址。|
|zone|区域|string（可空）|否|站点所属区域。|
|line\_ids|线路编号列表|int\[\]|否|线路编号列表。 默认 \[\]。|
|line\_names|线路名称列表|string\[\]|否|线路名称列表。 默认 \[\]。|



### MapStationResponse

地图站点集合。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|stations|站点列表|MapStationDTO\[\]|是|站点列表。|
|total|总数|int|是|总数。|



### RoadSegmentDTO

站点间地图路段。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|segment\_id|路段编号|int|是|路段编号。|
|line\_id|线路编号|int|是|线路编号。|
|line\_name|线路名称|string|是|线路名称；查询时用于模糊筛选。|
|start\_station\_id|起点站编号|int|是|起点站编号。|
|start\_station\_name|起点站名称|string|是|起点站名称。|
|end\_station\_id|终点站编号|int|是|终点站编号。|
|end\_station\_name|终点站名称|string|是|终点站名称。|
|path\_coordinates|路径坐标|float\[\]\[\]|否|路径坐标。   默认 \[\]。|
|distance\_km|距离\(km\)|float|是|线路总距离，单位 km。|
|passenger\_flow|客流量|int（可空）|否|客流量。   默认 0。|



### RoadSegmentResponse

地图路段集合。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|segments|路段列表|RoadSegmentDTO\[\]|是|路段列表。|
|total|总数|int|是|总数。|



### MapLineDTO

地图线路折线。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|line\_id|线路编号|int|是|线路编号。|
|line\_name|线路名称|string|是|线路名称；查询时用于模糊筛选。|
|line\_code|线路编码|string|是|线路唯一编码，最长 20 个字符。|
|start\_station|起点站|string|是|起点站编码或名称。|
|end\_station|终点站|string|是|终点站编码或名称。|
|color|线路颜色|string|否|线路颜色。 默认 "\#3B82F6"。|
|path\_coordinates|路径坐标|float\[\]\[\]|否|路径坐标。   默认 \[\]。|



### MapLineResponse

地图线路集合。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|lines|线路列表|MapLineDTO\[\]|是|线路列表。|
|total|总数|int|是|总数。|



### PassengerFlowTrendDTO

历史客流时间点记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|flow\_record\_id|客流记录编号|int|是|客流记录编号。|
|target\_type|目标类型|string|是|目标类型，例如   line、station。|
|target\_id|目标编号|int|是|收藏目标编号，必须为正整数。|
|bus\_stop\_code|站点编码|string（可空）|是|LTA   公交站编码。|
|record\_time|记录时间|datetime（可空）|是|记录时间。|
|day\_type|日期类型|string（可空）|是|日期类型。|
|tap\_in\_volume|上车量|int|是|上车量。|
|tap\_out\_volume|下车量|int|是|下车量。|
|total\_flow|总客流|int|是|总客流。|
|flow\_level|客流等级|string（可空）|是|客流等级。|
|data\_source|数据来源|string（可空）|是|数据来源。|



### PassengerFlowSummary

客流汇总指标。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|total\_tap\_in|总上车量|int|是|总上车量。|
|total\_tap\_out|总下车量|int|是|总下车量。|
|total\_flow|总客流|int|是|总客流。|
|peak\_hour|峰值小时|int（可空）|是|峰值小时。|
|peak\_flow|峰值客流|int（可空）|是|峰值客流。|
|dominant\_flow\_level|主要客流等级|string（可空）|是|主要客流等级。|



### PassengerFlowResponse

客流趋势与汇总。

|**说明：**历史客流趋势及汇总；Passenger Flow 指站点/线路上下车流量。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|items|结果列表|PassengerFlowTrendDTO\[\]|是|结果列表。|
|summary|汇总|PassengerFlowSummary|是|汇总。|



### PassengerFlowPredictionDTO

客流预测记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|prediction\_id|预测编号|int|是|预测编号。|
|target\_type|目标类型|string|是|目标类型，例如   line、station。|
|target\_id|目标编号|string|是|收藏目标编号，必须为正整数。|
|prediction\_time|预测生成时间|datetime|是|预测结果对应的业务时间。|
|predict\_time|预测目标时间|datetime|是|预测目标时间。|
|predicted\_flow|预测客流|int|是|预测客流。|
|crowd\_level|拥挤等级|string|是|拥挤等级。|
|confidence|置信度|float（可空）|是|预测置信度，通常范围 0\-1。|
|model\_version|模型版本|string（可空）|是|模型或规则版本。|



### EtaPredictionDTO

持久化的 ETA 预测记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|eta\_prediction\_id|ETA记录编号|int|是|ETA记录编号。|
|vehicle\_id|车辆编号|int|是|车辆编号。|
|line\_id|线路编号|int|是|线路编号。|
|target\_station\_id|目标站编号|int|是|目标到站/上车站编号。|
|prediction\_time|预测生成时间|datetime（可空）|是|预测结果对应的业务时间。|
|predicted\_eta\_minutes|预计到站分钟|float|是|预计到站时间，单位分钟。|
|arrival\_time|预计到站时间|datetime（可空）|是|预计到站时间点。|
|vehicle\_to\_stop\_distance\_m|车辆到站距离\(m\)|float（可空）|是|车辆到站距离\(m\)。|
|speed\_kph|速度\(km/h\)|float（可空）|是|车辆速度，单位 km/h（仿真接口字段）。|
|confidence|置信度|float（可空）|是|预测置信度，通常范围 0\-1。|
|model\_version|模型版本|string（可空）|是|模型或规则版本。|
|created\_at|创建时间|datetime|是|创建时间。|

### LoadPredictionDTO

持久化的客载预测记录。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|load\_prediction\_id|客载记录编号|int|是|客载记录编号。|
|vehicle\_id|车辆编号|int|是|车辆编号。|
|line\_id|线路编号|int|是|线路编号。|
|station\_id|站点编号|int（可空）|是|站点编号。|
|prediction\_time|预测生成时间|datetime（可空）|是|预测结果对应的业务时间。|
|predicted\_load\_level|预计客载等级|string|是|客载等级：seats\_available   / standing\_available / limited\_standing。|
|load\_score|客载体验分|float（可空）|是|客载体验得分，通常范围 0\-100。|
|predicted\_load\_rate|预计客载率|float（可空）|是|预计客载率；当前模型允许 0\-2。|
|onboard\_count|车上人数|int（可空）|是|当前车上人数。|
|capacity|容量|int（可空）|是|车辆核定容量。|
|confidence|置信度|float（可空）|是|预测置信度，通常范围 0\-1。|
|model\_version|模型版本|string（可空）|是|模型或规则版本。|
|created\_at|创建时间|datetime|是|创建时间。|



### GeoPoint

经纬度坐标。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|longitude|经度|float|是|经度，范围   \-180 至 180。 \>= \-180；\<= 180。|
|latitude|纬度|float|是|纬度，范围   \-90 至 90。 \>= \-90；\<= 90。|



### StationSummary

推荐与智能模块使用的站点摘要。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|station\_id|站点编号|int|是|站点编号。   \> 0。|
|station\_name|站点名称|string|是|站点名称；查询时用于模糊筛选。 最短 1；最长 100。|
|longitude|经度|float（可空）|否|经度，范围   \-180 至 180。|
|latitude|纬度|float（可空）|否|纬度，范围   \-90 至 90。|



### RouteSegment

推荐路线中的单段行程。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|segment\_order|segment\_order|int|是|segment\_order   字段。 \>= 1。|
|line\_id|线路编号|int|是|线路编号。   \> 0。|
|line\_name|线路名称|string|是|线路名称；查询时用于模糊筛选。 最短 1；最长 100。|
|boarding\_station\_id|boarding\_station\_id|int|是|boarding\_station\_id   字段。 \> 0。|
|alighting\_station\_id|alighting\_station\_id|int|是|alighting\_station\_id   字段。 \> 0。|
|ride\_time\_minutes|乘车时间\(分钟\)|float|是|乘车时间\(分钟\)。   \>= 0。|



### ExperienceWeights

体验评分权重。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|w\_load|客载权重|float|否|客载权重。 默认 0\.5；\>= 0；\<= 1。|
|w\_walk|步行权重|float|否|步行权重。 默认 0\.3；\>= 0；\<= 1。|
|w\_transfer|换乘权重|float|否|换乘权重。 默认 0\.2；\>= 0；\<= 1。|



### EtaResult

实时 ETA 计算结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|vehicle\_id|车辆编号|int|是|车辆编号。   \> 0。|
|target\_station\_id|目标站编号|int|是|目标到站/上车站编号。 \> 0。|
|predicted\_eta\_minutes|预计到站分钟|float|是|预计到站时间，单位分钟。 \>= 0。|
|arrival\_time|预计到站时间|datetime|是|预计到站时间点。|
|factors|factors|object|是|factors   字段。|
|model\_version|模型版本|string|是|模型或规则版本。|



### PassengerLoadPredictionResult

实时车辆客载预测结果。

|**说明：**车辆内客载状态预测；Passenger Load 与站点客流 Passenger Flow 不同。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|line\_id|线路编号|int|是|线路编号。|
|station\_id|站点编号|int|是|站点编号。|
|vehicle\_id|车辆编号|int（可空）|是|车辆编号。|
|predicted\_onboard\_count|predicted\_onboard\_count|int（可空）|是|预计车上人数。|
|capacity|容量|int（可空）|是|车辆核定容量。|
|predicted\_load\_rate|预计客载率|float（可空）|否|预计客载率；当前模型允许 0\-2。|
|predicted\_load\_level|预计客载等级|LoadLevel|是|客载等级：seats\_available   / standing\_available / limited\_standing。|
|load\_score|客载体验分|float|是|客载体验得分，通常范围 0\-100。 \>= 0；\<=   100。|
|confidence|置信度|float|是|预测置信度，通常范围 0\-1。 \>= 0；\<=   1。|
|predict\_time|预测目标时间|datetime|是|预测目标时间。|
|feature\_summary|feature\_summary|object|是|feature\_summary   字段。|
|model\_version|模型版本|string|是|模型或规则版本。|



### WalkingTimeResult

步行时间估算结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|origin|起点坐标|GeoPoint|是|起点坐标。|
|target\_station|目标站点|StationSummary|是|目标站点。|
|walk\_distance\_meters|步行距离\(m\)|float|是|步行距离\(m\)。   \>= 0。|
|walk\_time\_minutes|步行时间\(分钟\)|float|是|步行时间，单位分钟。 \>= 0。|
|walking\_speed\_mps|步行速度\(m/s\)|float|是|步行速度，默认 1\.2 m/s，范围 0\.6\-2\.0。   \>= 0\.6；\<= 2\.0。|
|route\_source|路径来源|WalkingRouteMode|是|路径来源。|



### TravelExperienceResult

出行体验评分结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|load\_score|客载体验分|float|是|客载体验得分，通常范围 0\-100。 \>= 0；\<=   100。|
|walk\_score|步行体验分|float|是|步行体验分。   \>= 0；\<= 100。|
|transfer\_score|换乘体验分|float|是|换乘体验分。   \>= 0；\<= 100。|
|experience\_score|综合体验分|float|是|综合体验分。   \>= 0；\<= 100。|
|factor\_weights|实际权重|ExperienceWeights|是|实际权重。|
|factor\_values|原始指标|object|是|原始指标。|
|reason|推荐理由|string|是|推荐理由。|



### PredictedLoadSummary

推荐方案中的客载摘要。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|predicted\_load\_rate|预计客载率|float（可空）|否|预计客载率；当前模型允许 0\-2。|
|predicted\_load\_level|预计客载等级|LoadLevel|是|客载等级：seats\_available   / standing\_available / limited\_standing。|
|predicted\_onboard\_count|predicted\_onboard\_count|int（可空）|否|预计车上人数。|
|capacity|容量|int（可空）|否|车辆核定容量。|
|confidence|置信度|float（可空）|否|预测置信度，通常范围 0\-1。|
|load\_score|客载体验分|float|是|客载体验得分，通常范围 0\-100。 \>= 0；\<=   100。|



### RouteRecommendation

单条推荐路线。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|route\_id|路线编号|string|是|待解释的路线编号；explain   模式可使用。|
|line\_ids|线路编号列表|int\[\]|是|线路编号列表。|
|segments|路段列表|RouteSegment\[\]|是|路段列表。|
|boarding\_station|上车站|StationSummary|是|上车站。|
|alighting\_station|下车站|StationSummary|是|下车站。|
|predicted\_eta\_minutes|预计到站分钟|float|是|预计到站时间，单位分钟。 \>= 0。|
|predicted\_load|预计客载|PredictedLoadSummary|是|预计客载。|
|walk\_time\_minutes|步行时间\(分钟\)|float|是|步行时间，单位分钟。 \>= 0。|
|ride\_time\_minutes|乘车时间\(分钟\)|float|是|乘车时间\(分钟\)。   \>= 0。|
|total\_time\_minutes|总时间\(分钟\)|float|是|总时间\(分钟\)。   \>= 0。|
|transfer\_count|换乘次数|int|是|换乘次数，最小   0。 \>= 0。|
|experience\_score|综合体验分|float|是|综合体验分。   \>= 0；\<= 100。|
|recommend\_types|推荐标签|RecommendType\[\]|否|推荐标签。|
|reason|推荐理由|string|是|推荐理由。|



### RecommendRoutesResult

路线推荐结果集合。

|**说明：**包含多条候选方案以及不同目标下的最优 route\_id。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|items|结果列表|RouteRecommendation\[\]|是|结果列表。|
|best\_experience\_route\_id|最佳体验路线编号|string|是|最佳体验路线编号。|
|fastest\_route\_id|最快路线编号|string|是|最快路线编号。|
|least\_crowded\_route\_id|最不拥挤路线编号|string|是|最不拥挤路线编号。|
|least\_walking\_route\_id|最少步行路线编号|string|是|最少步行路线编号。|
|least\_transfer\_route\_id|最少换乘路线编号|string|是|最少换乘路线编号。|
|preference|偏好|Preference|是|偏好：balanced   / low\_load / less\_walking / less\_transfer / fastest。|
|generated\_at|生成时间|datetime|是|生成时间。|



### AiTravelResult

AI 出行助手响应。

|**说明：**fallback=true 表示未使用外部大模型或外部能力不可用，返回了本地回退结果。|
|---|



|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|answer|AI回答|string|是|AI回答。|
|mode|AI模式|AiMode|是|AI   模式：qa / suggest / explain。|
|used\_tools|使用的工具|string\[\]|是|使用的工具。|
|related\_routes|相关路线|RouteRecommendation\[\]|是|相关路线。|
|reminders|提醒|string\[\]|是|提醒。|
|fallback|是否回退|bool|是|是否回退。|



### VehicleStatusUpdateResult

仿真车辆状态更新结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|vehicle\_id|车辆编号|int|是|车辆编号。|
|line\_id|线路编号|int|是|线路编号。|
|longitude|经度|float|是|经度，范围   \-180 至 180。|
|latitude|纬度|float|是|纬度，范围   \-90 至 90。|
|current\_station\_id|当前站编号|int|是|车辆当前站点编号。|
|next\_station\_id|下一站编号|int|是|车辆下一站编号。|
|speed\_kph|速度\(km/h\)|float|是|车辆速度，单位 km/h（仿真接口字段）。|
|onboard\_count|车上人数|int|是|当前车上人数。|
|capacity|容量|int|是|车辆核定容量。|
|status|状态|VehicleRunStatus|是|运行/资源状态；具体枚举随模块而定。|
|source|来源|string|是|数据来源标识。|
|updated\_at|更新时间|datetime|是|更新时间。|



### PredictionResultUpdateResult

预测结果写入/刷新结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|prediction\_type|prediction\_type|PredictionType|是|预测类型：eta   / passenger\_load / passenger\_flow。|
|storage\_key|存储键|string|是|存储键。|
|source|来源|string|是|数据来源标识。|
|model\_version|模型版本|string|是|模型或规则版本。|
|payload|预测负载对象|object|是|预测负载对象。|
|updated\_at|更新时间|datetime|是|更新时间。|
|expires\_at|过期时间|datetime|是|过期时间。|



### LtaBusArrivalRefreshResult

LTA 到站数据刷新结果。

|**字段**|**中文含义**|**类型**|**必有**|**说明**|
|---|---|---|---|---|
|bus\_stop\_code|站点编码|string|是|LTA   公交站编码。|
|service\_no|服务号|string|是|LTA 公交服务号/线路号。|
|operator|运营商|string|是|运营商。|
|vehicle\_id|车辆编号|int|是|车辆编号。|
|line\_id|线路编号|int|是|线路编号。|
|station\_id|站点编号|int|是|站点编号。|
|predicted\_eta\_minutes|预计到站分钟|float|是|预计到站时间，单位分钟。|
|estimated\_arrival|预计到达时间|datetime|是|预计到达时间。|
|predicted\_load\_level|预计客载等级|LoadLevel|是|客载等级：seats\_available   / standing\_available / limited\_standing。|
|predicted\_load\_rate|预计客载率|float|是|预计客载率；当前模型允许 0\-2。|
|monitored|是否监控|bool|是|是否监控。|
|latitude|纬度|float（可空）|是|纬度，范围   \-90 至 90。|
|longitude|经度|float（可空）|是|经度，范围   \-180 至 180。|
|feature|车辆特征|string|是|车辆特征。|
|bus\_type|车辆类型|string|是|车辆类型。|
|source|来源|string|是|数据来源标识。|
|refreshed\_at|刷新时间|datetime|是|刷新时间。|
|expires\_at|过期时间|datetime|是|过期时间。|



# 七、错误码与联调注意事项

## 7\.1 业务错误码

|**业务码**|**HTTP**|**含义/触发场景**|
|---|---|---|
|0|200/201|成功。|
|40001|400|通用请求或业务参数错误。|
|40002|400|业务参数不合法，例如密码错误、容量或权重非法。|
|40003|400|推荐路线起点与终点相同。|
|40400|404|通用资源/推荐方案不存在。|
|40401|404|站点/位置不存在。|
|40402|404|线路站点关系不存在。|
|40403|404|车辆不存在。|
|40900|409|用户名或线路编码冲突。|
|40901|409|收藏或线路站点关系重复。|
|40902|409|站点编码冲突。|
|40903|409|车辆编码冲突。|
|42200|422|Pydantic/FastAPI   参数校验失败。|
|50301|503|ETA/车辆状态服务不可用或车辆离线。|



## 7\.2 前后端联调注意事项

- Axios 响应拦截器返回 response\.data，因此页面拿到的是统一外壳对象；业务数据通常位于 response\.data。

- 列表接口返回的集合键并不统一：lines、stations、vehicles、items、segments 等，以各接口的 data 模型为准。

- 推荐接口可用“站点 ID 对”或“完整坐标对”两种输入；不要只提供半组坐标。

- 车辆数据库接口速度字段为 speed\_kmh；智能/仿真接口使用 speed\_kph，前端映射时注意。

- 车辆 CRUD status 与仿真 status 的枚举不同；不要互相直接复用。

- 历史 passenger\-flow 是站点/线路客流；passenger\-load\-prediction 和 history/load 是车辆客载。

- 当前写接口未做 admin 鉴权，属于演示联调状态；部署前建议补权限控制。

- OpenAPI 文档可通过运行主应用后访问 /docs 或 /openapi\.json，以运行时定义为最终准绳。

# 附录：典型请求示例

## A\.1 用户登录

|POST /api/v1/users/login<br>Content\-Type: application/json<br>\{<br>    "username": "demo\_user",<br>    "password": "12345678"<br>\}|
|---|



## A\.2 路线推荐

|POST /api/v1/recommend\-routes<br>Content\-Type: application/json<br>\{<br>    "start\_station\_id": 1,<br>    "end\_station\_id": 8,<br>    "preference": "balanced",<br>    "allow\_transfer": true,<br>    "max\_transfer\_count": 2<br>\}|
|---|



## A\.3 AI 出行建议

|POST /api/v1/ai/travel<br>Content\-Type: application/json<br>\{<br>    "mode": "suggest",<br>    "start\_station\_id": 1,<br>    "end\_station\_id": 8,<br>    "preference": "low\_load"<br>\}|
|---|



## A\.4 更新仿真车辆状态

|PATCH /api/v1/simulation/vehicle\-status/1<br>Content\-Type: application/json<br>\{<br>    "longitude": 116\.397,<br>    "latitude": 39\.908,<br>    "speed\_kph": 28,<br>    "onboard\_count": 24,<br>    "capacity": 60,<br>    "status": "normal"<br>\}|
|---|



