from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./meeting-workspace.db"
    internal_api_token: SecretStr = SecretStr("")
    allowed_hosts: str = "localhost,127.0.0.1,backend,testserver"
    llm_provider: Literal["disabled", "openai"] = "disabled"
    openai_api_key: SecretStr = SecretStr("")
    llm_model: str = ""

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("A disk-backed SQLite URL is required")
        if len(self.internal_api_token.get_secret_value()) < 32:
            raise ValueError("INTERNAL_API_TOKEN must contain at least 32 characters")
        if self.environment == "production" and "testserver" in self.allowed_hosts:
            raise ValueError("Configure explicit production ALLOWED_HOSTS")
        if self.llm_provider == "openai" and (not self.openai_api_key or not self.llm_model):
            raise ValueError("OpenAI requires a server key and explicit model")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
