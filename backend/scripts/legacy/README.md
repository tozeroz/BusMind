# Backend legacy scripts

这个目录归档后端根目录中历史遗留的临时排查、修复和手工测试脚本。

这些脚本不属于正式启动入口，也不属于正式测试套件。正式测试请使用：

```powershell
uv run pytest backend\tests
```

如果确实需要运行本目录里的旧脚本，请先确认脚本内容和数据库连接目标，再从 `backend/` 目录执行，避免相对路径或导入路径不一致。
