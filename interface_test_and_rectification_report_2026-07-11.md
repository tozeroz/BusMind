# 接口测试结果及后续整改方案报告

生成时间：2026-07-11  
项目目录：`D:\BusMind`  
测试命令：

```powershell
$env:PYTHONPATH="$PWD\backend;$PWD"
pytest .\backend\tests -q
```

## 一、测试结论

本次全量接口测试未完全通过。

- 总结果：`25 failed, 113 passed, 10 errors`
- 主要问题并非单一接口异常，而是测试环境、依赖注入、异步测试配置、个别接口兼容性四类问题叠加。
- 当前基础公交数据接口中的部分功能已经可用，但全量测试链路仍存在系统性阻塞，暂不适合直接作为“全量通过”的交付结果。

## 二、测试结果概览

### 1. 已通过部分

以下方向已有较多测试通过，说明已有代码基础可用：

- 基础用户相关接口
- 多数历史、推荐、智能模块中的纯逻辑测试
- 新增的 `geometry` GeoJSON 改造相关测试
- 已修复的启动导入问题相关测试

### 2. 未通过部分

本次失败主要集中在以下几类：

- 车辆实时接口测试兼容性失败
- ETA / 客流预测 / 步行时间 / 推荐路线 / 模拟更新等接口测试仍尝试连接本地 MySQL，导致失败
- 多个 `async def test_*` 测试未被 pytest 正常作为异步测试执行
- 一个 standalone 测试文件不符合 pytest 标准 fixture 组织方式，导致收集时报错

## 三、失败问题分类与原因分析

## 3.1 车辆接口序列化兼容问题

对应失败：

- `backend/tests/test_bus_vehicles_api.py::test_bus_vehicles_realtime_with_line_id`

报错特征：

- `AttributeError: 'dict' object has no attribute 'model_dump'`

根因分析：

- 当前车辆接口路由中，对返回列表统一按 Pydantic DTO 处理，直接调用 `item.model_dump()`
- 但测试中 mock 的返回值是普通 `dict`
- 因此在路由层序列化时，测试数据类型与生产 DTO 类型不兼容

影响范围：

- `/api/v1/vehicles/realtime`
- `/api/v1/bus-vehicles/realtime`
- `/api/v1/vehicles/line/{line_id}`

结论：

- 这是一个路由层兼容性问题，不是数据库或业务逻辑错误

## 3.2 Service-B 接口测试依赖仍然连接 MySQL

对应失败：

- `backend/tests/test_eta_api.py`
- `backend/tests/test_load_api.py`
- `backend/tests/test_recommendation_api.py`
- `backend/tests/test_walking_api.py`
- `backend/tests/test_simulation_update_api.py`
- `backend/tests/test_main_integration.py`

报错特征：

- `sqlalchemy.exc.OperationalError`
- `Can't connect to MySQL server on '127.0.0.1'`

根因分析：

- 测试本意是使用 demo / in-memory 风格依赖执行 Service-B 相关接口测试
- 但实际 FastAPI 依赖注入链仍从 `backend/app/api/v1/dependencies.py` 中构造 `MySQLTransitGateway`
- 这会触发真实数据库连接
- 一旦本地 MySQL 未启动、库表不完整或配置不匹配，就会批量失败

进一步说明：

- 这类失败不是接口业务算法本身错误
- 本质是测试环境没有把网关依赖替换为 demo gateway 或测试网关

结论：

- 这是当前全量测试失败的最大来源，优先级最高

## 3.3 异步测试未被 pytest 正常执行

对应失败：

- `backend/tests/test_eta_real_api.py`
- `backend/tests/test_eta_real_data.py`
- `backend/tests/test_eta_real_simple.py`
- `backend/tests/test_eta_real_standalone.py`
- `backend/tests/test_history_passenger_load.py`
- `backend/tests/test_history_predictions.py`
- `backend/tests/test_load_real_data.py`
- `backend/tests/test_recommendation_real_data.py`
- `backend/tests/test_walking_real_data.py`

报错特征：

- `async def functions are not natively supported`

根因分析：

- 项目中虽然安装了异步测试相关插件
- 但仓库根目录缺少 pytest 异步执行配置
- 导致部分 `async def test_*` 被当作普通测试收集，无法正常运行

结论：

- 这是测试框架配置问题，不是接口实现问题

## 3.4 standalone 测试文件组织方式不符合 pytest 规范

对应错误：

- `backend/tests/test_real_gateway_standalone.py`

报错特征：

- `fixture 'gateway' not found`
- `fixture 'station_id' not found`
- `fixture 'expected_name' not found`
- `fixture 'vehicle_id' not found`

根因分析：

- 该文件实际上更接近“可单独运行的脚本式测试”
- 但文件命名和函数命名都被 pytest 当作正式测试收集
- 文件内又没有提供对应 fixture，也没有使用标准参数化装饰器
- 最终导致 pytest 收集阶段就报错

结论：

- 这是测试文件结构问题，不是网关实现本身的问题

## 四、当前影响判断

### 1. 对服务端 A 基础公交接口的直接影响

直接影响较小的部分：

- 站点列表
- 线路列表
- 线路经过站点
- 站点详情
- 新增的线路 GeoJSON geometry 接口

因为本次大面积失败主要集中在：

- 智能推荐
- ETA
- 客流预测
- 步行时间
- 模拟更新
- standalone 网关测试

### 2. 对整体联调和项目交付的实际影响

直接影响较大：

- 项目无法给出“全量测试通过”的结果
- 组内联调时，智能出行相关接口可信度会受到质疑
- 若组长要求终端展示全量测试结果，当前输出会明显暴露环境依赖和测试组织问题

## 五、最小改动整改方案

整改目标：

- 不扩大修改范围
- 不重构现有模块
- 优先修复测试链路与依赖注入问题
- 在保证安全的前提下，使 `pytest .\backend\tests -q` 尽可能完整通过

## 5.1 整改项一：修复车辆接口序列化兼容性

修改位置：

- `backend/app/api/v1/vehicle/router.py`

建议改法：

- 在路由层增加一个很小的序列化 helper
- 若对象有 `model_dump()`，则调用
- 若对象本身为 `dict`，则直接返回

整改理由：

- 不改 service 返回类型
- 不改测试 mock 数据结构
- 改动面最小
- 可一次性兼容真实 DTO 和测试 stub

预期收益：

- 修复 `test_bus_vehicles_api.py` 相关失败

## 5.2 整改项二：在测试环境中强制覆盖 Service-B 依赖

修改位置：

- `backend/tests/conftest.py`

建议改法：

- 通过 `dependency_overrides` 覆盖以下依赖：
  - `get_eta_service`
  - `get_load_service`
  - `get_walking_service`
  - `get_recommendation_service`
  - `get_simulation_service`
  - 需要时覆盖 `get_ai_service`
- 所有测试依赖共享同一个 `DemoIntelligenceGateway` 实例
- 每次测试前后清理 `simulation_state_store`

整改理由：

- 不改生产依赖逻辑
- 不要求本地 MySQL 必须启动
- 保持接口测试稳定、可重复
- 能一次性修复大量因数据库连接导致的失败

特别说明：

- `test_main_integration.py` 直接导入正式应用，也应确保正式 app 在测试期可被同样覆盖

预期收益：

- 修复 ETA、负载、推荐、步行、模拟更新等接口测试中的大多数 MySQL 连接失败

## 5.3 整改项三：补充 pytest 异步配置

修改位置：

- 项目根目录新增 `pytest.ini`

建议内容：

```ini
[pytest]
asyncio_mode = auto
```

整改理由：

- 不需要逐个给每个异步测试补装饰器
- 属于标准测试框架配置
- 改动极小但收益很高

预期收益：

- 修复大量 `async def functions are not natively supported` 问题

## 5.4 整改项四：整理 standalone 网关测试文件

修改位置：

- `backend/tests/test_real_gateway_standalone.py`

建议改法：

- 将其改造成标准 pytest 文件
- 增加标准 fixture，例如：
  - `db_session`
  - `gateway`
- 对有参数输入的测试使用 `pytest.mark.parametrize`
- 去掉当前依赖“伪 fixture 参数”的写法

整改理由：

- 该文件当前不是标准 pytest 结构
- 若继续保留当前写法，会持续成为全量测试阻塞点

备选方案：

- 若短期目标只是保证主测试通过，可先将此文件移出 `tests` 收集范围
- 但从规范性和长期维护角度，建议改造成标准 pytest 结构

## 六、推荐整改优先级

### P0：立即处理

1. 测试环境依赖覆盖问题  
2. pytest 异步配置问题

原因：

- 这两项修复后，可直接消除当前绝大多数失败

### P1：随后处理

3. 车辆接口序列化兼容问题  
4. standalone 测试文件结构问题

原因：

- 改动小，收益明确，适合作为同一轮收尾整改

## 七、建议执行顺序

建议按以下顺序整改与回归：

1. 新增 `pytest.ini`，验证异步测试可被正常执行
2. 在 `conftest.py` 中统一覆盖 Service-B 依赖
3. 修复 `vehicle/router.py` 中的序列化兼容问题
4. 整理 `test_real_gateway_standalone.py`
5. 分批回归测试：

```powershell
python -m pytest .\backend\tests\test_bus_vehicles_api.py -q
python -m pytest .\backend\tests\test_eta_api.py .\backend\tests\test_load_api.py .\backend\tests\test_walking_api.py .\backend\tests\test_recommendation_api.py .\backend\tests\test_simulation_update_api.py -q
python -m pytest .\backend\tests\test_main_integration.py -q
python -m pytest .\backend\tests\test_real_gateway_standalone.py -q
python -m pytest .\backend\tests -q
```

## 八、最终结论

本次终端测试暴露出的主要问题并不是“接口整体不可用”，而是测试工程层面存在若干结构性缺口：

- 路由层对 mock 数据兼容性不足
- 测试依赖未与真实数据库解耦
- 异步测试运行配置缺失
- 个别 standalone 测试文件不符合 pytest 规范

从整改成本和安全性看，建议采用“最小改动”方案：

- 不重构业务逻辑
- 不强制依赖本地 MySQL
- 仅修复测试注入、异步配置、少量路由兼容和单个测试文件结构

按该方案实施后，预期可以显著提升全量接口测试通过率，并为后续组内联调和汇报提供更稳定的结果基础。
