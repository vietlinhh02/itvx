# InterviewX

InterviewX is a multi-service AI recruiting workspace:

- `backend/`: FastAPI API, auth, JD analysis, CV screening, interview orchestration
- `frontend/`: Next.js HR dashboard and candidate join flow
- `worker/`: LiveKit + Gemini realtime interview runtime

The repository can be run in two modes:

- Basic local mode: login, dashboard, JD upload, CV screening
- Full realtime mode: everything above plus live AI interview sessions

## Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL, Google Gemini
- Frontend: Next.js 16, React 19, NextAuth
- Realtime: LiveKit, Gemini realtime/native audio
- Tooling: `uv`, `pnpm`, Docker Compose

## Repository Layout

```text
.
├── backend/        FastAPI app and background jobs
├── frontend/       Next.js app
├── worker/         Realtime interview worker service
├── docs/           Design notes and planning docs
├── docker-compose.yml
└── .env.example
```

## Prerequisites

Install these first:

- Python `3.13+`
- Node.js `20+`
- `pnpm`
- `uv`
- Docker + Docker Compose
- `pdftotext`

`pdftotext` is required for company document parsing. On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y poppler-utils
```

## Environment Files

This repo uses two environment layers in local development:

1. Root `.env`
   Used by the backend and shared runtime scripts.

2. `frontend/.env.local`
   Used by the Next.js app.

Important: the frontend is started from `frontend/`, so it will not reliably use the root `.env` by itself. Put frontend vars in `frontend/.env.local`.

### 1. Create the root `.env`

```bash
cp .env.example .env
```

At minimum for basic local development, review these values in `.env`:

```env
POSTGRES_USER=interviewx
POSTGRES_PASSWORD=interviewx_secret
POSTGRES_DB=interviewx
DATABASE_URL=postgresql://interviewx:interviewx_secret@localhost:5432/interviewx

APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:3001

GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.1-flash-lite-preview
```

Notes:

- In `development`, `local`, and `test`, the backend can derive `JWT_SECRET_KEY` and `WORKER_CALLBACK_SECRET` automatically if they are empty.
- For realtime interview flows, you should still set `WORKER_CALLBACK_SECRET` explicitly when you want every process to share the same value.
- The backend auto-creates tables on startup via `init_db()`. There is no manual Alembic step required for first boot.

### 2. Create `frontend/.env.local`

```bash
cp frontend/.env.example frontend/.env.local
```

Then edit `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
API_URL=http://localhost:8000

AUTH_SECRET=replace-with-a-random-base64-secret
AUTH_GOOGLE_ID=your-google-client-id.apps.googleusercontent.com
AUTH_GOOGLE_SECRET=your-google-client-secret

NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
```

Generate `AUTH_SECRET` with:

```bash
openssl rand -base64 32
```

Notes:

- `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET` should usually match the Google OAuth credentials in the root `.env`.
- `NEXT_PUBLIC_LIVEKIT_URL` is only required for the candidate live interview room.
- If you want backend-generated share links to point somewhere other than `http://localhost:3000`, add this to the root `.env`:

```env
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## Google OAuth Setup

InterviewX uses Google sign-in in the frontend, then exchanges the Google token with the backend.

In Google Cloud Console, configure:

- Authorized JavaScript origin:

```text
http://localhost:3000
```

- Authorized redirect URI:

```text
http://localhost:3000/api/auth/callback/google
```

## Install Dependencies

### Backend

```bash
cd backend
uv sync --extra dev
```

### Worker

```bash
cd worker
uv sync --extra dev
```

### Frontend

```bash
cd frontend
pnpm install
```

## Start the Project

### Step 1. Start PostgreSQL

From the repository root:

```bash
docker compose up -d postgres
```

Check it is healthy:

```bash
docker compose ps
```

### Step 2. Start the backend API

Open terminal 1:

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API root: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- Swagger docs: `http://localhost:8000/docs`

### Step 3. Start the backend background job runner

Open terminal 2:

```bash
cd backend
uv run python -m src.scripts.run_background_jobs
```

This process is needed for background JD analysis and CV screening jobs.

### Step 4. Start the frontend

Open terminal 3:

```bash
cd frontend
pnpm dev
```

Frontend URL:

- App: `http://localhost:3000`

## Full Realtime Interview Setup

You only need this section if you want to publish and run live AI interviews.

### Required extra environment variables

Add these to the root `.env`:

```env
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
GEMINI_API_KEY=your-gemini-api-key
GEMINI_LIVE_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
WORKER_CALLBACK_SECRET=replace-with-a-shared-secret
INTERVIEW_WORKER_SERVICE_URL=http://127.0.0.1:8765
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

Also make sure `frontend/.env.local` contains:

```env
NEXT_PUBLIC_LIVEKIT_URL=wss://your-project.livekit.cloud
```

### Start the realtime worker service

Open terminal 4:

```bash
bash backend/src/scripts/run_interview_worker_service.sh
```

What this does:

- Starts the worker HTTP service from `worker/`
- Waits for backend dispatch requests at `http://127.0.0.1:8765`
- Spawns per-session realtime workers when a new interview is published

## Recommended Local Startup Order

If you want the full project running locally, use this order:

1. `docker compose up -d postgres`
2. backend API
3. backend background jobs
4. worker service, if testing live interviews
5. frontend

## First-Time Verification Checklist

### Basic mode

1. Open `http://localhost:3000/login`
2. Sign in with Google
3. Confirm you land on the dashboard
4. Upload one JD
5. Wait for JD analysis to finish
6. Upload one CV against that JD
7. Wait for CV screening to finish
8. Open the screening detail page

### Realtime mode

1. Complete the basic mode checklist
2. Open one completed screening
3. Publish an interview session
4. Open the generated share link in another browser profile
5. Join with microphone permission enabled
6. Confirm the AI asks the opening question
7. Answer once and confirm the AI responds
8. Refresh the HR dashboard and confirm transcript turns appear

## Useful Commands

### Backend

```bash
cd backend
uv run pytest
```

### Worker

```bash
cd worker
uv run pytest
```

### Frontend

```bash
cd frontend
pnpm lint
pnpm type-check
pnpm test
```

## Troubleshooting

### Frontend says backend is not configured

Check `frontend/.env.local` contains:

```env
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then restart `pnpm dev`.

### Google login redirects incorrectly or fails

Check all of these:

- `AUTH_GOOGLE_ID` and `AUTH_GOOGLE_SECRET` are set in `frontend/.env.local`
- `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set in the root `.env`
- Google Cloud redirect URI is exactly:

```text
http://localhost:3000/api/auth/callback/google
```

### JD/CV upload works but jobs never finish

The background job runner is probably not running. Start:

```bash
cd backend
uv run python -m src.scripts.run_background_jobs
```

### Interview publish works but live session never starts

Check all of these:

- the worker service is running
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `GEMINI_API_KEY`, and `WORKER_CALLBACK_SECRET` are set
- the backend can reach `INTERVIEW_WORKER_SERVICE_URL`

### Candidate join page loads but room connection fails

Check:

- `NEXT_PUBLIC_LIVEKIT_URL` in `frontend/.env.local`
- LiveKit credentials in the root `.env`
- browser microphone permission

### Company document upload succeeds but parsing fails

Make sure `pdftotext` is installed:

```bash
pdftotext -v
```

## Notes for Contributors

- Do not commit `.env`, `frontend/.env.local`, or uploaded files in `storage/`
- The backend and worker both target Python `3.13+`
- The repo currently uses PostgreSQL locally via Docker Compose
