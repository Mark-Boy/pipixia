"""
pipixia API 配置
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # 应用
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://pipixia:pipixia_secret@localhost:5432/pipixia"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin-secret"
    MINIO_BUCKET: str = "pipixia-images"

    # LLM
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-plus"

    # Shopee
    SHOPEE_MARKET_ID: int = 146
    SHOPEE_SIGNATURE_ENABLED: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
