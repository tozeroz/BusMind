from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # JWT 配置
    SECRET_KEY: str = "your-secret-key-here-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时

    # SQLite 数据库配置（用于测试）
    DATABASE_URL: str = "sqlite:///./busmind.db"

    class Config:
        env_file = ".env"

settings = Settings()