"""User schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None


class UserCreate(UserBase):
    """Schema for creating a user."""

    google_id: str | None = None
    role: str = "hr"


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    name: str | None = None
    avatar_url: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """Schema for user response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
