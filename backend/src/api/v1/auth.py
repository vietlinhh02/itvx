"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.database import get_db
from src.models.user import User
from src.schemas.auth import (
    GoogleTokenRequest,
    RefreshTokenRequest,
    UserWithTokens,
)
from src.schemas.user import UserResponse
from src.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/google", response_model=UserWithTokens)
async def login_with_google(
    request: GoogleTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> UserWithTokens:
    """Authenticate with Google OAuth token."""
    result = await auth_service.authenticate_with_google(db, request.token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    return result


@router.post("/refresh", response_model=UserWithTokens)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> UserWithTokens:
    """Refresh access token."""
    result = await auth_service.refresh_access_token(db, request.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    return result


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated user info."""
    return current_user
