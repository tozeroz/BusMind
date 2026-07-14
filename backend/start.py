from __future__ import annotations

import os
from pathlib import Path
import sys

import uvicorn


BACKEND_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_ROOT.parent

# Preserve the backend directory as the runtime working directory even when
# this script is launched from the repository root.
os.chdir(BACKEND_ROOT)
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="::",
        port=8001,
        reload=True,
        reload_dirs=[str(BACKEND_ROOT / "app")],
        reload_excludes=["tests/*", "scripts/*"],
    )
