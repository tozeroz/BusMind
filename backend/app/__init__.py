"""BusMind backend application package.

这里显式声明 `api` 子包，方便 IDE 在 `from app.api import ...`
这类导入上正确解析到本项目的 `backend/app/api`。
"""

from __future__ import annotations

from pathlib import Path
import sys


# 后端经常在 `backend` 目录内启动；补上项目根目录后，`algorithm.*`
# 这类仓库级共享包也能被 `app.*` 模块稳定导入。
PROJECT_ROOT = Path(__file__).resolve().parents[2]
project_root_text = str(PROJECT_ROOT)
if project_root_text not in sys.path:
    sys.path.insert(0, project_root_text)


__all__ = ["api"]
