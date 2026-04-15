"""JWT token service."""

from datetime import datetime, timedelta

from jose import JWTError, jwt

from src.config import settings


class JWTService:
    """Service for handling JWT tokens."""

    def __init__(self) -> None:
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.access_expire = timedelta(minutes=settings.access_token_expire_minutes)
        self.refresh_expire = timedelta(days=settings.refresh_token_expire_days)

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create access token."""
        expire = datetime.utcnow() + self.access_expire
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """Create refresh token."""
        expire = datetime.utcnow() + self.refresh_expire
        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict | None:
        """Decode and validate token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def get_token_expiry(self, token_type: str = "access") -> int:
        """Get token expiry in seconds."""
        if token_type == "access":
            return int(self.access_expire.total_seconds())
        return int(self.refresh_expire.total_seconds())


jwt_service = JWTService()
