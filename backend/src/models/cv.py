"""Candidate CV persistence models."""

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import TimestampMixin, UUIDMixin

json_type = JSON().with_variant(JSONB, "postgresql")


class CandidateProfile(UUIDMixin, TimestampMixin):
    """Persisted candidate profile derived from a CV."""

    __tablename__ = "candidate_profiles"

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(50))
    headline: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)
    skills: Mapped[list[str]] = mapped_column(json_type, default=list)
    education: Mapped[list[dict[str, str]]] = mapped_column(json_type, default=list)
    work_experience: Mapped[list[dict[str, str]]] = mapped_column(json_type, default=list)


class CandidateDocument(UUIDMixin, TimestampMixin):
    """Persisted source document for a candidate CV."""

    __tablename__ = "candidate_documents"

    candidate_profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id"),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    extracted_text: Mapped[str | None] = mapped_column(Text)


class CandidateScreening(UUIDMixin, TimestampMixin):
    """Persisted screening results for a candidate CV."""

    __tablename__ = "candidate_screenings"

    candidate_profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id"),
        nullable=False,
    )
    screening_summary: Mapped[str | None] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer)
    matched_skills: Mapped[list[str]] = mapped_column(json_type, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(json_type, default=list)
    analysis: Mapped[dict[str, str]] = mapped_column(json_type, default=dict)
