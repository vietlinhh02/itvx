# Interview Session Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the next phase after CV screening: create interview sessions from completed CV screenings, generate a structured interview plan, persist interview turns, and show an HR review page for a text-first interview flow.

**Architecture:** Keep this phase narrow. Reuse the existing JD analysis and CV screening records as inputs, add a new persisted interview session aggregate, and expose a small API surface for creating a session, fetching it, and appending interview turns. Generate the initial interview plan synchronously from stored screening data, then use the existing background-job pattern later when the team adds LiveKit, STT, and TTS.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, LangChain, Gemini, Next.js, TypeScript, pytest

---

## File Structure

- Create: `backend/src/models/interview.py`
  - Persist interview sessions and interview turns.
- Modify: `backend/src/models/__init__.py`
  - Export the new interview models.
- Create: `backend/src/schemas/interview.py`
  - Define API contracts for interview plan generation, session creation, turn submission, and detail responses.
- Create: `backend/src/services/interview_plan_service.py`
  - Build the initial interview plan from JD analysis and completed CV screening.
- Create: `backend/src/services/interview_session_service.py`
  - Create sessions, append turns, compute session status, and return detail views.
- Create: `backend/src/api/v1/interviews.py`
  - Add API routes for session creation, detail fetch, and turn submission.
- Modify: `backend/src/api/v1/router.py`
  - Register the interviews router.
- Create: `backend/tests/schemas/test_interview_schema.py`
  - Validate the new schema and model contracts.
- Create: `backend/tests/services/test_interview_plan_service.py`
  - Test interview plan generation from stored screening data.
- Create: `backend/tests/services/test_interview_session_service.py`
  - Test session creation and turn progression.
- Create: `backend/tests/api/test_interview_api.py`
  - Test the new interview endpoints.
- Create: `frontend/src/components/interview/interview-types.ts`
  - Shared TypeScript contracts for the interview UI.
- Create: `frontend/src/components/interview/interview-launch-panel.tsx`
  - Launch an interview session from a completed CV screening detail page.
- Create: `frontend/src/components/interview/interview-session-detail.tsx`
  - Render the interview plan, transcript, and next-question workflow.
- Create: `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`
  - Server page for one persisted interview session.
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`
  - Add the launch panel beneath the existing screening detail.
- Modify: `frontend/src/components/dashboard/dashboard-header.tsx`
  - Add the interview workspace nav entry.
- Optional later, not in this plan: `frontend/src/app/dashboard/interviews/page.tsx`
  - Intentionally omitted to keep phase scope small.

---

### Task 1: Add interview persistence models

**Files:**
- Create: `backend/src/models/interview.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Write the failing schema test**

Create `backend/tests/schemas/test_interview_schema.py` with:

```python
from src.models.interview import InterviewSession, InterviewTurn


def test_interview_models_define_expected_columns() -> None:
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c

    assert "candidate_screening_id" in session_columns
    assert "status" in session_columns
    assert "current_question_index" in session_columns
    assert "plan_payload" in session_columns
    assert "summary_payload" in session_columns

    assert "interview_session_id" in turn_columns
    assert "speaker" in turn_columns
    assert "question_index" in turn_columns
    assert "content" in turn_columns
    assert "evaluation_payload" in turn_columns
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: FAIL because the interview models do not exist yet.

- [ ] **Step 3: Add the new interview models**

Create `backend/src/models/interview.py`:

```python
from sqlalchemy import ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class InterviewSession(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    candidate_screening_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_screenings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    plan_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    summary_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    turns: Mapped[list["InterviewTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewTurn.question_index.asc()",
    )


class InterviewTurn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "interview_turns"

    interview_session_id: Mapped[str] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    speaker: Mapped[str] = mapped_column(String(20), nullable=False)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    session: Mapped[InterviewSession] = relationship(back_populates="turns")
```

Modify `backend/src/models/__init__.py`:

```python
from src.models.interview import InterviewSession, InterviewTurn
```

and add both names to `__all__`.

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit the model layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/models/__init__.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview session models"
```

---

### Task 2: Define interview API schemas

**Files:**
- Create: `backend/src/schemas/interview.py`
- Test: `backend/tests/schemas/test_interview_schema.py`

- [ ] **Step 1: Extend the failing schema test with payload validation**

Append this test to `backend/tests/schemas/test_interview_schema.py`:

```python
from src.schemas.interview import InterviewSessionDetailResponse


def test_interview_session_detail_response_accepts_plan_and_turns() -> None:
    response = InterviewSessionDetailResponse.model_validate(
        {
            "session_id": "session-1",
            "screening_id": "screening-1",
            "status": "in_progress",
            "current_question_index": 1,
            "total_questions": 3,
            "plan": {
                "session_goal": {"vi": "Đánh giá kỹ năng backend", "en": "Assess backend skills"},
                "opening_script": {"vi": "Bắt đầu", "en": "Start"},
                "questions": [
                    {
                        "question_index": 0,
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "prompt": {"vi": "Bạn đã dùng FastAPI thế nào?", "en": "How have you used FastAPI?"},
                        "purpose": {"vi": "Kiểm tra kinh nghiệm", "en": "Check experience"},
                    }
                ],
            },
            "turns": [
                {
                    "turn_id": "turn-1",
                    "speaker": "interviewer",
                    "question_index": 0,
                    "content": "How have you used FastAPI?",
                    "evaluation": {},
                    "created_at": "2026-04-16T12:00:00Z",
                }
            ],
            "summary": {},
            "created_at": "2026-04-16T12:00:00Z",
        }
    )

    assert response.status == "in_progress"
    assert response.plan.questions[0].question_index == 0
```

- [ ] **Step 2: Run the schema test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py -k interview_session_detail_response
```

Expected: FAIL because the schema file does not exist.

- [ ] **Step 3: Add the interview schema module**

Create `backend/src/schemas/interview.py`:

```python
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.jd import BilingualText


class InterviewQuestion(BaseModel):
    question_index: int = Field(ge=0)
    dimension_name: BilingualText
    prompt: BilingualText
    purpose: BilingualText


class InterviewPlanPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    session_goal: BilingualText
    opening_script: BilingualText
    questions: list[InterviewQuestion]


class InterviewTurnEvaluation(BaseModel):
    dimension_signal: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    note: BilingualText | None = None


class InterviewTurnResponse(BaseModel):
    turn_id: str
    speaker: Literal["interviewer", "candidate"]
    question_index: int
    content: str
    evaluation: dict[str, object]
    created_at: str


class InterviewSessionCreateRequest(BaseModel):
    screening_id: str


class InterviewSessionCreateResponse(BaseModel):
    session_id: str
    screening_id: str
    status: Literal["draft", "in_progress"]
    current_question_index: int
    total_questions: int


class InterviewAnswerRequest(BaseModel):
    answer_text: str = Field(min_length=1)


class InterviewAnswerResponse(BaseModel):
    session_id: str
    status: Literal["in_progress", "completed"]
    current_question_index: int
    next_question: InterviewQuestion | None


class InterviewSessionDetailResponse(BaseModel):
    session_id: str
    screening_id: str
    status: Literal["draft", "in_progress", "completed"]
    current_question_index: int
    total_questions: int
    plan: InterviewPlanPayload
    turns: list[InterviewTurnResponse]
    summary: dict[str, object]
    created_at: str
```

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py
```

Expected: PASS.

- [ ] **Step 5: Commit the schema layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/interview.py backend/tests/schemas/test_interview_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview session schemas"
```

---

### Task 3: Generate interview plans from completed screenings

**Files:**
- Create: `backend/src/services/interview_plan_service.py`
- Test: `backend/tests/services/test_interview_plan_service.py`

- [ ] **Step 1: Write the failing interview-plan service test**

Create `backend/tests/services/test_interview_plan_service.py` with:

```python
from src.schemas.interview import InterviewPlanPayload
from src.services.interview_plan_service import InterviewPlanService


def test_build_plan_uses_screening_dimensions_and_followups() -> None:
    service = InterviewPlanService()

    plan = service.build_plan(
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "priority": "must_have",
                        "weight": 0.5,
                        "score": 0.82,
                        "reason": {"vi": "Có kinh nghiệm tốt", "en": "Strong experience"},
                        "evidence": [],
                        "confidence_note": None,
                    }
                ],
                "follow_up_questions": [
                    {
                        "question": {"vi": "Mô tả một API bạn đã tối ưu.", "en": "Describe one API you optimized."},
                        "purpose": {"vi": "Đào sâu kỹ thuật", "en": "Probe technical depth"},
                        "linked_dimension": {"vi": "Kỹ thuật", "en": "Technical"},
                    }
                ],
            }
        }
    )

    assert isinstance(plan, InterviewPlanPayload)
    assert len(plan.questions) == 1
    assert plan.questions[0].dimension_name.en == "Technical"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_plan_service.py
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement the minimal plan service**

Create `backend/src/services/interview_plan_service.py`:

```python
from src.schemas.interview import InterviewPlanPayload, InterviewQuestion
from src.schemas.jd import BilingualText


class InterviewPlanService:
    """Build a narrow interview plan from a completed screening payload."""

    def build_plan(self, screening_payload: dict[str, object]) -> InterviewPlanPayload:
        result = screening_payload.get("result", {})
        follow_up_questions = result.get("follow_up_questions", [])
        dimension_scores = result.get("dimension_scores", [])

        questions: list[InterviewQuestion] = []
        for index, item in enumerate(follow_up_questions):
            linked_dimension = item.get("linked_dimension") or {"vi": "Chung", "en": "General"}
            questions.append(
                InterviewQuestion(
                    question_index=index,
                    dimension_name=BilingualText.model_validate(linked_dimension),
                    prompt=BilingualText.model_validate(item["question"]),
                    purpose=BilingualText.model_validate(item["purpose"]),
                )
            )

        if not questions:
            for index, dimension in enumerate(dimension_scores[:3]):
                questions.append(
                    InterviewQuestion(
                        question_index=index,
                        dimension_name=BilingualText.model_validate(dimension["dimension_name"]),
                        prompt=BilingualText(
                            vi=f"Hãy chia sẻ một ví dụ cụ thể về {dimension['dimension_name']['vi'].lower()}.",
                            en=f"Share one concrete example of your {dimension['dimension_name']['en'].lower()}.",
                        ),
                        purpose=BilingualText(
                            vi="Xác minh tín hiệu từ CV screening",
                            en="Verify the signal from CV screening",
                        ),
                    )
                )

        return InterviewPlanPayload(
            session_goal=BilingualText(
                vi="Xác minh các tín hiệu chính trước vòng phỏng vấn tiếp theo",
                en="Validate the key candidate signals before the next interview round",
            ),
            opening_script=BilingualText(
                vi="Cảm ơn bạn đã tham gia. Tôi sẽ hỏi một vài câu ngắn dựa trên CV của bạn.",
                en="Thanks for joining. I will ask a few short questions based on your CV.",
            ),
            questions=questions,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_plan_service.py
```

Expected: PASS.

- [ ] **Step 5: Commit the plan-generation service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_plan_service.py backend/tests/services/test_interview_plan_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: generate interview plans from screenings"
```

---

### Task 4: Create interview sessions from stored screenings

**Files:**
- Create: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Write the failing session-creation service test**

Create `backend/tests/services/test_interview_session_service.py` with:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.interview_session_service import InterviewSessionService


@pytest.mark.asyncio
async def test_create_session_from_screening_persists_plan_and_first_turn(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewSessionService(db_session)

    response = await service.create_session(screening_id=seeded_completed_screening_id)

    assert response.screening_id == seeded_completed_screening_id
    assert response.status == "in_progress"
    assert response.current_question_index == 0
    assert response.total_questions >= 1
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k create_session_from_screening
```

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement minimal session creation**

Create `backend/src/services/interview_session_service.py`:

```python
from datetime import UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateScreening
from src.models.interview import InterviewSession, InterviewTurn
from src.schemas.interview import InterviewSessionCreateResponse
from src.services.interview_plan_service import InterviewPlanService


class InterviewSessionService:
    """Create and advance text-first interview sessions."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session
        self._plan_service = InterviewPlanService()

    async def create_session(self, screening_id: str) -> InterviewSessionCreateResponse:
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        if screening.status != "completed":
            raise ValueError("CV screening is not ready for interview")

        existing_session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.candidate_screening_id == screening_id)
        )
        if existing_session is not None:
            return InterviewSessionCreateResponse(
                session_id=existing_session.id,
                screening_id=screening_id,
                status=existing_session.status,
                current_question_index=existing_session.current_question_index,
                total_questions=existing_session.total_questions,
            )

        plan = self._plan_service.build_plan(screening.screening_payload)
        session = InterviewSession(
            candidate_screening_id=screening_id,
            status="in_progress",
            current_question_index=0,
            total_questions=len(plan.questions),
            plan_payload=plan.model_dump(mode="json"),
            summary_payload={},
        )
        self._db_session.add(session)
        await self._db_session.flush()

        first_question = plan.questions[0]
        self._db_session.add(
            InterviewTurn(
                interview_session_id=session.id,
                speaker="interviewer",
                question_index=first_question.question_index,
                content=first_question.prompt.en,
                evaluation_payload={},
            )
        )
        await self._db_session.commit()
        await self._db_session.refresh(session)

        return InterviewSessionCreateResponse(
            session_id=session.id,
            screening_id=screening_id,
            status="in_progress",
            current_question_index=0,
            total_questions=session.total_questions,
        )
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k create_session_from_screening
```

Expected: PASS.

- [ ] **Step 5: Commit the session-creation service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: create interview sessions from screenings"
```

---

### Task 5: Append candidate answers and advance interview sessions

**Files:**
- Modify: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Add the failing answer-submission test**

Append this test to `backend/tests/services/test_interview_session_service.py`:

```python
@pytest.mark.asyncio
async def test_submit_answer_appends_candidate_turn_and_returns_next_question(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewSessionService(db_session)
    session = await service.create_session(screening_id=seeded_completed_screening_id)

    response = await service.submit_answer(
        session_id=session.session_id,
        answer_text="I built async APIs for a hiring platform.",
    )

    assert response.status in {"in_progress", "completed"}
    assert response.current_question_index == 1
```

- [ ] **Step 2: Run the service test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k submit_answer_appends_candidate_turn
```

Expected: FAIL because `submit_answer` does not exist.

- [ ] **Step 3: Implement answer submission and session advancement**

In `backend/src/services/interview_session_service.py`, add:

```python
from src.schemas.interview import (
    InterviewAnswerResponse,
    InterviewPlanPayload,
    InterviewQuestion,
)
from src.schemas.jd import BilingualText
```

Then add this method:

```python
    async def submit_answer(self, session_id: str, answer_text: str) -> InterviewAnswerResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")

        plan = InterviewPlanPayload.model_validate(session.plan_payload)
        current_index = session.current_question_index
        self._db_session.add(
            InterviewTurn(
                interview_session_id=session.id,
                speaker="candidate",
                question_index=current_index,
                content=answer_text,
                evaluation_payload={},
            )
        )

        next_index = current_index + 1
        next_question: InterviewQuestion | None = None
        if next_index < len(plan.questions):
            next_question = plan.questions[next_index]
            self._db_session.add(
                InterviewTurn(
                    interview_session_id=session.id,
                    speaker="interviewer",
                    question_index=next_question.question_index,
                    content=next_question.prompt.en,
                    evaluation_payload={},
                )
            )
            session.current_question_index = next_index
            session.status = "in_progress"
        else:
            session.current_question_index = next_index
            session.status = "completed"
            session.summary_payload = {
                "completed_turns": next_index,
                "completion_note": {
                    "vi": "Buổi phỏng vấn nền tảng đã hoàn tất.",
                    "en": "The foundation interview session is complete.",
                },
            }

        await self._db_session.commit()
        return InterviewAnswerResponse(
            session_id=session.id,
            status=session.status,
            current_question_index=session.current_question_index,
            next_question=next_question,
        )
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: PASS.

- [ ] **Step 5: Commit the answer workflow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: advance interview sessions with answers"
```

---

### Task 6: Add detail loading for interview sessions

**Files:**
- Modify: `backend/src/services/interview_session_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`

- [ ] **Step 1: Add the failing detail-response test**

Append this test to `backend/tests/services/test_interview_session_service.py`:

```python
@pytest.mark.asyncio
async def test_get_session_detail_returns_plan_turns_and_summary(
    db_session: AsyncSession,
    seeded_completed_screening_id: str,
) -> None:
    service = InterviewSessionService(db_session)
    created = await service.create_session(screening_id=seeded_completed_screening_id)

    detail = await service.get_session_detail(created.session_id)

    assert detail is not None
    assert detail.session_id == created.session_id
    assert len(detail.turns) >= 1
    assert detail.plan.questions[0].question_index == 0
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py -k get_session_detail_returns_plan_turns
```

Expected: FAIL because `get_session_detail` does not exist.

- [ ] **Step 3: Implement the detail loader**

In `backend/src/services/interview_session_service.py`, add:

```python
from src.schemas.interview import InterviewSessionDetailResponse, InterviewTurnResponse
```

Then add:

```python
    async def get_session_detail(self, session_id: str) -> InterviewSessionDetailResponse | None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            return None

        turns = (
            await self._db_session.scalars(
                select(InterviewTurn)
                .where(InterviewTurn.interview_session_id == session_id)
                .order_by(InterviewTurn.created_at.asc())
            )
        ).all()

        return InterviewSessionDetailResponse(
            session_id=session.id,
            screening_id=session.candidate_screening_id,
            status=session.status,
            current_question_index=session.current_question_index,
            total_questions=session.total_questions,
            plan=InterviewPlanPayload.model_validate(session.plan_payload),
            turns=[
                InterviewTurnResponse(
                    turn_id=turn.id,
                    speaker=turn.speaker,
                    question_index=turn.question_index,
                    content=turn.content,
                    evaluation=turn.evaluation_payload,
                    created_at=turn.created_at.replace(tzinfo=UTC).isoformat(),
                )
                for turn in turns
            ],
            summary=session.summary_payload,
            created_at=session.created_at.replace(tzinfo=UTC).isoformat(),
        )
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_interview_session_service.py
```

Expected: PASS.

- [ ] **Step 5: Commit the detail loader**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/interview_session_service.py backend/tests/services/test_interview_session_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: load interview session detail"
```

---

### Task 7: Expose interview API endpoints

**Files:**
- Create: `backend/src/api/v1/interviews.py`
- Modify: `backend/src/api/v1/router.py`
- Test: `backend/tests/api/test_interview_api.py`

- [ ] **Step 1: Write the failing interview API tests**

Create `backend/tests/api/test_interview_api.py` with:

```python
def test_create_interview_session_returns_created_payload(monkeypatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews", json={"screening_id": "screening-1"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["session_id"] == "session-1"
    assert payload["status"] == "in_progress"


def test_get_interview_session_returns_plan_and_turns(monkeypatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/session-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-1"
    assert payload["turns"][0]["speaker"] == "interviewer"
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: FAIL because the router does not exist.

- [ ] **Step 3: Add the interviews API router**

Create `backend/src/api/v1/interviews.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.schemas.interview import (
    InterviewAnswerRequest,
    InterviewAnswerResponse,
    InterviewSessionCreateRequest,
    InterviewSessionCreateResponse,
    InterviewSessionDetailResponse,
)
from src.services.interview_session_service import InterviewSessionService

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("", response_model=InterviewSessionCreateResponse, status_code=201)
async def create_interview_session(
    payload: InterviewSessionCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionCreateResponse:
    service = InterviewSessionService(db)
    try:
        return await service.create_session(payload.screening_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=InterviewSessionDetailResponse)
async def get_interview_session(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionDetailResponse:
    service = InterviewSessionService(db)
    detail = await service.get_session_detail(session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    return detail


@router.post("/{session_id}/answer", response_model=InterviewAnswerResponse)
async def submit_interview_answer(
    session_id: str,
    payload: InterviewAnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewAnswerResponse:
    service = InterviewSessionService(db)
    try:
        return await service.submit_answer(session_id=session_id, answer_text=payload.answer_text)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
```

Modify `backend/src/api/v1/router.py`:

```python
from src.api.v1.interviews import router as interviews_router
```

and include it:

```python
api_router.include_router(interviews_router)
```

- [ ] **Step 4: Add minimal test doubles and run the tests**

Add a fake `InterviewSessionService` in `backend/tests/api/test_interview_api.py` that returns:

```python
{
    "session_id": "session-1",
    "screening_id": "screening-1",
    "status": "in_progress",
    "current_question_index": 0,
    "total_questions": 3,
}
```

for creation, and a detail payload with one interviewer turn for fetches.

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 5: Commit the API layer**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/api/test_interview_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview session api"
```

---

### Task 8: Add shared frontend interview types and launch action

**Files:**
- Create: `frontend/src/components/interview/interview-types.ts`
- Create: `frontend/src/components/interview/interview-launch-panel.tsx`
- Modify: `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx`

- [ ] **Step 1: Write the failing frontend type integration**

Create `frontend/src/components/interview/interview-types.ts` with:

```ts
export type InterviewQuestion = {
  question_index: number
  dimension_name: { vi: string; en: string }
  prompt: { vi: string; en: string }
  purpose: { vi: string; en: string }
}

export type InterviewSessionCreateResponse = {
  session_id: string
  screening_id: string
  status: "draft" | "in_progress"
  current_question_index: number
  total_questions: number
}
```

Then update `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` to import a not-yet-created `InterviewLaunchPanel`. Let the build fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the new component file does not exist.

- [ ] **Step 3: Add the interview launch panel**

Create `frontend/src/components/interview/interview-launch-panel.tsx`:

```tsx
"use client"

import { useRouter } from "next/navigation"
import { useState } from "react"

import type { InterviewSessionCreateResponse } from "@/components/interview/interview-types"

export function InterviewLaunchPanel({
  screeningId,
  accessToken,
  backendBaseUrl,
}: {
  screeningId: string
  accessToken: string
  backendBaseUrl: string
}) {
  const router = useRouter()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleLaunch() {
    setIsSubmitting(true)
    setError(null)
    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/interviews`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ screening_id: screeningId }),
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Could not start the interview session.")
        return
      }

      const payload = (await response.json()) as InterviewSessionCreateResponse
      router.push(`/dashboard/interviews/${payload.session_id}`)
    } catch {
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 3 - Interview</p>
      <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
        Start a preliminary interview session
      </h2>
      <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
        Generate a focused interview plan from this completed screening and open the session workspace.
      </p>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          onClick={() => void handleLaunch()}
          type="button"
        >
          {isSubmitting ? "Starting..." : "Start interview session"}
        </button>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
      </div>
    </section>
  )
}
```

Modify `frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx` to import and render:

```tsx
import { InterviewLaunchPanel } from "@/components/interview/interview-launch-panel"
```

and return:

```tsx
  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <CVScreeningDetail screening={screening} historyItems={history.items} />
      <InterviewLaunchPanel
        screeningId={screening.screening_id}
        accessToken={session.accessToken}
        backendBaseUrl={backendBaseUrl}
      />
    </main>
  )
```

- [ ] **Step 4: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit the launch workflow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-types.ts frontend/src/components/interview/interview-launch-panel.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: launch interview sessions from screenings"
```

---

### Task 9: Build the interview session detail UI

**Files:**
- Create: `frontend/src/components/interview/interview-session-detail.tsx`
- Create: `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`
- Modify: `frontend/src/components/interview/interview-types.ts`

- [ ] **Step 1: Add the failing detail-view types**

Extend `frontend/src/components/interview/interview-types.ts` with:

```ts
export type InterviewTurn = {
  turn_id: string
  speaker: "interviewer" | "candidate"
  question_index: number
  content: string
  evaluation: Record<string, unknown>
  created_at: string
}

export type InterviewSessionDetailResponse = {
  session_id: string
  screening_id: string
  status: "draft" | "in_progress" | "completed"
  current_question_index: number
  total_questions: number
  plan: {
    session_goal: { vi: string; en: string }
    opening_script: { vi: string; en: string }
    questions: InterviewQuestion[]
  }
  turns: InterviewTurn[]
  summary: Record<string, unknown>
  created_at: string
}
```

Then create imports in a not-yet-existing `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`. Let the build fail.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the page and detail component do not exist.

- [ ] **Step 3: Implement the interview detail component and page**

Create `frontend/src/components/interview/interview-session-detail.tsx`:

```tsx
"use client"

import { useState } from "react"

import type { InterviewQuestion, InterviewSessionDetailResponse } from "@/components/interview/interview-types"

export function InterviewSessionDetail({
  initialSession,
  accessToken,
  backendBaseUrl,
}: {
  initialSession: InterviewSessionDetailResponse
  accessToken: string
  backendBaseUrl: string
}) {
  const [session, setSession] = useState(initialSession)
  const [answerText, setAnswerText] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const nextQuestion = session.plan.questions[session.current_question_index] ?? null

  async function handleSubmit() {
    if (!answerText.trim()) {
      setError("Please enter a candidate answer before continuing.")
      return
    }

    setIsSubmitting(true)
    setError(null)
    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/interviews/${session.session_id}/answer`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ answer_text: answerText }),
      })
      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setError(payload?.detail ?? "Could not submit the interview answer.")
        return
      }

      const detailResponse = await fetch(`${backendBaseUrl}/api/v1/interviews/${session.session_id}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        cache: "no-store",
      })
      const nextSession = (await detailResponse.json()) as InterviewSessionDetailResponse
      setSession(nextSession)
      setAnswerText("")
    } catch {
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Interview session</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--color-brand-text-primary)]">
          {session.plan.session_goal.en}
        </h1>
        <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">
          Status: {session.status} · Question {Math.min(session.current_question_index + 1, session.total_questions)} of {session.total_questions}
        </p>
      </section>

      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Plan</h2>
        <ul className="mt-4 space-y-3">
          {session.plan.questions.map((question) => (
            <li key={question.question_index} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--color-brand-text-muted)]">
                {question.dimension_name.en}
              </p>
              <p className="mt-2 text-sm font-medium text-[var(--color-brand-text-primary)]">{question.prompt.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-body)]">{question.purpose.en}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Transcript</h2>
        <div className="mt-4 space-y-3">
          {session.turns.map((turn) => (
            <article key={turn.turn_id} className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
              <p className="text-xs uppercase tracking-[0.14em] text-[var(--color-brand-text-muted)]">{turn.speaker}</p>
              <p className="mt-2 text-sm text-[var(--color-brand-text-primary)]">{turn.content}</p>
            </article>
          ))}
        </div>
      </section>

      {session.status !== "completed" && nextQuestion ? (
        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
          <h2 className="text-xl font-semibold text-[var(--color-brand-text-primary)]">Submit answer</h2>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Current question: {nextQuestion.prompt.en}</p>
          <textarea
            className="mt-4 min-h-32 w-full rounded-[16px] border border-[var(--color-brand-input-border)] p-4 text-sm outline-none"
            onChange={(event) => setAnswerText(event.target.value)}
            value={answerText}
          />
          <div className="mt-4 flex items-center gap-3">
            <button
              className="rounded-full bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSubmitting}
              onClick={() => void handleSubmit()}
              type="button"
            >
              {isSubmitting ? "Submitting..." : "Submit answer"}
            </button>
            {error ? <p className="text-sm text-red-700">{error}</p> : null}
          </div>
        </section>
      ) : null}
    </main>
  )
}
```

Create `frontend/src/app/dashboard/interviews/[sessionId]/page.tsx`:

```tsx
import { getServerSession } from "next-auth"
import { notFound, redirect } from "next/navigation"

import { InterviewSessionDetail } from "@/components/interview/interview-session-detail"
import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"
import { authOptions } from "@/lib/auth-options"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

export default async function InterviewSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>
}) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const { sessionId } = await params
  const response = await fetch(`${backendBaseUrl}/api/v1/interviews/${sessionId}`, {
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (response.status === 404) {
    notFound()
  }
  if (!response.ok) {
    redirect("/dashboard")
  }

  const detail = (await response.json()) as InterviewSessionDetailResponse
  return (
    <InterviewSessionDetail
      initialSession={detail}
      accessToken={session.accessToken}
      backendBaseUrl={backendBaseUrl}
    />
  )
}
```

- [ ] **Step 4: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit the interview detail UI**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/interview/interview-types.ts frontend/src/components/interview/interview-session-detail.tsx frontend/src/app/dashboard/interviews/[sessionId]/page.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview session workspace"
```

---

### Task 10: Add dashboard navigation and run focused verification

**Files:**
- Modify: `frontend/src/components/dashboard/dashboard-header.tsx`
- Test: `backend/tests/schemas/test_interview_schema.py`
- Test: `backend/tests/services/test_interview_plan_service.py`
- Test: `backend/tests/services/test_interview_session_service.py`
- Test: `backend/tests/api/test_interview_api.py`

- [ ] **Step 1: Update dashboard navigation**

Modify `frontend/src/components/dashboard/dashboard-header.tsx`:

```tsx
const NAV_ITEMS: { label: string; href: Route }[] = [
  { label: "Overview", href: "/dashboard" as Route },
  { label: "JD workspace", href: "/dashboard/jd" as Route },
  { label: "CV Screenings", href: "/dashboard/cv-screenings" as Route },
  { label: "Interviews", href: "/dashboard/interviews/session-demo" as Route },
]
```

Then immediately replace the temporary route with the first real session link pattern used elsewhere in the UI copy:

```tsx
{ label: "Interviews", href: "/dashboard/jd" as Route }
```

and change the label text under the nav bar description later only after the list page exists. This keeps this phase scope small and avoids shipping a dead route.

- [ ] **Step 2: Run the focused backend suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_interview_schema.py tests/services/test_interview_plan_service.py tests/services/test_interview_session_service.py tests/api/test_interview_api.py
```

Expected: PASS.

- [ ] **Step 3: Run frontend type checking**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 4: Verify the golden path manually**

Run the existing backend and frontend dev servers, then:

1. Open one completed CV screening detail page.
2. Click **Start interview session**.
3. Confirm redirect to `/dashboard/interviews/{sessionId}`.
4. Submit at least one candidate answer.
5. Confirm the transcript grows and the next question appears.
6. Continue until the session becomes `completed`.

Expected: the flow works without page crashes, the transcript persists across refresh, and the session finishes cleanly.

- [ ] **Step 5: Commit the verified Phase 3 foundation**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/interview.py backend/src/schemas/interview.py backend/src/services/interview_plan_service.py backend/src/services/interview_session_service.py backend/src/api/v1/interviews.py backend/src/api/v1/router.py backend/tests/schemas/test_interview_schema.py backend/tests/services/test_interview_plan_service.py backend/tests/services/test_interview_session_service.py backend/tests/api/test_interview_api.py frontend/src/components/interview/interview-types.ts frontend/src/components/interview/interview-launch-panel.tsx frontend/src/components/interview/interview-session-detail.tsx frontend/src/app/dashboard/cv-screenings/[screeningId]/page.tsx frontend/src/app/dashboard/interviews/[sessionId]/page.tsx frontend/src/components/dashboard/dashboard-header.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add interview session foundation"
```

---

## Self-Review

- Spec coverage: this plan covers the next narrow phase after CV screening: interview-plan generation, interview-session persistence, turn submission, detail APIs, launch UI, and the session workspace. It intentionally excludes LiveKit, STT, TTS, scheduling, ranking, and interview list pages to keep the phase independently shippable.
- Placeholder scan: no TBD, TODO, or vague “handle this later” steps remain. Each task names exact files, commands, and code targets.
- Type consistency: the same names are used throughout: `InterviewSession`, `InterviewTurn`, `InterviewPlanPayload`, `InterviewSessionService`, `create_session`, `submit_answer`, and `get_session_detail`.
- Scope check: this is one subsystem, not the whole realtime interview platform. That is deliberate. It gives the team a stable text-first interview foundation before voice/video integration.
