"""Application configuration."""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://interviewx:interviewx_secret@localhost:5432/interviewx"

    # JWT
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    # Gemini and uploads
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    jd_upload_dir: str = "storage/jd_uploads"
    jd_max_upload_size_bytes: int = 10_485_760
    cv_upload_dir: str = "storage/cv_uploads"
    cv_max_upload_size_bytes: int = 10_485_760

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def jd_upload_path(self) -> Path:
        """Return the JD upload directory as a path."""
        return Path(self.jd_upload_dir)

    @property
    def cv_upload_path(self) -> Path:
        """Return the CV upload directory as a path."""
        return Path(self.cv_upload_dir)


settings = Settings()
