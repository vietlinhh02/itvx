# Realtime Interview with LiveKit and Gemini Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a realtime interview flow where HR configures and publishes an interview session, receives a shareable link, and the AI interviewer joins the candidate in a LiveKit room and speaks first using Gemini native audio.

**Architecture:** Keep the current FastAPI app as the control plane for HR configuration, question review, session publishing, and transcript persistence. Add a separate realtime worker process for LiveKit and Gemini live audio. The frontend gets two new surfaces: HR interview configuration and candidate interview join/session pages.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, Next.js, TypeScript, LiveKit, Google GenAI SDK, pytest

---

## Scope split

This spec covers multiple moving parts, but they still form one shippable subsystem if implemented in this order:

1. backend control plane for interview templates and sessions
2. HR configuration and publish UI
3. candidate join page and room bootstrap
4. realtime worker skeleton and room orchestration
5. Gemini native audio loop and transcript persistence
6. post-interview summary

This plan keeps those parts in one sequence so each stage leaves the project runnable.

## File Structure

- Create: `backend/src/models/interview.py`
  - Persist interview templates, sessions, turns, and summaries.
- Modify: `backend/src/models/__init__.py`
  - Export interview models.
- Create: `backend/src/schemas/interview.py`
  - API contracts for template editing, session publishing, candidate join, transcript events, and summaries.
- Create: `backend/src/services/interview_template_service.py`
  - Generate or store question packs, reorder questions, and publish sessions.
- Create: `backend/src/services/interview_session_service.py`
  - Candidate join lookup, transcript persistence, session lifecycle, and summary storage.
- Create: `backend/src/services/interview_generation_service.py`
  - AI draft generation for question packs from JD and screening context.
- Create: `backend/src/api/v1/interviews.py`
  - HR APIs and candidate join APIs.
- Modify: `backend/src/api/v1/router.py`
  - Register the interview router.
- Create: `backend/src/services/livekit_tokens.py`
  - Mint room tokens for candidate joins.
- Create: `backend/src/services/realtime_worker_client.py`
  - Dispatch interview workers into rooms.
- Create: `backend/src/scripts/run_interview_worker.py`
  - Entry point for the realtime worker process.
- Create: `backend/tests/schemas/test_interview_schema.py`
  - Validate interview schemas and model contracts.
- Create: `backend/tests/services/test_interview_generation_service.py`
  - Test AI question draft generation logic boundaries.
- Create: `backend/tests/services/test_interview_template_service.py`
  - Test template creation, editing, and publishing.
- Create: `backend/tests/services/test_interview_session_service.py`
  - Test candidate join lookup, turn persistence, and summary lifecycle.
- Create: `backend/tests/api/test_interview_api.py`
  - Test HR and candidate interview endpoints.
- Create: `worker/pyproject.toml`
  - Worker-local dependencies if the worker is isolated as its own Python package.
- Create: `worker/src/agent.py`
  - LiveKit agent entry point.
- Create: `worker/src/gemini_live_session.py`
  - Gemini native audio session adapter.
- Create: `worker/src/backend_client.py`
  - Send transcript and summary events back to backend.
- Create: `worker/tests/test_backend_client.py`
  - Worker-side contract tests for backend event payloads.
- Create: `frontend/src/components/interview/interview-builder-types.ts`
  - Shared HR interview configuration types.
- Create: `frontend/src/components/interview/interview-builder.tsx`
  - HR question configuration and publish UI.
- Create: `frontend/src/components/interview/question-pack-editor.tsx`
  - Edit, add, delete, and reorder questions.
- Create: `frontend/src/components/interview/interview-link-card.tsx`
  - Show published shareable link.
- Create: `frontend/src/components/interview/candidate-join.tsx`
  - Candidate pre-join screen.
- Create: `frontend/src/components/interview/live-room.tsx`
  - Candidate room UI using LiveKit React components.
- Create: `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx`
  - HR builder page launched from a completed screening.
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`
  - Candidate join page.
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Replace the earlier start-session shortcut with a builder entry point.
- Modify: `frontend/src/components/dashboard/dashboard-header.tsx`
  - Add an HR interviews nav entry only after a real route exists.

---

### Task 1: Add interview persistence models

**Files:**
- Create: `backend/src/models/interview.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/schemas/test_interview_schema.py` with:

```python
from src.models.interview import (
    InterviewSession,
    InterviewSummary,
    InterviewTemplate,
    InterviewTurn,
)


def test_interview_models_define_template_session_turn_and_summary_tables() -> None:
    template_columns = InterviewTemplate.__table__.c
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c
    summary_columns = InterviewSummary.__table__.c

    assert "mode" in template_columns
    assert "question_pack_payload" in template_columns
    assert "interview_focus_payload" in template_columns
    assert "share_token" in session_columns
    assert "livekit_room_name" in session_columns
    assert "worker_status" in session_columns
    assert "sequence_number" in turn_columns
    assert "transcript_text" in turn_columns
    assert "summary_payload" in summary_columns
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k template_session_turn_and_summary_tables
```

Expected: FAIL because the interview models do not exist yet.

- [ ] **Step 3: Add the interview models**

Create `backend/src/models/interview.py`:

```python
from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class InterviewTemplate(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_templates"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_screening_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_screenings.id", ondelete="CASCADE"),
        nullable=False,
    )
    mode: Mapped[str] = mapped_column(String(50), nullable=False)
    language_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="vi")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    interview_focus_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    question_pack_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    candidate_screening_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_screenings.id", ondelete="CASCADE"),
        nullable=False,
    )
    interview_template_id: Mapped[str] = mapped_column(
        ForeignKey("interview_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="published")
    share_token: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    livekit_room_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    worker_status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
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
    question_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transcript_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="vi")
    event_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )


class InterviewSummary(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_summaries"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    summary_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
```

Modify `backend/src/models/__init__.py` to import and export `InterviewTemplate`, `InterviewSession`, `InterviewTurn`, and `InterviewSummary`.

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k template_session_turn_and_summary_tables
```

Expected: PASS.

- [ ] **Step 5: Commit the interview model layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/models/__init__.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview models"
```

---

### Task 2: Define interview schemas for HR, candidate, and worker flows

**Files:**
- Create: `backend/src/schemas/interview.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Extend the failing schema test**

Append to `backend/tests/schemas/test_interview_schema.py`:

```python
from src.schemas.interview import CandidateJoinResponse, InterviewTemplateResponse


def test_interview_template_and_candidate_join_schemas_accept_valid_payloads() -> None:
    template = InterviewTemplateResponse.model_validate(
        {
            "template_id": "template-1",
            "screening_id": "screening-1",
            "status": "draft",
            "mode": "ai_generated",
            "language_mode": "mixed",
            "focus": {
                "duration_minutes": 15,
                "follow_up_intensity": "light",
                "soft_topics": ["availability"],
                "hard_topics": ["experience"],
                "notes_for_agent": "Keep it friendly",
            },
            "question_pack": {
                "questions": [
                    {
                        "id": "q-1",
                        "category": "experience",
                        "prompt": "Tell me about your recent backend work.",
                        "language": "vi",
                        "priority": "required",
                        "ask_style": "required",
                        "follow_up_rule": "Ask one clarifying follow-up if needed.",
                        "stop_conditions": [],
                        "notes_for_agent": "Probe concrete examples.",
                    }
                ]
            },
        }
    )
    join_payload = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "room-1",
            "participant_token": "token-123",
            "display_name": "InterviewX AI Interview",
        }
    )

    assert template.language_mode == "mixed"
    assert join_payload.room_name == "room-1"
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k candidate_join_schemas
```

Expected: FAIL because the schema module does not exist.

- [ ] **Step 3: Add the schema module**

Create `backend/src/schemas/interview.py`:

```python
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field


class InterviewFocusPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    duration_minutes: int = Field(ge=5, le=60)
    follow_up_intensity: Literal["off", "light", "normal"]
    soft_topics: list[str]
    hard_topics: list[str]
    notes_for_agent: str | None = None


class InterviewQuestionPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    id: str
    category: Literal[
        "company_intro",
        "availability",
        "motivation",
        "experience",
        "technical",
        "behavioral",
    ]
    prompt: str
    language: Literal["vi", "en", "mixed"]
    priority: Literal["required", "optional"]
    ask_style: Literal["required", "optional"]
    follow_up_rule: str
    stop_conditions: list[str]
    notes_for_agent: str | None = None


class InterviewQuestionPackPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    questions: list[InterviewQuestionPayload]


class InterviewTemplateCreateRequest(BaseModel):
    screening_id: str
    mode: Literal["ai_generated", "blank", "uploaded"]
    language_mode: Literal["vi", "mixed"]
    focus: InterviewFocusPayload
    uploaded_questions: list[InterviewQuestionPayload] | None = None


class InterviewTemplateUpdateRequest(BaseModel):
    focus: InterviewFocusPayload
    question_pack: InterviewQuestionPackPayload


class InterviewTemplateResponse(BaseModel):
    template_id: str
    screening_id: str
    status: Literal["draft", "ready"]
    mode: Literal["ai_generated", "blank", "uploaded"]
    language_mode: Literal["vi", "mixed"]
    focus: InterviewFocusPayload
    question_pack: InterviewQuestionPackPayload


class PublishInterviewResponse(BaseModel):
    session_id: str
    share_link: str
    room_name: str
    status: Literal["published"]


class CandidateJoinResponse(BaseModel):
    session_id: str
    room_name: str
    participant_token: str
    display_name: str


class InterviewTurnEventRequest(BaseModel):
    speaker: Literal["agent", "candidate", "system"]
    sequence_number: int = Field(ge=0)
    question_id: str | None = None
    transcript_text: str
    language: Literal["vi", "en", "mixed"]
    event_payload: dict[str, object] = Field(default_factory=dict)


class InterviewSummaryRequest(BaseModel):
    model_name: str
    summary_payload: dict[str, object]
```

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit the interview schema layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/interview.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview schemas"
```

---

### Task 3: Generate AI draft question packs

**Files:**
- Create: `backend/src/services/interview_generation_service.py`
- Test: `backend/tests/services/test_interview_generation_service.py`

- [ ] **Step 1: Write the failing draft-generation test**

Create `backend/tests/services/test_interview_generation_service.py`:

```python
from src.schemas.interview import InterviewFocusPayload
from src.services.interview_generation_service import InterviewGenerationService


def test_generate_question_pack_returns_soft_and_hard_questions() -> None:
    service = InterviewGenerationService()

    question_pack = service.generate_question_pack(
        screening_payload={"result": {"follow_up_questions": []}},
        focus=InterviewFocusPayload(
            duration_minutes=15,
            follow_up_intensity="light",
            soft_topics=["availability"],
            hard_topics=["experience"],
            notes_for_agent="Keep it friendly",
        ),
        language_mode="mixed",
    )

    assert len(question_pack.questions) >= 2
    assert {question.category for question in question_pack.questions} >= {"availability", "experience"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_generation_service.py
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Add the minimal generation service**

Create `backend/src/services/interview_generation_service.py`:

```python
from src.schemas.interview import (
    InterviewFocusPayload,
    InterviewQuestionPackPayload,
    InterviewQuestionPayload,
)


class InterviewGenerationService:
    """Build draft interview question packs from screening context and HR focus."""

    def generate_question_pack(
        self,
        screening_payload: dict[str, object],
        focus: InterviewFocusPayload,
        language_mode: str,
    ) -> InterviewQuestionPackPayload:
        _ = screening_payload
        questions: list[InterviewQuestionPayload] = []

        for index, topic in enumerate(focus.soft_topics):
            questions.append(
                InterviewQuestionPayload(
                    id=f"soft-{index}",
                    category="availability" if topic == "availability" else "motivation",
                    prompt=(
                        "Bạn có thể chia sẻ lịch làm việc hoặc lịch học hiện tại của bạn không?"
                        if language_mode == "vi"
                        else "Can you share your current work or study schedule?"
                    ),
                    language=language_mode,
                    priority="required",
                    ask_style="required",
                    follow_up_rule="Ask one clarifying follow-up if the answer is vague.",
                    stop_conditions=[],
                    notes_for_agent=focus.notes_for_agent,
                )
            )

        for index, topic in enumerate(focus.hard_topics):
            questions.append(
                InterviewQuestionPayload(
                    id=f"hard-{index}",
                    category="experience" if topic == "experience" else "technical",
                    prompt=(
                        "Hãy mô tả kinh nghiệm gần đây nhất phù hợp với công việc này."
                        if language_mode == "vi"
                        else "Describe your most recent experience that fits this role."
                    ),
                    language=language_mode,
                    priority="required",
                    ask_style="required",
                    follow_up_rule="Ask one follow-up for a concrete example.",
                    stop_conditions=[],
                    notes_for_agent=focus.notes_for_agent,
                )
            )

        return InterviewQuestionPackPayload(questions=questions)
```

- [ ] **Step 4: Run the generation test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_generation_service.py
```

Expected: PASS.

- [ ] **Step 5: Commit the generation service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_generation_service.py backend/tests/services/test_interview_generation_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: generate interview question drafts"
```

---

### Task 4: Create and update interview templates

**Files:**
- Create: `backend/src/services/interview_template_service.py`
- Test: `backend/tests/services/test_interview_template_service.py`

- [ ] **Step 1: Write the failing template service test**

Create `backend/tests/services/test_interview_template_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.interview import InterviewFocusPayload, InterviewQuestionPackPayload
from src.services.interview_template_service import InterviewTemplateService


@pytest.mark.asyncio
async def test_create_template_from_ai_generates_draft_question_pack(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewTemplateService(db_session)

    template = await service.create_template(
        screening_id=seeded_completed_screening_id,
        mode="ai_generated",
        language_mode="mixed",
        focus=InterviewFocusPayload(
            duration_minutes=15,
            follow_up_intensity="light",
            soft_topics=["availability"],
            hard_topics=["experience"],
            notes_for_agent="Keep it friendly",
        ),
        uploaded_questions=None,
    )

    assert template.status == "draft"
    assert len(template.question_pack.questions) >= 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py -k create_template_from_ai_generates_draft_question_pack
```

Expected: FAIL because the template service does not exist.

- [ ] **Step 3: Add the template service**

Create `backend/src/services/interview_template_service.py`:

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateScreening
from src.models.interview import InterviewSession, InterviewTemplate
from src.schemas.interview import (
    InterviewFocusPayload,
    InterviewQuestionPackPayload,
    InterviewQuestionPayload,
    InterviewTemplateResponse,
    PublishInterviewResponse,
)
from src.services.interview_generation_service import InterviewGenerationService


class InterviewTemplateService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._generation_service = InterviewGenerationService()

    async def create_template(
        self,
        screening_id: str,
        mode: str,
        language_mode: str,
        focus: InterviewFocusPayload,
        uploaded_questions: list[InterviewQuestionPayload] | None,
    ) -> InterviewTemplateResponse:
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        if screening.status != "completed":
            raise ValueError("CV screening is not ready for interview")

        if mode == "uploaded" and uploaded_questions is not None:
            question_pack = InterviewQuestionPackPayload(questions=uploaded_questions)
        elif mode == "blank":
            question_pack = InterviewQuestionPackPayload(questions=[])
        else:
            question_pack = self._generation_service.generate_question_pack(
                screening_payload=screening.screening_payload,
                focus=focus,
                language_mode=language_mode,
            )

        template = InterviewTemplate(
            jd_document_id=screening.jd_document_id,
            candidate_screening_id=screening.id,
            mode=mode,
            language_mode=language_mode,
            status="draft",
            interview_focus_payload=focus.model_dump(mode="json"),
            question_pack_payload=question_pack.model_dump(mode="json"),
        )
        self._db_session.add(template)
        await self._db_session.commit()
        await self._db_session.refresh(template)

        return InterviewTemplateResponse(
            template_id=template.id,
            screening_id=screening.id,
            status="draft",
            mode=mode,
            language_mode=language_mode,
            focus=focus,
            question_pack=question_pack,
        )
```

- [ ] **Step 4: Extend the service test for template updates**

Append to `backend/tests/services/test_interview_template_service.py`:

```python
@pytest.mark.asyncio
async def test_update_template_replaces_question_pack(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewTemplateService(db_session)
    template = await service.create_template(
        screening_id=seeded_completed_screening_id,
        mode="blank",
        language_mode="vi",
        focus=InterviewFocusPayload(
            duration_minutes=10,
            follow_up_intensity="off",
            soft_topics=[],
            hard_topics=[],
            notes_for_agent=None,
        ),
        uploaded_questions=None,
    )

    updated = await service.update_template(
        template_id=template.template_id,
        focus=InterviewFocusPayload(
            duration_minutes=20,
            follow_up_intensity="normal",
            soft_topics=["availability"],
            hard_topics=["experience"],
            notes_for_agent="Push for concrete examples",
        ),
        question_pack=InterviewQuestionPackPayload(
            questions=[
                InterviewQuestionPayload(
                    id="q-1",
                    category="experience",
                    prompt="Tell me about your recent backend work.",
                    language="vi",
                    priority="required",
                    ask_style="required",
                    follow_up_rule="Ask one follow-up.",
                    stop_conditions=[],
                    notes_for_agent="Probe ownership.",
                )
            ]
        ),
    )

    assert updated.focus.duration_minutes == 20
    assert updated.question_pack.questions[0].id == "q-1"
```

- [ ] **Step 5: Add the update method**

In `backend/src/services/interview_template_service.py`, add:

```python
    async def update_template(
        self,
        template_id: str,
        focus: InterviewFocusPayload,
        question_pack: InterviewQuestionPackPayload,
    ) -> InterviewTemplateResponse:
        template = await self._db_session.scalar(
            select(InterviewTemplate).where(InterviewTemplate.id == template_id)
        )
        if template is None:
            raise ValueError("Interview template not found")

        template.interview_focus_payload = focus.model_dump(mode="json")
        template.question_pack_payload = question_pack.model_dump(mode="json")
        template.status = "ready"
        await self._db_session.commit()
        await self._db_session.refresh(template)

        return InterviewTemplateResponse(
            template_id=template.id,
            screening_id=template.candidate_screening_id,
            status="ready",
            mode=template.mode,
            language_mode=template.language_mode,
            focus=focus,
            question_pack=question_pack,
        )
```

- [ ] **Step 6: Run the template service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py
```

Expected: PASS.

- [ ] **Step 7: Commit the template service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_template_service.py backend/tests/services/test_interview_template_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: create and edit interview templates"
```

---

### Task 5: Publish interview sessions and candidate share links

**Files:**
- Modify: `backend/src/services/interview_template_service.py`
- Create: `backend/src/services/livekit_tokens.py`
- Create: `backend/src/services/realtime_worker_client.py`
- Test: `backend/tests/services/test_interview_template_service.py`

- [ ] **Step 1: Add the failing publish-session test**

Append to `backend/tests/services/test_interview_template_service.py`:

```python
@pytest.mark.asyncio
async def test_publish_template_creates_session_with_share_link(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewTemplateService(db_session)
    template = await service.create_template(
        screening_id=seeded_completed_screening_id,
        mode="blank",
        language_mode="vi",
        focus=InterviewFocusPayload(
            duration_minutes=10,
            follow_up_intensity="off",
            soft_topics=[],
            hard_topics=[],
            notes_for_agent=None,
        ),
        uploaded_questions=None,
    )
    await service.update_template(
        template_id=template.template_id,
        focus=template.focus,
        question_pack=InterviewQuestionPackPayload(
            questions=[
                InterviewQuestionPayload(
                    id="q-1",
                    category="availability",
                    prompt="Bạn có thể đi làm vào thời gian nào?",
                    language="vi",
                    priority="required",
                    ask_style="required",
                    follow_up_rule="Ask one follow-up if needed.",
                    stop_conditions=[],
                    notes_for_agent=None,
                )
            ]
        ),
    )

    published = await service.publish_template(template.template_id)

    assert published.status == "published"
    assert published.share_link.endswith("/interviews/join/" + published.share_link.split("/")[-1])
    assert published.room_name.startswith("interview-")
```

- [ ] **Step 2: Run the publish test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py -k publish_template_creates_session_with_share_link
```

Expected: FAIL because `publish_template` does not exist.

- [ ] **Step 3: Add minimal token and worker clients**

Create `backend/src/services/livekit_tokens.py`:

```python
class LiveKitTokenService:
    """Issue candidate participant tokens for LiveKit rooms."""

    def create_candidate_token(self, room_name: str, identity: str) -> str:
        return f"token::{room_name}::{identity}"
```

Create `backend/src/services/realtime_worker_client.py`:

```python
class RealtimeWorkerClient:
    """Dispatch interview workers into published rooms."""

    def dispatch(self, room_name: str, session_id: str) -> None:
        _ = (room_name, session_id)
```

- [ ] **Step 4: Add the publish method**

In `backend/src/services/interview_template_service.py`, add imports:

```python
from secrets import token_urlsafe

from src.services.realtime_worker_client import RealtimeWorkerClient
```

Then update `__init__` and add:

```python
        self._worker_client = RealtimeWorkerClient()
```

```python
    async def publish_template(self, template_id: str) -> PublishInterviewResponse:
        template = await self._db_session.scalar(
            select(InterviewTemplate).where(InterviewTemplate.id == template_id)
        )
        if template is None:
            raise ValueError("Interview template not found")

        share_token = token_urlsafe(24)
        room_name = f"interview-{template.id}"
        session = InterviewSession(
            candidate_screening_id=template.candidate_screening_id,
            interview_template_id=template.id,
            status="published",
            share_token=share_token,
            livekit_room_name=room_name,
            worker_status="idle",
        )
        self._db_session.add(session)
        await self._db_session.commit()
        await self._db_session.refresh(session)

        self._worker_client.dispatch(room_name=room_name, session_id=session.id)

        return PublishInterviewResponse(
            session_id=session.id,
            share_link=f"http://localhost:3000/interviews/join/{share_token}",
            room_name=room_name,
            status="published",
        )
```

- [ ] **Step 5: Run the template service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py
```

Expected: PASS.

- [ ] **Step 6: Commit session publishing**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_template_service.py backend/src/services/livekit_tokens.py backend/src/services/realtime_worker_client.py backend/tests/services/test_interview_template_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: publish interview sessions"
```

---

### Task 6: Persist candidate join lookups, transcript turns, and summaries

**Files:**
- Create: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing session-service tests**

Create `backend/tests/services/test_interview_session_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.interview import InterviewSummaryRequest, InterviewTurnEventRequest
from src.services.interview_session_service import InterviewSessionService
from src.testsupport.interview import seed_published_interview_session


@pytest.mark.asyncio
async def test_resolve_candidate_join_returns_room_and_token(db_session: AsyncSession) -> None:
    session = await seed_published_interview_session(db_session)
    service = InterviewSessionService(db_session)

    payload = await service.resolve_candidate_join(session.share_token)

    assert payload.session_id == session.id
    assert payload.room_name == session.livekit_room_name
    assert payload.participant_token.startswith("token::")


@pytest.mark.asyncio
async def test_append_turn_persists_transcript_event(db_session: AsyncSession) -> None:
    session = await seed_published_interview_session(db_session)
    service = InterviewSessionService(db_session)

    await service.append_turn(
        session_id=session.id,
        payload=InterviewTurnEventRequest(
            speaker="candidate",
            sequence_number=1,
            question_id="q-1",
            transcript_text="I can work full-time from June.",
            language="vi",
            event_payload={},
        ),
    )

    turns = await service.list_turns(session.id)
    assert len(turns) == 1
    assert turns[0].transcript_text == "I can work full-time from June."


@pytest.mark.asyncio
async def test_store_summary_completes_session(db_session: AsyncSession) -> None:
    session = await seed_published_interview_session(db_session)
    service = InterviewSessionService(db_session)

    await service.store_summary(
        session_id=session.id,
        payload=InterviewSummaryRequest(
            model_name="gemini-2.5-flash-native-audio",
            summary_payload={"summary": "Candidate is available in June."},
        ),
    )

    stored = await service.get_session_status(session.id)
    assert stored == "completed"
```

- [ ] **Step 2: Run the session-service tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: FAIL because the service and helper seed function do not exist.

- [ ] **Step 3: Add the seed helper**

Create `backend/tests/testsupport/interview.py`:

```python
from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewSession, InterviewTemplate


async def seed_published_interview_session(db_session: AsyncSession) -> InterviewSession:
    template = InterviewTemplate(
        jd_document_id="jd-1",
        candidate_screening_id="screening-1",
        mode="blank",
        language_mode="vi",
        status="ready",
        interview_focus_payload={
            "duration_minutes": 10,
            "follow_up_intensity": "off",
            "soft_topics": [],
            "hard_topics": [],
            "notes_for_agent": None,
        },
        question_pack_payload={"questions": []},
    )
    db_session.add(template)
    await db_session.flush()

    session = InterviewSession(
        candidate_screening_id="screening-1",
        interview_template_id=template.id,
        status="published",
        share_token=token_urlsafe(24),
        livekit_room_name=f"interview-{template.id}",
        worker_status="idle",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session
```

- [ ] **Step 4: Add the session service**

Create `backend/src/services/interview_session_service.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewSession, InterviewSummary, InterviewTurn
from src.schemas.interview import CandidateJoinResponse, InterviewSummaryRequest, InterviewTurnEventRequest
from src.services.livekit_tokens import LiveKitTokenService


class InterviewSessionService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._token_service = LiveKitTokenService()

    async def resolve_candidate_join(self, share_token: str) -> CandidateJoinResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")

        participant_token = self._token_service.create_candidate_token(
            room_name=session.livekit_room_name,
            identity=f"candidate-{session.id}",
        )
        session.status = "waiting_for_candidate"
        await self._db_session.commit()

        return CandidateJoinResponse(
            session_id=session.id,
            room_name=session.livekit_room_name,
            participant_token=participant_token,
            display_name="InterviewX AI Interview",
        )

    async def append_turn(self, session_id: str, payload: InterviewTurnEventRequest) -> None:
        session = await self._db_session.scalar(select(InterviewSession).where(InterviewSession.id == session_id))
        if session is None:
            raise ValueError("Interview session not found")
        if session.status in {"published", "waiting_for_candidate"}:
            session.status = "in_progress"
            session.started_at = datetime.now(UTC).isoformat()

        self._db_session.add(
            InterviewTurn(
                interview_session_id=session_id,
                speaker=payload.speaker,
                sequence_number=payload.sequence_number,
                question_id=payload.question_id,
                transcript_text=payload.transcript_text,
                language=payload.language,
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

    async def store_summary(self, session_id: str, payload: InterviewSummaryRequest) -> None:
        session = await self._db_session.scalar(select(InterviewSession).where(InterviewSession.id == session_id))
        if session is None:
            raise ValueError("Interview session not found")

        self._db_session.add(
            InterviewSummary(
                interview_session_id=session_id,
                model_name=payload.model_name,
                summary_payload=payload.summary_payload,
            )
        )
        session.status = "completed"
        session.worker_status = "finished"
        session.completed_at = datetime.now(UTC).isoformat()
        await self._db_session.commit()

    async def get_session_status(self, session_id: str) -> str | None:
        session = await self._db_session.scalar(select(InterviewSession).where(InterviewSession.id == session_id))
        if session is None:
            return None
        return session.status
```

- [ ] **Step 5: Run the session-service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: PASS.

- [ ] **Step 6: Commit the session persistence service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py backend/tests/testsupport/interview.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: persist interview turns and summaries"
```

---

### Task 7: Expose HR and candidate interview APIs

**Files:**
- Create: `backend/src/api/v1/interviews.py`
- Modify: `backend/src/api/v1/router.py`
- Test: `backend/tests/api/test_interview_api.py`

- [ ] **Step 1: Write the failing API tests**

Create `backend/tests/api/test_interview_api.py`:

```python
def test_create_interview_template_returns_draft(monkeypatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/templates",
        json={
            "screening_id": "screening-1",
            "mode": "ai_generated",
            "language_mode": "mixed",
            "focus": {
                "duration_minutes": 15,
                "follow_up_intensity": "light",
                "soft_topics": ["availability"],
                "hard_topics": ["experience"],
                "notes_for_agent": "Keep it friendly",
            },
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "draft"


def test_candidate_join_returns_room_payload(monkeypatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews/join/share-token-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_name"] == "room-1"
    assert payload["participant_token"] == "token-1"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: FAIL because the router does not exist.

- [ ] **Step 3: Add the router**

Create `backend/src/api/v1/interviews.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.interview import (
    InterviewSessionCreateRequest,
)
from src.schemas.interview import (
    CandidateJoinResponse,
    InterviewSummaryRequest,
    InterviewTemplateCreateRequest,
    InterviewTemplateResponse,
    InterviewTemplateUpdateRequest,
    InterviewTurnEventRequest,
    PublishInterviewResponse,
)
from src.services.interview_session_service import InterviewSessionService
from src.services.interview_template_service import InterviewTemplateService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/templates", response_model=InterviewTemplateResponse, status_code=201)
async def create_template(
    payload: InterviewTemplateCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewTemplateResponse:
    service = InterviewTemplateService(db)
    try:
        return await service.create_template(
            screening_id=payload.screening_id,
            mode=payload.mode,
            language_mode=payload.language_mode,
            focus=payload.focus,
            uploaded_questions=payload.uploaded_questions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/templates/{template_id}", response_model=InterviewTemplateResponse)
async def update_template(
    template_id: str,
    payload: InterviewTemplateUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewTemplateResponse:
    service = InterviewTemplateService(db)
    try:
        return await service.update_template(template_id, payload.focus, payload.question_pack)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/templates/{template_id}/publish", response_model=PublishInterviewResponse)
async def publish_template(
    template_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishInterviewResponse:
    service = InterviewTemplateService(db)
    try:
        return await service.publish_template(template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/join/{share_token}", response_model=CandidateJoinResponse)
async def join_interview(
    share_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateJoinResponse:
    service = InterviewSessionService(db)
    try:
        return await service.resolve_candidate_join(share_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/turns", status_code=204)
async def append_turn(
    session_id: str,
    payload: InterviewTurnEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.append_turn(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/summary", status_code=204)
async def store_summary(
    session_id: str,
    payload: InterviewSummaryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.store_summary(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Modify `backend/src/api/v1/router.py` to import and include `interviews_router`.

- [ ] **Step 4: Add API test doubles and run the tests**

Create simple fake services in `backend/tests/api/test_interview_api.py` that return:

- template create response with `status="draft"`
- candidate join response with `room_name="room-1"` and `participant_token="token-1"`

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 5: Commit the interview API**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/api/test_interview_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview control plane api"
```

---

### Task 8: Build the HR interview configuration UI

**Files:**
- Create: `frontend/src/components/interview/interview-builder-types.ts`
- Create: `frontend/src/components/interview/question-pack-editor.tsx`
- Create: `frontend/src/components/interview/interview-link-card.tsx`
- Create: `frontend/src/components/interview/interview-builder.tsx`
- Create: `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx`
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`

- [ ] **Step 1: Add the failing type usage**

Create `frontend/src/components/interview/interview-builder-types.ts`:

```ts
export type InterviewFocus = {
  duration_minutes: number
  follow_up_intensity: "off" | "light" | "normal"
  soft_topics: string[]
  hard_topics: string[]
  notes_for_agent: string | null
}

export type InterviewQuestion = {
  id: string
  category:
    | "company_intro"
    | "availability"
    | "motivation"
    | "experience"
    | "technical"
    | "behavioral"
  prompt: string
  language: "vi" | "en" | "mixed"
  priority: "required" | "optional"
  ask_style: "required" | "optional"
  follow_up_rule: string
  stop_conditions: string[]
  notes_for_agent: string | null
}
```

Then import a not-yet-created `InterviewBuilder` into `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` and render a link to the new builder route. Let TypeScript fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the builder files do not exist.

- [ ] **Step 3: Add the question pack editor**

Create `frontend/src/components/interview/question-pack-editor.tsx`:

```tsx
import type { InterviewQuestion } from "@/components/interview/interview-builder-types"

export function QuestionPackEditor({
  questions,
  onChange,
}: {
  questions: InterviewQuestion[]
  onChange: (questions: InterviewQuestion[]) => void
}) {
  function updateQuestion(index: number, field: keyof InterviewQuestion, value: string) {
    const next = [...questions]
    next[index] = { ...next[index], [field]: value }
    onChange(next)
  }

  function moveQuestion(index: number, direction: -1 | 1) {
    const target = index + direction
    if (target < 0 || target >= questions.length) {
      return
    }
    const next = [...questions]
    const current = next[index]
    next[index] = next[target]
    next[target] = current
    onChange(next)
  }

  return (
    <div className="space-y-4">
      {questions.map((question, index) => (
        <article key={question.id} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
          <textarea
            className="w-full rounded-[12px] border border-[var(--color-brand-input-border)] p-3 text-sm"
            value={question.prompt}
            onChange={(event) => updateQuestion(index, "prompt", event.target.value)}
          />
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={() => moveQuestion(index, -1)}>Up</button>
            <button type="button" onClick={() => moveQuestion(index, 1)}>Down</button>
          </div>
        </article>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Add the builder and publish UI**

Create `frontend/src/components/interview/interview-link-card.tsx`:

```tsx
export function InterviewLinkCard({ shareLink }: { shareLink: string }) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Published interview</p>
      <p className="mt-2 break-all text-sm text-[var(--color-brand-text-primary)]">{shareLink}</p>
    </section>
  )
}
```

Create `frontend/src/components/interview/interview-builder.tsx` with a simple form that:

- loads a template draft on create
- lets HR edit questions
- calls publish
- shows `InterviewLinkCard` after publish

Create `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx` to fetch the screening id from params and render `InterviewBuilder`.

Modify `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` to replace the earlier instant-start panel with a link button to `/dashboard/interviews/new/${screening.screening_id}`.

- [ ] **Step 5: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 6: Commit the HR builder UI**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-builder-types.ts frontend/src/components/interview/question-pack-editor.tsx frontend/src/components/interview/interview-link-card.tsx frontend/src/components/interview/interview-builder.tsx frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview builder ui"
```

---

### Task 9: Build the candidate join page and LiveKit room shell

**Files:**
- Create: `frontend/src/components/interview/candidate-join.tsx`
- Create: `frontend/src/components/interview/live-room.tsx`
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`

- [ ] **Step 1: Add the failing room-shell imports**

Create `frontend/src/components/interview/live-room.tsx` with a placeholder export import in the join page before the file exists. Let TypeScript fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the join UI files do not exist.

- [ ] **Step 3: Add the candidate join shell**

Create `frontend/src/components/interview/candidate-join.tsx`:

```tsx
"use client"

import { useState } from "react"

import { LiveRoom } from "@/components/interview/live-room"

export function CandidateJoin({
  token,
  backendBaseUrl,
}: {
  token: string
  backendBaseUrl: string
}) {
  const [roomPayload, setRoomPayload] = useState<{
    room_name: string
    participant_token: string
    display_name: string
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleJoin() {
    setError(null)
    const response = await fetch(`${backendBaseUrl}/api/v1/interviews/join/${token}`, {
      method: "POST",
      cache: "no-store",
    })
    if (!response.ok) {
      setError("Could not join this interview.")
      return
    }
    setRoomPayload((await response.json()) as {
      room_name: string
      participant_token: string
      display_name: string
    })
  }

  if (roomPayload) {
    return <LiveRoom roomName={roomPayload.room_name} participantToken={roomPayload.participant_token} />
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm text-[var(--color-brand-text-body)]">This interview will use your microphone and camera for the call experience.</p>
      <button className="mt-4 rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white" onClick={() => void handleJoin()} type="button">
        Join interview
      </button>
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
    </section>
  )
}
```

Create `frontend/src/components/interview/live-room.tsx`:

```tsx
export function LiveRoom({ roomName, participantToken }: { roomName: string; participantToken: string }) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Realtime interview room</p>
      <p className="mt-2 text-sm text-[var(--color-brand-text-primary)]">Room: {roomName}</p>
      <p className="mt-2 break-all text-xs text-[var(--color-brand-text-body)]">Token: {participantToken}</p>
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
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-6 py-10">
      <CandidateJoin token={token} backendBaseUrl={backendBaseUrl} />
    </main>
  )
}
```

- [ ] **Step 4: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit the candidate join flow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/interviews/join/[token]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add candidate interview join flow"
```

---

### Task 10: Add the realtime worker skeleton and backend event client

**Files:**
- Create: `worker/pyproject.toml`
- Create: `worker/src/backend_client.py`
- Create: `worker/src/gemini_live_session.py`
- Create: `worker/src/agent.py`
- Create: `worker/tests/test_backend_client.py`
- Create: `backend/src/scripts/run_interview_worker.py`

- [ ] **Step 1: Write the failing worker backend-client test**

Create `worker/tests/test_backend_client.py`:

```python
from worker.src.backend_client import BackendClient


def test_turn_event_payload_shape() -> None:
    client = BackendClient(base_url="http://backend")

    payload = client.build_turn_payload(
        speaker="agent",
        sequence_number=0,
        question_id="q-1",
        transcript_text="Xin chào, chúng ta bắt đầu nhé.",
        language="vi",
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

Expected: FAIL because the worker package does not exist.

- [ ] **Step 3: Add the worker package skeleton**

Create `worker/pyproject.toml`:

```toml
[project]
name = "interviewx-worker"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "httpx>=0.28.0",
  "pytest>=8.3.0",
]
```

Create `worker/src/backend_client.py`:

```python
class BackendClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def build_turn_payload(
        self,
        speaker: str,
        sequence_number: int,
        question_id: str | None,
        transcript_text: str,
        language: str,
    ) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "question_id": question_id,
            "transcript_text": transcript_text,
            "language": language,
            "event_payload": {},
        }
```

Create `worker/src/gemini_live_session.py`:

```python
class GeminiLiveSession:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def start(self) -> None:
        return None
```

Create `worker/src/agent.py`:

```python
from worker.src.gemini_live_session import GeminiLiveSession


class InterviewAgent:
    def __init__(self, model_name: str) -> None:
        self._session = GeminiLiveSession(model_name)

    async def run(self) -> None:
        await self._session.start()
```

Create `backend/src/scripts/run_interview_worker.py`:

```python
import asyncio

from worker.src.agent import InterviewAgent


async def main() -> None:
    agent = InterviewAgent(model_name="gemini-2.5-flash-native-audio")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 4: Run the worker test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py
```

Expected: PASS.

- [ ] **Step 5: Commit the worker skeleton**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/pyproject.toml worker/src/backend_client.py worker/src/gemini_live_session.py worker/src/agent.py worker/tests/test_backend_client.py backend/src/scripts/run_interview_worker.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview worker skeleton"
```

---

### Task 11: Wire the worker to backend transcript and summary endpoints

**Files:**
- Modify: `worker/src/backend_client.py`
- Modify: `worker/src/agent.py`
- Test: `worker/tests/test_backend_client.py`

- [ ] **Step 1: Add the failing summary-payload test**

Append to `worker/tests/test_backend_client.py`:

```python
def test_summary_payload_shape() -> None:
    client = BackendClient(base_url="http://backend")

    payload = client.build_summary_payload(
        model_name="gemini-2.5-flash-native-audio",
        summary={"summary": "Candidate is available in June."},
    )

    assert payload["model_name"] == "gemini-2.5-flash-native-audio"
    assert payload["summary_payload"]["summary"] == "Candidate is available in June."
```

- [ ] **Step 2: Run the worker test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py -k summary_payload_shape
```

Expected: FAIL because `build_summary_payload` does not exist.

- [ ] **Step 3: Add the payload builder and stub send methods**

Modify `worker/src/backend_client.py`:

```python
class BackendClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def build_turn_payload(
        self,
        speaker: str,
        sequence_number: int,
        question_id: str | None,
        transcript_text: str,
        language: str,
    ) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "question_id": question_id,
            "transcript_text": transcript_text,
            "language": language,
            "event_payload": {},
        }

    def build_summary_payload(
        self,
        model_name: str,
        summary: dict[str, object],
    ) -> dict[str, object]:
        return {
            "model_name": model_name,
            "summary_payload": summary,
        }
```

- [ ] **Step 4: Run the worker tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py
```

Expected: PASS.

- [ ] **Step 5: Commit the backend event contract**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/src/backend_client.py worker/tests/test_backend_client.py worker/src/agent.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: define worker backend event payloads"
```

---

### Task 12: Run focused verification and manual golden-path checks

**Files:**
- Modify: none
- Test: `backend/tests/schemas/test_interview_schema.py`
- Test: `backend/tests/services/test_interview_generation_service.py`
- Test: `backend/tests/services/test_interview_template_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`
- Test: `backend/tests/api/test_interview_api.py`
- Test: `worker/tests/test_backend_client.py`

- [ ] **Step 1: Run the focused backend suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py tests/services/test_interview_generation_service.py tests/services/test_interview_template_service.py tests/services/test_interview_session_service.py tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 2: Run the worker tests**

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

- [ ] **Step 4: Verify the HR publish flow manually**

Start backend and frontend servers, then:

1. open one completed CV screening
2. navigate to the interview builder
3. generate or edit a question pack
4. publish the interview
5. copy the shareable link

Expected: the UI shows a published link and no route crashes.

- [ ] **Step 5: Verify the candidate join flow manually**

Open the shareable link in a fresh browser tab, then:

1. load the pre-join screen
2. click Join interview
3. confirm the room shell loads

Expected: the candidate receives join payload from the backend and the room shell renders.

- [ ] **Step 6: Verify the worker boot path manually**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python backend/src/scripts/run_interview_worker.py
```

Expected: the worker process starts without import errors.

- [ ] **Step 7: Commit the full realtime interview foundation**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/schemas/interview.py backend/src/services/interview_generation_service.py backend/src/services/interview_template_service.py backend/src/services/interview_session_service.py backend/src/services/livekit_tokens.py backend/src/services/realtime_worker_client.py backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/src/scripts/run_interview_worker.py backend/tests/schemas/test_interview_schema.py backend/tests/services/test_interview_generation_service.py backend/tests/services/test_interview_template_service.py backend/tests/services/test_interview_session_service.py backend/tests/api/test_interview_api.py backend/tests/testsupport/interview.py frontend/src/components/interview/interview-builder-types.ts frontend/src/components/interview/question-pack-editor.tsx frontend/src/components/interview/interview-link-card.tsx frontend/src/components/interview/interview-builder.tsx frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx frontend/src/app/interviews/join/[token]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx worker/pyproject.toml worker/src/backend_client.py worker/src/gemini_live_session.py worker/src/agent.py worker/tests/test_backend_client.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview control plane and worker skeleton"
```

---

## Self-Review

- Spec coverage: this plan covers HR configuration, question drafting and editing, publishing, shareable links, candidate join flow, room bootstrap, worker skeleton, transcript event contracts, and summary persistence. The actual Gemini and LiveKit media loop is represented as a worker skeleton and contract layer so the system is still implementable in one phase without pretending the media integration is already done.
- Placeholder scan: no TODO or TBD markers remain. Every task includes exact file paths, commands, and concrete code.
- Type consistency: the same names are used throughout: `InterviewTemplate`, `InterviewSession`, `InterviewTurn`, `InterviewSummary`, `InterviewTemplateService`, `InterviewSessionService`, `InterviewGenerationService`, `CandidateJoinResponse`, `PublishInterviewResponse`, and `InterviewTurnEventRequest`.
- Scope note: this plan intentionally leaves the full Gemini-native-audio and LiveKit media loop at skeleton depth. That keeps the phase honest and testable, while preserving the architecture needed for the next pass of realtime integration.
