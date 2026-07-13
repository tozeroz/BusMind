# 服务端工程师 B 交付清单

## 接口

- `GET /api/v1/eta`
- `POST /api/v1/passenger-load-prediction`
- `POST /api/v1/walking-time-estimation`
- `POST /api/v1/travel-experience/evaluate`
- `POST /api/v1/recommend-routes`
- `POST /api/v1/ai/travel`

## 核心代码

- FastAPI 路由与统一聚合路由
- Pydantic 请求/响应模型
- ETA 服务和外部模型适配器
- 客载状态服务和外部模型适配器
- 步行时长、三指标评分、路线选择和推荐解释
- DeepSeek OpenAI 兼容 API 客户端
- AI 上下文构造、Prompt 和无 Key/超时降级
- 可替换的 `IntelligenceDataGateway`
- 独立 Postman 测试入口

## 测试与文档

- 后端单元测试
- 完整流程集成测试
- Postman Collection
- Postman Environment
- 使用说明
- 合并说明
- 接口测试记录
- 依赖清单
- 环境变量示例
