# Backend Scripts

本目录只保存可重复执行的后端维护、导入和联调脚本。一次性排查、编码修复和旧版手工测试脚本统一放在 `legacy/`。

| 脚本 | 用途 |
|---|---|
| `check_ai_config.py` | 检查 AI 服务配置是否完整 |
| `forecast_passenger_flow.py` | 生成站点未来 7 天客流预测并写入 `passenger_flow_prediction` |
| `import_csv_data.py` | 导入标准 CSV 数据 |
| `import_csv_simple.py` | 兼容旧数据的简化导入入口 |
| `inspect_refresh_jobs.py` | 查看后台刷新任务配置与状态 |
| `list_users.py` | 管理员本地查看用户数据 |
| `smoke_frontend_links.py` | 检查前端调用的后端路径是否存在 |
| `verify_priority_integration.py` | 执行重点接口联调检查 |
| `legacy/` | 历史临时脚本，不纳入正式启动和自动测试 |

从项目根目录运行，例如：

```powershell
uv run python backend\scripts\check_ai_config.py
uv run python backend\scripts\smoke_frontend_links.py
```

新增脚本必须使用小写下划线文件名，并在本表中登记；不要在 `backend/` 根目录新增临时脚本。

## 数据库连接自检

```powershell
uv run python backend\scripts\check_database_connection.py
```

该脚本读取正式配置并执行 `SELECT 1`，输出内容会隐藏数据库用户名和密码。
