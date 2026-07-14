from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import PROJECT_ROOT as CONFIG_PROJECT_ROOT  # noqa: E402
from app.core.config import settings  # noqa: E402


def _masked_database_target(database_url: str) -> str:
    url = make_url(database_url)
    host = url.host or ""
    port = f":{url.port}" if url.port else ""
    database = f"/{url.database}" if url.database else ""
    return f"{url.drivername}://{host}{port}{database}"


def main() -> int:
    env_file = CONFIG_PROJECT_ROOT / ".env"
    print(f"project_root: {CONFIG_PROJECT_ROOT}")
    print(f"shared_env_exists: {env_file.is_file()}")
    print(f"database_target: {_masked_database_target(settings.DATABASE_URL)}")

    connect_args: dict[str, object] = {}
    if settings.DATABASE_URL.startswith("mysql"):
        connect_args["connect_timeout"] = 5

    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        connect_args=connect_args,
    )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        print(f"database_connection: failed")
        print(f"error_type: {type(exc).__name__}")
        print(f"error: {exc}")
        return 1
    finally:
        engine.dispose()

    print("database_connection: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
