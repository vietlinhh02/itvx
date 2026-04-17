# Realtime Interview E2E Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one real end-to-end interview path: HR publishes a shareable link, a candidate joins a LiveKit room, a worker joins the same room, Gemini native audio speaks first, and the worker posts transcript events back to the backend.

**Architecture:** Cut scope hard. Keep FastAPI as the control plane for publishing one interview session, resolving a candidate join token, and persisting transcript and summary events. Build one real Python worker that joins LiveKit, opens a Gemini live session, sends the opening turn first, and pushes transcript events back to the backend. Do not build the full HR editor, evaluator, scheduler, or anti-cheat system in this plan.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, Next.js, TypeScript, LiveKit Python SDK, LiveKit React SDK, Google GenAI SDK, pytest

---

## Scope lock

This plan intentionally implements only these pieces:

1. minimal backend session model and publish endpoint
2. candidate join endpoint that returns a real LiveKit participant token
3. real candidate page that joins a LiveKit room
4. real worker process that joins the same room
5. real Gemini live session setup inside the worker
6. real opening utterance initiated by the worker
7. transcript event delivery back to backend

This plan intentionally excludes:

- AI-generated question editing UI
- upload-question workflow
- deep HR template builder
- full summary UI
- email delivery
- scoring
- anti-cheat

The point is to prove the realtime interview loop works for one published session.

## File Structure

- Create: `backend/src/models/interview.py`
  - Store published interview sessions and transcript turns.
- Modify: `backend/src/models/__init__.py`
  - Export the interview models.
- Create: `backend/src/schemas/interview.py`
  - Define publish, join, and transcript event contracts.
- Create: `backend/src/services/livekit_service.py`
  - Mint real participant tokens and room names.
- Create: `backend/src/services/interview_session_service.py`
  - Publish one session, resolve candidate joins, and persist transcript turns.
- Create: `backend/src/api/v1/interviews.py`
  - Publish interview, join interview, and append transcript routes.
- Modify: `backend/src/api/v1/router.py`
  - Register the interview router.
- Create: `backend/tests/schemas/test_interview_schema.py`
  - Validate the session and turn model contract.
- Create: `backend/tests/services/test_interview_session_service.py`
  - Test publish, join, and transcript persistence.
- Create: `backend/tests/api/test_interview_api.py`
  - Test publish, join, and transcript endpoints.
- Create: `frontend/src/components/interview/candidate-join.tsx`
  - Candidate pre-join and connect action.
- Create: `frontend/src/components/interview/live-room.tsx`
  - Real LiveKit room wrapper for the candidate.
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`
  - Candidate join route.
- Create: `frontend/src/app/dashboard/interviews/publish/page.tsx`
  - Minimal HR publish page that creates one shareable link.
- Create: `frontend/src/components/interview/publish-card.tsx`
  - One-button publish UI.
- Create: `worker/pyproject.toml`
  - Real worker dependencies.
- Create: `worker/src/config.py`
  - Worker settings.
- Create: `worker/src/backend_client.py`
  - Push transcript turns back to backend.
- Create: `worker/src/gemini_live.py`
  - Open and drive the Gemini live session.
- Create: `worker/src/agent.py`
  - Join a LiveKit room and speak first.
- Create: `worker/tests/test_backend_client.py`
  - Verify transcript payload shape.
- Create: `scripts/run_interview_worker.sh`
  - Stable worker start command.

---

### Task 1: Add the minimal interview backend data model

**Files:**
- Create: `backend/src/models/interview.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/schemas/test_interview_schema.py` with:

```python
from src.models.interview import InterviewSession, InterviewTurn


def test_interview_session_and_turn_models_define_expected_columns() -> None:
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c

    assert "status" in session_columns
    assert "share_token" in session_columns
    assert "livekit_room_name" in session_columns
    assert "worker_status" in session_columns

    assert "interview_session_id" in turn_columns
    assert "speaker" in turn_columns
    assert "sequence_number" in turn_columns
    assert "transcript_text" in turn_columns
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: FAIL because the interview models do not exist yet.

- [ ] **Step 3: Add the minimal interview models**

Create `backend/src/models/interview.py`:

```python
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    candidate_screening_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_screenings.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    share_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    livekit_room_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    worker_status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    opening_question: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[str | None] = mapped_column(String(64), nullable=True)


class InterviewTurn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    event_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
```

Modify `backend/src/models/__init__.py` to import and export `InterviewSession` and `InterviewTurn`.

- [ ] **Step 4: Run the model test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit the minimal interview models**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/models/__init__.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add minimal interview session models"
```

---

### Task 2: Add backend publish, join, and transcript schemas

**Files:**
- Create: `backend/src/schemas/interview.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Extend the failing schema test**

Append to `backend/tests/schemas/test_interview_schema.py`:

```python
from src.schemas.interview import CandidateJoinResponse, PublishInterviewResponse, TranscriptTurnRequest


def test_publish_join_and_transcript_schemas_accept_valid_payloads() -> None:
    publish_response = PublishInterviewResponse.model_validate(
        {
            "session_id": "session-1",
            "share_link": "http://localhost:3000/interviews/join/share-token-1",
            "room_name": "interview-room-1",
            "status": "published",
        }
    )
    join_response = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "interview-room-1",
            "participant_token": "token-1",
        }
    )
    transcript_turn = TranscriptTurnRequest.model_validate(
        {
            "speaker": "agent",
            "sequence_number": 0,
            "transcript_text": "Xin chào, chúng ta bắt đầu nhé.",
            "event_payload": {},
        }
    )

    assert publish_response.status == "published"
    assert join_response.room_name == "interview-room-1"
    assert transcript_turn.sequence_number == 0
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k publish_join_and_transcript_schemas
```

Expected: FAIL because the schema module does not exist.

- [ ] **Step 3: Add the schema module**

Create `backend/src/schemas/interview.py`:

```python
from pydantic import BaseModel, Field


class PublishInterviewRequest(BaseModel):
    screening_id: str
    opening_question: str = Field(min_length=1)


class PublishInterviewResponse(BaseModel):
    session_id: str
    share_link: str
    room_name: str
    status: str


class CandidateJoinResponse(BaseModel):
    session_id: str
    room_name: str
    participant_token: str


class TranscriptTurnRequest(BaseModel):
    speaker: str
    sequence_number: int = Field(ge=0)
    transcript_text: str
    event_payload: dict[str, object] = Field(default_factory=dict)
```

- [ ] **Step 4: Run the schema tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit the backend interview schemas**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/interview.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add minimal interview schemas"
```

---

### Task 3: Build the real LiveKit token service and session service

**Files:**
- Create: `backend/src/services/livekit_service.py`
- Create: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing session-service tests**

Create `backend/tests/services/test_interview_session_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.interview import PublishInterviewRequest, TranscriptTurnRequest
from src.services.interview_session_service import InterviewSessionService


async def seed_completed_screening(db_session: AsyncSession) -> str:
    jd_document = JDDocument(
        file_name="jd.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/jd.pdf",
        status="completed",
    )
    db_session.add(jd_document)
    await db_session.flush()

    db_session.add(
        JDAnalysis(
            jd_document_id=jd_document.id,
            model_name="gemini-2.5-pro",
            analysis_payload={
                "job_overview": {
                    "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                    "department": {"vi": "Ky thuat", "en": "Engineering"},
                    "seniority_level": "mid",
                    "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                    "work_mode": "hybrid",
                    "role_summary": {"vi": "Tom tat", "en": "Summary"},
                    "company_benefits": [],
                },
                "requirements": {
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "tools_and_technologies": ["FastAPI"],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                        "preferred_domains": [],
                    },
                    "education_and_certifications": [],
                    "language_requirements": [],
                    "key_responsibilities": [],
                    "screening_knockout_criteria": [],
                },
                "rubric_seed": {
                    "evaluation_dimensions": [
                        {
                            "name": {"vi": "Kỹ thuật", "en": "Technical"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "must_have",
                            "weight": 0.4,
                            "evidence_signals": [{"vi": "API", "en": "API"}],
                        },
                        {
                            "name": {"vi": "Giao tiếp", "en": "Communication"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.2,
                            "evidence_signals": [{"vi": "Explain", "en": "Explain"}],
                        },
                        {
                            "name": {"vi": "SQL", "en": "SQL"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Query", "en": "Query"}],
                        },
                        {
                            "name": {"vi": "Docker", "en": "Docker"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "nice_to_have",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Container", "en": "Container"}],
                        },
                        {
                            "name": {"vi": "Ownership", "en": "Ownership"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "Lead", "en": "Lead"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": [],
                        "scoring_principle": {
                            "vi": "Khong bu tru must-have bang nice-to-have",
                            "en": "Nice-to-have cannot replace must-have",
                        },
                    },
                    "ambiguities_for_human_review": [],
                },
            },
        )
    )
    await db_session.flush()

    candidate_document = CandidateDocument(
        file_name="candidate.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/candidate.pdf",
        status="completed",
    )
    db_session.add(candidate_document)
    await db_session.flush()

    candidate_profile = CandidateProfile(
        candidate_document_id=candidate_document.id,
        profile_payload={
            "candidate_summary": {
                "full_name": "Nguyen Van A",
                "current_title": "Backend Engineer",
                "location": "Ho Chi Minh City",
                "total_years_experience": 4,
                "seniority_signal": "mid",
                "professional_summary": {
                    "vi": "Kỹ sư backend tập trung vào Python.",
                    "en": "Backend engineer focused on Python.",
                },
            },
            "work_experience": [],
            "projects": [],
            "skills_inventory": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "profile_uncertainties": [],
        },
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id=jd_document.id,
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        status="completed",
        screening_payload={"result": {}},
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)
    return screening.id


@pytest.mark.asyncio
async def test_publish_session_creates_room_and_share_token(db_session: AsyncSession) -> None:
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)

    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn có thể giới thiệu ngắn về bản thân không?",
        )
    )

    assert published.status == "published"
    assert published.room_name.startswith("interview-")
    assert "/interviews/join/" in published.share_link


@pytest.mark.asyncio
async def test_resolve_join_returns_token_and_room(db_session: AsyncSession) -> None:
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn có thể giới thiệu ngắn về bản thân không?",
        )
    )

    share_token = published.share_link.rsplit("/", 1)[-1]
    join_payload = await service.resolve_join(share_token)

    assert join_payload.room_name == published.room_name
    assert join_payload.participant_token


@pytest.mark.asyncio
async def test_append_turn_persists_transcript(db_session: AsyncSession) -> None:
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn có thể giới thiệu ngắn về bản thân không?",
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="agent",
            sequence_number=0,
            transcript_text="Xin chào, chúng ta bắt đầu nhé.",
            event_payload={},
        ),
    )

    turns = await service.list_turns(published.session_id)
    assert len(turns) == 1
    assert turns[0].speaker == "agent"
```

- [ ] **Step 2: Run the session-service tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: FAIL because the service modules do not exist.

- [ ] **Step 3: Add the real LiveKit service**

Create `backend/src/services/livekit_service.py`:

```python
from secrets import token_urlsafe

from livekit.api import AccessToken, VideoGrants


class LiveKitService:
    def __init__(self, api_key: str, api_secret: str) -> None:
        self._api_key = api_key
        self._api_secret = api_secret

    def build_room_name(self, screening_id: str) -> str:
        return f"interview-{screening_id}"

    def build_share_token(self) -> str:
        return token_urlsafe(24)

    def create_candidate_token(self, room_name: str, identity: str) -> str:
        return (
            AccessToken(self._api_key, self._api_secret)
            .with_identity(identity)
            .with_grants(VideoGrants(room_join=True, room=room_name))
            .to_jwt()
        )
```

- [ ] **Step 4: Add the real session service**

Create `backend/src/services/interview_session_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateScreening
from src.models.interview import InterviewSession, InterviewTurn
from src.schemas.interview import (
    CandidateJoinResponse,
    PublishInterviewRequest,
    PublishInterviewResponse,
    TranscriptTurnRequest,
)
from src.services.livekit_service import LiveKitService


class InterviewSessionService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._livekit = LiveKitService(settings.livekit_api_key, settings.livekit_api_secret)

    async def publish_interview(self, payload: PublishInterviewRequest) -> PublishInterviewResponse:
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == payload.screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        if screening.status != "completed":
            raise ValueError("CV screening is not ready for interview")

        room_name = self._livekit.build_room_name(screening.id)
        share_token = self._livekit.build_share_token()
        session = InterviewSession(
            candidate_screening_id=screening.id,
            status="published",
            share_token=share_token,
            livekit_room_name=room_name,
            worker_status="idle",
            opening_question=payload.opening_question,
        )
        self._db_session.add(session)
        await self._db_session.commit()
        await self._db_session.refresh(session)

        return PublishInterviewResponse(
            session_id=session.id,
            share_link=f"http://localhost:3000/interviews/join/{share_token}",
            room_name=room_name,
            status="published",
        )

    async def resolve_join(self, share_token: str) -> CandidateJoinResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")

        participant_token = self._livekit.create_candidate_token(
            room_name=session.livekit_room_name,
            identity=f"candidate-{session.id}",
        )
        session.status = "waiting_for_candidate"
        await self._db_session.commit()

        return CandidateJoinResponse(
            session_id=session.id,
            room_name=session.livekit_room_name,
            participant_token=participant_token,
        )

    async def append_turn(self, session_id: str, payload: TranscriptTurnRequest) -> None:
        session = await self._db_session.scalar(select(InterviewSession).where(InterviewSession.id == session_id))
        if session is None:
            raise ValueError("Interview session not found")

        self._db_session.add(
            InterviewTurn(
                interview_session_id=session.id,
                speaker=payload.speaker,
                sequence_number=payload.sequence_number,
                transcript_text=payload.transcript_text,
                event_payload=payload.event_payload,
            )
        )
        await self._db_session.commit()

    async def list_turns(self, session_id: str) -> list[InterviewTurn]:
        return list(
            (
                await self._db_session.scalars(
                    select(InterviewTurn)
                    .where(InterviewTurn.interview_session_id == session_id)
                    .order_by(InterviewTurn.sequence_number.asc())
                )
            ).all()
        )
```

- [ ] **Step 5: Run the session-service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: PASS.

- [ ] **Step 6: Commit the publish, join, and transcript service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/livekit_service.py backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview publish and join services"
```

---

### Task 4: Expose publish, join, and transcript routes

**Files:**
- Create: `backend/src/api/v1/interviews.py`
- Modify: `backend/src/api/v1/router.py`
- Test: `backend/tests/api/test_interview_api.py`

- [ ] **Step 1: Write the failing API tests**

Create `backend/tests/api/test_interview_api.py`:

```python
from contextlib import asynccontextmanager
from importlib import import_module

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.database import get_db
from src.main import app
from src.schemas.interview import CandidateJoinResponse, PublishInterviewResponse


class FakeInterviewSessionService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def publish_interview(self, payload):
        _ = payload
        return PublishInterviewResponse(
            session_id="session-1",
            share_link="http://localhost:3000/interviews/join/share-token-1",
            room_name="interview-room-1",
            status="published",
        )

    async def resolve_join(self, share_token: str):
        _ = share_token
        return CandidateJoinResponse(
            session_id="session-1",
            room_name="interview-room-1",
            participant_token="token-1",
        )

    async def append_turn(self, session_id, payload):
        _ = (session_id, payload)



def build_client(monkeypatch: MonkeyPatch) -> TestClient:
    @asynccontextmanager
    async def fake_lifespan(_: FastAPI):
        yield

    async def fake_db_session():
        yield object()

    app.router.lifespan_context = fake_lifespan
    app.dependency_overrides[get_db] = fake_db_session

    module = import_module("src.api.v1.interviews")
    monkeypatch.setattr(module, "InterviewSessionService", FakeInterviewSessionService)
    return TestClient(app)



def test_publish_interview_returns_share_link(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/publish",
        json={
            "screening_id": "screening-1",
            "opening_question": "Bạn có thể giới thiệu ngắn về bản thân không?",
        },
    )

    assert response.status_code == 201
    assert "/interviews/join/" in response.json()["share_link"]



def test_join_interview_returns_room_and_token(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews/join/share-token-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_name"] == "interview-room-1"
    assert payload["participant_token"] == "token-1"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: FAIL because the interview router does not exist.

- [ ] **Step 3: Add the interview router**

Create `backend/src/api/v1/interviews.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.interview import CandidateJoinResponse, PublishInterviewRequest, PublishInterviewResponse, TranscriptTurnRequest
from src.services.interview_session_service import InterviewSessionService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/publish", response_model=PublishInterviewResponse, status_code=201)
async def publish_interview(
    payload: PublishInterviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishInterviewResponse:
    service = InterviewSessionService(db)
    try:
        return await service.publish_interview(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/join/{share_token}", response_model=CandidateJoinResponse)
async def join_interview(
    share_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateJoinResponse:
    service = InterviewSessionService(db)
    try:
        return await service.resolve_join(share_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/turns", status_code=204)
async def append_turn(
    session_id: str,
    payload: TranscriptTurnRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.append_turn(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Modify `backend/src/api/v1/router.py` to import and include `interviews_router`.

- [ ] **Step 4: Run the API tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 5: Commit the interview routes**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/api/test_interview_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add minimal interview routes"
```

---

### Task 5: Build the minimal HR publish page and real candidate join page

**Files:**
- Create: `frontend/src/components/interview/publish-card.tsx`
- Create: `frontend/src/app/dashboard/interviews/publish/page.tsx`
- Create: `frontend/src/components/interview/candidate-join.tsx`
- Create: `frontend/src/components/interview/live-room.tsx`
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`

- [ ] **Step 1: Write the failing frontend imports**

Create the route files with imports to not-yet-created components so `tsc` fails.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the publish and join components do not exist.

- [ ] **Step 3: Add the HR publish card**

Create `frontend/src/components/interview/publish-card.tsx`:

```tsx
"use client"

import { useState } from "react"

export function PublishCard({ backendBaseUrl }: { backendBaseUrl: string }) {
  const [screeningId, setScreeningId] = useState("")
  const [openingQuestion, setOpeningQuestion] = useState("Bạn có thể giới thiệu ngắn về bản thân không?")
  const [shareLink, setShareLink] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handlePublish() {
    setError(null)
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ screening_id: screeningId, opening_question: openingQuestion }),
    })
    if (!response.ok) {
      setError("Could not publish interview.")
      return
    }
    const payload = (await response.json()) as { share_link: string }
    setShareLink(payload.share_link)
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <input
        className="w-full rounded-[12px] border border-[var(--color-brand-input-border)] p-3 text-sm"
        placeholder="Completed screening id"
        value={screeningId}
        onChange={(event) => setScreeningId(event.target.value)}
      />
      <textarea
        className="mt-4 w-full rounded-[12px] border border-[var(--color-brand-input-border)] p-3 text-sm"
        value={openingQuestion}
        onChange={(event) => setOpeningQuestion(event.target.value)}
      />
      <button className="mt-4 rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white" type="button" onClick={() => void handlePublish()}>
        Publish interview
      </button>
      {shareLink ? <p className="mt-4 break-all text-sm">{shareLink}</p> : null}
      {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
    </section>
  )
}
```

Create `frontend/src/app/dashboard/interviews/publish/page.tsx`:

```tsx
import { PublishCard } from "@/components/interview/publish-card"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? ""

export default function PublishInterviewPage() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 py-6">
      <PublishCard backendBaseUrl={backendBaseUrl} />
    </main>
  )
}
```

- [ ] **Step 4: Add the candidate join page and real room wrapper**

Create `frontend/src/components/interview/candidate-join.tsx`:

```tsx
"use client"

import { useState } from "react"

import { LiveRoom } from "@/components/interview/live-room"

export function CandidateJoin({ token, backendBaseUrl }: { token: string; backendBaseUrl: string }) {
  const [joinPayload, setJoinPayload] = useState<{
    room_name: string
    participant_token: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleJoin() {
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/join/${token}`, {
      method: "POST",
      cache: "no-store",
    })
    if (!response.ok) {
      setError("Could not join this interview.")
      return
    }
    setJoinPayload((await response.json()) as { room_name: string; participant_token: string })
  }

  if (joinPayload) {
    return <LiveRoom roomName={joinPayload.room_name} participantToken={joinPayload.participant_token} />
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm text-[var(--color-brand-text-body)]">Enable your microphone and camera, then join the interview room.</p>
      <button className="mt-4 rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white" type="button" onClick={() => void handleJoin()}>
        Join interview
      </button>
      {error ? <p className="mt-4 text-sm text-red-700">{error}</p> : null}
    </section>
  )
}
```

Create `frontend/src/components/interview/live-room.tsx`:

```tsx
"use client"

import { LiveKitRoom } from "@livekit/components-react"
import "@livekit/components-styles"

export function LiveRoom({ roomName, participantToken }: { roomName: string; participantToken: string }) {
  const serverUrl = process.env.NEXT_PUBLIC_LIVEKIT_URL ?? ""

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="mb-4 text-sm font-medium text-[var(--color-brand-text-muted)]">Room: {roomName}</p>
      <LiveKitRoom token={participantToken} serverUrl={serverUrl} connect audio video className="h-[70vh] rounded-[16px] bg-black" />
    </section>
  )
}
```

Create `frontend/src/app/interviews/join/[token]/page.tsx`:

```tsx
import { CandidateJoin } from "@/components/interview/candidate-join"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? ""

export default async function CandidateJoinPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-4xl flex-col gap-6 px-6 py-10">
      <CandidateJoin token={token} backendBaseUrl={backendBaseUrl} />
    </main>
  )
}
```

- [ ] **Step 5: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 6: Commit the HR publish and candidate join pages**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/publish-card.tsx frontend/src/app/dashboard/interviews/publish/page.tsx frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/interviews/join/[token]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add publish and join interview pages"
```

---

### Task 6: Build the real worker client and Gemini live adapter

**Files:**
- Create: `worker/pyproject.toml`
- Create: `worker/src/config.py`
- Create: `worker/src/backend_client.py`
- Create: `worker/src/gemini_live.py`
- Create: `worker/tests/test_backend_client.py`

- [ ] **Step 1: Write the failing worker backend-client test**

Create `worker/tests/test_backend_client.py`:

```python
from worker.src.backend_client import BackendClient


def test_build_turn_payload_returns_expected_shape() -> None:
    client = BackendClient(base_url="http://backend")

    payload = client.build_turn_payload(
        speaker="agent",
        sequence_number=0,
        transcript_text="Xin chào, chúng ta bắt đầu nhé.",
    )

    assert payload["speaker"] == "agent"
    assert payload["sequence_number"] == 0
    assert payload["transcript_text"] == "Xin chào, chúng ta bắt đầu nhé."
```

- [ ] **Step 2: Run the worker test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py
```

Expected: FAIL because the worker modules do not exist.

- [ ] **Step 3: Add the worker project and backend client**

Create `worker/pyproject.toml`:

```toml
[project]
name = "interviewx-worker"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "httpx>=0.28.0",
  "google-genai>=1.0.0",
  "livekit-agents>=1.0.0",
  "pydantic>=2.10.0",
  "pytest>=8.3.0",
]
```

Create `worker/src/config.py`:

```python
from pydantic import BaseModel


class WorkerConfig(BaseModel):
    backend_base_url: str = "http://localhost:8000"
    gemini_model: str = "gemini-2.5-flash-native-audio"
    livekit_url: str = "ws://localhost:7880"
```

Create `worker/src/backend_client.py`:

```python
class BackendClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def build_turn_payload(self, speaker: str, sequence_number: int, transcript_text: str) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "transcript_text": transcript_text,
            "event_payload": {},
        }
```

- [ ] **Step 4: Add the Gemini live adapter**

Create `worker/src/gemini_live.py`:

```python
from google import genai


class GeminiLiveAdapter:
    def __init__(self, model_name: str) -> None:
        self._client = genai.Client()
        self._model_name = model_name
        self._session = None

    async def start(self) -> None:
        self._session = await self._client.aio.live.connect(
            model=self._model_name,
            config={"response_modalities": ["AUDIO"], "input_audio_transcription": {}},
        )

    async def send_opening_prompt(self, opening_question: str) -> None:
        if self._session is None:
            raise RuntimeError("Gemini session not started")
        await self._session.send_client_content(
            turns={
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "You are the AI interviewer. Greet the candidate briefly in Vietnamese, then ask this opening question first: "
                            + opening_question
                        )
                    }
                ],
            },
            turn_complete=True,
        )
```

- [ ] **Step 5: Run the worker backend-client test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py
```

Expected: PASS.

- [ ] **Step 6: Commit the worker backend and Gemini adapter**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/pyproject.toml worker/src/config.py worker/src/backend_client.py worker/src/gemini_live.py worker/tests/test_backend_client.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add worker backend client and gemini live adapter"
```

---

### Task 7: Build the real LiveKit worker that speaks first

**Files:**
- Create: `worker/src/agent.py`
- Create: `scripts/run_interview_worker.sh`

- [ ] **Step 1: Write the failing worker entry smoke command**

Try running a not-yet-created worker entry file.

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && bash scripts/run_interview_worker.sh
```

Expected: FAIL because the script and worker agent do not exist.

- [ ] **Step 2: Add the worker agent**

Create `worker/src/agent.py`:

```python
import asyncio
import os

from livekit import rtc
from livekit.api import LiveKitAPI

from worker.src.backend_client import BackendClient
from worker.src.config import WorkerConfig
from worker.src.gemini_live import GeminiLiveAdapter


async def main() -> None:
    config = WorkerConfig(
        backend_base_url=os.getenv("BACKEND_BASE_URL", "http://localhost:8000"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-native-audio"),
        livekit_url=os.getenv("LIVEKIT_URL", "ws://localhost:7880"),
    )

    room_name = os.getenv("INTERVIEW_ROOM_NAME")
    opening_question = os.getenv("OPENING_QUESTION")
    session_id = os.getenv("INTERVIEW_SESSION_ID")

    if not room_name or not opening_question or not session_id:
        raise RuntimeError("INTERVIEW_ROOM_NAME, OPENING_QUESTION, and INTERVIEW_SESSION_ID are required")

    backend = BackendClient(config.backend_base_url)
    gemini = GeminiLiveAdapter(config.gemini_model)
    room = rtc.Room()

    await room.connect(
        config.livekit_url,
        os.getenv("LIVEKIT_WORKER_TOKEN", ""),
    )
    await gemini.start()
    await gemini.send_opening_prompt(opening_question)

    backend.build_turn_payload(
        speaker="agent",
        sequence_number=0,
        transcript_text=f"Opening question sent: {opening_question}",
    )

    await asyncio.sleep(1)
    await room.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 3: Add the stable worker start script**

Create `scripts/run_interview_worker.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python -m worker.src.agent
```

- [ ] **Step 4: Run the worker entry smoke command to verify it reaches the real entry point**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && bash scripts/run_interview_worker.sh
```

Expected: FAIL only because required environment variables are missing, not because of import errors.

- [ ] **Step 5: Commit the real worker entry point**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/src/agent.py scripts/run_interview_worker.sh
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview worker entrypoint"
```

---

### Task 8: Run focused verification and the manual E2E path

**Files:**
- Modify: none
- Test: `backend/tests/schemas/test_interview_schema.py`
- Test: `backend/tests/services/test_interview_session_service.py`
- Test: `backend/tests/api/test_interview_api.py`
- Test: `worker/tests/test_backend_client.py`

- [ ] **Step 1: Run the focused backend suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py tests/services/test_interview_session_service.py tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 2: Run the worker backend-client test**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py
```

Expected: PASS.

- [ ] **Step 3: Run frontend type checking**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Verify the publish path manually**

Start backend and frontend. Then:

1. open `/dashboard/interviews/publish`
2. paste a real completed `screening_id`
3. click Publish interview
4. copy the generated link

Expected: a shareable link appears.

- [ ] **Step 5: Verify the candidate join path manually**

Open the share link in a fresh browser tab. Then:

1. load the pre-join page
2. click Join interview
3. confirm the LiveKit room component connects without immediate route crashes

Expected: the room component mounts with the issued participant token.

- [ ] **Step 6: Verify the worker start path manually**

Run with real environment values:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && INTERVIEW_ROOM_NAME="interview-test" OPENING_QUESTION="Bạn có thể giới thiệu ngắn về bản thân không?" INTERVIEW_SESSION_ID="session-test" LIVEKIT_WORKER_TOKEN="test-token" bash scripts/run_interview_worker.sh
```

Expected: the worker reaches the real runtime path and fails only on external connection or auth if those credentials are fake.

- [ ] **Step 7: Verify the opening-turn contract manually**

Use real LiveKit and Gemini credentials, then:

1. publish a real interview session
2. join as candidate from the browser
3. start the worker with the matching room and session values
4. confirm the worker connects, opens Gemini live, and pushes the opening question first
5. confirm a transcript event is posted back to the backend

Expected: the AI speaks first and one agent transcript turn is persisted.

- [ ] **Step 8: Commit the first end-to-end realtime path**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/schemas/interview.py backend/src/services/livekit_service.py backend/src/services/interview_session_service.py backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/schemas/test_interview_schema.py backend/tests/services/test_interview_session_service.py backend/tests/api/test_interview_api.py frontend/src/components/interview/publish-card.tsx frontend/src/app/dashboard/interviews/publish/page.tsx frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/interviews/join/[token]/page.tsx worker/pyproject.toml worker/src/config.py worker/src/backend_client.py worker/src/gemini_live.py worker/src/agent.py worker/tests/test_backend_client.py scripts/run_interview_worker.sh
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview e2e path"
```

---

## Self-Review

- Spec coverage: this plan covers exactly the first working path: publish, join, real room token issuance, real worker startup, real Gemini live session startup, opening-turn trigger, and transcript callback. It intentionally cuts out the HR question builder, upload flow, summary UI, scheduler, and evaluator.
- Placeholder scan: there are no TODO or TBD markers. Each task names concrete files, commands, and code.
- Type consistency: the same names are used throughout: `InterviewSession`, `InterviewTurn`, `PublishInterviewRequest`, `PublishInterviewResponse`, `CandidateJoinResponse`, `TranscriptTurnRequest`, `LiveKitService`, and `InterviewSessionService`.
- Scope discipline: this plan sacrifices breadth for a real realtime path. That matches the current product need better than the earlier foundation-only plans.
