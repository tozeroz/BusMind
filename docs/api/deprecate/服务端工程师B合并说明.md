# 服务端工程师 B 合并说明

## 新增路由入口

```python
from backend.app.api.v1.intelligence_router import router as intelligence_router

app.include_router(intelligence_router, prefix="/api/v1")
```

## 新增异常处理

```python
from backend.app.core.exception_handlers import register_intelligence_exception_handlers

register_intelligence_exception_handlers(app)
```

团队已有统一异常处理中间件时，不要重复注册；只需保证业务错误码和统一响应格式一致。

## 数据边界

- 服务端 B 不直接依赖服务端 A 的 SQLAlchemy Model。
- 服务端 B 通过 `IntelligenceDataGateway` 获取站点、车辆、距离和候选路线。
- 服务端 A 在启动时调用 `configure_intelligence_gateway()` 注入数据库适配器。
- 数据处理工程师通过可配置的 Python 函数入口提供 ETA 和 Load 模型。
- 模型未交付时启用规则降级，不阻塞接口联调。

## 冲突检查

合并前检查队友是否已经创建以下同名文件：

```text
backend/app/api/v1/intelligence_router.py
backend/app/intelligence_demo.py
backend/app/core/exception_handlers.py
backend/app/services/intelligence_gateway.py
```

若已有统一文件，应把本模块的注册代码合并进去，不要直接覆盖队友实现。
