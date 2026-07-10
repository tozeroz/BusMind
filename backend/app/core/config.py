from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or ``.env``."""

    SECRET_KEY: str = "your-secret-key-here-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Production/联调 should explicitly set a MySQL URL, for example:
    # mysql+pymysql://busmind_dev:password@127.0.0.1:13306/busmind?charset=utf8mb4
    DATABASE_URL: str = "sqlite:///./busmind.db"

    # The official MySQL schema is initialized by database/schema/init_busmind.sql.
    # Keep automatic table creation disabled in production to avoid schema drift.
    AUTO_CREATE_TABLES: bool = False
    VALIDATE_DB_SCHEMA_ON_STARTUP: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
