from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent

# Keep ``backend/.env`` as the canonical runtime configuration file.  The
# repository-level ``.env`` remains a compatibility fallback.  Absolute paths
# make configuration loading independent of the shell's current directory.
ENV_FILES = (
    PROJECT_ROOT / ".env",
    BACKEND_ROOT / ".env",
)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or project env files."""

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

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # QQ Mail SMTP settings for sending verification codes.
    # QQ_MAIL_AUTH_CODE is an SMTP authorization code (not the QQ password).
    # Obtain it from QQ Mail → Settings → Account → POP3/SMTP service.
    QQ_MAIL_HOST: str = "smtp.qq.com"
    QQ_MAIL_PORT: int = 465
    QQ_MAIL_USERNAME: str = ""
    QQ_MAIL_AUTH_CODE: str = ""
    QQ_MAIL_FROM_NAME: str = "BusMind"
    EMAIL_CODE_EXPIRE_MINUTES: int = 5
    EMAIL_CODE_RESEND_SECONDS: int = 60


settings = Settings()
