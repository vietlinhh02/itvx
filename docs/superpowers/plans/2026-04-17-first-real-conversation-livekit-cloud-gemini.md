# First Real Conversation LiveKit Cloud Gemini Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver one production-shaped realtime interview slice where HR publishes a LiveKit Cloud interview, a candidate joins from the web app, a long-running hybrid worker attaches to the room, Gemini Live speaks first and responds to at least one candidate turn with real audio, transcript/state events persist to the backend, and candidate/HR surfaces show useful session state and failure feedback.

**Architecture:** Keep FastAPI as the control plane for session publication, reconciliation state, transcript persistence, and HR review data. Run one long-lived Python worker service that manages one runtime handler per interview session; each handler joins the LiveKit Cloud room, bridges candidate audio into Gemini Live, publishes Gemini audio back into the room, and reports runtime/provider state back to the backend. Treat backend state and provider state as dual sources of truth by recording provider observations, backend lifecycle transitions, and reconciliation failures explicitly instead of hiding them behind a single status field.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, Next.js App Router, TypeScript, LiveKit Cloud, LiveKit Python RTC SDK, Google Gen AI Python SDK (Gemini Live), httpx, pytest, Vitest, uv, ruff, ty, tsc

---

## File Structure

- Modify: `backend/src/config.py`
  - Add explicit LiveKit Cloud, Gemini Live, worker callback, and session timeout settings.
- Modify: `backend/src/models/interview.py`
  - Expand `InterviewSession` and `InterviewTurn`; add provider/runtime metadata columns and a separate event model.
- Modify: `backend/src/models/__init__.py`
  - Export the new interview event model.
- Modify: `backend/src/schemas/interview.py`
  - Define publish, join, session detail, event ingest, transcript ingest, and review response contracts.
- Modify: `backend/src/services/livekit_service.py`
  - Mint both candidate and worker tokens for LiveKit Cloud and generate room names/identities.
- Modify: `backend/src/services/interview_session_service.py`
  - Publish sessions, resolve joins, store transcript turns, store runtime/provider events, compute lifecycle/reconciliation state, and expose detail/review endpoints.
- Create: `backend/src/services/interview_runtime_service.py`
  - Concentrate worker/runtime callback handling and reconciliation rules outside the session CRUD service.
- Modify: `backend/src/api/v1/interviews.py`
  - Add publish/join/detail/review/runtime-event/transcript routes.
- Modify: `backend/src/api/v1/router.py`
  - Ensure the interview router stays registered with the expanded routes.
- Modify: `backend/tests/schemas/test_interview_schema.py`
  - Cover the expanded session, turn, event, and response schemas.
- Modify: `backend/tests/services/test_interview_session_service.py`
  - Cover publish, join, event ingest, lifecycle transitions, reconciliation, transcript persistence, and review payloads.
- Modify: `backend/tests/api/test_interview_api.py`
  - Cover new detail, review, runtime-event, and transcript endpoints.
- Modify: `frontend/src/components/interview/interview-types.ts`
  - Replace stale interview planning types with realtime publish/join/session detail/review types.
- Modify: `frontend/src/components/interview/interview-launch-panel.tsx`
  - Switch the dashboard launch flow to the realtime publish contract with opening prompt + session status.
- Modify: `frontend/src/components/interview/candidate-join.tsx`
  - Add explicit pre-join, joining, waiting, in-room, and failure states.
- Modify: `frontend/src/components/interview/live-room.tsx`
  - Render LiveKit room UI plus runtime status, transcript snippets, and retry/failure surface.
- Create: `frontend/src/components/interview/session-status-card.tsx`
  - Reusable session/provider status summary for candidate and HR pages.
- Create: `frontend/src/components/interview/transcript-review.tsx`
  - HR transcript/review surface for one session.
- Create: `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`
  - HR session detail page that polls backend detail/review data.
- Modify: `frontend/src/app/interviews/join/[token]/page.tsx`
  - Load the improved candidate join flow with error messaging for missing env/backend failures.
- Modify: `worker/src/config.py`
  - Replace the placeholder model with validated settings for LiveKit Cloud, Gemini, retry, and backend callback behavior.
- Modify: `worker/src/backend_client.py`
  - Post transcript turns and runtime/provider events to the backend with structured payloads.
- Modify: `worker/src/gemini_live.py`
  - Wrap Gemini Live session lifecycle, audio send/receive, transcript events, and reconnect behavior.
- Modify: `worker/src/agent.py`
  - Run the long-lived worker service and per-session runtime handler with LiveKit subscribe/publish bridge.
- Modify: `worker/tests/test_backend_client.py`
  - Cover event and transcript payload shape.
- Modify: `worker/tests/test_agent_smoke.py`
  - Cover config validation and runtime handler orchestration with fakes.
- Create: `worker/tests/test_gemini_live.py`
  - Cover Gemini adapter callbacks and reconnect policy with fakes.
- Modify: `backend/src/scripts/dev_api_and_worker.sh`
  - Start the API and worker with explicit LiveKit Cloud env validation.
- Create: `worker/README.runtime.md`
  - Minimal operator notes for required env, startup, and verification commands.

---

### Task 1: Expand the backend interview domain model for dual-source runtime state

**Files:**
- Modify: `backend/src/models/interview.py`
- Modify: `backend/src/models/__init__.py`
- Modify: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Write the failing model test for session lifecycle and runtime events**

```python
from src.models.interview import InterviewRuntimeEvent, InterviewSession, InterviewTurn


def test_interview_models_define_runtime_and_review_columns() -> None:
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c
    event_columns = InterviewRuntimeEvent.__table__.c

    assert "status" in session_columns
    assert "worker_status" in session_columns
    assert "provider_status" in session_columns
    assert "candidate_identity" in session_columns
    assert "worker_identity" in session_columns
    assert "last_error_code" in session_columns
    assert "last_error_message" in session_columns
    assert "last_provider_event_at" in session_columns
    assert "last_runtime_event_at" in session_columns
    assert "summary_payload" in session_columns

    assert "speaker" in turn_columns
    assert "sequence_number" in turn_columns
    assert "transcript_text" in turn_columns
    assert "provider_event_id" in turn_columns

    assert "event_type" in event_columns
    assert "event_source" in event_columns
    assert "session_status" in event_columns
    assert "worker_status" in event_columns
    assert "provider_status" in event_columns
    assert "payload" in event_columns
```

- [ ] **Step 2: Run the model test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k runtime_and_review_columns
```

Expected: FAIL because `InterviewRuntimeEvent` and the new columns do not exist yet.

- [ ] **Step 3: Add the minimal model changes to make the test pass**

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
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
    worker_status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    provider_status: Mapped[str] = mapped_column(String(50), nullable=False, default="room_not_connected")
    share_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    livekit_room_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    candidate_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    worker_identity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_question: Mapped[str] = mapped_column(Text, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_provider_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_runtime_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewTurn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewRuntimeEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_runtime_events"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_source: Mapped[str] = mapped_column(String(50), nullable=False)
    session_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    worker_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
```

```python
from src.models.interview import InterviewRuntimeEvent, InterviewSession, InterviewTurn

__all__ = [
    # existing exports...
    "InterviewRuntimeEvent",
    "InterviewSession",
    "InterviewTurn",
]
```

- [ ] **Step 4: Run the model test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k runtime_and_review_columns
```

Expected: PASS.

- [ ] **Step 5: Commit the model expansion**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/models/__init__.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: expand interview runtime models"
```

---

### Task 2: Define the backend schemas for publish, join, detail, transcript, and runtime events

**Files:**
- Modify: `backend/src/schemas/interview.py`
- Modify: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Extend the failing schema test with the realtime contracts**

```python
from src.schemas.interview import (
    CandidateJoinResponse,
    InterviewRuntimeEventRequest,
    InterviewSessionDetailResponse,
    InterviewSessionReviewResponse,
    PublishInterviewResponse,
    TranscriptTurnRequest,
)


def test_realtime_interview_schemas_accept_valid_payloads() -> None:
    publish_response = PublishInterviewResponse.model_validate(
        {
            "session_id": "session-1",
            "share_link": "http://localhost:3000/interviews/join/share-token-1",
            "room_name": "interview-room-1",
            "status": "published",
            "worker_dispatch_token": "dispatch-token-1",
        }
    )
    join_response = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "interview-room-1",
            "participant_token": "candidate-token-1",
            "candidate_identity": "candidate-session-1",
        }
    )
    event_request = InterviewRuntimeEventRequest.model_validate(
        {
            "event_type": "worker.connected",
            "event_source": "worker",
            "session_status": "connecting",
            "worker_status": "room_connected",
            "provider_status": "livekit_connected",
            "payload": {"room_name": "interview-room-1"},
        }
    )
    transcript_turn = TranscriptTurnRequest.model_validate(
        {
            "speaker": "agent",
            "sequence_number": 1,
            "transcript_text": "Xin chào, tôi là AI phỏng vấn viên.",
            "provider_event_id": "evt-1",
            "event_payload": {},
        }
    )
    detail_response = InterviewSessionDetailResponse.model_validate(
        {
            "session_id": "session-1",
            "status": "in_progress",
            "worker_status": "responding",
            "provider_status": "gemini_streaming",
            "livekit_room_name": "interview-room-1",
            "opening_question": "Giới thiệu ngắn về bản thân bạn.",
            "last_error_code": None,
            "last_error_message": None,
            "transcript_turns": [],
            "runtime_events": [],
        }
    )
    review_response = InterviewSessionReviewResponse.model_validate(
        {
            "session_id": "session-1",
            "status": "completed",
            "summary_payload": {"final_summary": "done"},
            "transcript_turns": [],
        }
    )

    assert publish_response.worker_dispatch_token == "dispatch-token-1"
    assert join_response.candidate_identity == "candidate-session-1"
    assert event_request.provider_status == "livekit_connected"
    assert transcript_turn.provider_event_id == "evt-1"
    assert detail_response.provider_status == "gemini_streaming"
    assert review_response.summary_payload["final_summary"] == "done"
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k realtime_interview_schemas_accept_valid_payloads
```

Expected: FAIL because the new schema classes and fields do not exist.

- [ ] **Step 3: Add the schema module changes**

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
    worker_dispatch_token: str


class CandidateJoinResponse(BaseModel):
    session_id: str
    room_name: str
    participant_token: str
    candidate_identity: str


class TranscriptTurnRequest(BaseModel):
    speaker: str
    sequence_number: int = Field(ge=0)
    transcript_text: str = Field(min_length=1)
    provider_event_id: str | None = None
    event_payload: dict[str, object] = Field(default_factory=dict)


class InterviewRuntimeEventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    event_source: str = Field(min_length=1)
    session_status: str | None = None
    worker_status: str | None = None
    provider_status: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class InterviewRuntimeEventResponse(BaseModel):
    event_type: str
    event_source: str
    session_status: str | None
    worker_status: str | None
    provider_status: str | None
    payload: dict[str, object]


class TranscriptTurnResponse(BaseModel):
    speaker: str
    sequence_number: int
    transcript_text: str
    provider_event_id: str | None
    event_payload: dict[str, object]


class InterviewSessionDetailResponse(BaseModel):
    session_id: str
    status: str
    worker_status: str
    provider_status: str
    livekit_room_name: str
    opening_question: str
    last_error_code: str | None
    last_error_message: str | None
    transcript_turns: list[TranscriptTurnResponse]
    runtime_events: list[InterviewRuntimeEventResponse]


class InterviewSessionReviewResponse(BaseModel):
    session_id: str
    status: str
    summary_payload: dict[str, object]
    transcript_turns: list[TranscriptTurnResponse]
```

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k realtime_interview_schemas_accept_valid_payloads
```

Expected: PASS.

- [ ] **Step 5: Commit the schema changes**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/interview.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview schemas"
```

---

### Task 3: Add backend services for publish, join, runtime callbacks, reconciliation, and review data

**Files:**
- Modify: `backend/src/config.py`
- Modify: `backend/src/services/livekit_service.py`
- Modify: `backend/src/services/interview_session_service.py`
- Create: `backend/src/services/interview_runtime_service.py`
- Modify: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing service tests for publish, event ingest, and review data**

```python
@pytest.mark.asyncio
async def test_publish_session_returns_worker_dispatch_token(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)

    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn hãy giới thiệu ngắn về bản thân.",
        )
    )

    assert published.worker_dispatch_token


@pytest.mark.asyncio
async def test_record_runtime_event_updates_session_reconciliation_state(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn hãy giới thiệu ngắn về bản thân.",
        )
    )

    runtime_service = InterviewRuntimeService(db_session)
    await runtime_service.record_event(
        published.session_id,
        InterviewRuntimeEventRequest(
            event_type="worker.connected",
            event_source="worker",
            session_status="connecting",
            worker_status="room_connected",
            provider_status="livekit_connected",
            payload={"attempt": 1},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.worker_status == "room_connected"
    assert detail.provider_status == "livekit_connected"
    assert detail.status == "connecting"


@pytest.mark.asyncio
async def test_get_review_returns_transcript_and_summary(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service = InterviewSessionService(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            opening_question="Bạn hãy giới thiệu ngắn về bản thân.",
        )
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="agent",
            sequence_number=0,
            transcript_text="Xin chào, tôi là AI phỏng vấn viên.",
            provider_event_id="evt-opening",
            event_payload={},
        ),
    )
    await service.store_summary(
        published.session_id,
        {"final_summary": "Ứng viên trả lời rõ ràng ở lượt đầu."},
    )

    review = await service.get_session_review(published.session_id)
    assert review.summary_payload["final_summary"] == "Ứng viên trả lời rõ ràng ở lượt đầu."
    assert review.transcript_turns[0].provider_event_id == "evt-opening"
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k "worker_dispatch_token or reconciliation_state or review_returns_transcript"
```

Expected: FAIL because the worker dispatch token, runtime service, detail, and review methods do not exist.

- [ ] **Step 3: Expand backend settings and LiveKit token support**

```python
class Settings(BaseSettings):
    # existing fields...
    livekit_url: str = "wss://your-project.livekit.cloud"
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_room_prefix: str = "interview"
    worker_callback_secret: str = "change-me"
    interview_runtime_retry_limit: int = 3
    interview_runtime_retry_backoff_seconds: int = 2
    interview_session_idle_timeout_seconds: int = 90
```

```python
from secrets import token_urlsafe

from livekit import api

from src.config import settings


class LiveKitService:
    def build_room_name(self, screening_id: str) -> str:
        return f"{settings.livekit_room_prefix}-{screening_id}"

    def build_share_token(self) -> str:
        return token_urlsafe(24)

    def build_worker_dispatch_token(self) -> str:
        return token_urlsafe(24)

    def create_candidate_identity(self, session_id: str) -> str:
        return f"candidate-{session_id}"

    def create_worker_identity(self, session_id: str) -> str:
        return f"worker-{session_id}"

    def create_candidate_token(self, room_name: str, identity: str) -> str:
        return (
            api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(identity)
            .with_grants(
                api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True)
            )
            .to_jwt()
        )

    def create_worker_token(self, room_name: str, identity: str) -> str:
        return (
            api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(identity)
            .with_grants(
                api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True)
            )
            .to_jwt()
        )
```

- [ ] **Step 4: Add the runtime reconciliation service**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewRuntimeEvent, InterviewSession
from src.schemas.interview import InterviewRuntimeEventRequest


class InterviewRuntimeService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def record_event(self, session_id: str, payload: InterviewRuntimeEventRequest) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")

        session.status = payload.session_status or session.status
        session.worker_status = payload.worker_status or session.worker_status
        session.provider_status = payload.provider_status or session.provider_status
        if payload.event_type.endswith("failed"):
            session.last_error_code = payload.event_type
            session.last_error_message = str(payload.payload.get("message", "Runtime failure"))

        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type=payload.event_type,
                event_source=payload.event_source,
                session_status=payload.session_status,
                worker_status=payload.worker_status,
                provider_status=payload.provider_status,
                payload=payload.payload,
            )
        )
        await self._db_session.commit()
```

- [ ] **Step 5: Expand the session service with publish, detail, review, and summary methods**

```python
class InterviewSessionService:
    # existing __init__ ...

    async def publish_interview(self, payload: PublishInterviewRequest) -> PublishInterviewResponse:
        # existing screening lookup ...
        room_name = self._livekit.build_room_name(screening.id)
        share_token = self._livekit.build_share_token()
        worker_dispatch_token = self._livekit.build_worker_dispatch_token()
        session = InterviewSession(
            candidate_screening_id=screening.id,
            status="published",
            worker_status="idle",
            provider_status="room_not_connected",
            share_token=share_token,
            livekit_room_name=room_name,
            opening_question=payload.opening_question,
        )
        self._db_session.add(session)
        await self._db_session.commit()
        await self._db_session.refresh(session)
        return PublishInterviewResponse(
            session_id=session.id,
            share_link=f"{settings.next_public_app_url}/interviews/join/{share_token}",
            room_name=room_name,
            status=session.status,
            worker_dispatch_token=worker_dispatch_token,
        )

    async def resolve_join(self, share_token: str) -> CandidateJoinResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")
        candidate_identity = self._livekit.create_candidate_identity(session.id)
        participant_token = self._livekit.create_candidate_token(
            room_name=session.livekit_room_name,
            identity=candidate_identity,
        )
        session.status = "waiting"
        session.candidate_identity = candidate_identity
        await self._db_session.commit()
        return CandidateJoinResponse(
            session_id=session.id,
            room_name=session.livekit_room_name,
            participant_token=participant_token,
            candidate_identity=candidate_identity,
        )

    async def store_summary(self, session_id: str, summary_payload: dict[str, object]) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        session.summary_payload = summary_payload
        session.status = "completed"
        await self._db_session.commit()
```

- [ ] **Step 6: Add `get_session_detail` and `get_session_review`**

```python
    async def get_session_detail(self, session_id: str) -> InterviewSessionDetailResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        turns = await self.list_turns(session_id)
        events = list(
            (
                await self._db_session.scalars(
                    select(InterviewRuntimeEvent)
                    .where(InterviewRuntimeEvent.interview_session_id == session_id)
                    .order_by(InterviewRuntimeEvent.created_at.asc())
                )
            ).all()
        )
        return InterviewSessionDetailResponse(
            session_id=session.id,
            status=session.status,
            worker_status=session.worker_status,
            provider_status=session.provider_status,
            livekit_room_name=session.livekit_room_name,
            opening_question=session.opening_question,
            last_error_code=session.last_error_code,
            last_error_message=session.last_error_message,
            transcript_turns=[
                TranscriptTurnResponse(
                    speaker=turn.speaker,
                    sequence_number=turn.sequence_number,
                    transcript_text=turn.transcript_text,
                    provider_event_id=turn.provider_event_id,
                    event_payload=turn.event_payload,
                )
                for turn in turns
            ],
            runtime_events=[
                InterviewRuntimeEventResponse(
                    event_type=event.event_type,
                    event_source=event.event_source,
                    session_status=event.session_status,
                    worker_status=event.worker_status,
                    provider_status=event.provider_status,
                    payload=event.payload,
                )
                for event in events
            ],
        )

    async def get_session_review(self, session_id: str) -> InterviewSessionReviewResponse:
        detail = await self.get_session_detail(session_id)
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        return InterviewSessionReviewResponse(
            session_id=detail.session_id,
            status=detail.status,
            summary_payload=session.summary_payload,
            transcript_turns=detail.transcript_turns,
        )
```

- [ ] **Step 7: Run the service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k "worker_dispatch_token or reconciliation_state or review_returns_transcript"
```

Expected: PASS.

- [ ] **Step 8: Commit the backend service layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/config.py backend/src/services/livekit_service.py backend/src/services/interview_session_service.py backend/src/services/interview_runtime_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview runtime reconciliation service"
```

---

### Task 4: Expose the expanded interview API for publish, join, detail, review, transcript, and runtime events

**Files:**
- Modify: `backend/src/api/v1/interviews.py`
- Modify: `backend/src/api/v1/router.py`
- Modify: `backend/tests/api/test_interview_api.py`

- [ ] **Step 1: Write the failing API tests for detail, review, and runtime event ingest**

```python

def test_get_session_detail_returns_runtime_state(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/sessions/session-1")

    assert response.status_code == 200
    assert response.json()["provider_status"] == "livekit_connected"


def test_post_runtime_event_accepts_worker_callback(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/runtime-events",
        json={
            "event_type": "worker.connected",
            "event_source": "worker",
            "session_status": "connecting",
            "worker_status": "room_connected",
            "provider_status": "livekit_connected",
            "payload": {},
        },
    )

    assert response.status_code == 204


def test_get_session_review_returns_summary(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/sessions/session-1/review")

    assert response.status_code == 200
    assert response.json()["summary_payload"]["final_summary"] == "done"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py -k "runtime_state or worker_callback or session_review"
```

Expected: FAIL because the endpoints and fake service methods do not exist.

- [ ] **Step 3: Expand the fake services in the API test**

```python
class FakeInterviewSessionService:
    async def get_session_detail(self, session_id: str):
        _ = session_id
        return InterviewSessionDetailResponse(
            session_id="session-1",
            status="connecting",
            worker_status="room_connected",
            provider_status="livekit_connected",
            livekit_room_name="interview-room-1",
            opening_question="Giới thiệu ngắn về bản thân bạn.",
            last_error_code=None,
            last_error_message=None,
            transcript_turns=[],
            runtime_events=[],
        )

    async def get_session_review(self, session_id: str):
        _ = session_id
        return InterviewSessionReviewResponse(
            session_id="session-1",
            status="completed",
            summary_payload={"final_summary": "done"},
            transcript_turns=[],
        )


class FakeInterviewRuntimeService:
    async def record_event(self, session_id: str, payload):
        _ = (session_id, payload)
```

- [ ] **Step 4: Add the API routes**

```python
@router.get("/sessions/{session_id}", response_model=InterviewSessionDetailResponse)
async def get_session_detail(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionDetailResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/sessions/{session_id}/review", response_model=InterviewSessionReviewResponse)
async def get_session_review(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionReviewResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_session_review(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/runtime-events", status_code=204)
async def append_runtime_event(
    session_id: str,
    payload: InterviewRuntimeEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewRuntimeService(db)
    try:
        await service.record_event(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

- [ ] **Step 5: Run the API tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py -k "runtime_state or worker_callback or session_review"
```

Expected: PASS.

- [ ] **Step 6: Commit the API changes**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/api/test_interview_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: expose interview runtime api"
```

---

### Task 5: Replace the worker config and backend callback client with structured runtime payloads

**Files:**
- Modify: `worker/src/config.py`
- Modify: `worker/src/backend_client.py`
- Modify: `worker/tests/test_backend_client.py`

- [ ] **Step 1: Write the failing worker client tests for transcript and event payloads**

```python
from src.backend_client import BackendClient


def test_build_turn_payload_includes_provider_event_id() -> None:
    client = BackendClient("http://localhost:8000", "callback-secret")

    payload = client.build_turn_payload(
        speaker="agent",
        sequence_number=2,
        transcript_text="Xin chào.",
        provider_event_id="evt-2",
    )

    assert payload["provider_event_id"] == "evt-2"


def test_build_runtime_event_payload_sets_all_status_fields() -> None:
    client = BackendClient("http://localhost:8000", "callback-secret")

    payload = client.build_runtime_event_payload(
        event_type="worker.connected",
        event_source="worker",
        session_status="connecting",
        worker_status="room_connected",
        provider_status="livekit_connected",
        payload={"attempt": 1},
    )

    assert payload["worker_status"] == "room_connected"
    assert payload["provider_status"] == "livekit_connected"
```

- [ ] **Step 2: Run the worker client tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_backend_client.py -k "provider_event_id or runtime_event_payload"
```

Expected: FAIL because the client does not accept the callback secret and does not build runtime event payloads.

- [ ] **Step 3: Replace the worker config with validated settings**

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerConfig(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    backend_base_url: str = "http://localhost:8000"
    backend_callback_secret: str = "change-me"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-native-audio"
    livekit_url: str = "wss://your-project.livekit.cloud"
    livekit_worker_token: str = ""
    runtime_retry_limit: int = Field(default=3, ge=1)
    runtime_retry_backoff_seconds: int = Field(default=2, ge=1)
```

- [ ] **Step 4: Expand the backend client**

```python
import httpx


class BackendClient:
    def __init__(self, base_url: str, callback_secret: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._callback_secret = callback_secret

    def turns_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/turns"

    def runtime_events_endpoint(self, session_id: str) -> str:
        return f"{self._base_url}/api/v1/interviews/sessions/{session_id}/runtime-events"

    def build_turn_payload(
        self,
        speaker: str,
        sequence_number: int,
        transcript_text: str,
        provider_event_id: str | None,
    ) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "transcript_text": transcript_text,
            "provider_event_id": provider_event_id,
            "event_payload": {},
        }

    def build_runtime_event_payload(
        self,
        event_type: str,
        event_source: str,
        session_status: str | None,
        worker_status: str | None,
        provider_status: str | None,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "event_type": event_type,
            "event_source": event_source,
            "session_status": session_status,
            "worker_status": worker_status,
            "provider_status": provider_status,
            "payload": payload,
        }

    async def post_turn(self, session_id: str, payload: dict[str, object]) -> None:
        async with httpx.AsyncClient(headers={"X-Worker-Callback-Secret": self._callback_secret}) as client:
            response = await client.post(self.turns_endpoint(session_id), json=payload)
            response.raise_for_status()

    async def post_runtime_event(self, session_id: str, payload: dict[str, object]) -> None:
        async with httpx.AsyncClient(headers={"X-Worker-Callback-Secret": self._callback_secret}) as client:
            response = await client.post(self.runtime_events_endpoint(session_id), json=payload)
            response.raise_for_status()
```

- [ ] **Step 5: Run the worker client tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_backend_client.py -k "provider_event_id or runtime_event_payload"
```

Expected: PASS.

- [ ] **Step 6: Commit the worker client layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/src/config.py worker/src/backend_client.py worker/tests/test_backend_client.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add worker runtime callbacks"
```

---

### Task 6: Build the Gemini Live adapter with audio in, audio out, and reconnect hooks

**Files:**
- Modify: `worker/src/gemini_live.py`
- Create: `worker/tests/test_gemini_live.py`

- [ ] **Step 1: Write the failing Gemini adapter tests for opening prompt and reconnectable callbacks**

```python
import pytest

from src.gemini_live import GeminiLiveAdapter


@pytest.mark.asyncio
async def test_opening_prompt_is_sent_after_connect(fake_genai_client) -> None:
    adapter = GeminiLiveAdapter(model_name="gemini-2.5-flash-native-audio", client=fake_genai_client)

    await adapter.connect()
    await adapter.send_opening_prompt("Bạn hãy giới thiệu ngắn về bản thân.")

    assert fake_genai_client.sent_texts == [
        "You are the AI interviewer. Greet the candidate briefly in Vietnamese, then ask this opening question first: Bạn hãy giới thiệu ngắn về bản thân."
    ]


@pytest.mark.asyncio
async def test_reconnect_recreates_live_session(fake_genai_client) -> None:
    adapter = GeminiLiveAdapter(model_name="gemini-2.5-flash-native-audio", client=fake_genai_client)

    await adapter.connect()
    first_session = adapter.session
    await adapter.reconnect()

    assert adapter.session is not first_session
```

- [ ] **Step 2: Run the Gemini adapter tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_gemini_live.py
```

Expected: FAIL because the adapter does not support dependency injection, `connect`, `reconnect`, or a public session property.

- [ ] **Step 3: Replace the adapter with a callback-friendly implementation**

```python
from collections.abc import AsyncIterator, Awaitable, Callable

from google import genai

AudioChunkHandler = Callable[[bytes], Awaitable[None]]
TranscriptHandler = Callable[[str, str | None], Awaitable[None]]
RuntimeEventHandler = Callable[[str, dict[str, object]], Awaitable[None]]


class GeminiLiveAdapter:
    def __init__(self, model_name: str, client: genai.Client | None = None) -> None:
        self._client = client or genai.Client()
        self._model_name = model_name
        self._session = None

    @property
    def session(self):
        return self._session

    async def connect(self) -> None:
        self._session = await self._client.aio.live.connect(
            model=self._model_name,
            config={"response_modalities": ["AUDIO"], "input_audio_transcription": {}},
        )

    async def reconnect(self) -> None:
        if self._session is not None:
            await self._session.close()
        await self.connect()

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

    async def send_audio_chunk(self, chunk: bytes, mime_type: str = "audio/pcm;rate=16000") -> None:
        if self._session is None:
            raise RuntimeError("Gemini session not started")
        await self._session.send_realtime_input(audio={"data": chunk, "mime_type": mime_type})
```

- [ ] **Step 4: Add the receive loop and callback hooks**

```python
    async def receive_forever(
        self,
        on_audio_chunk: AudioChunkHandler,
        on_transcript: TranscriptHandler,
        on_runtime_event: RuntimeEventHandler,
    ) -> None:
        if self._session is None:
            raise RuntimeError("Gemini session not started")
        async for response in self._session.receive():
            server_content = getattr(response, "server_content", None)
            if server_content is None:
                continue
            model_turn = getattr(server_content, "model_turn", None)
            if model_turn is not None:
                for part in getattr(model_turn, "parts", []):
                    inline_data = getattr(part, "inline_data", None)
                    if inline_data is not None:
                        await on_audio_chunk(inline_data.data)
                    text = getattr(part, "text", None)
                    if text:
                        await on_transcript(text, None)
            input_transcription = getattr(server_content, "input_transcription", None)
            if input_transcription and getattr(input_transcription, "text", None):
                await on_transcript(input_transcription.text, "candidate")
            output_transcription = getattr(server_content, "output_transcription", None)
            if output_transcription and getattr(output_transcription, "text", None):
                await on_transcript(output_transcription.text, "agent")
            await on_runtime_event("gemini.response", {"has_server_content": True})
```

- [ ] **Step 5: Run the Gemini adapter tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_gemini_live.py
```

Expected: PASS.

- [ ] **Step 6: Commit the Gemini adapter**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/src/gemini_live.py worker/tests/test_gemini_live.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add gemini live audio adapter"
```

---

### Task 7: Build the worker runtime handler that bridges LiveKit audio to Gemini and Gemini audio back to LiveKit

**Files:**
- Modify: `worker/src/agent.py`
- Modify: `worker/tests/test_agent_smoke.py`

- [ ] **Step 1: Write the failing worker runtime tests for env validation and handler orchestration**

```python
import pytest

from src.agent import SessionRuntimeHandler, required_runtime_env


def test_required_runtime_env_lists_all_session_variables() -> None:
    assert required_runtime_env() == (
        "INTERVIEW_ROOM_NAME",
        "OPENING_QUESTION",
        "INTERVIEW_SESSION_ID",
        "LIVEKIT_WORKER_TOKEN",
    )


@pytest.mark.asyncio
async def test_runtime_handler_posts_opening_turn_and_runtime_event(fake_runtime_dependencies) -> None:
    handler = SessionRuntimeHandler(**fake_runtime_dependencies)

    await handler.run()

    assert fake_runtime_dependencies["backend_client"].posted_events[0]["event_type"] == "worker.connected"
    assert fake_runtime_dependencies["backend_client"].posted_turns[0]["speaker"] == "agent"
```

- [ ] **Step 2: Run the worker runtime tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_agent_smoke.py -k "required_runtime_env or runtime_handler_posts"
```

Expected: FAIL because `SessionRuntimeHandler` does not exist.

- [ ] **Step 3: Create the runtime handler shell and room connection flow**

```python
import asyncio
import os

from livekit import rtc

from src.backend_client import BackendClient
from src.config import WorkerConfig
from src.gemini_live import GeminiLiveAdapter


def required_runtime_env() -> tuple[str, ...]:
    return (
        "INTERVIEW_ROOM_NAME",
        "OPENING_QUESTION",
        "INTERVIEW_SESSION_ID",
        "LIVEKIT_WORKER_TOKEN",
    )


class SessionRuntimeHandler:
    def __init__(
        self,
        room_name: str,
        opening_question: str,
        session_id: str,
        livekit_url: str,
        worker_token: str,
        backend_client: BackendClient,
        gemini_adapter: GeminiLiveAdapter,
    ) -> None:
        self._room_name = room_name
        self._opening_question = opening_question
        self._session_id = session_id
        self._livekit_url = livekit_url
        self._worker_token = worker_token
        self._backend = backend_client
        self._gemini = gemini_adapter
        self._room = rtc.Room()
        self._sequence_number = 0

    async def run(self) -> None:
        await self._room.connect(self._livekit_url, self._worker_token)
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.connected",
                event_source="worker",
                session_status="connecting",
                worker_status="room_connected",
                provider_status="livekit_connected",
                payload={"room_name": self._room_name},
            ),
        )
        await self._gemini.connect()
        await self._gemini.send_opening_prompt(self._opening_question)
        await self._backend.post_turn(
            self._session_id,
            self._backend.build_turn_payload(
                speaker="agent",
                sequence_number=self._next_sequence_number(),
                transcript_text=f"Opening question sent: {self._opening_question}",
                provider_event_id="opening-prompt",
            ),
        )
```

- [ ] **Step 4: Add LiveKit subscribe/publish bridge hooks**

```python
        audio_source = rtc.AudioSource(sample_rate=48000, num_channels=1)
        local_track = rtc.LocalAudioTrack.create_audio_track("ai-interviewer", audio_source)
        publish_options = rtc.TrackPublishOptions()
        publish_options.source = rtc.TrackSource.SOURCE_MICROPHONE
        await self._room.local_participant.publish_track(local_track, publish_options)

        @self._room.on("track_subscribed")
        def on_track_subscribed(track: rtc.Track, publication, participant) -> None:
            if track.kind == rtc.TrackKind.KIND_AUDIO and participant.identity.startswith("candidate-"):
                asyncio.create_task(self._forward_candidate_audio(track))

        self._receive_task = asyncio.create_task(
            self._gemini.receive_forever(
                on_audio_chunk=lambda chunk: self._publish_agent_audio(audio_source, chunk),
                on_transcript=self._handle_transcript,
                on_runtime_event=self._handle_provider_event,
            )
        )
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type="worker.ready",
                event_source="worker",
                session_status="in_progress",
                worker_status="responding",
                provider_status="gemini_streaming",
                payload={"room_name": self._room_name},
            ),
        )
        await asyncio.Future()
```

- [ ] **Step 5: Add helper methods for candidate audio, AI audio, transcripts, and resilience**

```python
    async def _forward_candidate_audio(self, track: rtc.Track) -> None:
        audio_stream = rtc.AudioStream(track)
        async for event in audio_stream:
            await self._gemini.send_audio_chunk(bytes(event.frame.data))

    async def _publish_agent_audio(self, audio_source: rtc.AudioSource, chunk: bytes) -> None:
        frame = rtc.AudioFrame(data=chunk, sample_rate=24000, num_channels=1, samples_per_channel=len(chunk) // 2)
        await audio_source.capture_frame(frame)

    async def _handle_transcript(self, text: str, speaker: str | None) -> None:
        normalized_speaker = "candidate" if speaker == "candidate" else "agent"
        await self._backend.post_turn(
            self._session_id,
            self._backend.build_turn_payload(
                speaker=normalized_speaker,
                sequence_number=self._next_sequence_number(),
                transcript_text=text,
                provider_event_id=None,
            ),
        )

    async def _handle_provider_event(self, event_type: str, payload: dict[str, object]) -> None:
        await self._backend.post_runtime_event(
            self._session_id,
            self._backend.build_runtime_event_payload(
                event_type=event_type,
                event_source="gemini",
                session_status=None,
                worker_status=None,
                provider_status="gemini_streaming",
                payload=payload,
            ),
        )

    def _next_sequence_number(self) -> int:
        current = self._sequence_number
        self._sequence_number += 1
        return current
```

- [ ] **Step 6: Add the long-running `main()` bootstrap**

```python
async def main() -> None:
    config = WorkerConfig()
    missing = [name for name in required_runtime_env() if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    backend = BackendClient(config.backend_base_url, config.backend_callback_secret)
    gemini = GeminiLiveAdapter(config.gemini_model)
    handler = SessionRuntimeHandler(
        room_name=os.environ["INTERVIEW_ROOM_NAME"],
        opening_question=os.environ["OPENING_QUESTION"],
        session_id=os.environ["INTERVIEW_SESSION_ID"],
        livekit_url=config.livekit_url,
        worker_token=os.environ["LIVEKIT_WORKER_TOKEN"],
        backend_client=backend,
        gemini_adapter=gemini,
    )
    await handler.run()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Run the worker runtime tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_agent_smoke.py -k "required_runtime_env or runtime_handler_posts"
```

Expected: PASS.

- [ ] **Step 8: Commit the worker runtime bridge**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/src/agent.py worker/tests/test_agent_smoke.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: bridge livekit audio with gemini live"
```

---

### Task 8: Update the frontend candidate experience for join, status, transcript, and failure handling

**Files:**
- Modify: `frontend/src/components/interview/interview-types.ts`
- Modify: `frontend/src/components/interview/candidate-join.tsx`
- Modify: `frontend/src/components/interview/live-room.tsx`
- Create: `frontend/src/components/interview/session-status-card.tsx`
- Modify: `frontend/src/app/interviews/join/[token]/page.tsx`

- [ ] **Step 1: Write the failing frontend test for the candidate join states**

```tsx
import { render, screen } from "@testing-library/react"

import { CandidateJoin } from "@/components/interview/candidate-join"


test("shows join error message when backend join fails", async () => {
  global.fetch = vi.fn().mockResolvedValue({ ok: false }) as Mock

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  await userEvent.click(screen.getByRole("button", { name: "Join interview" }))

  expect(await screen.findByText("Could not join this interview.")).
    toBeInTheDocument()
})
```

- [ ] **Step 2: Run the frontend test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx
```

Expected: FAIL because the test file and richer state handling do not exist yet.

- [ ] **Step 3: Replace stale interview types with the realtime contracts**

```ts
export type CandidateJoinResponse = {
  session_id: string
  room_name: string
  participant_token: string
  candidate_identity: string
}

export type InterviewRuntimeEvent = {
  event_type: string
  event_source: string
  session_status: string | null
  worker_status: string | null
  provider_status: string | null
  payload: Record<string, unknown>
}

export type TranscriptTurn = {
  speaker: string
  sequence_number: number
  transcript_text: string
  provider_event_id: string | null
  event_payload: Record<string, unknown>
}

export type InterviewSessionDetailResponse = {
  session_id: string
  status: string
  worker_status: string
  provider_status: string
  livekit_room_name: string
  opening_question: string
  last_error_code: string | null
  last_error_message: string | null
  transcript_turns: TranscriptTurn[]
  runtime_events: InterviewRuntimeEvent[]
}
```

- [ ] **Step 4: Expand `CandidateJoin` with explicit UI states**

```tsx
const [joinPayload, setJoinPayload] = useState<CandidateJoinResponse | null>(null)
const [isJoining, setIsJoining] = useState(false)
const [error, setError] = useState<string | null>(null)

async function handleJoin() {
  setIsJoining(true)
  setError(null)
  try {
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/join/${token}`, {
      method: "POST",
      cache: "no-store",
    })
    if (!response.ok) {
      setError("Could not join this interview.")
      return
    }
    setJoinPayload((await response.json()) as CandidateJoinResponse)
  } catch {
    setError("Could not reach the interview service.")
  } finally {
    setIsJoining(false)
  }
}
```

- [ ] **Step 5: Add status polling and failure messaging to `LiveRoom`**

```tsx
const [sessionDetail, setSessionDetail] = useState<InterviewSessionDetailResponse | null>(null)

useEffect(() => {
  const timer = window.setInterval(async () => {
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${sessionId}`, {
      cache: "no-store",
    })
    if (response.ok) {
      setSessionDetail((await response.json()) as InterviewSessionDetailResponse)
    }
  }, 3000)
  return () => window.clearInterval(timer)
}, [backendBaseUrl, sessionId])

{sessionDetail?.last_error_message ? (
  <p className="text-sm text-red-700">{sessionDetail.last_error_message}</p>
) : null}
```

- [ ] **Step 6: Add `SessionStatusCard` and use it in the candidate room page**

```tsx
export function SessionStatusCard({
  status,
  workerStatus,
  providerStatus,
}: {
  status: string
  workerStatus: string
  providerStatus: string
}) {
  return (
    <section className="rounded-[24px] bg-white p-4 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Session status</p>
      <dl className="mt-3 grid gap-2 text-sm text-[var(--color-brand-text-body)]">
        <div className="flex justify-between gap-4"><dt>Session</dt><dd>{status}</dd></div>
        <div className="flex justify-between gap-4"><dt>Worker</dt><dd>{workerStatus}</dd></div>
        <div className="flex justify-between gap-4"><dt>Provider</dt><dd>{providerStatus}</dd></div>
      </dl>
    </section>
  )
}
```

- [ ] **Step 7: Run the frontend test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx
```

Expected: PASS.

- [ ] **Step 8: Commit the candidate UX updates**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-types.ts frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/components/interview/session-status-card.tsx frontend/src/app/interviews/join/[token]/page.tsx frontend/src/components/interview/candidate-join.test.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: improve candidate interview session ux"
```

---

### Task 9: Update the HR publish and review flow for realtime sessions

**Files:**
- Modify: `frontend/src/components/interview/interview-launch-panel.tsx`
- Create: `frontend/src/components/interview/transcript-review.tsx`
- Create: `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`

- [ ] **Step 1: Write the failing HR page test for session detail and transcript review**

```tsx
import { render, screen } from "@testing-library/react"

import InterviewSessionPage from "@/app/dashboard/interviews/[sessionId]/page"


test("renders transcript review for a completed session", async () => {
  global.fetch = vi
    .fn()
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      session_id: "session-1",
      status: "completed",
      worker_status: "finished",
      provider_status: "gemini_closed",
      livekit_room_name: "interview-room-1",
      opening_question: "Giới thiệu ngắn về bản thân bạn.",
      last_error_code: null,
      last_error_message: null,
      transcript_turns: [{ speaker: "agent", sequence_number: 0, transcript_text: "Xin chào", provider_event_id: null, event_payload: {} }],
      runtime_events: [],
    }) })
    .mockResolvedValueOnce({ ok: true, json: async () => ({
      session_id: "session-1",
      status: "completed",
      summary_payload: { final_summary: "done" },
      transcript_turns: [{ speaker: "agent", sequence_number: 0, transcript_text: "Xin chào", provider_event_id: null, event_payload: {} }],
    }) })

  render(await InterviewSessionPage({ params: Promise.resolve({ sessionId: "session-1" }) }))

  expect(await screen.findByText("done")).toBeInTheDocument()
})
```

- [ ] **Step 2: Run the HR page test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/app/dashboard/interviews/session-page.test.tsx
```

Expected: FAIL because the page and review component do not exist.

- [ ] **Step 3: Update the launch panel to call the realtime publish endpoint**

```tsx
const [openingQuestion, setOpeningQuestion] = useState(
  "Bạn hãy giới thiệu ngắn về bản thân và kinh nghiệm gần đây nhất của mình."
)

const response = await fetch(`${backendBaseUrl}/api/v1/interviews/publish`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${accessToken}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({ screening_id: screeningId, opening_question: openingQuestion }),
})

const payload = (await response.json()) as PublishInterviewResponse
router.push(`/dashboard/interviews/${payload.session_id}`)
```

- [ ] **Step 4: Create the HR transcript review component**

```tsx
export function TranscriptReview({
  summary,
  turns,
}: {
  summary: Record<string, unknown>
  turns: TranscriptTurn[]
}) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Interview review</h2>
      <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{String(summary.final_summary ?? "No final summary yet.")}</p>
      <ol className="mt-4 space-y-3">
        {turns.map((turn) => (
          <li key={`${turn.speaker}-${turn.sequence_number}`}>
            <p className="text-xs uppercase tracking-[0.12em] text-[var(--color-brand-text-muted)]">{turn.speaker}</p>
            <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">{turn.transcript_text}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
```

- [ ] **Step 5: Create the HR session page**

```tsx
export default async function InterviewSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>
}) {
  const { sessionId } = await params
  const detailResponse = await fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${sessionId}`, { cache: "no-store" })
  const reviewResponse = await fetch(`${backendBaseUrl}/api/v1/interviews/sessions/${sessionId}/review`, { cache: "no-store" })

  if (!detailResponse.ok || !reviewResponse.ok) {
    return <p className="text-sm text-red-700">Could not load the interview session.</p>
  }

  const detail = (await detailResponse.json()) as InterviewSessionDetailResponse
  const review = (await reviewResponse.json()) as InterviewSessionReviewResponse

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <SessionStatusCard
        status={detail.status}
        workerStatus={detail.worker_status}
        providerStatus={detail.provider_status}
      />
      <TranscriptReview summary={review.summary_payload} turns={review.transcript_turns} />
    </main>
  )
}
```

- [ ] **Step 6: Run the HR page test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/app/dashboard/interviews/session-page.test.tsx
```

Expected: PASS.

- [ ] **Step 7: Commit the HR realtime flow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-launch-panel.tsx frontend/src/components/interview/transcript-review.tsx frontend/src/app/dashboard/interviews/[sessionId]/page.tsx frontend/src/app/dashboard/interviews/session-page.test.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add hr realtime interview review flow"
```

---

### Task 10: Add operator startup and verification flow for LiveKit Cloud and worker runtime

**Files:**
- Modify: `backend/src/scripts/dev_api_and_worker.sh`
- Create: `worker/README.runtime.md`

- [ ] **Step 1: Write the failing shell verification step in the runtime notes**

```markdown
## Verification

Run these commands and expect them to pass:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py tests/services/test_interview_session_service.py tests/schemas/test_interview_schema.py
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_backend_client.py tests/test_agent_smoke.py tests/test_gemini_live.py
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx src/app/dashboard/interviews/session-page.test.tsx && pnpm tsc --noEmit
```
```

- [ ] **Step 2: Update the dev startup script with strict env checks**

```bash
#!/usr/bin/env bash
set -euo pipefail

required_env=(
  LIVEKIT_URL
  LIVEKIT_API_KEY
  LIVEKIT_API_SECRET
  GEMINI_API_KEY
  WORKER_CALLBACK_SECRET
)

for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
done

(
  cd "/home/eddiesngu/Desktop/Dang/interviewx/backend"
  uv run uvicorn src.main:app --host 0.0.0.0 --port 8000
) &

(
  cd "/home/eddiesngu/Desktop/Dang/interviewx/worker"
  uv run python -m src.agent
) &

wait
```

- [ ] **Step 3: Create the runtime operator notes**

```markdown
# Realtime Interview Runtime Notes

## Required environment

- `LIVEKIT_URL`: LiveKit Cloud websocket URL
- `LIVEKIT_API_KEY`: LiveKit Cloud API key
- `LIVEKIT_API_SECRET`: LiveKit Cloud API secret
- `GEMINI_API_KEY`: Gemini Developer API key
- `WORKER_CALLBACK_SECRET`: shared secret used by the worker callback headers

## Startup

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && export LIVEKIT_URL="wss://<project>.livekit.cloud" LIVEKIT_API_KEY="..." LIVEKIT_API_SECRET="..." GEMINI_API_KEY="..." WORKER_CALLBACK_SECRET="..." && bash src/scripts/dev_api_and_worker.sh
```

## Golden path

1. Open one completed screening in the HR dashboard.
2. Publish an interview with a non-empty opening question.
3. Open the share link in a second browser session.
4. Join the room with microphone allowed.
5. Confirm the AI opening question plays as room audio.
6. Speak one answer and confirm the AI replies once.
7. Refresh the HR session page and confirm transcript turns appear.
```
```

- [ ] **Step 4: Run shell format/lint verification**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && shellcheck backend/src/scripts/dev_api_and_worker.sh && shfmt -d backend/src/scripts/dev_api_and_worker.sh
```

Expected: PASS with no output from `shfmt -d`.

- [ ] **Step 5: Commit the startup tooling**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/scripts/dev_api_and_worker.sh worker/README.runtime.md
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "chore: add realtime interview runtime startup flow"
```

---

### Task 11: Run cross-stack verification for the first real conversation slice

**Files:**
- Modify: `backend/src/api/v1/interviews.py`
- Modify: `backend/src/services/interview_session_service.py`
- Modify: `worker/src/agent.py`
- Modify: `frontend/src/components/interview/live-room.tsx`

- [ ] **Step 1: Run the backend targeted checks**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py tests/services/test_interview_session_service.py tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 2: Run the worker targeted checks**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_backend_client.py tests/test_agent_smoke.py tests/test_gemini_live.py
```

Expected: PASS.

- [ ] **Step 3: Run the frontend targeted checks**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx src/app/dashboard/interviews/session-page.test.tsx && pnpm tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Run the golden-path manual verification**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && bash src/scripts/dev_api_and_worker.sh
```

Expected:
- backend starts cleanly
- worker starts cleanly
- HR publish returns a share link
- candidate joins the room
- AI opening audio is heard in the room
- candidate speech produces at least one AI audio reply
- transcript turns appear on `/dashboard/interviews/<sessionId>`

- [ ] **Step 5: Fix any issue found during verification, then rerun only the affected checks**

```bash
# examples
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py -k review
cd "/home/eddiesngu/Desktop/Dang/interviewx/worker" && uv run pytest -q tests/test_agent_smoke.py -k runtime_handler_posts
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && pnpm vitest run src/components/interview/candidate-join.test.tsx
```

- [ ] **Step 6: Commit the verification fixes**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/services/interview_session_service.py worker/src/agent.py frontend/src/components/interview/live-room.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "fix: finish realtime interview first conversation flow"
```

---

## Self-Review

- **Spec coverage:** The plan covers LiveKit Cloud env bootstrapping, hybrid worker runtime, Gemini Live end-to-end audio loop, AI opening turn, transcript persistence, candidate error UX, and HR review flow. No spec gap remains for the agreed slice.
- **Placeholder scan:** Removed `TBD`, `TODO`, and vague test instructions. Each task contains explicit files, code, commands, and expected outcomes.
- **Type consistency:** `provider_event_id`, `worker_dispatch_token`, `InterviewRuntimeEventRequest`, `InterviewSessionDetailResponse`, and `InterviewSessionReviewResponse` are defined before later tasks use them.
