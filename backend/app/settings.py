"""Centralized configuration loaded from environment variables."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Entra ID
    TENANT_ID: str
    API_CLIENT_ID: str
    API_CLIENT_SECRET: str
    SPA_CLIENT_ID: str
    API_SCOPE_NAME: str = "access_as_user"

    # Dataverse
    DATAVERSE_URL: str = "https://example.crm.dynamics.com"
    DATAVERSE_TABLE: str = "cr0b4_tasks"

    # Server
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    LOG_LEVEL: str = "INFO"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.TENANT_ID}"

    @property
    def dataverse_scope(self) -> str:
        return f"{self.DATAVERSE_URL}/.default"


@lru_cache
def get_settings() -> Settings:
    return Settings()
