"""Persistence model for background AI jobs."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class BackgroundJobType(StrEnum):
    """Known background job kinds."""

    JD_ANALYSIS = "jd_analysis"
    CV_SCREENING = "cv_screening"
    INTERVIEW_SUMMARY = "interview_summary"
    INTERVIEW_DISCONNECT_TIMEOUT = "interview_disconnect_timeout"
    COMPANY_KNOWLEDGE_INGESTION = "company_knowledge_ingestion"


class BackgroundJobStatus(StrEnum):
    """Lifecycle states for background jobs."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundResourceType(StrEnum):
    """Resource kinds tracked by background jobs."""

    JD_DOCUMENT = "jd_document"
    JD_COMPANY_DOCUMENT = "jd_company_document"
    CANDIDATE_SCREENING = "candidate_screening"
    INTERVIEW_SESSION = "interview_session"


class BackgroundJob(Base, UUIDMixin, TimestampMixin):
    """Queued or running background job record."""

    __tablename__ = "background_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
