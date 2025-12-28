from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    TITLE: str = "LinguaTile API"
    DESCRIPTION: str = "An API used by LinguaTile to aid in studying Japanese"
    VERSION: str = "0.8.0"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    # Database
    MONGO_HOST: str

    # External APIs
    API_KEY: str | None = None

    # VAPID / Push Notifications
    VAPID_PRIVATE_KEY: str | None = None
    VAPID_PUBLIC_KEY: str | None = None
    VAPID_CLAIMS_SUB: str = "mailto:admin@lingua-tile.com"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


@lru_cache
def get_settings():
    return Settings()
