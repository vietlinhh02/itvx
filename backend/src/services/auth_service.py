"""Authentication service."""

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.schemas.auth import GoogleUserInfo, TokenResponse, UserWithTokens
from src.services.jwt_service import jwt_service


class AuthService:
    """Service for handling authentication."""

    def __init__(self) -> None:
        """Initialize auth service with Google client ID."""
        self.google_client_id = settings.google_client_id

    async def verify_google_token(self, token: str) -> GoogleUserInfo | None:
        """Verify Google ID token and return user info."""
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                self.google_client_id,
            )

            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                return None

            return GoogleUserInfo(
                sub=idinfo["sub"],
                email=idinfo["email"],
                name=idinfo.get("name"),
                picture=idinfo.get("picture"),
                email_verified=idinfo.get("email_verified", False),
            )
        except Exception:
            return None

    async def get_or_create_user(self, db: AsyncSession, google_info: GoogleUserInfo) -> User:
        """Get existing user or create new one from Google info."""
        # Try to find by Google ID first
        result = await db.execute(select(User).where(User.google_id == google_info.sub))
        user = result.scalar_one_or_none()

        if user:
            return user

        # Try to find by email
        result = await db.execute(select(User).where(User.email == google_info.email))
        user = result.scalar_one_or_none()

        if user:
            # Link Google account to existing user
            user.google_id = google_info.sub
            if google_info.picture:
                user.avatar_url = google_info.picture
            await db.commit()
            return user

        # Create new user
        new_user = User(
            email=google_info.email,
            name=google_info.name,
            google_id=google_info.sub,
            avatar_url=google_info.picture,
            role="hr",
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    async def authenticate_with_google(self, db: AsyncSession, token: str) -> UserWithTokens | None:
        """Authenticate user with Google token."""
        # Verify Google token
        google_info = await self.verify_google_token(token)
        if not google_info:
            return None

        # Get or create user
        user = await self.get_or_create_user(db, google_info)

        if not user.is_active:
            return None

        # Generate tokens
        access_token = jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        refresh_token = jwt_service.create_refresh_token(user_id=user.id)

        return UserWithTokens(
            user=user,
            tokens=TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=jwt_service.get_token_expiry("access"),
            ),
        )

    async def refresh_access_token(
        self, db: AsyncSession, refresh_token: str
    ) -> UserWithTokens | None:
        """Refresh access token using refresh token."""
        payload = jwt_service.decode_token(refresh_token)

        if not payload or payload.get("type") != "refresh":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        # Get user from database
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return None

        # Generate new tokens
        new_access_token = jwt_service.create_access_token(
            user_id=user.id,
            email=user.email,
            role=user.role,
        )
        new_refresh_token = jwt_service.create_refresh_token(user_id=user.id)

        return UserWithTokens(
            user=user,
            tokens=TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=jwt_service.get_token_expiry("access"),
            ),
        )


auth_service = AuthService()
