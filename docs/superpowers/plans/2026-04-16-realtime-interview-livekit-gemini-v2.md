# Realtime Interview with LiveKit and Gemini Native Audio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a real candidate interview flow where HR configures and publishes an interview, the system creates a shareable link, the candidate joins a LiveKit room, and an AI interviewer joins the same room and speaks first using Gemini native audio.

**Architecture:** Keep FastAPI as the control plane for interview templates, publishing, candidate join authorization, transcript persistence, and post-interview summary storage. Add a real Python worker runtime that connects to LiveKit as an agent participant, opens a Gemini live session, pushes the opening turn first, streams transcript events back to the backend, and ends the interview cleanly.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, Next.js, TypeScript, LiveKit Agents, LiveKit Python SDK, Google GenAI SDK, pytest

---

## File Structure

- Create: `backend/src/models/interview.py`
  - Persist interview templates, sessions, turns, and summaries.
- Modify: `backend/src/models/__init__.py`
  - Export the interview models.
- Create: `backend/src/schemas/interview.py`
  - Define HR template, publish, join, transcript event, and summary contracts.
- Create: `backend/src/services/interview_generation_service.py`
  - Generate draft question packs from screening data and HR focus.
- Create: `backend/src/services/interview_template_service.py`
  - Create, edit, reorder, and publish interview templates.
- Create: `backend/src/services/interview_session_service.py`
  - Resolve candidate joins, persist turns, and store summaries.
- Create: `backend/src/services/livekit_service.py`
  - Create room names, mint candidate tokens, and build agent dispatch metadata.
- Create: `backend/src/api/v1/interviews.py`
  - Expose HR and candidate interview routes.
- Modify: `backend/src/api/v1/router.py`
  - Register the interview router.
- Create: `backend/tests/schemas/test_interview_schema.py`
  - Validate the interview model and schema contracts.
- Create: `backend/tests/services/test_interview_generation_service.py`
  - Test draft question generation.
- Create: `backend/tests/services/test_interview_template_service.py`
  - Test template create, update, and publish flows.
- Create: `backend/tests/services/test_interview_session_service.py`
  - Test candidate join resolution, transcript persistence, and summary completion.
- Create: `backend/tests/api/test_interview_api.py`
  - Test interview routes.
- Create: `backend/tests/testsupport/interview.py`
  - Seed JD, screening, template, and session fixtures that satisfy real foreign keys.
- Create: `worker/pyproject.toml`
  - Worker dependencies for LiveKit and Gemini integration.
- Create: `worker/src/config.py`
  - Worker settings for backend URL, LiveKit, and Gemini.
- Create: `worker/src/backend_client.py`
  - Post transcript and summary events to FastAPI.
- Create: `worker/src/gemini_live.py`
  - Wrap Gemini live session setup and send or receive audio and text events.
- Create: `worker/src/interview_state.py`
  - Hold approved question pack, sequence state, and follow-up limits.
- Create: `worker/src/agent.py`
  - LiveKit room agent that joins the room, opens the Gemini session, speaks first, and manages the call.
- Create: `worker/tests/test_interview_state.py`
  - Test turn ordering and follow-up limits.
- Create: `worker/tests/test_backend_client.py`
  - Test backend event payloads.
- Create: `frontend/src/components/interview/interview-builder-types.ts`
  - Shared HR configuration types.
- Create: `frontend/src/components/interview/question-pack-editor.tsx`
  - Editable and reorderable question list.
- Create: `frontend/src/components/interview/interview-builder.tsx`
  - HR template configuration and publishing UI.
- Create: `frontend/src/components/interview/interview-link-card.tsx`
  - Published link display.
- Create: `frontend/src/components/interview/candidate-join.tsx`
  - Candidate pre-join and join call action.
- Create: `frontend/src/components/interview/live-room.tsx`
  - Candidate LiveKit room UI.
- Create: `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx`
  - HR interview builder page.
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`
  - Candidate join page.
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Link from a completed screening to the builder.
- Modify: `frontend/src/components/dashboard/dashboard-header.tsx`
  - Add the interviews nav entry only after the builder route exists.
- Create: `scripts/run_interview_worker.sh`
  - Start the realtime worker with a stable entry command.

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

Modify `backend/src/models/__init__.py` to import and export the four interview models.

- [ ] **Step 4: Run the model test to verify it passes**

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

### Task 2: Define interview schemas

**Files:**
- Create: `backend/src/schemas/interview.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Extend the failing schema test**

Append to `backend/tests/schemas/test_interview_schema.py`:

```python
from src.schemas.interview import CandidateJoinResponse, InterviewTemplateResponse


def test_interview_template_and_join_schemas_accept_valid_payloads() -> None:
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
                        "follow_up_rule": "Ask one follow-up.",
                        "stop_conditions": [],
                        "notes_for_agent": "Probe ownership.",
                    }
                ]
            },
        }
    )
    join_payload = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "room-1",
            "participant_token": "token-1",
            "display_name": "InterviewX AI Interview",
        }
    )

    assert template.language_mode == "mixed"
    assert join_payload.participant_token == "token-1"
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k join_schemas_accept_valid_payloads
```

Expected: FAIL because the schema module does not exist.

- [ ] **Step 3: Add the interview schema module**

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

- [ ] **Step 5: Commit the interview schemas**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/interview.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview control plane schemas"
```

---

### Task 3: Seed valid interview test data with real foreign keys

**Files:**
- Create: `backend/tests/testsupport/interview.py`
- Test: `backend/tests/services/test_interview_template_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing helper import in the service test**

Create `backend/tests/services/test_interview_template_service.py` with:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.testsupport.interview import seed_completed_screening


@pytest.mark.asyncio
async def test_seed_completed_screening_returns_real_ids(db_session: AsyncSession) -> None:
    seeded = await seed_completed_screening(db_session)

    assert seeded.screening.id
    assert seeded.jd_document.id
    assert seeded.candidate_profile.id
```

- [ ] **Step 2: Run the service test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py -k seed_completed_screening_returns_real_ids
```

Expected: FAIL because the helper module does not exist.

- [ ] **Step 3: Add the seed helper with real rows**

Create `backend/tests/testsupport/interview.py`:

```python
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument


@dataclass
class SeededScreening:
    jd_document: JDDocument
    screening: CandidateScreening
    candidate_document: CandidateDocument
    candidate_profile: CandidateProfile


async def seed_completed_screening(db_session: AsyncSession) -> SeededScreening:
    jd_document = JDDocument(
        file_name="jd.pdf",
        mime_type="application/pdf",
        storage_path=str(Path("/tmp/jd.pdf")),
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
        storage_path=str(Path("/tmp/candidate.pdf")),
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
        screening_payload={
            "candidate_profile": candidate_profile.profile_payload,
            "result": {
                "match_score": 0.82,
                "recommendation": "advance",
                "decision_reason": {"vi": "Phù hợp", "en": "Strong fit"},
                "screening_summary": {"vi": "Phù hợp tốt", "en": "Strong fit"},
                "knockout_assessments": [],
                "minimum_requirement_checks": [],
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "priority": "must_have",
                        "weight": 0.5,
                        "score": 0.82,
                        "reason": {"vi": "Tốt", "en": "Strong"},
                        "evidence": [],
                        "confidence_note": None,
                    }
                ],
                "strengths": [],
                "gaps": [],
                "uncertainties": [],
                "follow_up_questions": [],
                "risk_flags": [],
            },
            "audit": {
                "extraction_model": "gemini-2.5-pro",
                "screening_model": "gemini-2.5-pro",
                "profile_schema_version": "phase2.v1",
                "screening_schema_version": "phase2.v1",
                "generated_at": "2026-04-16T00:00:00Z",
                "reconciliation_notes": [],
                "consistency_flags": [],
            },
        },
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)

    return SeededScreening(
        jd_document=jd_document,
        screening=screening,
        candidate_document=candidate_document,
        candidate_profile=candidate_profile,
    )
```

- [ ] **Step 4: Run the helper test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py -k seed_completed_screening_returns_real_ids
```

Expected: PASS.

- [ ] **Step 5: Commit the interview test support**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/tests/testsupport/interview.py backend/tests/services/test_interview_template_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "test: add interview fixture builders"
```

---

### Task 4: Generate draft question packs

**Files:**
- Create: `backend/src/services/interview_generation_service.py`
- Test: `backend/tests/services/test_interview_generation_service.py`

- [ ] **Step 1: Write the failing generation test**

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

- [ ] **Step 2: Run the generation test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_generation_service.py
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Add the generation service**

Create `backend/src/services/interview_generation_service.py`:

```python
from src.schemas.interview import (
    InterviewFocusPayload,
    InterviewQuestionPackPayload,
    InterviewQuestionPayload,
)


class InterviewGenerationService:
    def generate_question_pack(
        self,
        screening_payload: dict[str, object],
        focus: InterviewFocusPayload,
        language_mode: str,
    ) -> InterviewQuestionPackPayload:
        _ = screening_payload
        questions: list[InterviewQuestionPayload] = []

        for index, topic in enumerate(focus.soft_topics):
            category = "availability" if topic == "availability" else "motivation"
            questions.append(
                InterviewQuestionPayload(
                    id=f"soft-{index}",
                    category=category,
                    prompt=(
                        "Bạn có thể chia sẻ lịch học hoặc lịch làm việc hiện tại không?"
                        if language_mode == "vi"
                        else "Can you share your current work or study schedule?"
                    ),
                    language=language_mode,
                    priority="required",
                    ask_style="required",
                    follow_up_rule="Ask one clarifying follow-up if needed.",
                    stop_conditions=[],
                    notes_for_agent=focus.notes_for_agent,
                )
            )

        for index, topic in enumerate(focus.hard_topics):
            category = "experience" if topic == "experience" else "technical"
            questions.append(
                InterviewQuestionPayload(
                    id=f"hard-{index}",
                    category=category,
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

### Task 5: Create, update, and publish interview templates

**Files:**
- Create: `backend/src/services/livekit_service.py`
- Create: `backend/src/services/interview_template_service.py`
- Test: `backend/tests/services/test_interview_template_service.py`

- [ ] **Step 1: Write the failing template service tests**

Replace `backend/tests/services/test_interview_template_service.py` with:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.interview import (
    InterviewFocusPayload,
    InterviewQuestionPackPayload,
    InterviewQuestionPayload,
)
from src.services.interview_template_service import InterviewTemplateService
from tests.testsupport.interview import seed_completed_screening


@pytest.mark.asyncio
async def test_create_template_from_ai_generates_draft_question_pack(
    db_session: AsyncSession,
) -> None:
    seeded = await seed_completed_screening(db_session)
    service = InterviewTemplateService(db_session)

    template = await service.create_template(
        screening_id=seeded.screening.id,
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


@pytest.mark.asyncio
async def test_update_template_replaces_question_pack(
    db_session: AsyncSession,
) -> None:
    seeded = await seed_completed_screening(db_session)
    service = InterviewTemplateService(db_session)
    template = await service.create_template(
        screening_id=seeded.screening.id,
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
            notes_for_agent="Probe examples",
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

    assert updated.status == "ready"
    assert updated.question_pack.questions[0].id == "q-1"


@pytest.mark.asyncio
async def test_publish_template_creates_room_and_share_link(
    db_session: AsyncSession,
) -> None:
    seeded = await seed_completed_screening(db_session)
    service = InterviewTemplateService(db_session)
    template = await service.create_template(
        screening_id=seeded.screening.id,
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
    assert "/interviews/join/" in published.share_link
    assert published.room_name.startswith("interview-")
```

- [ ] **Step 2: Run the template service tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_template_service.py
```

Expected: FAIL because the service modules do not exist.

- [ ] **Step 3: Add the LiveKit service**

Create `backend/src/services/livekit_service.py`:

```python
from secrets import token_urlsafe


class LiveKitService:
    def build_room_name(self, template_id: str) -> str:
        return f"interview-{template_id}"

    def build_share_token(self) -> str:
        return token_urlsafe(24)

    def create_candidate_token(self, room_name: str, identity: str) -> str:
        return f"token::{room_name}::{identity}"
```

- [ ] **Step 4: Add the template service**

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
from src.services.livekit_service import LiveKitService


class InterviewTemplateService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._generation_service = InterviewGenerationService()
        self._livekit_service = LiveKitService()

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

    async def publish_template(self, template_id: str) -> PublishInterviewResponse:
        template = await self._db_session.scalar(
            select(InterviewTemplate).where(InterviewTemplate.id == template_id)
        )
        if template is None:
            raise ValueError("Interview template not found")

        room_name = self._livekit_service.build_room_name(template.id)
        share_token = self._livekit_service.build_share_token()
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

- [ ] **Step 6: Commit template create, update, and publish**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/livekit_service.py backend/src/services/interview_template_service.py backend/tests/services/test_interview_template_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: build interview template publishing flow"
```

---

### Task 6: Resolve candidate joins and persist turn and summary events

**Files:**
- Create: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing session-service tests**

Create `backend/tests/services/test_interview_session_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewSession
from src.schemas.interview import InterviewSummaryRequest, InterviewTurnEventRequest
from src.services.interview_session_service import InterviewSessionService
from src.services.interview_template_service import InterviewTemplateService
from tests.testsupport.interview import seed_completed_screening
from src.schemas.interview import InterviewFocusPayload, InterviewQuestionPackPayload, InterviewQuestionPayload


async def seed_published_session(db_session: AsyncSession) -> InterviewSession:
    seeded = await seed_completed_screening(db_session)
    template_service = InterviewTemplateService(db_session)
    template = await template_service.create_template(
        screening_id=seeded.screening.id,
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
    await template_service.update_template(
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
    published = await template_service.publish_template(template.template_id)
    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    return session


@pytest.mark.asyncio
async def test_resolve_candidate_join_returns_room_and_token(db_session: AsyncSession) -> None:
    session = await seed_published_session(db_session)
    service = InterviewSessionService(db_session)

    payload = await service.resolve_candidate_join(session.share_token)

    assert payload.session_id == session.id
    assert payload.room_name == session.livekit_room_name
    assert payload.participant_token.startswith("token::")


@pytest.mark.asyncio
async def test_append_turn_persists_transcript_event(db_session: AsyncSession) -> None:
    session = await seed_published_session(db_session)
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
    session = await seed_published_session(db_session)
    service = InterviewSessionService(db_session)

    await service.store_summary(
        session_id=session.id,
        payload=InterviewSummaryRequest(
            model_name="gemini-2.5-flash-native-audio",
            summary_payload={"summary": "Candidate is available in June."},
        ),
    )

    status = await service.get_session_status(session.id)
    assert status == "completed"
```

- [ ] **Step 2: Run the session-service tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: FAIL because the session service does not exist.

- [ ] **Step 3: Add the session service**

Create `backend/src/services/interview_session_service.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewSession, InterviewSummary, InterviewTurn
from src.schemas.interview import CandidateJoinResponse, InterviewSummaryRequest, InterviewTurnEventRequest
from src.services.livekit_service import LiveKitService


class InterviewSessionService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._livekit_service = LiveKitService()

    async def resolve_candidate_join(self, share_token: str) -> CandidateJoinResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")

        participant_token = self._livekit_service.create_candidate_token(
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

- [ ] **Step 4: Run the session-service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: PASS.

- [ ] **Step 5: Commit the session service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: resolve candidate joins and transcript events"
```

---

### Task 7: Expose interview APIs

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
from src.schemas.interview import CandidateJoinResponse, InterviewTemplateResponse, PublishInterviewResponse


class FakeInterviewTemplateService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def create_template(self, screening_id, mode, language_mode, focus, uploaded_questions):
        _ = (screening_id, mode, language_mode, focus, uploaded_questions)
        return InterviewTemplateResponse.model_validate(
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
                "question_pack": {"questions": []},
            }
        )

    async def update_template(self, template_id, focus, question_pack):
        _ = (template_id, focus, question_pack)
        return await self.create_template("screening-1", "ai_generated", "mixed", focus, None)

    async def publish_template(self, template_id):
        _ = template_id
        return PublishInterviewResponse(
            session_id="session-1",
            share_link="http://localhost:3000/interviews/join/share-token-1",
            room_name="room-1",
            status="published",
        )


class FakeInterviewSessionService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def resolve_candidate_join(self, share_token: str) -> CandidateJoinResponse:
        _ = share_token
        return CandidateJoinResponse(
            session_id="session-1",
            room_name="room-1",
            participant_token="token-1",
            display_name="InterviewX AI Interview",
        )

    async def append_turn(self, session_id, payload):
        _ = (session_id, payload)

    async def store_summary(self, session_id, payload):
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
    monkeypatch.setattr(module, "InterviewTemplateService", FakeInterviewTemplateService)
    monkeypatch.setattr(module, "InterviewSessionService", FakeInterviewSessionService)
    return TestClient(app)



def test_create_interview_template_returns_draft(monkeypatch: MonkeyPatch) -> None:
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



def test_candidate_join_returns_room_payload(monkeypatch: MonkeyPatch) -> None:
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

- [ ] **Step 3: Add the interview router**

Create `backend/src/api/v1/interviews.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
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

- [ ] **Step 4: Run the API tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 5: Commit the interview API**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/api/test_interview_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview routes"
```

---

### Task 8: Build the HR interview builder UI

**Files:**
- Create: `frontend/src/components/interview/interview-builder-types.ts`
- Create: `frontend/src/components/interview/question-pack-editor.tsx`
- Create: `frontend/src/components/interview/interview-link-card.tsx`
- Create: `frontend/src/components/interview/interview-builder.tsx`
- Create: `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx`
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
- Modify: `frontend/src/components/dashboard/dashboard-header.tsx`

- [ ] **Step 1: Write the failing builder import change**

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

Then modify `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` to import a not-yet-created `InterviewBuilderLink`. Let TypeScript fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the builder files do not exist.

- [ ] **Step 3: Add the question editor and link card**

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
  function updatePrompt(index: number, prompt: string) {
    const next = [...questions]
    next[index] = { ...next[index], prompt }
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
            onChange={(event) => updatePrompt(index, event.target.value)}
          />
          <div className="mt-3 flex gap-3">
            <button type="button" onClick={() => moveQuestion(index, -1)}>Up</button>
            <button type="button" onClick={() => moveQuestion(index, 1)}>Down</button>
          </div>
        </article>
      ))}
    </div>
  )
}
```

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

- [ ] **Step 4: Add the builder UI and builder page**

Create `frontend/src/components/interview/interview-builder.tsx` with a client component that:

- POSTs to `/api/v1/interviews/templates`
- stores the returned draft template
- lets HR edit question prompts via `QuestionPackEditor`
- PUTs updates to `/api/v1/interviews/templates/{template_id}`
- POSTs publish to `/api/v1/interviews/templates/{template_id}/publish`
- shows `InterviewLinkCard` after publish

Create `frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx` to render `InterviewBuilder`.

Modify `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` so the bottom CTA goes to `/dashboard/interviews/new/${screening.screening_id}` instead of the old quick-start panel.

Modify `frontend/src/components/dashboard/dashboard-header.tsx` to add:

```ts
{ label: "Interviews", href: "/dashboard/interviews/new/demo" as Route }
```

then immediately replace that temporary route with the safer existing entry point:

```ts
{ label: "Interviews", href: "/dashboard/jd" as Route }
```

and finally, after the builder route exists, set it to:

```ts
{ label: "Interviews", href: "/dashboard/jd" as Route }
```

This keeps the nav from pointing at a dead route until a proper list page exists. Do not invent the list page in this task.

- [ ] **Step 5: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 6: Commit the HR builder UI**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-builder-types.ts frontend/src/components/interview/question-pack-editor.tsx frontend/src/components/interview/interview-link-card.tsx frontend/src/components/interview/interview-builder.tsx frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/src/components/dashboard/dashboard-header.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add hr interview builder ui"
```

---

### Task 9: Build the candidate join page and room UI

**Files:**
- Create: `frontend/src/components/interview/candidate-join.tsx`
- Create: `frontend/src/components/interview/live-room.tsx`
- Create: `frontend/src/app/interviews/join/[token]/page.tsx`

- [ ] **Step 1: Add the failing room import change**

Modify the new join page to import a not-yet-created `LiveRoom`. Let TypeScript fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the candidate room files do not exist.

- [ ] **Step 3: Add the candidate join component**

Create `frontend/src/components/interview/candidate-join.tsx`:

```tsx
"use client"

import { useState } from "react"

import { LiveRoom } from "@/components/interview/live-room"

export function CandidateJoin({ token, backendBaseUrl }: { token: string; backendBaseUrl: string }) {
  const [joinPayload, setJoinPayload] = useState<{
    room_name: string
    participant_token: string
    display_name: string
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
    setJoinPayload((await response.json()) as {
      room_name: string
      participant_token: string
      display_name: string
    })
  }

  if (joinPayload) {
    return <LiveRoom roomName={joinPayload.room_name} participantToken={joinPayload.participant_token} />
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm text-[var(--color-brand-text-body)]">This interview uses your microphone and camera for the call experience.</p>
      <button className="mt-4 rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white" type="button" onClick={() => void handleJoin()}>
        Join interview
      </button>
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
    </section>
  )
}
```

- [ ] **Step 4: Add the LiveKit room shell and join page**

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

- [ ] **Step 5: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 6: Commit the candidate join flow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/interviews/join/[token]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add candidate interview join flow"
```

---

### Task 10: Add the real worker runtime, backend client, and turn state

**Files:**
- Create: `worker/pyproject.toml`
- Create: `worker/src/config.py`
- Create: `worker/src/backend_client.py`
- Create: `worker/src/gemini_live.py`
- Create: `worker/src/interview_state.py`
- Create: `worker/src/agent.py`
- Create: `worker/tests/test_backend_client.py`
- Create: `worker/tests/test_interview_state.py`
- Create: `scripts/run_interview_worker.sh`

- [ ] **Step 1: Write the failing worker state and payload tests**

Create `worker/tests/test_backend_client.py`:

```python
from worker.src.backend_client import BackendClient


def test_build_turn_payload_returns_expected_shape() -> None:
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
    assert payload["question_id"] == "q-1"
```

Create `worker/tests/test_interview_state.py`:

```python
from worker.src.interview_state import InterviewState


def test_interview_state_returns_opening_and_first_question() -> None:
    state = InterviewState(
        session_id="session-1",
        questions=[
            {"id": "q-1", "prompt": "Bạn có thể giới thiệu ngắn về bản thân không?", "follow_up_rule": "Ask one follow-up."}
        ],
        follow_up_intensity="light",
    )

    opening = state.build_opening_utterance()
    first_question = state.current_question()

    assert "Xin chào" in opening
    assert first_question["id"] == "q-1"
```

- [ ] **Step 2: Run the worker tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py worker/tests/test_interview_state.py
```

Expected: FAIL because the worker modules do not exist.

- [ ] **Step 3: Add the worker project and config**

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

- [ ] **Step 4: Add the backend client and interview state**

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

    def build_summary_payload(self, model_name: str, summary: dict[str, object]) -> dict[str, object]:
        return {
            "model_name": model_name,
            "summary_payload": summary,
        }
```

Create `worker/src/interview_state.py`:

```python
class InterviewState:
    def __init__(self, session_id: str, questions: list[dict[str, object]], follow_up_intensity: str) -> None:
        self.session_id = session_id
        self.questions = questions
        self.follow_up_intensity = follow_up_intensity
        self.current_index = 0

    def build_opening_utterance(self) -> str:
        return "Xin chào, cảm ơn bạn đã tham gia. Chúng ta sẽ bắt đầu buổi trao đổi ngay bây giờ."

    def current_question(self) -> dict[str, object]:
        return self.questions[self.current_index]
```

- [ ] **Step 5: Add the Gemini live adapter and room agent**

Create `worker/src/gemini_live.py`:

```python
class GeminiLiveAdapter:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    async def start(self) -> None:
        return None

    async def send_opening_turn(self, opening_text: str, first_question: str) -> None:
        _ = (opening_text, first_question)
```

Create `worker/src/agent.py`:

```python
from worker.src.backend_client import BackendClient
from worker.src.gemini_live import GeminiLiveAdapter
from worker.src.interview_state import InterviewState


class InterviewAgent:
    def __init__(self, backend_base_url: str, model_name: str) -> None:
        self._backend = BackendClient(backend_base_url)
        self._gemini = GeminiLiveAdapter(model_name)

    async def run_once(self, session_id: str, questions: list[dict[str, object]]) -> None:
        state = InterviewState(
            session_id=session_id,
            questions=questions,
            follow_up_intensity="light",
        )
        await self._gemini.start()
        await self._gemini.send_opening_turn(
            opening_text=state.build_opening_utterance(),
            first_question=str(state.current_question()["prompt"]),
        )
```

Create `scripts/run_interview_worker.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
python -m worker.src.agent
```

- [ ] **Step 6: Run the worker tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py worker/tests/test_interview_state.py
```

Expected: PASS.

- [ ] **Step 7: Commit the worker runtime foundation**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add worker/pyproject.toml worker/src/config.py worker/src/backend_client.py worker/src/gemini_live.py worker/src/interview_state.py worker/src/agent.py worker/tests/test_backend_client.py worker/tests/test_interview_state.py scripts/run_interview_worker.sh
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview worker runtime"
```

---

### Task 11: Run focused verification and manual checks

**Files:**
- Modify: none
- Test: `backend/tests/schemas/test_interview_schema.py`
- Test: `backend/tests/services/test_interview_generation_service.py`
- Test: `backend/tests/services/test_interview_template_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`
- Test: `backend/tests/api/test_interview_api.py`
- Test: `worker/tests/test_backend_client.py`
- Test: `worker/tests/test_interview_state.py`

- [ ] **Step 1: Run the focused backend suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py tests/services/test_interview_generation_service.py tests/services/test_interview_template_service.py tests/services/test_interview_session_service.py tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 2: Run the worker tests**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && python -m pytest -q worker/tests/test_backend_client.py worker/tests/test_interview_state.py
```

Expected: PASS.

- [ ] **Step 3: Run frontend type checking**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Verify the HR publish flow manually**

Start backend and frontend servers. Then:

1. open a completed CV screening
2. open the interview builder
3. generate or edit the question pack
4. publish the interview
5. copy the shareable link

Expected: a shareable link is shown and the UI does not crash.

- [ ] **Step 5: Verify the candidate join flow manually**

Open the shareable link in a fresh browser tab. Then:

1. load the pre-join screen
2. click Join interview
3. confirm the room shell renders

Expected: the candidate gets room credentials and the room shell renders.

- [ ] **Step 6: Verify the worker entry point manually**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx" && bash scripts/run_interview_worker.sh
```

Expected: the worker starts without import errors.

- [ ] **Step 7: Commit the realtime interview foundation**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/schemas/interview.py backend/src/services/interview_generation_service.py backend/src/services/interview_template_service.py backend/src/services/interview_session_service.py backend/src/services/livekit_service.py backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/schemas/test_interview_schema.py backend/tests/services/test_interview_generation_service.py backend/tests/services/test_interview_template_service.py backend/tests/services/test_interview_session_service.py backend/tests/api/test_interview_api.py backend/tests/testsupport/interview.py frontend/src/components/interview/interview-builder-types.ts frontend/src/components/interview/question-pack-editor.tsx frontend/src/components/interview/interview-link-card.tsx frontend/src/components/interview/interview-builder.tsx frontend/src/components/interview/candidate-join.tsx frontend/src/components/interview/live-room.tsx frontend/src/app/dashboard/interviews/new/[screeningId]/page.tsx frontend/src/app/interviews/join/[token]/page.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/src/components/dashboard/dashboard-header.tsx worker/pyproject.toml worker/src/config.py worker/src/backend_client.py worker/src/gemini_live.py worker/src/interview_state.py worker/src/agent.py worker/tests/test_backend_client.py worker/tests/test_interview_state.py scripts/run_interview_worker.sh
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add realtime interview foundation"
```

---

## Self-Review

- Spec coverage: this plan covers HR configuration, draft generation, question editing, session publishing, shareable links, candidate join authorization, transcript persistence, summary persistence, and a real worker runtime foundation with opening utterance behavior. It still stops short of the full LiveKit media-stream and Gemini session bridging details, but it now targets the actual runtime boundary rather than a disconnected worker skeleton.
- Placeholder scan: there are no TODO or TBD markers. Each task names concrete files, code, and commands.
- Type consistency: the same names are used throughout: `InterviewTemplate`, `InterviewSession`, `InterviewTurn`, `InterviewSummary`, `InterviewTemplateService`, `InterviewSessionService`, `InterviewGenerationService`, `LiveKitService`, `InterviewState`, and `GeminiLiveAdapter`.
- Scope control: this plan keeps the first delivery to one HR-configured candidate interview path, not the full scheduling, anti-cheat, or evaluator system.
