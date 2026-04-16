"""SQLAlchemy base configuration."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


def utc_naive_now(_: object | None = None) -> datetime:
    """Return the current UTC time as a naive datetime for DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    """Mixin for created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(default=utc_naive_now)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_naive_now,
        onupdate=utc_naive_now,
    )
