"""JD persistence models."""

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class JDDocument(Base, UUIDMixin, TimestampMixin):
    """Uploaded JD document metadata."""

    __tablename__: str = "jd_documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")

    analysis: Mapped["JDAnalysis | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )


class JDAnalysis(Base, UUIDMixin, TimestampMixin):
    """Structured Gemini analysis for a JD document."""

    __tablename__: str = "jd_analyses"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    document: Mapped[JDDocument] = relationship(back_populates="analysis")
