"""Authentication schemas."""

from pydantic import BaseModel, EmailStr

from src.schemas.user import UserResponse


class GoogleTokenRequest(BaseModel):
    """Schema for Google token verification request."""

    token: str


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserWithTokens(BaseModel):
    """Schema for user with tokens."""

    user: UserResponse
    tokens: TokenResponse


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request."""

    refresh_token: str


class GoogleUserInfo(BaseModel):
    """Schema for Google user info."""

    sub: str  # Google ID
    email: EmailStr
    name: str | None = None
    picture: str | None = None
    email_verified: bool = False
