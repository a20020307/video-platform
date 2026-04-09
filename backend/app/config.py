from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Video Upload Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/videodb"

    # OSS
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = "oss-cn-hangzhou.aliyuncs.com"
    OSS_INTERNAL_ENDPOINT: str = ""  # set this when running inside Alibaba Cloud VPC

    # Upload
    DEFAULT_CHUNK_SIZE_BYTES: int = 10 * 1024 * 1024   # 10 MB
    MAX_CHUNK_SIZE_BYTES: int = 500 * 1024 * 1024       # 500 MB
    MAX_PARTS: int = 9000                                # leave headroom below OSS 10000 limit
    UPLOAD_SESSION_TTL_HOURS: int = 24

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost:80"]

    # Rate limiting (requests per minute)
    AUTH_RATE_LIMIT: str = "10/minute"


@lru_cache
def get_settings() -> Settings:
    return Settings()
