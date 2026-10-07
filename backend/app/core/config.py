from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./meeting-workspace.db"
    turso_database_url: str = ""
    turso_auth_token: SecretStr = SecretStr("")
    internal_api_token: SecretStr = SecretStr("")
    allowed_hosts: str = "localhost,127.0.0.1,backend,testserver"
    llm_provider: Literal["disabled", "openai"] = "disabled"
    openai_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    reads_per_minute: int = Field(120, ge=1, le=10000)
    writes_per_minute: int = Field(30, ge=1, le=1000)
    imports_per_ten_minutes: int = Field(5, ge=1, le=100)
    exports_per_minute: int = Field(10, ge=1, le=100)
    ai_per_minute: int = Field(5, ge=1, le=100)
    max_workspaces: int = 500
    max_meetings: int = 100
    global_text_bytes: int = 512 * 1024 * 1024
    disk_reserve_bytes: int = 100 * 1024 * 1024

    @property
    def remote_database(self) -> bool:
        return bool(self.turso_database_url)

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if not self.database_url.startswith("sqlite:///"):
            raise ValueError("A disk-backed SQLite URL is required")
        if bool(self.turso_database_url) != bool(self.turso_auth_token.get_secret_value()):
            raise ValueError("Configure both TURSO_DATABASE_URL and TURSO_AUTH_TOKEN")
        if self.remote_database:
            url = urlsplit(self.turso_database_url)
            if (
                url.scheme != "libsql"
                or not url.hostname
                or not url.hostname.endswith(".turso.io")
                or url.username
                or url.password
                or url.port
                or url.query
                or url.fragment
                or url.path not in {"", "/"}
            ):
                raise ValueError("TURSO_DATABASE_URL must be a libsql:// Turso Cloud hostname")
        elif self.environment == "production":
            raise ValueError("Production requires remote Turso libSQL; local storage is ephemeral")
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
