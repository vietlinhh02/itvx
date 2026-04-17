# Background JD Analysis and CV Screening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move JD analysis and CV screening off the request path so uploads return `202 Accepted` immediately, while a database-backed worker processes AI tasks and updates resource state.

**Architecture:** Add a persistent `background_jobs` model, a worker command that claims queued jobs from the database, and enqueue APIs for JD analysis and CV screening. Keep read endpoints intact, add a job-status endpoint for polling, and update frontend upload flows to handle `processing`, `completed`, and `failed` states.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, Pydantic v2, Next.js, TypeScript, pytest

---

## File Structure

- Create: `backend/src/models/background_job.py`
  - Database model and enums for background jobs.
- Modify: `backend/src/models/__init__.py`
  - Export the new model if the package currently centralizes model imports.
- Modify: `backend/src/models/cv.py`
  - Add persisted `status` to `CandidateScreening`.
- Modify: `backend/src/schemas/jd.py`
  - Add async enqueue response types if current synchronous schemas do not fit.
- Modify: `backend/src/schemas/cv.py`
  - Add async enqueue response types and job-status response types.
- Modify: `backend/src/services/jd_service.py`
  - Split enqueue work from worker execution.
- Modify: `backend/src/services/cv_screening_service.py`
  - Split enqueue work from worker execution.
- Create: `backend/src/services/background_jobs.py`
  - Queue claim, finalize, and failure helpers.
- Create: `backend/src/api/v1/jobs.py`
  - Polling endpoint for job status.
- Modify: `backend/src/api/v1/jd.py`
  - Return `202` and enqueue JD work.
- Modify: `backend/src/api/v1/cv.py`
  - Return `202` and enqueue CV work.
- Modify: `backend/src/main.py`
  - Register the jobs router.
- Create: `backend/src/scripts/run_background_jobs.py`
  - Worker loop entry point.
- Modify: `backend/tests/api/test_jd_api.py`
  - Add enqueue and status endpoint tests.
- Modify: `backend/tests/api/test_cv_api.py`
  - Add enqueue and status endpoint tests.
- Modify: `backend/tests/services/test_jd_service.py`
  - Add enqueue and worker execution tests.
- Modify: `backend/tests/services/test_cv_screening_service.py`
  - Add enqueue and worker execution tests.
- Modify: `frontend/src/components/jd/jd-upload-panel.tsx`
  - Handle enqueue response and processing state.
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`
  - Handle enqueue response and processing state.
- Modify: `frontend/src/components/jd/cv-screening-types.ts`
  - Add async response and job-status types.
- Modify: `frontend/src/components/jd/jd-upload-types.ts` or the file that defines JD types.
  - Add enqueue response and job-status types if that file exists; otherwise keep them in `jd-upload-panel.tsx`.

---

### Task 1: Add the background job model and screening status field

**Files:**
- Create: `backend/src/models/background_job.py`
- Modify: `backend/src/models/cv.py`
- Test: `backend/tests/schemas/test_cv_schema.py`

- [ ] **Step 1: Write the failing schema test for screening status and background jobs**

Add this test to `backend/tests/schemas/test_cv_schema.py`:

```python
from src.models.background_job import BackgroundJob
from src.models.cv import CandidateScreening


def test_background_job_and_screening_status_columns_exist() -> None:
    status_column = CandidateScreening.__table__.c.status
    assert not bool(status_column.nullable)
    assert status_column.default is not None

    job_columns = BackgroundJob.__table__.c
    assert "job_type" in job_columns
    assert "resource_type" in job_columns
    assert "payload" in job_columns
    assert "error_message" in job_columns
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_cv_schema.py -k background_job_and_screening_status_columns_exist
```

Expected: FAIL because the model and column do not exist yet.

- [ ] **Step 3: Add the model and status field**

Create `backend/src/models/background_job.py`:

```python
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class BackgroundJobType(StrEnum):
    JD_ANALYSIS = "jd_analysis"
    CV_SCREENING = "cv_screening"


class BackgroundJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundResourceType(StrEnum):
    JD_DOCUMENT = "jd_document"
    CANDIDATE_SCREENING = "candidate_screening"


class BackgroundJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "background_jobs"

    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="queued")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
```

Modify `backend/src/models/cv.py` by adding the field inside `CandidateScreening`:

```python
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")
```

- [ ] **Step 4: Run the schema test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/schemas/test_cv_schema.py -k background_job_and_screening_status_columns_exist
```

Expected: PASS.

- [ ] **Step 5: Commit the model changes**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/background_job.py backend/src/models/cv.py backend/tests/schemas/test_cv_schema.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add background job model"
```

---

### Task 2: Add shared background job service helpers

**Files:**
- Create: `backend/src/services/background_jobs.py`
- Test: `backend/tests/services/test_jd_service.py`

- [ ] **Step 1: Write the failing test for claiming a queued job**

Add this test to `backend/tests/services/test_jd_service.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.services.background_jobs import BackgroundJobService


@pytest.mark.asyncio
async def test_claim_next_job_marks_job_running(db_session: AsyncSession) -> None:
    db_session.add(
        BackgroundJob(
            job_type="jd_analysis",
            status="queued",
            resource_type="jd_document",
            resource_id="jd-1",
            payload={"jd_id": "jd-1"},
        )
    )
    await db_session.commit()

    service = BackgroundJobService(db_session)
    job = await service.claim_next_job()

    assert job is not None
    assert job.status == "running"
    assert job.started_at is not None
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k claim_next_job_marks_job_running
```

Expected: FAIL because `BackgroundJobService` does not exist.

- [ ] **Step 3: Implement the minimal background job service**

Create `backend/src/services/background_jobs.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob


class BackgroundJobService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def claim_next_job(self) -> BackgroundJob | None:
        statement = (
            select(BackgroundJob)
            .where(BackgroundJob.status == "queued")
            .order_by(BackgroundJob.created_at.asc())
            .limit(1)
        )
        job = await self._db_session.scalar(statement)
        if job is None:
            return None
        job.status = "running"
        job.started_at = datetime.now(UTC).replace(tzinfo=None)
        await self._db_session.commit()
        await self._db_session.refresh(job)
        return job

    async def mark_completed(self, job: BackgroundJob) -> None:
        job.status = "completed"
        job.completed_at = datetime.now(UTC).replace(tzinfo=None)
        job.error_message = None
        await self._db_session.commit()

    async def mark_failed(self, job: BackgroundJob, error_message: str) -> None:
        job.status = "failed"
        job.completed_at = datetime.now(UTC).replace(tzinfo=None)
        job.error_message = error_message
        await self._db_session.commit()
```

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k claim_next_job_marks_job_running
```

Expected: PASS.

- [ ] **Step 5: Commit the helper service**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/background_jobs.py backend/tests/services/test_jd_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add background job service"
```

---

### Task 3: Make JD analysis enqueue work instead of running inline

**Files:**
- Modify: `backend/src/schemas/jd.py`
- Modify: `backend/src/services/jd_service.py`
- Modify: `backend/src/api/v1/jd.py`
- Test: `backend/tests/services/test_jd_service.py`
- Test: `backend/tests/api/test_jd_api.py`

- [ ] **Step 1: Write the failing JD enqueue service test**

Add this test to `backend/tests/services/test_jd_service.py`:

```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.models.jd import JDDocument
from src.services.jd_service import JDAnalysisService


@pytest.mark.asyncio
async def test_enqueue_analysis_creates_processing_document_and_job(
    db_session: AsyncSession,
    tmp_path,
) -> None:
    service = JDAnalysisService(upload_dir=tmp_path, db_session=db_session)

    response = await service.enqueue_analysis_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\njd",
    )

    document = await db_session.scalar(select(JDDocument).where(JDDocument.id == response.jd_id))
    job = await db_session.scalar(select(BackgroundJob).where(BackgroundJob.id == response.job_id))

    assert response.status == "processing"
    assert document is not None
    assert document.status == "processing"
    assert job is not None
    assert job.job_type == "jd_analysis"
```

- [ ] **Step 2: Run the service test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k enqueue_analysis_creates_processing_document_and_job
```

Expected: FAIL because `enqueue_analysis_upload` and the response shape do not exist.

- [ ] **Step 3: Add the enqueue response schema**

In `backend/src/schemas/jd.py`, add:

```python
class JDAnalysisEnqueueResponse(BaseModel):
    job_id: str
    jd_id: str
    file_name: str
    status: Literal["processing"]
```

- [ ] **Step 4: Implement enqueue logic in the JD service**

In `backend/src/services/jd_service.py`, add:

```python
from src.models.background_job import BackgroundJob
from src.schemas.jd import JDAnalysisEnqueueResponse
```

Then add:

```python
    async def enqueue_analysis_upload(
        self,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> JDAnalysisEnqueueResponse:
        if self._db_session is None:
            raise RuntimeError("JDAnalysisService requires a database session")

        stored_file = store_upload_file(
            upload_dir=self._upload_dir,
            file_name=file_name,
            file_bytes=file_bytes,
        )
        document = JDDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        self._db_session.add(document)
        await self._db_session.flush()

        job = BackgroundJob(
            job_type="jd_analysis",
            status="queued",
            resource_type="jd_document",
            resource_id=document.id,
            payload={
                "jd_id": document.id,
                "file_name": stored_file.file_name,
                "mime_type": mime_type,
                "storage_path": stored_file.storage_path,
            },
        )
        self._db_session.add(job)
        await self._db_session.commit()
        await self._db_session.refresh(job)

        return JDAnalysisEnqueueResponse(
            job_id=job.id,
            jd_id=document.id,
            file_name=stored_file.file_name,
            status="processing",
        )
```

- [ ] **Step 5: Change the JD API route to return `202 Accepted`**

In `backend/src/api/v1/jd.py`, change the route decorator and body:

```python
@router.post("/analyze", response_model=JDAnalysisEnqueueResponse, status_code=202)
async def analyze_jd(...):
    ...
    service = JDAnalysisService(upload_dir=settings.jd_upload_path, db_session=db)
    return await service.enqueue_analysis_upload(
        file_name=file.filename or "uploaded.jd",
        mime_type=file.content_type,
        file_bytes=file_bytes,
    )
```

- [ ] **Step 6: Add the failing API test for `202 Accepted`**

In `backend/tests/api/test_jd_api.py`, add:

```python
def test_jd_analyze_returns_processing_enqueue_response(monkeypatch) -> None:
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"%PDF-1.7\njd", "application/pdf")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "processing"
    assert "job_id" in payload
    assert "jd_id" in payload
```

Update the fake JD service so `enqueue_analysis_upload()` returns a matching response.

- [ ] **Step 7: Run the JD enqueue tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k enqueue_analysis_creates_processing_document_and_job
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_jd_api.py -k jd_analyze_returns_processing_enqueue_response
```

Expected: both PASS.

- [ ] **Step 8: Commit the JD enqueue path**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/jd.py backend/src/services/jd_service.py backend/src/api/v1/jd.py backend/tests/services/test_jd_service.py backend/tests/api/test_jd_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: enqueue jd analysis jobs"
```

---

### Task 4: Make CV screening enqueue work instead of running inline

**Files:**
- Modify: `backend/src/schemas/cv.py`
- Modify: `backend/src/services/cv_screening_service.py`
- Modify: `backend/src/api/v1/cv.py`
- Test: `backend/tests/services/test_cv_screening_service.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Write the failing CV enqueue service test**

Add this test to `backend/tests/services/test_cv_screening_service.py`:

```python
@pytest.mark.asyncio
async def test_enqueue_screening_creates_processing_screening_and_job(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    service = CVScreeningService(upload_dir=tmp_path, db_session=db_session)

    response = await service.enqueue_screening_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    screening = await db_session.scalar(
        select(CandidateScreening).where(CandidateScreening.id == response.screening_id)
    )
    job = await db_session.scalar(select(BackgroundJob).where(BackgroundJob.id == response.job_id))

    assert response.status == "processing"
    assert screening is not None
    assert screening.status == "processing"
    assert job is not None
    assert job.job_type == "cv_screening"
```

- [ ] **Step 2: Run the service test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_cv_screening_service.py -k enqueue_screening_creates_processing_screening_and_job
```

Expected: FAIL because `enqueue_screening_upload` and the response type do not exist.

- [ ] **Step 3: Add the CV enqueue response schema**

In `backend/src/schemas/cv.py`, add:

```python
class CVScreeningEnqueueResponse(BaseModel):
    job_id: str
    screening_id: str
    jd_id: str
    file_name: str
    status: Literal["processing"]
```

- [ ] **Step 4: Implement CV enqueue logic**

In `backend/src/services/cv_screening_service.py`, add:

```python
from src.models.background_job import BackgroundJob
from src.schemas.cv import CVScreeningEnqueueResponse
```

Then add:

```python
    async def enqueue_screening_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningEnqueueResponse:
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        await self._load_jd_analysis(jd_id)
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        candidate_document = CandidateDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        self._db_session.add(candidate_document)
        await self._db_session.flush()

        candidate_profile = CandidateProfile(
            candidate_document_id=candidate_document.id,
            profile_payload={},
        )
        self._db_session.add(candidate_profile)
        await self._db_session.flush()

        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=candidate_profile.id,
            model_name=settings.gemini_model,
            status="processing",
            screening_payload={},
        )
        self._db_session.add(screening)
        await self._db_session.flush()

        job = BackgroundJob(
            job_type="cv_screening",
            status="queued",
            resource_type="candidate_screening",
            resource_id=screening.id,
            payload={
                "screening_id": screening.id,
                "jd_id": jd_id,
                "candidate_document_id": candidate_document.id,
                "candidate_profile_id": candidate_profile.id,
                "file_name": stored_file.file_name,
                "mime_type": mime_type,
                "storage_path": stored_file.storage_path,
            },
        )
        self._db_session.add(job)
        await self._db_session.commit()
        await self._db_session.refresh(job)

        return CVScreeningEnqueueResponse(
            job_id=job.id,
            screening_id=screening.id,
            jd_id=jd_id,
            file_name=stored_file.file_name,
            status="processing",
        )
```

- [ ] **Step 5: Change the CV API route to return `202 Accepted`**

In `backend/src/api/v1/cv.py`, update the route decorator and body:

```python
@router.post("/screen", response_model=CVScreeningEnqueueResponse, status_code=202)
async def screen_cv(...):
    ...
    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    try:
        return await service.enqueue_screening_upload(
            jd_id=jd_id,
            file_name=file.filename or "uploaded-cv",
            mime_type=file.content_type,
            file_bytes=file_bytes,
        )
```

- [ ] **Step 6: Add the failing CV enqueue API test**

In `backend/tests/api/test_cv_api.py`, add:

```python
def test_cv_screen_returns_processing_enqueue_response(monkeypatch: MonkeyPatch) -> None:
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "processing"
    assert payload["jd_id"] == "test-jd-id"
    assert "job_id" in payload
    assert "screening_id" in payload
```

Update the fake CV service to provide `enqueue_screening_upload()`.

- [ ] **Step 7: Run the CV enqueue tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_cv_screening_service.py -k enqueue_screening_creates_processing_screening_and_job
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_cv_api.py -k cv_screen_returns_processing_enqueue_response
```

Expected: both PASS.

- [ ] **Step 8: Commit the CV enqueue path**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/cv.py backend/src/services/cv_screening_service.py backend/src/api/v1/cv.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: enqueue cv screening jobs"
```

---

### Task 5: Add worker execution for JD and CV jobs

**Files:**
- Modify: `backend/src/services/jd_service.py`
- Modify: `backend/src/services/cv_screening_service.py`
- Create: `backend/src/scripts/run_background_jobs.py`
- Test: `backend/tests/services/test_jd_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing JD worker test**

Add this test to `backend/tests/services/test_jd_service.py`:

```python
@pytest.mark.asyncio
async def test_run_jd_job_completes_document_and_analysis(
    db_session: AsyncSession,
    tmp_path,
) -> None:
    service = JDAnalysisService(upload_dir=tmp_path, db_session=db_session)
    response = await service.enqueue_analysis_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\njd",
    )

    await service.run_analysis_job(response.jd_id)

    document = await db_session.scalar(select(JDDocument).where(JDDocument.id == response.jd_id))
    analysis = await db_session.scalar(select(JDAnalysis).where(JDAnalysis.jd_document_id == response.jd_id))

    assert document is not None
    assert document.status == "completed"
    assert analysis is not None
```

- [ ] **Step 2: Write the failing CV worker test**

Add this test to `backend/tests/services/test_cv_screening_service.py`:

```python
@pytest.mark.asyncio
async def test_run_cv_job_completes_screening(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    response = await service.enqueue_screening_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    await service.run_screening_job(response.screening_id)

    screening = await db_session.scalar(
        select(CandidateScreening).where(CandidateScreening.id == response.screening_id)
    )

    assert screening is not None
    assert screening.status == "completed"
    assert screening.screening_payload["result"]["recommendation"] == "advance"
```

- [ ] **Step 3: Run the worker tests to verify they fail**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k run_jd_job_completes_document_and_analysis
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_cv_screening_service.py -k run_cv_job_completes_screening
```

Expected: FAIL because `run_analysis_job` and `run_screening_job` do not exist.

- [ ] **Step 4: Implement JD worker execution**

In `backend/src/services/jd_service.py`, add:

```python
    async def run_analysis_job(self, jd_id: str) -> None:
        if self._db_session is None:
            raise RuntimeError("JDAnalysisService requires a database session")

        document = await self._db_session.scalar(
            select(JDDocument).where(JDDocument.id == jd_id)
        )
        if document is None:
            raise ValueError("JD document not found")

        analysis = await self._extractor.extract(Path(document.storage_path), document.mime_type)
        self._db_session.add(
            JDAnalysis(
                jd_document_id=document.id,
                model_name=settings.gemini_model,
                analysis_payload=analysis.model_dump(mode="json"),
            )
        )
        document.status = "completed"
        await self._db_session.commit()
```

- [ ] **Step 5: Implement CV worker execution**

In `backend/src/services/cv_screening_service.py`, add:

```python
    async def run_screening_job(self, screening_id: str) -> None:
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateProfile, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            raise ValueError("CV screening not found")

        screening, profile, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        jd_analysis = await self._load_jd_analysis(screening.jd_document_id)
        candidate_profile = await self._extractor.extract(
            Path(candidate_document.storage_path),
            candidate_document.mime_type,
        )
        profile.profile_payload = candidate_profile.model_dump(mode="json")

        generated_payload = await self._generate_screening_payload(jd_analysis, candidate_profile)
        reconciled_payload = self._reconcile_screening_payload(generated_payload)
        screening.screening_payload = reconciled_payload.model_dump(mode="json")
        screening.status = "completed"
        candidate_document.status = "completed"
        await self._db_session.commit()
```

- [ ] **Step 6: Add the worker script**

Create `backend/src/scripts/run_background_jobs.py`:

```python
import asyncio

from src.database import AsyncSessionLocal
from src.services.background_jobs import BackgroundJobService
from src.services.cv_screening_service import CVScreeningService
from src.services.jd_service import JDAnalysisService


async def run_once() -> bool:
    async with AsyncSessionLocal() as session:
        job_service = BackgroundJobService(session)
        job = await job_service.claim_next_job()
        if job is None:
            return False
        try:
            if job.job_type == "jd_analysis":
                jd_service = JDAnalysisService(db_session=session)
                await jd_service.run_analysis_job(job.resource_id)
            else:
                cv_service = CVScreeningService(db_session=session)
                await cv_service.run_screening_job(job.resource_id)
            await job_service.mark_completed(job)
        except Exception as exc:
            await job_service.mark_failed(job, str(exc))
        return True


async def main() -> None:
    while True:
        ran_job = await run_once()
        if not ran_job:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 7: Run the worker tests to verify they pass**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py -k run_jd_job_completes_document_and_analysis
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_cv_screening_service.py -k run_cv_job_completes_screening
```

Expected: both PASS.

- [ ] **Step 8: Commit the worker execution path**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/services/jd_service.py backend/src/services/cv_screening_service.py backend/src/scripts/run_background_jobs.py backend/tests/services/test_jd_service.py backend/tests/services/test_cv_screening_service.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: run jd and cv jobs in background worker"
```

---

### Task 6: Add the job-status API endpoint

**Files:**
- Modify: `backend/src/schemas/cv.py`
- Create: `backend/src/api/v1/jobs.py`
- Modify: `backend/src/main.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Write the failing job-status API test**

Add this test to `backend/tests/api/test_cv_api.py`:

```python
def test_get_job_status_returns_resource_tracking_fields(monkeypatch: MonkeyPatch) -> None:
    stub_jobs_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/jobs/test-job-id")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_id"] == "test-job-id"
    assert payload["status"] == "running"
    assert payload["resource_type"] == "candidate_screening"
    assert payload["resource_id"] == "screening-id"
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_cv_api.py -k get_job_status_returns_resource_tracking_fields
```

Expected: FAIL because the route and schema do not exist.

- [ ] **Step 3: Add the job-status schema**

In `backend/src/schemas/cv.py`, add:

```python
class BackgroundJobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    resource_type: str
    resource_id: str
    error_message: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
```

- [ ] **Step 4: Create the jobs API route**

Create `backend/src/api/v1/jobs.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.background_job import BackgroundJob
from src.schemas.cv import BackgroundJobResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(job_id: str, db: AsyncSession = Depends(get_db)) -> BackgroundJobResponse:
    job = await db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Background job not found")
    return BackgroundJobResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        error_message=job.error_message,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )
```

- [ ] **Step 5: Register the router and update the test double**

In `backend/src/main.py`, import and include the jobs router.

In `backend/tests/api/test_cv_api.py`, add a fake jobs-service or override path so the new route returns:

```json
{
  "job_id": "test-job-id",
  "job_type": "cv_screening",
  "status": "running",
  "resource_type": "candidate_screening",
  "resource_id": "screening-id",
  "error_message": null,
  "started_at": "2026-04-16T00:00:00Z",
  "completed_at": null
}
```

- [ ] **Step 6: Run the job-status API test to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/api/test_cv_api.py -k get_job_status_returns_resource_tracking_fields
```

Expected: PASS.

- [ ] **Step 7: Commit the jobs API**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/schemas/cv.py backend/src/api/v1/jobs.py backend/src/main.py backend/tests/api/test_cv_api.py
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: add background job status api"
```

---

### Task 7: Update frontend JD upload flow for async jobs

**Files:**
- Modify: `frontend/src/components/jd/jd-upload-panel.tsx`
- Test: `frontend/src/components/jd/jd-upload-panel.tsx`

- [ ] **Step 1: Write the failing frontend type change**

Update the result type usage in `frontend/src/components/jd/jd-upload-panel.tsx` so submit logic expects:

```ts
type JDAnalysisEnqueueResponse = {
  job_id: string
  jd_id: string
  file_name: string
  status: "processing"
}
```

Then change the submit handler to assign the result to this type. Let TypeScript fail where the old synchronous shape is assumed.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the component still expects the old analysis payload immediately.

- [ ] **Step 3: Update the JD upload panel to handle processing state**

Change the submit path so it:

- stores `job_id`
- stores `jd_id`
- shows a processing message
- polls `/api/v1/jobs/{job_id}` until `completed` or `failed`
- redirects to `/dashboard/jd/${jd_id}` on completion

Use a minimal polling pattern inside the component:

```ts
async function pollJob(jobId: string): Promise<BackgroundJobResponse> {
  while (true) {
    const response = await fetch(`${backendBaseUrl}/api/v1/jobs/${jobId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
      cache: "no-store",
    })
    const job = (await response.json()) as BackgroundJobResponse
    if (job.status === "completed" || job.status === "failed") {
      return job
    }
    await new Promise((resolve) => setTimeout(resolve, 1000))
  }
}
```

- [ ] **Step 4: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit the JD frontend async flow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/jd/jd-upload-panel.tsx
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: poll jd background jobs in frontend"
```

---

### Task 8: Update frontend CV upload flow for async jobs

**Files:**
- Modify: `frontend/src/components/jd/cv-screening-panel.tsx`
- Modify: `frontend/src/components/jd/cv-screening-types.ts`

- [ ] **Step 1: Write the failing frontend type change for CV enqueue**

In `frontend/src/components/jd/cv-screening-types.ts`, add:

```ts
export type CVScreeningEnqueueResponse = {
  job_id: string
  screening_id: string
  jd_id: string
  file_name: string
  status: "processing"
}

export type BackgroundJobResponse = {
  job_id: string
  job_type: string
  status: string
  resource_type: string
  resource_id: string
  error_message: string | null
  started_at: string | null
  completed_at: string | null
}
```

Then update `cv-screening-panel.tsx` to expect `CVScreeningEnqueueResponse` and let TypeScript fail where it still expects `CVScreeningResponse` directly.

- [ ] **Step 2: Run type checking to verify it fails**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: FAIL because the submit code still expects a completed screening payload.

- [ ] **Step 3: Update the CV screening panel to poll jobs**

Change submit behavior so it:

- stores `job_id`
- stores `screening_id`
- shows `processing`
- polls `/api/v1/jobs/{job_id}`
- redirects to `/dashboard/cv-screenings/${screening_id}` on completion
- shows failure state if the job returns `failed`

Use the same polling helper pattern as the JD upload panel.

- [ ] **Step 4: Run type checking to verify it passes**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 5: Commit the CV frontend async flow**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add frontend/src/components/jd/cv-screening-panel.tsx frontend/src/components/jd/cv-screening-types.ts
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: poll cv background jobs in frontend"
```

---

### Task 9: Verify the full async flow end to end

**Files:**
- Modify: none
- Test: `backend/tests/api/test_jd_api.py`
- Test: `backend/tests/api/test_cv_api.py`
- Test: `backend/tests/services/test_jd_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Run the full targeted backend suite**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run pytest -q tests/services/test_jd_service.py tests/services/test_cv_screening_service.py tests/api/test_jd_api.py tests/api/test_cv_api.py
```

Expected: PASS.

- [ ] **Step 2: Run frontend type checking**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npx tsc --noEmit
```

Expected: PASS.

- [ ] **Step 3: Start the worker locally**

Run:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run python -m src.scripts.run_background_jobs
```

Expected: process stays running and polls for jobs.

- [ ] **Step 4: Start or reuse backend and frontend dev servers**

Run only if needed:

```bash
cd "/home/eddiesngu/Desktop/Dang/interviewx/backend" && uv run uvicorn src.main:app --reload
cd "/home/eddiesngu/Desktop/Dang/interviewx/frontend" && npm run dev
```

Expected: backend and frontend are reachable locally.

- [ ] **Step 5: Verify JD upload returns processing first**

Upload one JD through the UI or API.

Expected:
- upload returns quickly
- frontend shows processing state
- worker picks up the job
- JD detail becomes available after completion

- [ ] **Step 6: Verify CV upload returns processing first**

Upload one CV against a completed JD.

Expected:
- upload returns quickly
- frontend shows processing state
- worker picks up the job
- screening detail opens after completion

- [ ] **Step 7: Commit the final async processing feature**

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" status --short
```

If only intended files changed, commit them:

```bash
git -C "/home/eddiesngu/Desktop/Dang/interviewx" add backend/src/models/background_job.py backend/src/models/cv.py backend/src/services/background_jobs.py backend/src/services/jd_service.py backend/src/services/cv_screening_service.py backend/src/api/v1/jd.py backend/src/api/v1/cv.py backend/src/api/v1/jobs.py backend/src/main.py backend/src/scripts/run_background_jobs.py backend/src/schemas/jd.py backend/src/schemas/cv.py backend/tests/schemas/test_cv_schema.py backend/tests/services/test_jd_service.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_jd_api.py backend/tests/api/test_cv_api.py frontend/src/components/jd/jd-upload-panel.tsx frontend/src/components/jd/cv-screening-panel.tsx frontend/src/components/jd/cv-screening-types.ts
git -C "/home/eddiesngu/Desktop/Dang/interviewx" commit -m "feat: move jd and cv ai work to background jobs"
```

---

## Self-Review

- Spec coverage: this plan covers schema changes, enqueue endpoints, worker execution, polling status, frontend processing UX, and failure states.
- Placeholder scan: no TODO or TBD markers remain.
- Type consistency: the same names are used throughout: `BackgroundJob`, `JDAnalysisEnqueueResponse`, `CVScreeningEnqueueResponse`, `BackgroundJobResponse`, `enqueue_analysis_upload`, `enqueue_screening_upload`, `run_analysis_job`, and `run_screening_job`.
