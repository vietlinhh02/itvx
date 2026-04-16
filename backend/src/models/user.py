"""User model."""

from typing import override

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """User model for HR/Admin accounts."""

    __tablename__: str = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(50), default="hr")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    @override
    def __repr__(self) -> str:
        """Return a compact debug representation for the user."""
        return f"<User {self.email}>"
