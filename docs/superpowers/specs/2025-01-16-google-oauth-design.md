# InterviewX - Google OAuth Implementation Design

**Date**: 2025-01-16  
**Status**: Approved  
**Scope**: Authentication system setup for InterviewX Multi-Agent Interview Platform

---

## 1. Executive Summary

InterviewX là hệ thống Multi-Agent AI gồm 5 agent chuyên biệt (Orchestrator, CV Screener, Interviewer, Evaluator, Scheduler) tự phối hợp để tuyển dụng từ đầu đến cuối. Document này mô tả design cho Google OAuth authentication - phase đầu tiên của dự án.

**Key Decisions**:
- Monorepo structure: Backend Python + Frontend Next.js trong cùng repo
- FastAPI + LangChain cho backend
- Next.js 16 với NextAuth.js v5 cho frontend
- PostgreSQL chạy via Docker Compose
- Chỉ HR/Admin dùng Google OAuth (ứng viên không cần login)

---

## 2. Architecture Overview

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Client                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Next.js 16 (Frontend)                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │  │
│  │  │   Auth UI   │  │  Dashboard  │  │   Components  │  │  │
│  │  └─────────────┘  └─────────────┘  └───────────────┘  │  │
│  │           │                    │                      │  │
│  │  ┌────────┴────────────────────┴──────────────────┐   │  │
│  │  │              NextAuth.js v5                    │   │  │
│  │  │         (Google OAuth Provider)                │   │  │
│  │  └──────────────────┬─────────────────────────────┘   │  │
│  └─────────────────────┼─────────────────────────────────┘  │
│                        │ JWT Token                           │
│                        ▼                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │            FastAPI + LangChain (Backend)              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐  │  │
│  │  │ Auth API    │  │  Agents     │  │  External     │  │  │
│  │  │ /auth/*     │  │  /agents/*  │  │  Integrations │  │  │
│  │  └─────────────┘  └─────────────┘  └───────────────┘  │  │
│  │           │              │                             │  │
│  │  ┌────────┴───────────────┴──────────┐                │  │
│  │  │      PostgreSQL (Docker)          │                │  │
│  │  │  ┌────────┐ ┌────────┐ ┌────────┐ │                │  │
│  │  │  │ Users  │ │Configs │ │Sessions│ │                │  │
│  │  │  └────────┘ └────────┘ └────────┘ │                │  │
│  │  └───────────────────────────────────┘                │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Project Structure

```
interviewx/
├── docker-compose.yml              # PostgreSQL + services
├── .env.example                    # Environment variables template
├── backend/
│   ├── pyproject.toml              # UV dependencies
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Settings (Pydantic)
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependencies (auth)
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py       # API v1 router
│   │   │       ├── auth.py         # Auth endpoints
│   │   │       └── users.py        # User endpoints
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # SQLAlchemy base
│   │   │   └── user.py             # User model
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # Auth schemas
│   │   │   └── user.py             # User schemas
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py     # Auth business logic
│   │   │   └── jwt_service.py      # JWT handling
│   │   └── agents/                 # LangChain agents (future)
│   │       ├── __init__.py
│   │       ├── orchestrator.py
│   │       ├── cv_screener.py
│   │       ├── interviewer.py
│   │       ├── evaluator.py
│   │       └── scheduler.py
│   └── tests/
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tsconfig.json
    ├── Dockerfile
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx          # Root layout
    │   │   ├── page.tsx            # Landing page
    │   │   ├── (auth)/
    │   │   │   ├── login/
    │   │   │   │   └── page.tsx
    │   │   │   └── callback/
    │   │   │       └── page.tsx
    │   │   └── (dashboard)/
    │   │       ├── layout.tsx
    │   │       └── page.tsx
    │   ├── lib/
    │   │   ├── auth.ts             # NextAuth config
    │   │   └── api.ts              # API client
    │   └── components/
    │       └── ui/                 # UI components
    └── public/
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.13 |
| Package Manager | UV | Latest |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0+ |
| Migrations | Alembic | Latest |
| Auth | python-jose, passlib | Latest |
| Agents | LangChain | 0.3+ |
| Database | PostgreSQL | 16 |

### 3.2 Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | Next.js | 16 |
| Language | TypeScript | 5.7+ |
| Auth | NextAuth.js | 5 (beta) |
| Styling | Tailwind CSS | 4 |
| Components | shadcn/ui | Latest |

### 3.3 Infrastructure

| Component | Technology |
|-----------|-----------|
| Container | Docker |
| Orchestration | Docker Compose |
| Database | PostgreSQL 16 |

---

## 4. Authentication Flow

### 4.1 Google OAuth Flow

1. **Initiate Login**: User clicks "Login with Google"
2. **Google OAuth**: NextAuth redirects to Google OAuth consent screen
3. **Callback**: Google redirects ve `/api/auth/callback/google`
4. **Token Exchange**: NextAuth lay Google access_token
5. **Backend Verification**: Frontend gui Google token → Backend `/api/v1/auth/google`
6. **User Lookup/Create**: Backend verify token, tim hoac tao user trong DB
7. **JWT Generation**: Backend tao JWT tokens (access + refresh)
8. **Session**: Frontend luu JWT, dung cho moi API calls sau nay

### 4.2 Token Strategy

**Access Token**:
- JWT voi secret key
- Expiration: 15 minutes
- Chua: user_id, email, role
- Dung trong Authorization header: `Bearer <token>`

**Refresh Token**:
- JWT rieng biet voi longer expiration
- Expiration: 7 days
- Luu trong httpOnly cookie
- Dung de refresh access token khi het han

---

## 5. Database Schema

### 5.1 Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    google_id VARCHAR(255) UNIQUE,
    avatar_url TEXT,
    role VARCHAR(50) DEFAULT 'hr',  -- 'admin', 'hr'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_google_id ON users(google_id);
```

### 5.2 Refresh Tokens Table

```sql
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
```

---

## 6. API Endpoints

### 6.1 Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/google` | Verify Google token, create/login user |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Revoke refresh token |
| GET | `/api/v1/auth/me` | Get current user info |

### 6.2 Users

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users` | List all users (admin only) |
| GET | `/api/v1/users/{id}` | Get user by ID |
| PATCH | `/api/v1/users/{id}` | Update user |
| DELETE | `/api/v1/users/{id}` | Delete user (admin only) |

---

## 7. Environment Variables

### 7.1 Backend (.env)

```
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/interviewx

# JWT
JWT_SECRET_KEY=your-super-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:3000/api/auth/callback/google

# App
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000
```

### 7.2 Frontend (.env.local)

```
# NextAuth
AUTH_SECRET=your-nextauth-secret
AUTH_GOOGLE_ID=your-google-client-id
AUTH_GOOGLE_SECRET=your-google-client-secret

# API
NEXT_PUBLIC_API_URL=http://localhost:8000
API_URL=http://localhost:8000
```

---

## 8. Success Criteria

- [ ] User co the dang nhap bang Google OAuth
- [ ] JWT tokens duoc tao va quan ly dung cach
- [ ] Protected routes hoat dong (ca frontend va backend)
- [ ] Refresh token mechanism hoat dong
- [ ] User data duoc luu trong PostgreSQL
- [ ] Docker Compose chay PostgreSQL thanh cong

---

## 9. Out of Scope

- Interview agents implementation (phase sau)
- Firestore integration (da co)
- LiveKit integration
- Email/SMTP integration
- CV upload functionality
- Dashboard features beyond basic auth

---

## 10. Future Considerations

- Redis cho session caching
- Celery cho async tasks
- Agent workflow implementation
- Real-time features via WebSocket
- Audit logging
- Rate limiting

---

**Approved by**: User  
**Date**: 2025-01-16
