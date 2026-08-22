from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    return database_url


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+psycopg://lastmile:lastmile@localhost:5434/lastmile",
        alias="DATABASE_URL",
    )
    app_env: str = Field(default="development", alias="APP_ENV")
    frontend_url: str = Field(default="http://localhost:5173", alias="FRONTEND_URL")
    jwt_secret: str = Field(
        default="change-me-for-local-development-secret", alias="JWT_SECRET"
    )
    access_token_expire_minutes: int = Field(
        default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    demo_password: str = Field(default="change-me-for-local-demo", alias="DEMO_PASSWORD")
    geoapify_api_key: str = Field(default="", alias="GEOAPIFY_API_KEY")
    geocoding_country_code: str = Field(default="in", alias="GEOCODING_COUNTRY_CODE")
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    email_from: str = Field(default="", alias="EMAIL_FROM")
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str = Field(default="", alias="TWILIO_FROM_NUMBER")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        return normalize_database_url(value)


@lru_cache
def get_settings() -> Settings:
    return Settings()
