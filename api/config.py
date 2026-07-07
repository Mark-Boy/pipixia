"""
pipixia API 配置
"""

from pydantic_settings import BaseSettings


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
    LLM_BASE_URL: str = "http://127.0.0.1:8080/v1"
    LLM_MODEL: str = "qwen-plus"
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_MODEL: str = "qwen-max"

    # Shopee
    SHOPEE_APP_KEY: str = "your_app_key_here"
    SHOPEE_SECRET: str = "your_secret_here"
    SHOPEE_MARKET_ID: int = 146
    SHOPEE_SIGNATURE_ENABLED: bool = False

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # 利润熔断阈值
    MIN_PROFIT_MARGIN: float = 10.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


def get_settings() -> Settings:
    return Settings()
