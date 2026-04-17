"""Application configuration."""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    gemini_model: str = "gemini-3.1-flash-lite-preview"
    livekit_url: str = "wss://your-project.livekit.cloud"
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_room_prefix: str = "interview"
    worker_callback_secret: str = "change-me"
    interview_worker_service_url: str = "http://127.0.0.1:8765"
    interview_worker_dispatch_timeout_seconds: float = 10.0
    interview_reconnect_grace_seconds: int = 120
    interview_worker_repo_root: str = "/home/eddiesngu/Desktop/Dang/interviewx"
    next_public_app_url: str = "http://localhost:3000"
    jd_upload_dir: str = "storage/jd_uploads"
    jd_max_upload_size_bytes: int = 10_485_760
    company_doc_upload_dir: str = "storage/company_docs"
    company_doc_max_upload_size_bytes: int = 10_485_760
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
    def company_doc_upload_path(self) -> Path:
        """Return the company document upload directory as a path."""
        return Path(self.company_doc_upload_dir)

    @property
    def cv_upload_path(self) -> Path:
        """Return the CV upload directory as a path."""
        return Path(self.cv_upload_dir)


settings = Settings()
