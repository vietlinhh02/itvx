"""Candidate CV persistence models."""

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class CandidateDocument(Base, UUIDMixin, TimestampMixin):
    """Persisted source document for a candidate CV."""

    __tablename__ = "candidate_documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")

    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CandidateProfile(Base, UUIDMixin, TimestampMixin):
    """Persisted candidate profile derived from a CV."""

    __tablename__ = "candidate_profiles"

    candidate_document_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    profile_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    document: Mapped[CandidateDocument] = relationship(back_populates="profile")
    screenings: Mapped[list["CandidateScreening"]] = relationship(
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )


class CandidateScreening(Base, UUIDMixin, TimestampMixin):
    """Persisted screening results for a candidate CV."""

    __tablename__ = "candidate_screenings"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    screening_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    candidate_profile: Mapped[CandidateProfile] = relationship(back_populates="screenings")
