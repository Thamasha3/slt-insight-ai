"""
Centralized configuration.

Values come from environment variables (and `.env` in local development).
Secrets are never hardcoded.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    mongodb_uri: str
    mongodb_database: str = "insight_ai"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    admin_email_1: str
    admin_email_2: str

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_location: str = "global"
    google_cloud_project: str = ""
    google_application_credentials: str = ""

    environment: str = "development"
    cors_origins: str = "http://localhost:5173"
    upload_dir: str = "uploads"
    max_upload_mb: int = 20

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_emails(self) -> set[str]:
        return {self.admin_email_1.strip().lower(), self.admin_email_2.strip().lower()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
