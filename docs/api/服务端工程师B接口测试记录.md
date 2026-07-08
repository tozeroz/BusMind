# 服务端工程师 B 接口测试记录

## 测试环境

| 项目 | 内容 |
|---|---|
| 测试日期 | 2026-07-08 |
| Python | 3.13.5 |
| FastAPI | 0.128.2 |
| Pydantic | 2.13.4 |
| HTTPX | 0.28.1 |
| Pytest | 9.0.2 |
| 测试入口 | 独立 FastAPI TestClient |

## 自动化测试结果

执行命令：

```text
PYTHONPATH=. pytest -q backend/tests tests/integration
```

结果：

```text
18 passed in 0.31s
```

| 用例 | 结果 |
|---|---|
| ETA 正常计算 | 通过 |
| ETA 车辆与线路不匹配 | 通过，code=40002 |
| ETA 参数缺失 | 通过，code=42200 |
| 客载量正常预计 | 通过 |
| 客载量车辆与线路不匹配 | 通过，code=40002 |
| 客载容量为 0 | 通过，code=42200 |
| 步行时长正常估算 | 通过 |
| 步行速度越界 | 通过，code=42200 |
| 三指标体验分示例 | 通过，58/84/100/74.2 |
| 权重和不为 1 | 通过，code=40002 |
| 缺少客载信息 | 通过，code=42200 |
| 综合路线推荐 | 通过 |
| 禁止换乘 | 通过 |
| 起终点相同 | 通过，code=40003 |
| AI 未配置 Key 时降级 | 通过，fallback=true |
| AI QA 缺少问题 | 通过，code=42200 |
| AI 注入模拟 DeepSeek 客户端 | 通过，fallback=false |
| ETA→Load→Recommend→AI 完整流程 | 通过 |

## Postman 状态

已生成可导入的 Collection 和 Environment，并包含响应结构、状态码、枚举、分数范围等自动断言。由于当前环境没有 Postman GUI，本次未生成 Postman 截图；在本地启动服务后可直接运行 Collection。

## 降级测试结论

- ETA 模型不存在时：返回 `eta_rule_v1`。
- Load 模型不存在时：返回 `load_rule_v1`。
- 未配置 DeepSeek Key、网络超时或 API 错误时：AI 返回模板结果且 `fallback=true`。
- 降级过程中不返回 API Key、本地模型路径和异常堆栈。
