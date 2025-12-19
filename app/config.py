from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BookMyShow Backend"
    environment: str = "dev"
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    lock_ttl_seconds: int = 300
    cors_origins: list[str] = ["*"]
    admin_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="BMS_", case_sensitive=False)


def get_settings() -> Settings:
    return Settings()
