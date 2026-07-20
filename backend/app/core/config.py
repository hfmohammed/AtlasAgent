from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AtlasAgent"
    environment: str = "development"
    database_url: str = "sqlite:///./atlasagent.db"
    redis_url: str = "redis://localhost:6379/0"
    llm_provider: str = "deterministic"
    chat_model: str = "gpt-5-mini"
    embedding_model: str = "text-embedding-3-small"
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "ATLAS_OPENAI_API_KEY"),
    )
    approval_secret: str = "development-only-secret"
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_prefix="ATLAS_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

