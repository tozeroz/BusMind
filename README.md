# BusMind 智行公交系统

BusMind 是一个面向公交出行体验的推荐系统。项目围绕新加坡 LTA DataMall 数据，完成公交站点、线路、实时到站、客载状态、道路速度热力图、历史客流和推荐评分等能力。

当前核心链路是：

```text
前端 5173 -> 后端 8001 -> SSH 隧道 3307 -> 远程 MySQL 3306
```

后端负责生成候选路线并补齐业务字段，推荐模型负责对候选路线评分，前端负责展示推荐结果。

## 目录职责

```text
frontend/      Vue 3 前端项目
backend/       FastAPI 后端服务
algorithm/     推荐模型、离线特征数据集和训练脚本
data/          LTA 原始数据、采集脚本和 processed CSV 处理脚本
database/      MySQL 初始化 SQL 和 CSV 导入脚本
docs/          当前项目文档；旧 API 文档归档在 docs/api/deprecate
postman/       当前保留的完整接口测试集合
tools/         本地开发、校验和辅助脚本
```

## 环境准备

需要提前安装：

```text
Python 3.11 或 3.12
uv
Node.js 18+
npm
OpenSSH Client
```

首次拉取项目后，在项目根目录执行：

```powershell
cd D:\SummerTraining\BusMind
uv sync
```

之后所有 Python 命令统一使用：

```powershell
uv run python ...
```

`backend/requirements.txt` 仅保留作历史兼容说明，新的 Python 依赖以根目录 `pyproject.toml` 为准。

## 环境变量

真实 `.env` 不提交到 Git。请按模板创建：

```powershell
Copy-Item .env.example .env
```

根目录 `.env` 是整个项目的唯一共享配置，供 backend、algorithm、数据脚本和本地工具共同读取。不要再维护 `backend/.env` 的第二份配置，避免同名变量互相覆盖。

必须配置的变量：

```env
DATABASE_URL=mysql+pymysql://用户名:密码@127.0.0.1:3307/busmind?charset=utf8mb4
LTA_ACCOUNT_KEY=你的_LTA_DataMall_AccountKey
DEEPSEEK_API_KEY=你的_DeepSeek_Key
DEEPSEEK_MODEL=deepseek-chat
```

后端邮件验证码还需要：

```env
QQ_MAIL_HOST=smtp.qq.com
QQ_MAIL_PORT=465
QQ_MAIL_USERNAME=你的_QQ_邮箱
QQ_MAIL_AUTH_CODE=你的_SMTP_授权码
QQ_MAIL_FROM_NAME=BusMind
EMAIL_CODE_EXPIRE_MINUTES=5
EMAIL_CODE_RESEND_SECONDS=60
```

## 启动开发环境

按顺序打开 3 个 PowerShell 窗口。

也可以直接使用统一启动脚本，它会先执行 `uv sync`，再按顺序打开数据库隧道、后端、前端三个窗口：

```powershell
cd D:\SummerTraining\BusMind
.\tools\dev\start-all-dev.ps1
```

### 1. 打开数据库 SSH 隧道

```powershell
ssh -N -L 3307:127.0.0.1:3306 training-server-backend
```

这个窗口保持开启，没有输出是正常的。

如果接口报数据库连接错误，先检查隧道：

```powershell
Test-NetConnection 127.0.0.1 -Port 3307
```

看到 `TcpTestSucceeded : True` 才表示隧道正常。

### 2. 启动后端

```powershell
cd D:\SummerTraining\BusMind\backend
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

后端文档：

```text
http://127.0.0.1:8001/docs
```

### 3. 启动前端

```powershell
cd D:\SummerTraining\BusMind\frontend
npm install
npm run dev
```

打开：

```text
http://127.0.0.1:5173
```

## 常用命令

检查 Python 环境：

```powershell
uv run python --version
```

运行后端测试：

```powershell
cd D:\SummerTraining\BusMind
uv run pytest backend\tests
```

运行前端接口契约测试：

```powershell
cd D:\SummerTraining\BusMind\frontend
npm run test:api-contract
```

运行推荐模型预测 smoke test：

```powershell
cd D:\SummerTraining\BusMind
uv run python algorithm\model\predictor.py --features algorithm\dataset\recommendation\v1\features.csv --preference balanced --top-routes 1
```

校验 processed 数据：

```powershell
cd D:\SummerTraining\BusMind
uv run python tools\validate_processed_data.py --processed-dir data\processed
```

MySQL 导入 dry-run：

```powershell
cd D:\SummerTraining\BusMind
uv run python database\import\import_processed_to_mysql.py --processed-dir data\processed --dry-run
```

## 文档入口

当前 API 文档入口：

```text
docs/api/README.md
docs/api/BusMind项目接口文档.md
docs/api/后端与推荐模型数据契约.md
```

历史接口草稿、联调记录和旧版交付文档统一归档在：

```text
docs/api/deprecate/
```

## 开发脚本归档

后端根目录只保留正式应用目录、测试目录、环境模板和兼容启动入口。历史排查、修复和手工测试脚本已归档到：

```text
backend/scripts/legacy/
```

## 注意事项

不要提交真实 `.env`、数据库密码、LTA AccountKey、DeepSeek Key、QQ 邮箱授权码。

不要把真实 raw / processed 大数据文件随意提交，仓库主要保留采集脚本、处理脚本和必要的小规模模型样例数据。

推荐模型不负责生成候选路线。完整推荐链路是：后端寻路生成候选路线，后端补字段，模型预处理并评分，后端排序分组，前端展示。
