from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed application configuration.

    Trading is deliberately disabled by default. Secrets are loaded only from
    environment variables and are never part of research objects or prompts.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    database_url: str = Field(
        default="postgresql+psycopg://trading:trading_dev_password@localhost:5433/trading_research",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", alias="RABBITMQ_URL")
    binance_base_url: str = Field(default="https://api.binance.com", alias="BINANCE_BASE_URL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_research_model: str = Field(default="gpt-5.6-luna", alias="OPENAI_RESEARCH_MODEL")

    trading_environment: str = Field(default="paper", alias="TRADING_ENVIRONMENT")
    trading_enabled: bool = Field(default=False, alias="TRADING_ENABLED")
    trading_kill_switch: bool = Field(default=True, alias="TRADING_KILL_SWITCH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
