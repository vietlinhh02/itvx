# Google OAuth Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Setup complete Google OAuth authentication system voi FastAPI backend va Next.js 16 frontend, including PostgreSQL via Docker Compose.

**Architecture:** Monorepo structure voi backend Python (FastAPI, SQLAlchemy, JWT) va frontend Next.js (NextAuth.js v5). Backend xu ly Google token verification va JWT generation, frontend quan ly OAuth flow va session storage.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Docker Compose, Next.js 16, NextAuth.js v5, TypeScript

---

## File Structure Overview

```
interviewx/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── auth.py
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   └── user.py
│   │   ├── schemas/
│   │   │   ├── auth.py
│   │   │   └── user.py
│   │   └── services/
│   │       ├── auth_service.py
│   │       └── jwt_service.py
│   └── tests/
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tsconfig.json
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx
    │   │   ├── page.tsx
    │   │   ├── (auth)/
    │   │   │   └── login/
    │   │   │       └── page.tsx
    │   │   └── (dashboard)/
    │   │       ├── layout.tsx
    │   │       └── page.tsx
    │   ├── lib/
    │   │   └── auth.ts
    │   └── middleware.ts
    └── .env.local
```

---

## Phase 1: Infrastructure Setup

### Task 1: Docker Compose va PostgreSQL

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1.1: Create docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    container_name: interviewx-db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-interviewx}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-interviewx_secret}
      POSTGRES_DB: ${POSTGRES_DB:-interviewx}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-interviewx}"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

- [ ] **Step 1.2: Create .env.example**

```bash
# Database
POSTGRES_USER=interviewx
POSTGRES_PASSWORD=interviewx_secret
POSTGRES_DB=interviewx
DATABASE_URL=postgresql://interviewx:interviewx_secret@localhost:5432/interviewx

# JWT
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# App
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_SECRET=your-nextauth-secret-generate-with-openssl-rand-base64-32
AUTH_GOOGLE_ID=your-google-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-google-client-secret
```

- [ ] **Step 1.3: Start PostgreSQL**

```bash
docker-compose up -d
```

Expected output:
```
[+] Running 2/2
 ✔ Network interviewx_default     Created
 ✔ Container interviewx-db        Started
```

- [ ] **Step 1.4: Verify database is running**

```bash
docker-compose ps
```

Expected output:
```
NAME           IMAGE                STATUS
interviewx-db  postgres:16-alpine   Up 5 seconds (healthy)
```

- [ ] **Step 1.5: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "infra: add docker-compose with PostgreSQL"
```

---

## Phase 2: Backend Setup (FastAPI)

### Task 2: Project Structure va Dependencies

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/__init__.py`
- Create: `backend/README.md`

- [ ] **Step 2.1: Create backend directory structure**

```bash
mkdir -p backend/src/{api/v1,models,schemas,services,agents}
mkdir -p backend/tests
```

- [ ] **Step 2.2: Create backend/pyproject.toml**

```toml
[project]
name = "interviewx-backend"
version = "0.1.0"
description = "InterviewX Multi-Agent Interview Platform Backend"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "google-auth>=2.37.0",
    "langchain>=0.3.0",
    "langchain-google-genai>=2.0.0",
    "python-multipart>=0.0.20",
    "httpx>=0.28.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "ty>=0.9.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.ruff]
target-version = "py313"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "D", "UP", "B", "C4", "SIM"]
ignore = ["D100", "D104"]

[tool.ty]
python-version = "3.13"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2.3: Create backend/src/__init__.py**

```python
"""InterviewX Backend."""

__version__ = "0.1.0"
```

- [ ] **Step 2.4: Install dependencies with UV**

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
```

Expected output:
```
Using Python 3.13.x
Creating virtual environment
Installed ... packages
```

- [ ] **Step 2.5: Commit**

```bash
cd ..
git add backend/
git commit -m "chore(backend): setup project structure and dependencies"
```

---

### Task 3: Configuration (Pydantic Settings)

**Files:**
- Create: `backend/src/config.py`

- [ ] **Step 3.1: Create backend/src/config.py**

```python
"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql://interviewx:interviewx_secret@localhost:5432/interviewx"

    # JWT
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
```

- [ ] **Step 3.2: Commit**

```bash
git add backend/src/config.py
git commit -m "feat(config): add pydantic settings"
```

---

### Task 4: Database Models (SQLAlchemy)

**Files:**
- Create: `backend/src/models/base.py`
- Create: `backend/src/models/__init__.py`
- Create: `backend/src/models/user.py`

- [ ] **Step 4.1: Create backend/src/models/base.py**

```python
"""SQLAlchemy base configuration."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class TimestampMixin:
    """Mixin for created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
```

- [ ] **Step 4.2: Create backend/src/models/user.py**

```python
"""User model."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    """User model for HR/Admin accounts."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(50), default="hr")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
```

- [ ] **Step 4.3: Create backend/src/models/__init__.py**

```python
"""Database models."""

from src.models.base import Base
from src.models.user import User

__all__ = ["Base", "User"]
```

- [ ] **Step 4.4: Commit**

```bash
git add backend/src/models/
git commit -m "feat(models): add User model with SQLAlchemy"
```

---

### Task 5: Database Connection va Engine

**Files:**
- Create: `backend/src/database.py`

- [ ] **Step 5.1: Create backend/src/database.py**

```python
"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from src.config import settings

# Convert postgresql:// to postgresql+asyncpg://
DATABASE_URL = settings.database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.app_env == "development",
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

- [ ] **Step 5.2: Update backend/src/models/base.py to use same Base**

```python
"""SQLAlchemy base configuration."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class UUIDMixin:
    """Mixin for UUID primary key."""

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )


class TimestampMixin:
    """Mixin for created/updated timestamps."""

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
```

- [ ] **Step 5.3: Commit**

```bash
git add backend/src/database.py backend/src/models/base.py
git commit -m "feat(database): add async database connection"
```

---

### Task 6: Pydantic Schemas

**Files:**
- Create: `backend/src/schemas/user.py`
- Create: `backend/src/schemas/auth.py`
- Create: `backend/src/schemas/__init__.py`

- [ ] **Step 6.1: Create backend/src/schemas/user.py**

```python
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
```

- [ ] **Step 6.2: Create backend/src/schemas/auth.py**

```python
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
```

- [ ] **Step 6.3: Create backend/src/schemas/__init__.py**

```python
"""Schemas."""

from src.schemas.auth import (
    GoogleTokenRequest,
    GoogleUserInfo,
    RefreshTokenRequest,
    TokenResponse,
    UserWithTokens,
)
from src.schemas.user import UserCreate, UserResponse, UserUpdate

__all__ = [
    "GoogleTokenRequest",
    "GoogleUserInfo",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserWithTokens",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
]
```

- [ ] **Step 6.4: Commit**

```bash
git add backend/src/schemas/
git commit -m "feat(schemas): add user and auth pydantic schemas"
```

---

### Task 7: JWT Service

**Files:**
- Create: `backend/src/services/jwt_service.py`
- Create: `backend/src/services/__init__.py`

- [ ] **Step 7.1: Create backend/src/services/jwt_service.py**

```python
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
```

- [ ] **Step 7.2: Create backend/src/services/__init__.py**

```python
"""Services."""

from src.services.jwt_service import JWTService, jwt_service

__all__ = ["JWTService", "jwt_service"]
```

- [ ] **Step 7.3: Commit**

```bash
git add backend/src/services/
git commit -m "feat(services): add JWT service"
```

---

### Task 8: Auth Service (Google OAuth)

**Files:**
- Create: `backend/src/services/auth_service.py`

- [ ] **Step 8.1: Create backend/src/services/auth_service.py**

```python
"""Authentication service."""

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.user import User
from src.schemas.auth import GoogleUserInfo, UserWithTokens
from src.schemas.user import UserCreate
from src.services.jwt_service import jwt_service


class AuthService:
    """Service for handling authentication."""

    def __init__(self) -> None:
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

    async def get_or_create_user(
        self, db: AsyncSession, google_info: GoogleUserInfo
    ) -> User:
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

    async def authenticate_with_google(
        self, db: AsyncSession, token: str
    ) -> UserWithTokens | None:
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
            user=user,  # type: ignore
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
            user=user,  # type: ignore
            tokens=TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=jwt_service.get_token_expiry("access"),
            ),
        )


# Need to import here to avoid circular import
from src.schemas.auth import TokenResponse

auth_service = AuthService()
```

- [ ] **Step 8.2: Update backend/src/services/__init__.py**

```python
"""Services."""

from src.services.auth_service import AuthService, auth_service
from src.services.jwt_service import JWTService, jwt_service

__all__ = ["AuthService", "auth_service", "JWTService", "jwt_service"]
```

- [ ] **Step 8.3: Commit**

```bash
git add backend/src/services/
git commit -m "feat(services): add Google OAuth authentication service"
```

---

### Task 9: API Dependencies (Auth)

**Files:**
- Create: `backend/src/api/deps.py`

- [ ] **Step 9.1: Create backend/src/api/deps.py**

```python
"""API dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.user import User
from src.schemas.user import UserResponse
from src.services.jwt_service import jwt_service

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token."""
    token = credentials.credentials
    payload = jwt_service.decode_token(token)

    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from sqlalchemy import select

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
```

- [ ] **Step 9.2: Commit**

```bash
git add backend/src/api/deps.py
git commit -m "feat(api): add authentication dependencies"
```

---

### Task 10: Auth API Endpoints

**Files:**
- Create: `backend/src/api/v1/auth.py`
- Create: `backend/src/api/v1/__init__.py`

- [ ] **Step 10.1: Create backend/src/api/v1/auth.py**

```python
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
```

- [ ] **Step 10.2: Create backend/src/api/v1/__init__.py**

```python
"""API v1 endpoints."""

from src.api.v1.auth import router as auth_router

__all__ = ["auth_router"]
```

- [ ] **Step 10.3: Commit**

```bash
git add backend/src/api/v1/
git commit -m "feat(api): add authentication endpoints"
```

---

### Task 11: API Router va Main App

**Files:**
- Create: `backend/src/api/v1/router.py`
- Modify: `backend/src/api/__init__.py`
- Create: `backend/src/main.py`

- [ ] **Step 11.1: Create backend/src/api/v1/router.py**

```python
"""API v1 router."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
```

- [ ] **Step 11.2: Create backend/src/api/__init__.py**

```python
"""API module."""

from src.api.v1.router import api_router

__all__ = ["api_router"]
```

- [ ] **Step 11.3: Create backend/src/main.py**

```python
"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import api_router
from src.config import settings
from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title="InterviewX API",
    description="Multi-Agent Interview Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env == "development",
    )
```

- [ ] **Step 11.4: Test backend startup**

```bash
cd backend
source .venv/bin/activate
cp ../.env.example .env
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Will watch for changes in these directories: ['/.../backend/src']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

- [ ] **Step 11.5: Test health endpoint**

Open new terminal:
```bash
curl http://localhost:8000/health
```

Expected output:
```json
{"status":"healthy"}
```

- [ ] **Step 11.6: Commit**

```bash
git add backend/src/main.py backend/src/api/
git commit -m "feat(api): add main FastAPI application"
```

---

## Phase 3: Frontend Setup (Next.js 16)

### Task 12: Next.js Project Initialization

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.js`

- [ ] **Step 12.1: Create frontend directory and package.json**

```bash
mkdir -p frontend/src/{app,lib,components}
```

```json
{
  "name": "interviewx-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "next-auth": "5.0.0-beta.25",
    "@auth/core": "0.37.0"
  },
  "devDependencies": {
    "typescript": "^5.7.0",
    "@types/node": "^22.10.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.5.0"
  }
}
```

- [ ] **Step 12.2: Create frontend/tsconfig.json**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 12.3: Create frontend/next.config.js**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    typedRoutes: true,
  },
}

module.exports = nextConfig
```

- [ ] **Step 12.4: Install frontend dependencies**

```bash
cd frontend
pnpm install
```

- [ ] **Step 12.5: Commit**

```bash
cd ..
git add frontend/package.json frontend/tsconfig.json frontend/next.config.js
git commit -m "chore(frontend): initialize Next.js 16 project"
```

---

### Task 13: NextAuth Configuration

**Files:**
- Create: `frontend/src/lib/auth.ts`
- Create: `frontend/src/app/api/auth/[...nextauth]/route.ts`

- [ ] **Step 13.1: Create frontend/src/lib/auth.ts**

```typescript
import NextAuth from "next-auth"
import Google from "next-auth/providers/google"

export const {
  handlers: { GET, POST },
  auth,
  signIn,
  signOut,
} = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },
  callbacks: {
    async jwt({ token, account, user }) {
      // Initial sign in
      if (account && user) {
        try {
          // Exchange Google token for our backend tokens
          const response = await fetch(
            `${process.env.API_URL}/api/v1/auth/google`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ token: account.id_token }),
            }
          )

          if (!response.ok) {
            throw new Error("Failed to authenticate with backend")
          }

          const data = await response.json()

          return {
            ...token,
            accessToken: data.tokens.access_token,
            refreshToken: data.tokens.refresh_token,
            expiresIn: data.tokens.expires_in,
            user: data.user,
          }
        } catch (error) {
          console.error("Auth error:", error)
          return token
        }
      }

      // Return previous token if not expired
      const tokenExpiry = (token as any).expiry as number
      if (Date.now() < tokenExpiry) {
        return token
      }

      // Refresh token if expired
      try {
        const response = await fetch(
          `${process.env.API_URL}/api/v1/auth/refresh`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: (token as any).refreshToken }),
          }
        )

        if (!response.ok) {
          throw new Error("Failed to refresh token")
        }

        const data = await response.json()

        return {
          ...token,
          accessToken: data.tokens.access_token,
          refreshToken: data.tokens.refresh_token,
          expiresIn: data.tokens.expires_in,
          expiry: Date.now() + data.tokens.expires_in * 1000,
        }
      } catch (error) {
        console.error("Token refresh error:", error)
        return { ...token, error: "RefreshTokenError" }
      }
    },
    async session({ session, token }) {
      session.accessToken = (token as any).accessToken
      session.refreshToken = (token as any).refreshToken
      session.user = (token as any).user
      session.error = (token as any).error
      return session
    },
  },
  pages: {
    signIn: "/login",
    error: "/login",
  },
})

// Type augmentation
declare module "next-auth" {
  interface Session {
    accessToken?: string
    refreshToken?: string
    error?: string
    user?: {
      id: string
      email: string
      name: string | null
      role: string
      avatar_url: string | null
    }
  }

  interface JWT {
    accessToken?: string
    refreshToken?: string
    expiresIn?: number
    expiry?: number
    user?: any
    error?: string
  }
}
```

- [ ] **Step 13.2: Create frontend/src/app/api/auth/[...nextauth]/route.ts**

```typescript
export { GET, POST } from "@/lib/auth"
```

- [ ] **Step 13.3: Create frontend/src/app/layout.tsx**

```typescript
import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "InterviewX - AI Interview Platform",
  description: "Multi-Agent AI Interview System",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  )
}
```

- [ ] **Step 13.4: Create frontend/src/app/globals.css**

```css
* {
  box-sizing: border-box;
  padding: 0;
  margin: 0;
}

html,
body {
  max-width: 100vw;
  overflow-x: hidden;
}
```

- [ ] **Step 13.5: Create frontend/.env.local from example**

```bash
cp .env.example frontend/.env.local
```

Edit `frontend/.env.local` to keep only frontend variables:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_SECRET=your-nextauth-secret-generate-with-openssl-rand-base64-32
AUTH_GOOGLE_ID=your-google-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-google-client-secret
```

- [ ] **Step 13.6: Commit**

```bash
git add frontend/src/lib/auth.ts frontend/src/app/
git commit -m "feat(auth): add NextAuth configuration with Google OAuth"
```

---

### Task 14: Auth Pages

**Files:**
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/page.tsx`

- [ ] **Step 14.1: Create frontend/src/app/login/page.tsx**

```typescript
import { signIn } from "@/lib/auth"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-900">InterviewX</h1>
          <p className="mt-2 text-gray-600">Sign in to access your dashboard</p>
        </div>

        <form
          action={async () => {
            "use server"
            await signIn("google", { redirectTo: "/dashboard" })
          }}
        >
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-3 px-4 py-3 border border-gray-300 rounded-lg shadow-sm text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
          >
            <svg className="w-5 h-5" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="#34A853"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="#FBBC05"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="#EA4335"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Continue with Google
          </button>
        </form>

        <p className="text-center text-sm text-gray-500">
          Only authorized HR and Admin accounts can access this system.
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 14.2: Create frontend/src/app/page.tsx**

```typescript
import { redirect } from "next/navigation"
import { auth } from "@/lib/auth"

export default async function HomePage() {
  const session = await auth()

  if (session) {
    redirect("/dashboard")
  }

  redirect("/login")
}
```

- [ ] **Step 14.3: Create frontend/src/middleware.ts**

```typescript
export { auth as middleware } from "@/lib/auth"

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|login).*)"],
}
```

- [ ] **Step 14.4: Commit**

```bash
git add frontend/src/app/login/ frontend/src/app/page.tsx frontend/src/middleware.ts
git commit -m "feat(pages): add login page and auth middleware"
```

---

### Task 15: Dashboard Page

**Files:**
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/dashboard/layout.tsx`

- [ ] **Step 15.1: Create frontend/src/app/dashboard/layout.tsx**

```typescript
import { auth } from "@/lib/auth"
import { redirect } from "next/navigation"

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await auth()

  if (!session) {
    redirect("/login")
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-semibold">InterviewX Dashboard</h1>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                {session.user?.name || session.user?.email}
              </span>
              <form
                action={async () => {
                  "use server"
                  const { signOut } = await import("@/lib/auth")
                  await signOut({ redirectTo: "/login" })
                }}
              >
                <button
                  type="submit"
                  className="text-sm text-red-600 hover:text-red-800"
                >
                  Sign out
                </button>
              </form>
            </div>
          </div>
        </div>
      </header>
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
```

- [ ] **Step 15.2: Create frontend/src/app/dashboard/page.tsx**

```typescript
import { auth } from "@/lib/auth"

export default async function DashboardPage() {
  const session = await auth()

  return (
    <div className="space-y-6">
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">
          Welcome to InterviewX
        </h2>
        <p className="text-gray-600">
          This is your AI-powered interview management dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Interviews</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">0</p>
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-500">Pending Reviews</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">0</p>
        </div>
        <div className="bg-white shadow rounded-lg p-6">
          <h3 className="text-sm font-medium text-gray-500">Active Jobs</h3>
          <p className="mt-2 text-3xl font-bold text-gray-900">0</p>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Recent Activity
        </h3>
        <p className="text-gray-500">No recent activity.</p>
      </div>

      {process.env.NODE_ENV === "development" && (
        <div className="bg-gray-100 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Debug Info</h4>
          <pre className="text-xs text-gray-600 overflow-auto">
            {JSON.stringify(session, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 15.3: Commit**

```bash
git add frontend/src/app/dashboard/
git commit -m "feat(dashboard): add dashboard layout and page"
```

---

## Phase 4: Testing Integration

### Task 16: Test Full Authentication Flow

**Files:**
- Modify: `.env.example`

- [ ] **Step 16.1: Update .env.example with complete config**

```bash
# Database
POSTGRES_USER=interviewx
POSTGRES_PASSWORD=interviewx_secret
POSTGRES_DB=interviewx
DATABASE_URL=postgresql://interviewx:interviewx_secret@localhost:5432/interviewx

# JWT (generate with: openssl rand -base64 32)
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth - Get from https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

# App
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
API_URL=http://localhost:8000
AUTH_SECRET=your-nextauth-secret-generate-with-openssl-rand-base64-32
AUTH_GOOGLE_ID=your-google-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-google-client-secret
```

- [ ] **Step 16.2: Create setup instructions in README.md**

```markdown
# InterviewX

Multi-Agent AI Interview Platform

## Setup

### 1. Environment Variables

```bash
cp .env.example .env
```

Fill in your Google OAuth credentials from https://console.cloud.google.com/apis/credentials

### 2. Start Database

```bash
docker-compose up -d
```

### 3. Start Backend

```bash
cd backend
uv venv
uv pip install -e ".[dev]"
source .venv/bin/activate
uvicorn src.main:app --reload
```

Backend runs at http://localhost:8000
API docs at http://localhost:8000/docs

### 4. Start Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Frontend runs at http://localhost:3000

### 5. Test Authentication

1. Open http://localhost:3000
2. Click "Continue with Google"
3. Complete OAuth flow
4. You should be redirected to dashboard

## Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: Next.js 16 + NextAuth.js v5
- **Auth**: Google OAuth + JWT tokens
```

- [ ] **Step 16.3: Commit final changes**

```bash
git add .env.example README.md
git commit -m "docs: add setup instructions and complete env example"
```

---

## Summary

This implementation plan creates a complete Google OAuth authentication system with:

### Backend (FastAPI)
- PostgreSQL database via Docker Compose
- SQLAlchemy async models
- JWT token generation and validation
- Google OAuth token verification
- Protected API endpoints

### Frontend (Next.js 16)
- NextAuth.js v5 with Google provider
- JWT session management with refresh tokens
- Login page with Google button
- Protected dashboard with middleware
- Automatic token refresh

### Key Files Created
- `docker-compose.yml` - PostgreSQL container
- `backend/src/main.py` - FastAPI app
- `backend/src/api/v1/auth.py` - Auth endpoints
- `frontend/src/lib/auth.ts` - NextAuth config
- `frontend/src/app/login/page.tsx` - Login UI
- `frontend/src/app/dashboard/page.tsx` - Dashboard

### Environment Setup Required
1. Google OAuth credentials from Google Cloud Console
2. Copy `.env.example` to `.env` and fill in values
3. Run `docker-compose up -d` for database
4. Start backend and frontend

Total estimated time: 2-3 hours
