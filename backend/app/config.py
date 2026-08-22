from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://lastmile:lastmile@localhost:5434/lastmile",
        alias="DATABASE_URL",
    )
    app_env: str = Field(default="development", alias="APP_ENV")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
