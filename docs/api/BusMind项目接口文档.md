# BusMind项目接口文档

# 一、统一接口规范

## 1\.1 基础约定

|**规范项**|**约定内容**|
|---|---|
|Base   URL|本地开发：http://127\.0\.0\.1:8000；统一接口前缀：/api/v1|
|协议与编码|HTTP/HTTPS；UTF\-8|
|请求格式|GET   使用 Path/Query；POST/PATCH 使用 application/json|
|字段命名|请求与响应字段统一使用 snake\_case；API 路径使用小写短横线|
|时间格式|日期   YYYY\-MM\-DD；日期时间 ISO 8601，例如 2026\-07\-08T09:00:00\+08:00|
|分页规则|page   从 1 开始；page\_size 默认 10，最大 100；返回 items、total、page、page\_size|
|坐标格式|WGS84   或项目统一坐标系；经度 longitude，纬度 latitude|
|数值精度|分钟保留 1 位小数；距离以米为单位；客载率范围 0\-1，保留 2 位小数|
|幂等性|GET、PATCH、DELETE   应保持幂等；重复收藏返回 40900|



## 1\.2 统一返回格式

### 成功响应

|\{<br>  "code": 0,<br>  "message": "success",<br>  "data": \{\},<br>  "trace\_id":   "req\_202607080001",<br>  "timestamp":   "2026\-07\-08T09:00:00\+08:00"<br>\}|
|---|



### 失败响应

|\{<br>  "code": 40001,<br>  "message": "参数校验失败：station\_id 不能为空",<br>  "data": null,<br>  "trace\_id":   "req\_202607080002",<br>  "timestamp":   "2026\-07\-08T09:00:01\+08:00"<br>\}|
|---|



## 1\.3 错误码

|**错误码**|**HTTP**|**含义**|**前端处理建议**|
|---|---|---|---|
|0|200|请求成功|正常渲染   data|
|40001|400|请求参数缺失或格式错误|提示用户检查输入|
|40002|400|业务参数不合法|展示后端   message|
|40003|400|起点与终点无法解析或相同|提示重新选择站点|
|40100|401|未携带   Token|跳转登录或按匿名模式调用|
|40101|401|Token   过期或无效|清除   Token 并重新登录|
|40300|403|无权访问资源|提示无权限|
|40400|404|线路、站点、车辆或方案不存在|提示未找到|
|40900|409|重复注册、重复收藏等数据冲突|提示已存在|
|42200|422|FastAPI/Pydantic   校验失败|展示字段校验信息|
|42900|429|请求频率过高|稍后重试|
|50000|500|服务器内部异常|记录   trace\_id|
|50001|500|数据库读写异常|提示数据服务异常|
|50301|503|ETA   服务暂不可用|返回基础线路信息|
|50302|503|客载量预计服务暂不可用|使用历史均值或   unknown|
|50303|503|大模型服务暂不可用|返回结构化推荐结果|



## 1\.4 鉴权规则

|**接口类别**|**鉴权要求**|**规则**|
|---|---|---|
|注册、登录|不需要|匿名调用|
|线路、站点、车辆、ETA、客载量预计、步行时长估算|不需要|便于基础查询和演示|
|出行体验评价与推荐|可选|匿名可调用；登录后记录偏好和查询历史|
|AI   出行助手|可选|匿名只使用当前上下文；登录后可结合收藏与历史|
|个人信息、收藏、查询历史|需要|Authorization:   Bearer \<token\>|



## 1\.5 枚举与计算规则

|**字段**|**允许值**|**说明**|
|---|---|---|
|load\_level|seats\_available   / standing\_available / limited\_standing|有座位 / 可站立 / 站立空间有限|
|preference|balanced   / low\_load / less\_walking / less\_transfer / fastest|综合 / 少拥挤 / 少步行 / 少换乘 / 最快|
|recommend\_type|best\_experience   / least\_crowded / least\_walking / least\_transfer / fastest|推荐标签|
|vehicle\_status|normal   / delayed / offline|车辆运行状态；不再用 crowded 表示车辆状态|
|ai\_mode|qa   / suggest / explain|AI 问答 / 出行建议 / 路线解释|



|**综合分规则：**experience\_score = w\_load × load\_score \+ w\_walk ×   walk\_score \+ w\_transfer × transfer\_score。默认权重建议为 0\.50、0\.30、0\.20，三项权重之和必须为 1。ETA   不参与 experience\_score，但可用于 fastest 排序和结果展示。|
|---|



# 二、接口总览

|**模块**|**接口路径**|**方法**|**功能说明**|**鉴权**|**负责人**|
|---|---|---|---|---|---|
|用户|/api/v1/users/register|POST|用户注册|否|服务端A|
|用户|/api/v1/users/login|POST|用户登录|否|服务端A|
|用户|/api/v1/users/me|GET|获取当前用户信息|是|服务端A|
|用户|/api/v1/users/me|PATCH|修改当前用户信息|是|服务端A|
|用户|/api/v1/users/me/favorites|GET|查询收藏路线|是|服务端A|
|用户|/api/v1/users/me/favorites|POST|新增收藏路线|是|服务端A|
|用户|/api/v1/users/me/favorites/\{favorite\_id\}|DELETE|取消收藏路线|是|服务端A|
|用户|/api/v1/users/me/query\-history|GET|查询用户历史|是|服务端A|
|线路|/api/v1/bus\-lines|GET|查询公交线路列表|否|服务端A|
|线路|/api/v1/bus\-lines/\{line\_id\}|GET|查询线路详情|否|服务端A|
|线路|/api/v1/bus\-lines/\{line\_id\}/stations|GET|查询线路站点|否|服务端A|
|线路|/api/v1/bus\-lines/\{line\_id\}/map|GET|获取线路地图数据|否|服务端A|
|站点|/api/v1/bus\-stations|GET|查询站点列表|否|服务端A|
|站点|/api/v1/bus\-stations/\{station\_id\}|GET|查询站点详情|否|服务端A|
|站点|/api/v1/bus\-stations/nearby|GET|查询附近站点|否|服务端A|
|车辆|/api/v1/bus\-vehicles/realtime|GET|查询车辆实时状态与地图点位|否|服务端A|
|ETA|/api/v1/eta|GET|查询预计到站时间|否|服务端B|
|客载量|/api/v1/passenger\-load\-prediction|POST|客载量预计|否|服务端B/数据处理|
|步行|/api/v1/walking\-time\-estimation|POST|估算到上车站步行时长|否|服务端B|
|体验评价|/api/v1/travel\-experience/evaluate|POST|计算三项指标与综合分|可选|服务端B|
|推荐|/api/v1/recommend\-routes|POST|生成出行体验推荐方案|可选|服务端B|
|AI|/api/v1/ai/travel|POST|AI 出行问答、建议与解释|可选|服务端B|
|历史|/api/v1/history/passenger\-flow|GET|查询站点客流统计|否|数据处理/服务端B|
|历史|/api/v1/history/passenger\-load|GET|查询车辆客载量趋势|否|数据处理/服务端B|
|历史|/api/v1/history/predictions|GET|查询预测记录|否|数据处理/服务端B|



# 三、核心响应数据对象

|**对象名**|**主要字段**|**用途**|
|---|---|---|
|UserDTO|user\_id,   username, nickname, created\_at, updated\_at|用户基础信息|
|FavoriteRouteDTO|favorite\_id,   route\_name, start\_station, end\_station, line\_ids, created\_at|收藏路线|
|BusLineDTO|line\_id,   line\_name, direction, start\_station, end\_station, first\_bus\_time,   last\_bus\_time, status|线路信息|
|StationDTO|station\_id,   station\_name, longitude, latitude, served\_lines|站点信息|
|VehicleRealtimeDTO|vehicle\_id,   line\_id, longitude, latitude, current\_station\_id, next\_station\_id, progress,   speed, onboard\_count, capacity, status, update\_time|车辆实时状态和地图点位|
|EtaDTO|vehicle\_id,   target\_station\_id, predicted\_eta\_minutes, arrival\_time, factors,   model\_version|ETA   结果|
|PassengerLoadPredictionDTO|vehicle\_id,   line\_id, station\_id, predicted\_onboard\_count, capacity, predicted\_load\_rate,   predicted\_load\_level, confidence, predict\_time|客载量预计结果|
|WalkingTimeDTO|origin,   target\_station, walk\_distance\_meters, walk\_time\_minutes, walking\_speed\_mps,   route\_source|步行时长估算结果|
|TravelExperienceDTO|load\_score,   walk\_score, transfer\_score, experience\_score, factor\_weights, factor\_values|三项指标评价结果|
|RouteRecommendationDTO|route\_id,   segments, boarding\_station, alighting\_station, predicted\_eta\_minutes,   predicted\_load, walk\_time\_minutes, transfer\_count, experience\_score,   recommend\_types, reason|推荐路线|
|AiTravelResponseDTO|answer,   mode, used\_tools, related\_routes, reminders, fallback|AI   自然语言输出|



# 四、各接口请求参数与响应结构

## 4\.1 用户功能模块

### 4\.1\.1 POST /api/v1/users/register

|**项目**|**内容**|
|---|---|
|接口名称|用户注册|
|鉴权要求|无需鉴权|
|功能说明|创建用户账号，密码只保存哈希值。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|username|Body|string|是|4\-32   个字符，系统内唯一|
|password|Body|string|是|8\-64   个字符|
|nickname|Body|string|否|用户昵称，最长 32 个字符|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|user|UserDTO|新建用户信息|



### 4\.1\.2 POST /api/v1/users/login

|**项目**|**内容**|
|---|---|
|接口名称|用户登录|
|鉴权要求|无需鉴权|
|功能说明|校验账号密码并签发访问令牌。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|username|Body|string|是|用户账号|
|password|Body|string|是|用户密码|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|access\_token|string|JWT   访问令牌|
|token\_type|string|固定为   Bearer|
|expires\_in|int|有效期秒数|
|user|UserDTO|当前用户信息|



### 4\.1\.3 GET /api/v1/users/me

|**项目**|**内容**|
|---|---|
|接口名称|获取当前用户信息|
|鉴权要求|Bearer   Token|
|功能说明|返回当前登录用户的个人信息和统计数量。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|Authorization|Header|string|是|Bearer   \<token\>|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|user|UserDTO|用户信息|
|favorite\_count|int|收藏数量|
|history\_count|int|查询历史数量|



### 4\.1\.4 PATCH /api/v1/users/me

|**项目**|**内容**|
|---|---|
|接口名称|修改当前用户信息|
|鉴权要求|Bearer   Token|
|功能说明|修改昵称等允许更新的字段。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|nickname|Body|string|否|新昵称|
|old\_password|Body|string|否|修改密码时必填|
|new\_password|Body|string|否|新密码|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|user|UserDTO|更新后的用户信息|

### 4\.1\.5 GET /api/v1/users/me/favorites

|**项目**|**内容**|
|---|---|
|接口名称|查询收藏路线|
|鉴权要求|Bearer   Token|
|功能说明|分页查询当前用户收藏的线路或出行方案。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|page|Query|int|否|默认   1|
|page\_size|Query|int|否|默认   10，最大 100|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<FavoriteRouteDTO\>|收藏列表|
|total|int|总条数|
|page|int|当前页|
|page\_size|int|每页条数|



### 4\.1\.6 POST /api/v1/users/me/favorites

|**项目**|**内容**|
|---|---|
|接口名称|新增收藏路线|
|鉴权要求|Bearer   Token|
|功能说明|收藏线路或完整路线方案。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|route\_name|Body|string|否|用户自定义名称|
|start\_station\_id|Body|int|是|起点站编号|
|end\_station\_id|Body|int|是|终点站编号|
|line\_ids|Body|array\<int\>|是|线路编号列表|
|route\_snapshot|Body|object|否|保存展示所需的路线快照|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|favorite|FavoriteRouteDTO|新建收藏|



### 4\.1\.7 DELETE /api/v1/users/me/favorites/\{favorite\_id\}

|**项目**|**内容**|
|---|---|
|接口名称|取消收藏路线|
|鉴权要求|Bearer   Token|
|功能说明|删除当前用户的一条收藏。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|favorite\_id|Path|int|是|收藏编号|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|favorite\_id|int|已删除收藏编号|
|deleted|bool|是否删除成功|



### 4\.1\.8 GET /api/v1/users/me/query\-history

|**项目**|**内容**|
|---|---|
|接口名称|查询用户历史|
|鉴权要求|Bearer   Token|
|功能说明|查询线路、推荐或 AI 历史记录。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|query\_type|Query|string|否|line   / station / recommend / ai|
|page|Query|int|否|默认   1|
|page\_size|Query|int|否|默认   10|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<QueryHistoryDTO\>|历史记录|
|total|int|总条数|
|page|int|当前页|
|page\_size|int|每页条数|



## 4\.2 公交线路、站点与车辆模块

### 4\.2\.1 GET /api/v1/bus\-lines

|**项目**|**内容**|
|---|---|
|接口名称|查询公交线路列表|
|鉴权要求|无需鉴权|
|功能说明|按关键字、起点站或终点站筛选线路。完整路线推荐由 recommend\-routes 接口负责。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|keyword|Query|string|否|线路名或站点名关键字|
|start\_station\_id|Query|int|否|起点站编号|
|end\_station\_id|Query|int|否|终点站编号|
|direction|Query|int|否|运行方向|
|page|Query|int|否|默认   1|
|page\_size|Query|int|否|默认   20|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<BusLineDTO\>|线路列表|
|total|int|线路总数|
|page|int|当前页|
|page\_size|int|每页条数|



### 4\.2\.2 GET /api/v1/bus\-lines/\{line\_id\}

|**项目**|**内容**|
|---|---|
|接口名称|查询线路详情|
|鉴权要求|无需鉴权|
|功能说明|返回线路基本信息和运营信息。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|line|BusLineDTO|线路详情|
|station\_count|int|站点数量|
|vehicle\_count|int|在线车辆数量|



### 4\.2\.3 GET /api/v1/bus\-lines/\{line\_id\}/stations

|**项目**|**内容**|
|---|---|
|接口名称|查询线路站点|
|鉴权要求|无需鉴权|
|功能说明|按站点顺序返回指定线路的站点。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号|
|direction|Query|int|否|运行方向|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|line\_id|int|线路编号|
|direction|int|运行方向|
|stations|array\<LineStationDTO\>|含   station\_order、distance\_to\_next、average\_travel\_minutes|



### 4\.2\.4 GET /api/v1/bus\-lines/\{line\_id\}/map

|**项目**|**内容**|
|---|---|
|接口名称|获取线路地图数据|
|鉴权要求|无需鉴权|
|功能说明|返回线路折线、站点坐标和地图视野范围。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Path|int|是|线路编号|
|direction|Query|int|否|运行方向|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|line\_id|int|线路编号|
|polyline|array\<GeoPoint\>|线路折线坐标|
|stations|array\<MapStationDTO\>|站点坐标|
|bounds|object|地图视野边界|



### 4\.2\.5 GET /api/v1/bus\-stations

|**项目**|**内容**|
|---|---|
|接口名称|查询站点列表|
|鉴权要求|无需鉴权|
|功能说明|按名称关键字查询站点，用于站点页和起终点选择。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|keyword|Query|string|否|站点名称关键字|
|line\_id|Query|int|否|过滤经过指定线路的站点|
|page|Query|int|否|默认   1|
|page\_size|Query|int|否|默认   20|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<StationDTO\>|站点列表|
|total|int|站点总数|
|page|int|当前页|
|page\_size|int|每页条数|



### 4\.2\.6 GET /api/v1/bus\-stations/\{station\_id\}

|**项目**|**内容**|
|---|---|
|接口名称|查询站点详情|
|鉴权要求|无需鉴权|
|功能说明|返回站点坐标、经过线路和下一班车辆摘要。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|station\_id|Path|int|是|站点编号|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|station|StationDTO|站点详情|
|served\_lines|array\<BusLineSummaryDTO\>|经过线路|
|next\_vehicles|array\<VehicleArrivalSummaryDTO\>|下一班车辆摘要|



### 4\.2\.7 GET /api/v1/bus\-stations/nearby

|**项目**|**内容**|
|---|---|
|接口名称|查询附近站点|
|鉴权要求|无需鉴权|
|功能说明|根据用户坐标查找一定半径内的站点，并返回直线距离和粗略步行时长。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|longitude|Query|float|是|用户经度|
|latitude|Query|float|是|用户纬度|
|radius\_meters|Query|int|否|默认   1000|
|limit|Query|int|否|默认   10|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<NearbyStationDTO\>|附近站点，含   distance\_meters、estimated\_walk\_minutes|



### 4\.2\.8 GET /api/v1/bus\-vehicles/realtime

|**项目**|**内容**|
|---|---|
|接口名称|查询车辆实时状态|
|鉴权要求|无需鉴权|
|功能说明|返回车辆位置、运行状态、当前载客人数和容量。地图点位直接使用本接口。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int|否|线路编号|
|station\_id|Query|int|否|关注站点编号|
|vehicle\_id|Query|int|否|车辆编号|
|status|Query|string|否|normal   / delayed / offline|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<VehicleRealtimeDTO\>|车辆实时状态|
|update\_time|datetime|本批数据更新时间|



## 4\.3 ETA、客载量与步行时长模块

### 4\.3\.1 GET /api/v1/eta

|**项目**|**内容**|
|---|---|
|接口名称|查询预计到站时间|
|鉴权要求|无需鉴权|
|功能说明|计算指定车辆到达目标站点所需时间。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|vehicle\_id|Query|int|是|车辆编号|
|target\_station\_id|Query|int|是|目标站点编号|
|line\_id|Query|int|否|用于校验车辆与线路关系|
|query\_time|Query|datetime|否|默认当前时间|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|vehicle\_id|int|车辆编号|
|target\_station\_id|int|目标站点编号|
|predicted\_eta\_minutes|float|预计到站分钟数|
|arrival\_time|datetime|预计到站时间|
|factors|object|距离、时段、天气、停站等影响因素|
|model\_version|string|模型或规则版本|



### 4\.3\.2 POST /api/v1/passenger\-load\-prediction

|**项目**|**内容**|
|---|---|
|接口名称|客载量预计|
|鉴权要求|无需鉴权|
|功能说明|预计车辆在目标站点或目标时间的客载量。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Body|int|是|线路编号|
|station\_id|Body|int|是|预测站点|
|vehicle\_id|Body|int|否|车辆编号；未提供时可预测线路平均车次|
|target\_time|Body|datetime|否|默认当前时间|
|current\_onboard\_count|Body|int|否|当前车上人数|
|capacity|Body|int|否|车辆容量|
|weather|Body|string|否|天气特征|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|line\_id|int|线路编号|
|station\_id|int|站点编号|
|vehicle\_id|int/null|车辆编号|
|predicted\_onboard\_count|int/null|预计车上人数；使用分类数据时可为空|
|capacity|int/null|车辆容量|
|predicted\_load\_rate|float/null|预计客载率   0\-1|
|predicted\_load\_level|string|seats\_available   / standing\_available / limited\_standing|
|confidence|float|预测置信度   0\-1|
|predict\_time|datetime|预测时间|
|feature\_summary|object|时段、站点热度、历史客流等摘要|
|model\_version|string|规则模型或机器学习模型版本|



|**实现说明：**当使用本地模拟数据时，优先返回预计人数和客载率；当使用 LTA Load 风格分类标签时，至少返回   predicted\_load\_level。接口字段保持兼容。|
|---|

### 4\.3\.3 POST /api/v1/walking\-time\-estimation

|**项目**|**内容**|
|---|---|
|接口名称|估算前往上车站步行时长|
|鉴权要求|无需鉴权|
|功能说明|根据用户位置和上车站坐标估算步行距离和步行时长。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|origin\_longitude|Body|float|是|用户经度|
|origin\_latitude|Body|float|是|用户纬度|
|target\_station\_id|Body|int|是|目标上车站|
|walking\_speed\_mps|Body|float|否|默认   1\.2 m/s，范围 0\.6\-2\.0|
|route\_mode|Body|string|否|straight\_line   / map\_api，默认 straight\_line|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|origin|GeoPoint|用户位置|
|target\_station|StationDTO|目标站点|
|walk\_distance\_meters|float|步行距离|
|walk\_time\_minutes|float|步行时长|
|walking\_speed\_mps|float|采用的步行速度|
|route\_source|string|straight\_line   / map\_api|



## 4\.4 出行体验评价与推荐模块

### 4\.4\.1 POST /api/v1/travel\-experience/evaluate

|**项目**|**内容**|
|---|---|
|接口名称|计算出行体验评价指标|
|鉴权要求|可选鉴权|
|功能说明|对一个候选方案按客载量、换乘次数和步行时长计算综合分。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|predicted\_load\_rate|Body|float|否|客载率   0\-1；与 predicted\_load\_level 至少提供一个|
|predicted\_load\_level|Body|string|否|客载等级|
|transfer\_count|Body|int|是|换乘次数，最小   0|
|walk\_time\_minutes|Body|float|是|前往上车站步行时长|
|weights|Body|object|否|w\_load、w\_walk、w\_transfer，和为   1|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|load\_score|float|客载体验得分   0\-100|
|walk\_score|float|步行体验得分   0\-100|
|transfer\_score|float|换乘体验得分   0\-100|
|experience\_score|float|出行体验综合分   0\-100|
|factor\_weights|object|实际采用的权重|
|factor\_values|object|三项原始指标值|
|reason|string|结构化推荐理由|



|**实现说明：**ETA、乘车时间和总行程时间可作为展示字段，但不参与 experience\_score。|
|---|



### 4\.4\.2 POST /api/v1/recommend\-routes

|**项目**|**内容**|
|---|---|
|接口名称|生成出行体验推荐方案|
|鉴权要求|可选鉴权|
|功能说明|生成候选公交方案，调用 ETA、客载量预计和步行时长估算，并按三项指标评价。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|start\_station\_id|Body|int|否|已选择起点站时使用|
|end\_station\_id|Body|int|否|已选择终点站时使用|
|origin\_longitude|Body|float|否|使用当前位置时提供|
|origin\_latitude|Body|float|否|使用当前位置时提供|
|destination\_longitude|Body|float|否|目的地坐标|
|destination\_latitude|Body|float|否|目的地坐标|
|depart\_time|Body|datetime|否|默认当前时间|
|preference|Body|string|否|balanced   / low\_load / less\_walking / less\_transfer / fastest|
|allow\_transfer|Body|bool|否|默认   true|
|max\_transfer\_count|Body|int|否|默认   2|
|max\_walk\_minutes|Body|float|否|可接受最大步行时长|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<RouteRecommendationDTO\>|候选方案列表|
|best\_experience\_route\_id|string|出行体验综合分最高方案|
|fastest\_route\_id|string|预计总耗时最短方案|
|least\_crowded\_route\_id|string|预计客载压力最低方案|
|least\_walking\_route\_id|string|步行时长最短方案|
|least\_transfer\_route\_id|string|换乘次数最少方案|
|preference|string|本次偏好|
|generated\_at|datetime|生成时间|



|**实现说明：**每条方案必须返回 predicted\_load、walk\_time\_minutes、transfer\_count、experience\_score   和 reason。predicted\_eta\_minutes 继续返回，但不计入体验分。|
|---|



## 4\.5 AI 出行助手模块

### 4\.5\.1 POST /api/v1/ai/travel

|**项目**|**内容**|
|---|---|
|接口名称|AI 出行问答、建议与解释|
|鉴权要求|可选鉴权|
|功能说明|统一承载问答、推荐建议和路线解释，避免三个接口重复。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|mode|Body|string|是|qa   / suggest / explain|
|question|Body|string|否|用户自然语言问题|
|route\_id|Body|string|否|解释指定方案时提供|
|start\_station\_id|Body|int|否|起点站|
|end\_station\_id|Body|int|否|终点站|
|preference|Body|string|否|用户偏好|
|context|Body|object|否|前端已有的推荐结果；后端需校验字段|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|answer|string|自然语言回答|
|mode|string|实际执行模式|
|used\_tools|array\<string\>|调用的线路、ETA、客载量、推荐等工具|
|related\_routes|array\<RouteRecommendationDTO\>|相关路线|
|reminders|array\<string\>|出行提醒|
|fallback|bool|是否使用降级结果|



|**实现说明：**大模型不直接计算 ETA、客载量或体验分，只读取后端结构化结果并生成自然语言解释。|
|---|



## 4\.6 历史趋势模块

### 4\.6\.1 GET /api/v1/history/passenger\-flow

|**项目**|**内容**|
|---|---|
|接口名称|查询站点客流统计|
|鉴权要求|无需鉴权|
|功能说明|查询站点上下车人流和时段热度，用于图表和客载量预计特征。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int|否|线路编号|
|station\_id|Query|int|否|站点编号|
|start\_date|Query|date|否|开始日期|
|end\_date|Query|date|否|结束日期|
|granularity|Query|string|否|hour   / day / week|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<PassengerFlowHistoryDTO\>|上下车客流趋势|
|summary|object|总上车人数、总下车人数、峰值时段|



### 4\.6\.2 GET /api/v1/history/passenger\-load

|**项目**|**内容**|
|---|---|
|接口名称|查询车辆客载量趋势|
|鉴权要求|无需鉴权|
|功能说明|查询历史在车人数、客载率和客载等级。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|line\_id|Query|int|否|线路编号|
|station\_id|Query|int|否|站点编号|
|vehicle\_id|Query|int|否|车辆编号|
|start\_time|Query|datetime|否|开始时间|
|end\_time|Query|datetime|否|结束时间|
|granularity|Query|string|否|hour   / day|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<PassengerLoadHistoryDTO\>|客载量趋势|
|summary|object|平均客载率、峰值客载率、主要等级|



### 4\.6\.3 GET /api/v1/history/predictions

|**项目**|**内容**|
|---|---|
|接口名称|查询预测记录|
|鉴权要求|无需鉴权|
|功能说明|查询 ETA、客载量预计和出行体验评价的预测记录。|



**请求参数**

|**字段名**|**位置**|**类型**|**必填**|**说明**|
|---|---|---|---|---|
|prediction\_type|Query|string|否|eta   / passenger\_load / travel\_experience|
|line\_id|Query|int|否|线路编号|
|station\_id|Query|int|否|站点编号|
|start\_time|Query|datetime|否|开始时间|
|end\_time|Query|datetime|否|结束时间|
|page|Query|int|否|默认   1|
|page\_size|Query|int|否|默认   20|



**响应 data**

|**字段名**|**类型**|**说明**|
|---|---|---|
|items|array\<PredictionRecordDTO\>|预测记录|
|total|int|记录总数|
|page|int|当前页|
|page\_size|int|每页条数|



# 五、关键接口 JSON 示例

### 5\.1 客载量预计响应示例

|\{<br>  "code": 0,<br>  "message": "success",<br>  "data": \{<br>    "line\_id": 1,<br>    "station\_id": 3,<br>    "vehicle\_id": 101,<br>    "predicted\_onboard\_count": 46,<br>    "capacity": 60,<br>    "predicted\_load\_rate": 0\.77,<br>    "predicted\_load\_level":   "standing\_available",<br>    "confidence": 0\.84,<br>    "predict\_time":   "2026\-07\-08T09:10:00\+08:00",<br>    "feature\_summary": \{<br>      "is\_peak": true,<br>      "station\_flow\_level":   "high",<br>      "weather": "rain"<br>    \},<br>    "model\_version":   "load\_xgb\_v1"<br>  \},<br>  "trace\_id":   "req\_load\_001",<br>  "timestamp":   "2026\-07\-08T09:09:30\+08:00"<br>\}|
|---|



### 5\.2 出行体验评价响应示例

|\{<br>  "code": 0,<br>  "message": "success",<br>  "data": \{<br>    "load\_score": 58\.0,<br>    "walk\_score": 84\.0,<br>    "transfer\_score": 100\.0,<br>    "experience\_score": 74\.2,<br>    "factor\_weights": \{<br>      "w\_load": 0\.50,<br>      "w\_walk": 0\.30,<br>      "w\_transfer": 0\.20<br>    \},<br>    "factor\_values": \{<br>      "predicted\_load\_rate": 0\.77,<br>      "walk\_time\_minutes": 6\.5,<br>      "transfer\_count": 0<br>    \},<br>    "reason": "无需换乘且步行时间较短，但预计车内可站立，综合体验中等偏好。"<br>  \},<br>  "trace\_id":   "req\_exp\_001",<br>  "timestamp":   "2026\-07\-08T09:10:00\+08:00"<br>\}|
|---|



### 5\.3 出行体验推荐响应示例

|\{<br>  "code": 0,<br>  "message": "success",<br>  "data": \{<br>    "best\_experience\_route\_id":   "route\_002",<br>    "fastest\_route\_id":   "route\_001",<br>    "least\_crowded\_route\_id":   "route\_002",<br>    "least\_walking\_route\_id":   "route\_001",<br>    "least\_transfer\_route\_id":   "route\_001",<br>    "preference":   "balanced",<br>    "generated\_at":   "2026\-07\-08T09:12:00\+08:00",<br>    "items": \[<br>      \{<br>        "route\_id":   "route\_002",<br>        "line\_ids": \[2\],<br>        "boarding\_station":   \{"station\_id": 5, "station\_name": "西门站"\},<br>        "alighting\_station":   \{"station\_id": 12, "station\_name": "教学楼站"\},<br>        "predicted\_eta\_minutes":   7\.0,<br>        "predicted\_load": \{<br>          "predicted\_load\_rate":   0\.52,<br>          "predicted\_load\_level":   "seats\_available"<br>        \},<br>        "walk\_time\_minutes": 8\.0,<br>        "transfer\_count": 0,<br>        "experience\_score": 86\.5,<br>        "recommend\_types":   \["best\_experience", "least\_crowded"\],<br>        "reason": "预计有座位、无需换乘，步行时间可接受。"<br>      \}<br>    \]<br>  \},<br>  "trace\_id":   "req\_rec\_001",<br>  "timestamp":   "2026\-07\-08T09:12:00\+08:00"<br>\}|
|---|



### 5\.4 AI 出行助手响应示例

|\{<br>  "code": 0,<br>  "message": "success",<br>  "data": \{<br>    "answer": "建议选择校园 2 号线。该方案预计车内有座位、无需换乘，前往西门站步行约 8 分钟，出行体验综合分最高。最快方案是校园 1 号线，但预计客载压力更大。",<br>    "mode": "suggest",<br>    "used\_tools": \[<br>      "bus\_stations",<br>      "eta",<br>      "passenger\_load\_prediction",<br>      "walking\_time\_estimation",<br>      "recommend\_routes"<br>    \],<br>    "related\_routes": \[\],<br>    "reminders": \["雨天步行时间可能增加 1\-2 分钟"\],<br>    "fallback": false<br>  \},<br>  "trace\_id":   "req\_ai\_001",<br>  "timestamp":   "2026\-07\-08T09:13:00\+08:00"<br>\}|
|---|



# 六、数据库字段到接口字段映射

数据库字段统一采用 snake\_case。密码哈希、内部特征和调试字段不得直接返回前端；计算字段可由服务层动态生成。

|**数据表**|**数据库字段**|**接口字段**|**类型**|**说明**|
|---|---|---|---|---|
|user|id|user\_id|int|用户编号|
|user|username|username|string|登录账号|
|user|password\_hash|不返回|string|仅后端鉴权使用|
|user|nickname|nickname|string|昵称|
|user|created\_at|created\_at|datetime|注册时间|
|user\_favorite|favorite\_id|favorite\_id|int|收藏编号|
|user\_favorite|route\_name|route\_name|string|收藏名称|
|user\_favorite|route\_snapshot|route\_snapshot|json|路线快照|
|query\_history|history\_id|history\_id|int|历史编号|
|query\_history|query\_type|query\_type|string|查询类型|
|bus\_line|line\_id|line\_id|int|线路编号|
|bus\_line|line\_name|line\_name|string|线路名称|
|bus\_line|first\_bus\_time|first\_bus\_time|time|首班时间|
|bus\_line|last\_bus\_time|last\_bus\_time|time|末班时间|
|bus\_station|station\_id|station\_id|int|站点编号|
|bus\_station|station\_name|station\_name|string|站点名称|
|bus\_station|longitude|longitude|float|经度|
|bus\_station|latitude|latitude|float|纬度|
|line\_station|station\_order|station\_order|int|站点顺序|
|line\_station|distance\_to\_next|distance\_to\_next|float|到下一站距离|
|line\_station|average\_travel\_minutes|average\_travel\_minutes|float|平均站间耗时|
|bus\_vehicle|vehicle\_id|vehicle\_id|int|车辆编号|
|bus\_vehicle|capacity|capacity|int|车辆容量|
|bus\_realtime|longitude|longitude|float|车辆经度|
|bus\_realtime|latitude|latitude|float|车辆纬度|
|bus\_realtime|current\_station\_id|current\_station\_id|int|当前站点|
|bus\_realtime|next\_station\_id|next\_station\_id|int|下一站|
|bus\_realtime|progress|progress|float|站间进度|
|bus\_realtime|speed|speed|float|当前速度|
|bus\_realtime|onboard\_count|onboard\_count|int|当前车上人数|
|passenger\_flow\_history|passenger\_up|passenger\_up|int|上车人数|
|passenger\_flow\_history|passenger\_down|passenger\_down|int|下车人数|
|passenger\_load\_prediction|predicted\_onboard\_count|predicted\_onboard\_count|int|预计车上人数|
|passenger\_load\_prediction|predicted\_load\_rate|predicted\_load\_rate|float|预计客载率|
|passenger\_load\_prediction|predicted\_load\_level|predicted\_load\_level|string|预计客载等级|
|passenger\_load\_prediction|confidence|confidence|float|置信度|
|passenger\_load\_prediction|model\_version|model\_version|string|模型版本|
|计算字段|\-|walk\_distance\_meters|float|由坐标或地图 API 计算|
|计算字段|\-|walk\_time\_minutes|float|距离   / 步行速度|
|计算字段|\-|transfer\_count|int|路线段数   \- 1|
|计算字段|\-|experience\_score|float|三项指标加权计算|



# 七、Postman / Apifox 接口测试记录

下表为执行模板。后端开发完成后，应填写实际结果、响应耗时、截图编号和问题单编号。

|**用例编号**|**接口**|**测试目标**|**测试数据**|**预期结果**|**实际结果**|
|---|---|---|---|---|---|
|TC\-USER\-001|POST   /users/register|正常注册|合法   username/password|code=0，返回   user|待执行|
|TC\-USER\-002|POST   /users/register|重复注册|重复   username|code=40900|待执行|
|TC\-USER\-003|POST   /users/login|正常登录|正确账号密码|返回   access\_token|待执行|
|TC\-USER\-004|GET   /users/me|缺少鉴权|无   Token|code=40100|待执行|
|TC\-LINE\-001|GET   /bus\-lines|查询线路|keyword   为空|返回   items、total|待执行|
|TC\-STATION\-001|GET   /bus\-stations|查询站点|keyword=教学楼|返回匹配站点|待执行|
|TC\-STATION\-002|GET   /bus\-stations/nearby|附近站点|合法经纬度|按距离升序|待执行|
|TC\-STATION\-003|GET   /bus\-stations/nearby|非法坐标|latitude=120|code=42200|待执行|
|TC\-VEH\-001|GET   /bus\-vehicles/realtime|车辆实时状态|line\_id=1|含坐标、人数、容量|待执行|
|TC\-ETA\-001|GET   /eta|正常   ETA|vehicle\_id=101,   station\_id=3|返回分钟和到站时间|待执行|
|TC\-ETA\-002|GET   /eta|车辆不在线路|错误   line\_id|code=40002|待执行|
|TC\-LOAD\-001|POST   /passenger\-load\-prediction|正常预计|line/station/vehicle|返回人数、客载率、等级|待执行|
|TC\-LOAD\-002|POST   /passenger\-load\-prediction|容量为   0|capacity=0|code=40002/42200|待执行|
|TC\-WALK\-001|POST   /walking\-time\-estimation|正常估算|坐标\+站点|返回距离和分钟|待执行|
|TC\-WALK\-002|POST   /walking\-time\-estimation|步速越界|speed=5\.0|code=42200|待执行|
|TC\-EXP\-001|POST   /travel\-experience/evaluate|默认权重|三项指标合法|返回三分项和综合分|待执行|
|TC\-EXP\-002|POST   /travel\-experience/evaluate|权重和不为   1|0\.5\+0\.5\+0\.5|code=40002|待执行|
|TC\-REC\-001|POST   /recommend\-routes|综合推荐|起终点\+balanced|返回各类   route\_id|待执行|
|TC\-REC\-002|POST   /recommend\-routes|禁止换乘|allow\_transfer=false|不返回换乘方案|待执行|
|TC\-REC\-003|POST   /recommend\-routes|相同起终点|start=end|code=40003|待执行|
|TC\-AI\-001|POST   /ai/travel|问答模式|mode=qa,   question|返回   answer、used\_tools|待执行|
|TC\-AI\-002|POST   /ai/travel|大模型超时降级|模拟超时|fallback=true   或 code=50303|待执行|
|TC\-HIS\-001|GET   /history/passenger\-flow|客流趋势|日期范围|返回   items、summary|待执行|
|TC\-HIS\-002|GET   /history/passenger\-load|客载量趋势|line\_id=1|返回客载率趋势|待执行|



## 7\.1 Apifox / Postman 环境变量

|**变量名**|**示例值**|**用途**|
|---|---|---|
|base\_url|http://127\.0\.0\.1:8000/api/v1|统一接口地址|
|token|登录返回   access\_token|自动填充   Authorization|
|line\_id|1|线路测试|
|station\_id|3|站点、ETA、客载量测试|
|vehicle\_id|101|车辆、ETA、客载量测试|
|longitude|103\.8519|附近站点和步行时长测试|
|latitude|1\.2903|附近站点和步行时长测试|



## 7\.2 建议断言

|**断言项**|**断言规则**|
|---|---|
|HTTP   状态码|成功 200；参数错误 400/422；未鉴权 401；资源不存在 404|
|统一结构|响应包含   code、message、data、trace\_id、timestamp|
|成功状态|code=0   且 message=success|
|分页接口|data\.items   为数组，data\.total/page/page\_size 为数字|
|客载量结果|predicted\_load\_level   必须属于规定枚举；客载率在 0\-1|
|体验分|三项分数和   experience\_score 均在 0\-100；权重和为 1|
|步行时长|walk\_time\_minutes   \>= 0，distance \>= 0|
|异常安全|不得返回数据库堆栈、密钥或模型本地路径|



# 八、Vue 前端与 FastAPI 后端联调清单

|**前端页面**|**调用接口**|**页面展示**|**验收标准**|**状态**|
|---|---|---|---|---|
|登录注册页|/users/register；/users/login|表单、Token   保存|注册后可登录，Token   正确保存|待联调|
|个人中心|/users/me；/users/me/favorites；/users/me/query\-history|个人信息、收藏、历史|鉴权失效时跳转登录|待联调|
|首页|/bus\-stations/nearby；/bus\-lines；/recommend\-routes|附近站点、起终点输入、推荐入口|可选择站点并发起推荐|待联调|
|线路查询页|/bus\-lines；/bus\-lines/\{id\}|线路列表和详情|线路筛选与详情正确|待联调|
|站点查询页|/bus\-stations；/bus\-stations/\{id\}|站点列表、经过线路|搜索与详情可用|待联调|
|公交详情页|/bus\-lines/\{id\}/stations；/bus\-vehicles/realtime；/eta；/passenger\-load\-prediction|站点、车辆、ETA、客载量|车辆状态和预测值可刷新|待联调|
|地图区域|/bus\-lines/\{id\}/map；/bus\-vehicles/realtime|线路、站点、车辆点位|坐标可渲染，点位更新|待联调|
|推荐页|/walking\-time\-estimation；/travel\-experience/evaluate；/recommend\-routes|三项指标、综合分、分类推荐|综合分不包含   ETA|待联调|
|AI   助手页|/ai/travel|问答、建议、解释|异常时显示降级提示|待联调|
|历史趋势页|/history/passenger\-flow；/history/passenger\-load；/history/predictions|客流、客载量、预测记录|ECharts   正常渲染|待联调|



