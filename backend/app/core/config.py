from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # JWT éç½®
    SECRET_KEY: str = "your-secret-key-here-change-in-production-1234567890"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24åæ¶

    # SQLite ææ®åºéç½®ï¼ç¨aºæµe¯ï¼?
    DATABASE_URL: str = "sqlite:///./busmind.db"

    class Config:
        env_file = ".env"

settings = Settings()
