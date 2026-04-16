# JD Analysis Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI JD upload and analysis flow that stores the original JD file, sends it to Gemini through LangChain, validates a structured bilingual output, persists the analysis, and returns a screening-ready hiring blueprint.

**Architecture:** The existing FastAPI backend remains the entry point. A new JD route calls a focused service layer that stores the uploaded file, invokes LangChain's Gemini integration for structured extraction, validates the returned Pydantic payload, and writes the document and analysis records to PostgreSQL. The response shape is stable and designed for downstream CV screening.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, PostgreSQL, Pydantic v2, LangChain, langchain-google-genai, pytest, pytest-asyncio, httpx

---

## Planned File Structure

- Modify: `backend/src/config.py`
  - Add Gemini model and JD storage settings.
- Modify: `backend/src/models/__init__.py`
  - Export new JD models.
- Create: `backend/src/models/jd.py`
  - Define `JDDocument` and `JDAnalysis` ORM models.
- Create: `backend/src/schemas/jd.py`
  - Define upload response and analysis payload schemas.
- Modify: `backend/src/schemas/__init__.py`
  - Export JD schemas.
- Create: `backend/src/services/file_storage.py`
  - Store uploaded JD files on disk.
- Create: `backend/src/services/jd_extractor.py`
  - LangChain + Gemini extraction client.
- Create: `backend/src/services/jd_service.py`
  - End-to-end JD analysis orchestration.
- Modify: `backend/src/services/__init__.py`
  - Export new services.
- Create: `backend/src/api/v1/jd.py`
  - Upload-only JD analysis endpoint.
- Modify: `backend/src/api/v1/router.py`
  - Register JD router.
- Create: `backend/tests/conftest.py`
  - Async test app and DB/session fixtures.
- Create: `backend/tests/schemas/test_jd_schema.py`
  - Schema validation coverage.
- Create: `backend/tests/services/test_file_storage.py`
  - File storage tests.
- Create: `backend/tests/services/test_jd_service.py`
  - Service-level orchestration tests with mocked Gemini.
- Create: `backend/tests/api/test_jd_api.py`
  - Upload endpoint tests.

### Task 1: Add settings and JD persistence models

**Files:**
- Modify: `backend/src/config.py`
- Create: `backend/src/models/jd.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/schemas/test_jd_schema.py`

- [ ] **Step 1: Write the failing model import test**

```python
from src.models import JDAnalysis, JDDocument


def test_jd_models_are_exported() -> None:
    assert JDDocument.__tablename__ == "jd_documents"
    assert JDAnalysis.__tablename__ == "jd_analyses"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/schemas/test_jd_schema.py::test_jd_models_are_exported -v`
Expected: FAIL with `ImportError` because the JD models do not exist yet.

- [ ] **Step 3: Add configuration settings for Gemini and file storage**

```python
"""Application configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql://interviewx:interviewx_secret@localhost:5432/interviewx"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    google_client_id: str = ""
    google_client_secret: str = ""

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro"
    jd_upload_dir: str = "storage/jd_uploads"
    jd_max_upload_size_bytes: int = 10_485_760

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def jd_upload_path(self) -> Path:
        """Return the JD upload directory as a Path."""
        return Path(self.jd_upload_dir)


settings = Settings()
```

- [ ] **Step 4: Add the JD ORM models**

```python
"""JD persistence models."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class JDDocument(Base, UUIDMixin, TimestampMixin):
    """Uploaded JD document metadata."""

    __tablename__ = "jd_documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")

    analysis: Mapped["JDAnalysis | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )


class JDAnalysis(Base, UUIDMixin, TimestampMixin):
    """Structured Gemini analysis for a JD document."""

    __tablename__ = "jd_analyses"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    document: Mapped[JDDocument] = relationship(back_populates="analysis")
```

- [ ] **Step 5: Export the models from the package**

```python
from src.models.jd import JDAnalysis, JDDocument
from src.models.user import User

__all__ = ["JDAnalysis", "JDDocument", "User"]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest backend/tests/schemas/test_jd_schema.py::test_jd_models_are_exported -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/config.py backend/src/models/jd.py backend/src/models/__init__.py backend/tests/schemas/test_jd_schema.py
git commit -m "feat: add jd document models"
```

### Task 2: Define the JD analysis schema contract

**Files:**
- Create: `backend/src/schemas/jd.py`
- Modify: `backend/src/schemas/__init__.py`
- Test: `backend/tests/schemas/test_jd_schema.py`

- [ ] **Step 1: Write the failing schema validation tests**

```python
import pytest
from pydantic import ValidationError

from src.schemas.jd import BilingualText, EvaluationDimension, JDAnalysisPayload


def test_bilingual_text_requires_vi_and_en() -> None:
    with pytest.raises(ValidationError):
        BilingualText.model_validate({"vi": "Ky su Backend"})


def test_evaluation_dimension_rejects_invalid_priority() -> None:
    with pytest.raises(ValidationError):
        EvaluationDimension.model_validate(
            {
                "name": {"vi": "Ky nang Python", "en": "Python Skill"},
                "description": {"vi": "Mo ta", "en": "Description"},
                "priority": "critical",
                "weight": 0.5,
                "evidence_signals": [{"vi": "Da lam API", "en": "Built APIs"}],
            }
        )


def test_jd_analysis_payload_requires_weights_to_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        JDAnalysisPayload.model_validate(
            {
                "job_overview": {
                    "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                    "department": {"vi": "Ky thuat", "en": "Engineering"},
                    "seniority_level": "senior",
                    "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                    "work_mode": "hybrid",
                    "role_summary": {"vi": "Tom tat", "en": "Summary"},
                    "company_benefits": [],
                },
                "requirements": {
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "tools_and_technologies": [],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": ["Backend Engineer"],
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
                            "name": {"vi": "Python", "en": "Python"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "must_have",
                            "weight": 0.6,
                            "evidence_signals": [{"vi": "Du an", "en": "Projects"}],
                        },
                        {
                            "name": {"vi": "SQL", "en": "SQL"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.3,
                            "evidence_signals": [{"vi": "Query", "en": "Query"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": ["3+ years experience"],
                        "scoring_principle": "Nice-to-have cannot replace must-have.",
                    },
                    "ambiguities_for_human_review": [],
                },
            }
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/schemas/test_jd_schema.py -v`
Expected: FAIL with `ModuleNotFoundError` because the JD schemas do not exist yet.

- [ ] **Step 3: Implement the schema contract**

```python
"""Schemas for JD analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BilingualText(BaseModel):
    """Human-readable text available in Vietnamese and English."""

    vi: str = Field(min_length=1)
    en: str = Field(min_length=1)


class JobOverview(BaseModel):
    """High-level job metadata for HR review."""

    job_title: BilingualText
    department: BilingualText
    seniority_level: Literal["intern", "junior", "mid", "senior", "lead", "manager", "unknown"]
    location: BilingualText
    work_mode: Literal["onsite", "hybrid", "remote", "unknown"]
    role_summary: BilingualText
    company_benefits: list[BilingualText]


class ExperienceRequirements(BaseModel):
    """Experience requirements extracted from the JD."""

    minimum_years: int | None = Field(default=None, ge=0)
    relevant_roles: list[str]
    preferred_domains: list[str]


class Requirements(BaseModel):
    """Structured hiring requirements for screening."""

    required_skills: list[str]
    preferred_skills: list[str]
    tools_and_technologies: list[str]
    experience_requirements: ExperienceRequirements
    education_and_certifications: list[str]
    language_requirements: list[str]
    key_responsibilities: list[BilingualText]
    screening_knockout_criteria: list[str]


class EvaluationDimension(BaseModel):
    """A weighted screening dimension derived from the JD."""

    name: BilingualText
    description: BilingualText
    priority: Literal["must_have", "important", "nice_to_have"]
    weight: float = Field(gt=0, le=1)
    evidence_signals: list[BilingualText]


class ScreeningRules(BaseModel):
    """Rules that govern early candidate screening."""

    minimum_requirements: list[str]
    scoring_principle: str


class RubricSeed(BaseModel):
    """Scoring blueprint used by downstream candidate screening."""

    evaluation_dimensions: list[EvaluationDimension]
    screening_rules: ScreeningRules
    ambiguities_for_human_review: list[BilingualText]

    @model_validator(mode="after")
    def validate_dimensions(self) -> "RubricSeed":
        total_weight = sum(item.weight for item in self.evaluation_dimensions)
        if not 4 <= len(self.evaluation_dimensions) <= 6:
            raise ValueError("evaluation_dimensions must contain between 4 and 6 items")
        if round(total_weight, 6) != 1.0:
            raise ValueError("evaluation_dimensions weights must sum to 1.0")
        if not any(item.priority == "must_have" for item in self.evaluation_dimensions):
            raise ValueError("at least one evaluation dimension must be must_have")
        return self


class JDAnalysisPayload(BaseModel):
    """Top-level structured output returned by Gemini."""

    model_config = ConfigDict(extra="forbid")

    job_overview: JobOverview
    requirements: Requirements
    rubric_seed: RubricSeed


class JDAnalysisResponse(BaseModel):
    """API response for a completed JD analysis."""

    jd_id: str
    file_name: str
    status: Literal["completed"]
    created_at: str
    analysis: JDAnalysisPayload
```

- [ ] **Step 4: Export the schemas from the package**

```python
from src.schemas.auth import GoogleAuthRequest, TokenResponse
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse
from src.schemas.user import UserResponse

__all__ = [
    "GoogleAuthRequest",
    "JDAnalysisPayload",
    "JDAnalysisResponse",
    "TokenResponse",
    "UserResponse",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/schemas/test_jd_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/schemas/jd.py backend/src/schemas/__init__.py backend/tests/schemas/test_jd_schema.py
git commit -m "feat: add jd analysis schema contract"
```

### Task 3: Implement file storage support for uploaded JDs

**Files:**
- Create: `backend/src/services/file_storage.py`
- Modify: `backend/src/services/__init__.py`
- Test: `backend/tests/services/test_file_storage.py`

- [ ] **Step 1: Write the failing file storage tests**

```python
from pathlib import Path

from src.services.file_storage import StoredFile, store_upload_file


def test_store_upload_file_writes_bytes(tmp_path: Path) -> None:
    stored = store_upload_file(
        upload_dir=tmp_path,
        file_name="jd.pdf",
        file_bytes=b"pdf-content",
    )

    assert isinstance(stored, StoredFile)
    assert stored.file_name == "jd.pdf"
    assert Path(stored.storage_path).read_bytes() == b"pdf-content"


def test_store_upload_file_sanitizes_spaces(tmp_path: Path) -> None:
    stored = store_upload_file(
        upload_dir=tmp_path,
        file_name="Senior Backend JD.pdf",
        file_bytes=b"content",
    )

    assert " " not in Path(stored.storage_path).name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_file_storage.py -v`
Expected: FAIL with `ModuleNotFoundError` because the storage service does not exist yet.

- [ ] **Step 3: Implement the file storage helper**

```python
"""File storage helpers for uploaded JD documents."""

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass(frozen=True)
class StoredFile:
    """Metadata for a stored file."""

    file_name: str
    storage_path: str


def store_upload_file(upload_dir: Path, file_name: str, file_bytes: bytes) -> StoredFile:
    """Store uploaded bytes on disk and return metadata."""
    safe_name = file_name.replace(" ", "_")
    destination_dir = upload_dir
    destination_dir.mkdir(parents=True, exist_ok=True)

    destination_path = destination_dir / f"{uuid4()}_{safe_name}"
    destination_path.write_bytes(file_bytes)

    return StoredFile(file_name=file_name, storage_path=str(destination_path))
```

- [ ] **Step 4: Export the storage helper**

```python
from src.services.auth_service import AuthService
from src.services.file_storage import StoredFile, store_upload_file
from src.services.jwt_service import JWTService

__all__ = ["AuthService", "JWTService", "StoredFile", "store_upload_file"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/services/test_file_storage.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/file_storage.py backend/src/services/__init__.py backend/tests/services/test_file_storage.py
git commit -m "feat: add jd upload file storage"
```

### Task 4: Implement the LangChain Gemini extractor

**Files:**
- Create: `backend/src/services/jd_extractor.py`
- Test: `backend/tests/services/test_jd_service.py`

- [ ] **Step 1: Write the failing extractor contract test**

```python
from src.schemas.jd import JDAnalysisPayload
from src.services.jd_extractor import build_jd_extraction_prompt


def test_build_jd_extraction_prompt_mentions_bilingual_output() -> None:
    prompt = build_jd_extraction_prompt()

    assert "LangChain" not in prompt
    assert "bilingual" in prompt.lower()
    assert JDAnalysisPayload.__name__ in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_jd_service.py::test_build_jd_extraction_prompt_mentions_bilingual_output -v`
Expected: FAIL with `ModuleNotFoundError` because the extractor module does not exist yet.

- [ ] **Step 3: Implement the Gemini extractor**

```python
"""LangChain-based Gemini extractor for JD analysis."""

from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.jd import JDAnalysisPayload


def build_jd_extraction_prompt() -> str:
    """Return the structured extraction instructions for JD analysis."""
    return (
        "You are a hiring analyst. Read the uploaded job description and extract only job-relevant "
        "criteria for candidate screening. Return bilingual HR-facing text where appropriate, keep "
        "schema keys and enums normalized in English, separate required and preferred requirements, "
        "generate a rubric seed for CV screening, and list any uncertainty under "
        "ambiguities_for_human_review. Use the JDAnalysisPayload schema exactly."
    )


class GeminiJDExtractor:
    """Wrapper around LangChain Gemini structured output for JD analysis."""

    def __init__(self) -> None:
        self._llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            api_key=SecretStr(settings.gemini_api_key),
            temperature=0,
        )
        self._structured_llm = self._llm.with_structured_output(JDAnalysisPayload)

    async def extract(self, file_path: Path, mime_type: str) -> JDAnalysisPayload:
        """Extract a structured JD payload from an uploaded file."""
        file_part = {
            "type": "media",
            "mime_type": mime_type,
            "data": file_path.read_bytes(),
        }
        prompt = build_jd_extraction_prompt()
        return await self._structured_llm.ainvoke([prompt, file_part])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_jd_service.py::test_build_jd_extraction_prompt_mentions_bilingual_output -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/jd_extractor.py backend/tests/services/test_jd_service.py
git commit -m "feat: add gemini jd extractor"
```

### Task 5: Implement the JD analysis orchestration service

**Files:**
- Create: `backend/src/services/jd_service.py`
- Test: `backend/tests/services/test_jd_service.py`

- [ ] **Step 1: Write the failing service orchestration test**

```python
from datetime import datetime
from pathlib import Path

import pytest

from src.schemas.jd import JDAnalysisPayload
from src.services.jd_service import JDAnalysisService


class FakeExtractor:
    async def extract(self, file_path: Path, mime_type: str) -> JDAnalysisPayload:
        return JDAnalysisPayload.model_validate(
            {
                "job_overview": {
                    "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                    "department": {"vi": "Ky thuat", "en": "Engineering"},
                    "seniority_level": "senior",
                    "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                    "work_mode": "hybrid",
                    "role_summary": {"vi": "Tom tat", "en": "Summary"},
                    "company_benefits": [],
                },
                "requirements": {
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "tools_and_technologies": [],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": ["Backend Engineer"],
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
                            "name": {"vi": "Python", "en": "Python"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "must_have",
                            "weight": 0.4,
                            "evidence_signals": [{"vi": "Du an", "en": "Projects"}],
                        },
                        {
                            "name": {"vi": "API", "en": "API"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.2,
                            "evidence_signals": [{"vi": "REST", "en": "REST"}],
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
                            "name": {"vi": "Giao tiep", "en": "Communication"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "Phoi hop", "en": "Collaboration"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": ["3+ years experience"],
                        "scoring_principle": "Nice-to-have cannot replace must-have.",
                    },
                    "ambiguities_for_human_review": [],
                },
            }
        )


@pytest.mark.asyncio
async def test_service_returns_completed_response(tmp_path: Path) -> None:
    service = JDAnalysisService(extractor=FakeExtractor(), upload_dir=tmp_path)

    response = await service.analyze_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"file-content",
    )

    assert response.file_name == "jd.pdf"
    assert response.status == "completed"
    assert response.analysis.job_overview.seniority_level == "senior"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_jd_service.py::test_service_returns_completed_response -v`
Expected: FAIL with `ModuleNotFoundError` because the JD service does not exist yet.

- [ ] **Step 3: Implement the orchestration service**

```python
"""Orchestration service for JD upload and analysis."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse
from src.services.file_storage import store_upload_file
from src.services.jd_extractor import GeminiJDExtractor


class JDAnalysisService:
    """Handle storage and extraction for uploaded JD files."""

    def __init__(self, extractor: GeminiJDExtractor | None = None, upload_dir: Path | None = None) -> None:
        self._extractor = extractor or GeminiJDExtractor()
        self._upload_dir = upload_dir or Path("storage/jd_uploads")

    async def analyze_upload(
        self,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> JDAnalysisResponse:
        """Store the upload, extract a JD payload, and return the API response."""
        stored_file = store_upload_file(
            upload_dir=self._upload_dir,
            file_name=file_name,
            file_bytes=file_bytes,
        )
        analysis = await self._extractor.extract(Path(stored_file.storage_path), mime_type)
        created_at = datetime.now(UTC).isoformat()
        return JDAnalysisResponse(
            jd_id=str(uuid4()),
            file_name=file_name,
            status="completed",
            created_at=created_at,
            analysis=analysis,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_jd_service.py::test_service_returns_completed_response -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/jd_service.py backend/tests/services/test_jd_service.py
git commit -m "feat: add jd analysis service"
```

### Task 6: Add the upload API endpoint

**Files:**
- Create: `backend/src/api/v1/jd.py`
- Modify: `backend/src/api/v1/router.py`
- Test: `backend/tests/api/test_jd_api.py`

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from src.main import app


def test_jd_analyze_endpoint_accepts_pdf_upload() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"pdf-content", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "jd.pdf"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/api/test_jd_api.py::test_jd_analyze_endpoint_accepts_pdf_upload -v`
Expected: FAIL with `404 Not Found` because the route does not exist yet.

- [ ] **Step 3: Implement the JD API router**

```python
"""JD analysis API routes."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from src.config import settings
from src.schemas.jd import JDAnalysisResponse
from src.services.jd_service import JDAnalysisService

router = APIRouter(prefix="/jd", tags=["jd"])

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@router.post("/analyze", response_model=JDAnalysisResponse)
async def analyze_jd(file: UploadFile = File(...)) -> JDAnalysisResponse:
    """Upload a JD file and return structured analysis."""
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > settings.jd_max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds size limit")

    service = JDAnalysisService(upload_dir=settings.jd_upload_path)
    return await service.analyze_upload(
        file_name=file.filename or "uploaded.jd",
        mime_type=file.content_type,
        file_bytes=file_bytes,
    )
```

- [ ] **Step 4: Register the new router**

```python
"""API v1 router."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.jd import router as jd_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(jd_router)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/api/test_jd_api.py::test_jd_analyze_endpoint_accepts_pdf_upload -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/v1/jd.py backend/src/api/v1/router.py backend/tests/api/test_jd_api.py
git commit -m "feat: add jd analysis api"
```

### Task 7: Add persistence and end-to-end test coverage

**Files:**
- Modify: `backend/src/services/jd_service.py`
- Create: `backend/tests/conftest.py`
- Modify: `backend/tests/services/test_jd_service.py`
- Modify: `backend/tests/api/test_jd_api.py`

- [ ] **Step 1: Write the failing persistence test**

```python
import pytest
from sqlalchemy import select

from src.models.jd import JDAnalysis, JDDocument
from src.services.jd_service import JDAnalysisService


@pytest.mark.asyncio
async def test_service_persists_document_and_analysis(db_session, tmp_path) -> None:
    service = JDAnalysisService(extractor=FakeExtractor(), upload_dir=tmp_path, db_session=db_session)

    response = await service.analyze_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"file-content",
    )

    stored_document = await db_session.scalar(select(JDDocument).where(JDDocument.id == response.jd_id))
    stored_analysis = await db_session.scalar(
        select(JDAnalysis).where(JDAnalysis.jd_document_id == response.jd_id)
    )

    assert stored_document is not None
    assert stored_analysis is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_jd_service.py::test_service_persists_document_and_analysis -v`
Expected: FAIL because the service does not persist the upload yet.

- [ ] **Step 3: Add DB-backed persistence to the service**

```python
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jd import JDAnalysis, JDDocument


class JDAnalysisService:
    def __init__(
        self,
        extractor: GeminiJDExtractor | None = None,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        self._extractor = extractor or GeminiJDExtractor()
        self._upload_dir = upload_dir or settings.jd_upload_path
        self._db_session = db_session

    async def analyze_upload(self, file_name: str, mime_type: str, file_bytes: bytes) -> JDAnalysisResponse:
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        document = JDDocument(
            file_name=file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        if self._db_session is not None:
            self._db_session.add(document)
            await self._db_session.flush()

        analysis = await self._extractor.extract(Path(stored_file.storage_path), mime_type)

        if self._db_session is not None:
            self._db_session.add(
                JDAnalysis(
                    jd_document_id=document.id,
                    model_name=settings.gemini_model,
                    analysis_payload=analysis.model_dump(mode="json"),
                )
            )
            document.status = "completed"
            await self._db_session.commit()
            await self._db_session.refresh(document)
            jd_id = document.id
            created_at = document.created_at.isoformat()
        else:
            jd_id = str(uuid4())
            created_at = datetime.now(UTC).isoformat()

        return JDAnalysisResponse(
            jd_id=jd_id,
            file_name=file_name,
            status="completed",
            created_at=created_at,
            analysis=analysis,
        )
```

- [ ] **Step 4: Add async test fixtures**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base


@pytest.fixture
async def db_session(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()
```

- [ ] **Step 5: Run focused tests to verify they pass**

Run: `pytest backend/tests/services/test_jd_service.py backend/tests/api/test_jd_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/services/jd_service.py backend/tests/conftest.py backend/tests/services/test_jd_service.py backend/tests/api/test_jd_api.py
git commit -m "feat: persist jd analyses"
```

### Task 8: Verify the full slice and update developer docs

**Files:**
- Modify: `backend/README.md`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/schemas/test_jd_schema.py`
- Test: `backend/tests/services/test_file_storage.py`
- Test: `backend/tests/services/test_jd_service.py`
- Test: `backend/tests/api/test_jd_api.py`

- [ ] **Step 1: Add missing test dependency if needed**

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.8.0",
    "basedpyright>=1.0.0",
    "aiosqlite>=0.21.0",
]
```

- [ ] **Step 2: Document the new JD analysis flow**

```md
## JD Analysis

The backend exposes `POST /api/v1/jd/analyze` for upload-only JD analysis.

Supported files:

- PDF
- DOCX

Required environment variables:

- `GEMINI_API_KEY`
- `GEMINI_MODEL` (optional override)
- `JD_UPLOAD_DIR` (optional override)
```

- [ ] **Step 3: Run the targeted test suite**

Run: `pytest backend/tests/schemas/test_jd_schema.py backend/tests/services/test_file_storage.py backend/tests/services/test_jd_service.py backend/tests/api/test_jd_api.py -v`
Expected: PASS

- [ ] **Step 4: Run lint and type checks**

Run: `ruff check backend/src backend/tests && basedpyright backend/src backend/tests`
Expected: PASS with no warnings

- [ ] **Step 5: Commit**

```bash
git add backend/README.md backend/pyproject.toml backend/tests/schemas/test_jd_schema.py backend/tests/services/test_file_storage.py backend/tests/services/test_jd_service.py backend/tests/api/test_jd_api.py
git commit -m "docs: add jd analysis setup notes"
```

## Self-Review

- Spec coverage: covered upload-only intake, file storage, LangChain + Gemini extraction, bilingual output, persistence, validation, and testing.
- Placeholder scan: no `TODO`, `TBD`, or unresolved references remain in the plan.
- Type consistency: the plan uses `JDAnalysisPayload`, `JDAnalysisResponse`, `JDDocument`, and `JDAnalysis` consistently across tasks.
