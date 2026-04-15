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
