from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    candidate_screening_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_screenings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    share_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    worker_dispatch_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    livekit_room_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    worker_status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    provider_status: Mapped[str] = mapped_column(String(50), nullable=False, default="room_not_connected")
    candidate_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worker_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_question: Mapped[str] = mapped_column(Text, nullable=False)
    approved_questions: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    manual_questions: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    question_guidance: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    scheduled_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    schedule_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unscheduled")
    schedule_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    candidate_proposed_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    candidate_proposed_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    disconnect_deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_disconnect_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_provider_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_runtime_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewTurn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewRuntimeEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_runtime_events"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_source: Mapped[str] = mapped_column(String(50), nullable=False)
    session_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    worker_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewFeedbackRecord(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_feedback_records"
    __table_args__ = (UniqueConstraint("interview_session_id", name="uq_interview_feedback_session"),)

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    submitted_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    submitted_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overall_agreement_score: Mapped[float] = mapped_column(nullable=False)
    ai_recommendation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    hr_recommendation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recommendation_agreement: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overall_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_evidence_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    false_positive_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    false_negative_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewFeedbackPolicy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_feedback_policies"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="suggested")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    source_feedback_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    summary_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    approved_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_by_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class InterviewFeedbackPolicyAudit(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_feedback_policy_audits"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    policy_id: Mapped[str | None] = mapped_column(
        ForeignKey("interview_feedback_policies.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewFeedbackMemory(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_feedback_memories"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    interview_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    feedback_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("interview_feedback_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    memory_text: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(nullable=False, default=0.5)
    source_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
