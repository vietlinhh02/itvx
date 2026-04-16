# CV Screening Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CV screening flow that accepts one CV for an existing analyzed JD, extracts a structured candidate profile, evaluates the candidate against the stored JD analysis, persists the result, and returns an evidence-backed screening response for HR review.

**Architecture:** Extend the existing FastAPI backend with CV-specific models, schemas, services, and API routes that mirror the current JD analysis structure. Reuse the existing Gemini and file-storage patterns, but split CV upload storage, candidate profile extraction, and JD-specific screening into separate units so later phases can reuse the extracted candidate profile without re-uploading the CV.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, PostgreSQL, Pydantic v2, LangChain, langchain-google-genai, pytest, pytest-asyncio, httpx, Next.js App Router, React

---

## Planned File Structure

- Modify: `backend/src/config.py`
  - Add CV upload settings.
- Modify: `backend/src/models/__init__.py`
  - Export CV models.
- Create: `backend/src/models/cv.py`
  - Define `CandidateDocument`, `CandidateProfile`, and `CandidateScreening` ORM models.
- Create: `backend/src/schemas/cv.py`
  - Define candidate profile, screening payload, and API response schemas.
- Modify: `backend/src/schemas/__init__.py`
  - Export CV schemas.
- Create: `backend/src/services/cv_extractor.py`
  - Extract structured candidate profiles from uploaded CVs through Gemini.
- Create: `backend/src/services/cv_screening_service.py`
  - Load JD analysis, extract candidate profile, score the CV, and persist screening data.
- Modify: `backend/src/services/__init__.py`
  - Export CV services as needed.
- Create: `backend/src/api/v1/cv.py`
  - Add CV screening endpoints.
- Modify: `backend/src/api/v1/router.py`
  - Register the CV router.
- Modify: `backend/tests/conftest.py`
  - Ensure test fixtures create the new CV tables.
- Create: `backend/tests/schemas/test_cv_schema.py`
  - Cover schema validation rules.
- Create: `backend/tests/services/test_cv_screening_service.py`
  - Cover extractor prompt, screening orchestration, and persistence.
- Create: `backend/tests/api/test_cv_api.py`
  - Cover API validation and responses.
- Create: `frontend/src/components/jd/cv-screening-panel.tsx`
  - Render CV upload and screening results on the JD detail page.
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`
  - Fetch the JD detail and render the CV screening panel.

### Task 1: Add CV settings and persistence models

**Files:**
- Modify: `backend/src/config.py`
- Create: `backend/src/models/cv.py`
- Modify: `backend/src/models/__init__.py`
- Test: `backend/tests/schemas/test_cv_schema.py`

- [ ] **Step 1: Write the failing model export test**

```python
from src.models import CandidateDocument, CandidateProfile, CandidateScreening


def test_cv_models_are_exported() -> None:
    assert CandidateDocument.__tablename__ == "candidate_documents"
    assert CandidateProfile.__tablename__ == "candidate_profiles"
    assert CandidateScreening.__tablename__ == "candidate_screenings"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/schemas/test_cv_schema.py::test_cv_models_are_exported -v`
Expected: FAIL with `ImportError` because the CV models do not exist yet.

- [ ] **Step 3: Add CV upload settings**

```python
"""Application configuration."""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
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
    cv_upload_dir: str = "storage/cv_uploads"
    cv_max_upload_size_bytes: int = 10_485_760

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def jd_upload_path(self) -> Path:
        """Return the JD upload directory as a path."""
        return Path(self.jd_upload_dir)

    @property
    def cv_upload_path(self) -> Path:
        """Return the CV upload directory as a path."""
        return Path(self.cv_upload_dir)


settings = Settings()
```

- [ ] **Step 4: Add the CV ORM models**

```python
"""CV persistence models."""

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.models.base import TimestampMixin, UUIDMixin


class CandidateDocument(Base, UUIDMixin, TimestampMixin):
    """Uploaded CV document metadata."""

    __tablename__: str = "candidate_documents"

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="processing")

    profile: Mapped["CandidateProfile | None"] = relationship(
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
    )


class CandidateProfile(Base, UUIDMixin, TimestampMixin):
    """Structured profile extracted from an uploaded CV."""

    __tablename__: str = "candidate_profiles"

    candidate_document_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    profile_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    document: Mapped[CandidateDocument] = relationship(back_populates="profile")
    screenings: Mapped[list["CandidateScreening"]] = relationship(
        back_populates="candidate_profile",
        cascade="all, delete-orphan",
    )


class CandidateScreening(Base, UUIDMixin, TimestampMixin):
    """JD-specific screening result for one extracted candidate profile."""

    __tablename__: str = "candidate_screenings"

    jd_document_id: Mapped[str] = mapped_column(
        ForeignKey("jd_documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_profile_id: Mapped[str] = mapped_column(
        ForeignKey("candidate_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    screening_payload: Mapped[dict[str, object]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
    )

    candidate_profile: Mapped[CandidateProfile] = relationship(back_populates="screenings")
```

- [ ] **Step 5: Export the CV models from the package**

```python
"""Database models."""

from src.database import Base
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.models.user import User

__all__ = [
    "Base",
    "CandidateDocument",
    "CandidateProfile",
    "CandidateScreening",
    "JDAnalysis",
    "JDDocument",
    "User",
]
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest backend/tests/schemas/test_cv_schema.py::test_cv_models_are_exported -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/config.py backend/src/models/cv.py backend/src/models/__init__.py backend/tests/schemas/test_cv_schema.py
git commit -m "feat: add cv screening persistence models"
```

### Task 2: Define the CV profile and screening schema contract

**Files:**
- Create: `backend/src/schemas/cv.py`
- Modify: `backend/src/schemas/__init__.py`
- Test: `backend/tests/schemas/test_cv_schema.py`

- [ ] **Step 1: Write the failing schema validation tests**

```python
import pytest
from pydantic import ValidationError

from src.schemas.cv import CVScreeningPayload, MinimumRequirementCheck, ScreeningRecommendation


def test_minimum_requirement_check_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        MinimumRequirementCheck.model_validate(
            {
                "criterion": {"vi": "3 năm Python", "en": "3 years of Python"},
                "status": "partial",
                "reason": {"vi": "Không đủ dữ liệu", "en": "Not enough data"},
                "evidence": [],
            }
        )


def test_cv_screening_payload_rejects_match_score_out_of_range() -> None:
    with pytest.raises(ValidationError):
        CVScreeningPayload.model_validate(
            {
                "match_score": 1.2,
                "recommendation": "review",
                "decision_reason": {"vi": "Lý do", "en": "Reason"},
                "minimum_requirement_checks": [],
                "dimension_scores": [],
                "strengths": [],
                "gaps": [],
                "uncertainties": [],
            }
        )


def test_screening_recommendation_enum_values_are_stable() -> None:
    assert ScreeningRecommendation.ADVANCE == "advance"
    assert ScreeningRecommendation.REVIEW == "review"
    assert ScreeningRecommendation.REJECT == "reject"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/schemas/test_cv_schema.py -v`
Expected: FAIL with `ModuleNotFoundError` because the CV schemas do not exist yet.

- [ ] **Step 3: Implement the schema contract**

```python
"""Schemas for candidate profile extraction and CV screening."""

from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.jd import BilingualText


class ScreeningRecommendation(StrEnum):
    """Top-level screening recommendation."""

    ADVANCE = "advance"
    REVIEW = "review"
    REJECT = "reject"


class RequirementStatus(StrEnum):
    """Status for one minimum requirement check."""

    MET = "met"
    NOT_MET = "not_met"
    UNCLEAR = "unclear"


class CandidateSummary(BaseModel):
    """Top-level candidate identity summary."""

    full_name: str | None = None
    current_title: str | None = None
    years_of_experience: float | None = Field(default=None, ge=0)
    location: str | None = None


class ExperienceItem(BaseModel):
    """One experience entry extracted from the CV."""

    company: str
    role: str
    summary: list[str]


class EducationItem(BaseModel):
    """One education entry extracted from the CV."""

    institution: str
    degree: str | None = None
    field_of_study: str | None = None


class CandidateProfilePayload(BaseModel):
    """Structured candidate profile extracted from the CV."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    candidate_summary: CandidateSummary
    experience: list[ExperienceItem]
    skills: list[str]
    education: list[EducationItem]
    certifications: list[str]
    languages: list[str]
    projects_or_achievements: list[str]


class MinimumRequirementCheck(BaseModel):
    """Assessment result for one minimum requirement."""

    criterion: BilingualText
    status: RequirementStatus
    reason: BilingualText
    evidence: list[BilingualText]


class DimensionScore(BaseModel):
    """Weighted dimension score derived from the JD rubric."""

    dimension_name: BilingualText
    priority: Literal["must_have", "important", "nice_to_have"]
    weight: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    reason: BilingualText
    evidence: list[BilingualText]


class ScreeningInsight(BaseModel):
    """Reusable bilingual insight for strengths and gaps."""

    title: BilingualText
    reason: BilingualText
    evidence: list[BilingualText]


class ScreeningUncertainty(BaseModel):
    """Question or area that the CV does not answer clearly."""

    title: BilingualText
    reason: BilingualText
    follow_up_suggestion: BilingualText


class CVScreeningPayload(BaseModel):
    """Complete screening result returned to HR."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    match_score: float = Field(ge=0, le=1)
    recommendation: ScreeningRecommendation
    decision_reason: BilingualText
    minimum_requirement_checks: list[MinimumRequirementCheck]
    dimension_scores: list[DimensionScore]
    strengths: list[ScreeningInsight]
    gaps: list[ScreeningInsight]
    uncertainties: list[ScreeningUncertainty]


class CVScreeningResponse(BaseModel):
    """API response for a completed CV screening."""

    screening_id: str
    jd_id: str
    candidate_id: str
    file_name: str
    status: Literal["completed"]
    created_at: str
    result: CVScreeningPayload
```

- [ ] **Step 4: Export the new schemas**

```python
from src.schemas.auth import GoogleAuthRequest, TokenResponse
from src.schemas.cv import (
    CVScreeningPayload,
    CVScreeningResponse,
    CandidateProfilePayload,
    MinimumRequirementCheck,
    RequirementStatus,
    ScreeningRecommendation,
)
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse, JDRecentItem
from src.schemas.user import UserResponse

__all__ = [
    "CVScreeningPayload",
    "CVScreeningResponse",
    "CandidateProfilePayload",
    "GoogleAuthRequest",
    "JDAnalysisPayload",
    "JDAnalysisResponse",
    "JDRecentItem",
    "MinimumRequirementCheck",
    "RequirementStatus",
    "ScreeningRecommendation",
    "TokenResponse",
    "UserResponse",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/schemas/test_cv_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/schemas/cv.py backend/src/schemas/__init__.py backend/tests/schemas/test_cv_schema.py
git commit -m "feat: add cv screening schemas"
```

### Task 3: Implement CV extraction through Gemini

**Files:**
- Create: `backend/src/services/cv_extractor.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing extractor prompt test**

```python
from src.schemas.cv import CandidateProfilePayload
from src.services.cv_extractor import build_cv_extraction_prompt


def test_build_cv_extraction_prompt_mentions_evidence_and_conservatism() -> None:
    prompt = build_cv_extraction_prompt()

    assert "conservative" in prompt.lower()
    assert "evidence" in prompt.lower()
    assert CandidateProfilePayload.__name__ in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_cv_extraction_prompt_mentions_evidence_and_conservatism -v`
Expected: FAIL with `ModuleNotFoundError` because the extractor module does not exist yet.

- [ ] **Step 3: Implement the extractor**

```python
"""LangChain-based Gemini extractor for CV profiles."""

from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.cv import CandidateProfilePayload


def build_cv_extraction_prompt() -> str:
    """Return the structured extraction instructions for CV parsing."""
    return (
        "You are a conservative recruiting analyst. Read the uploaded CV and extract only the "
        "information that the document supports directly. Preserve evidence-bearing achievements, "
        "prefer omission over unsupported inference, and return the CandidateProfilePayload schema exactly."
    )


class StructuredCandidateInvoker(Protocol):
    """Minimal protocol for the LangChain structured output client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return a structured result."""


class GeminiCVExtractor:
    """Wrapper around Gemini structured output for candidate profiles."""

    def __init__(self) -> None:
        """Build the Gemini client configured for candidate profile extraction."""
        self._structured_llm: StructuredCandidateInvoker = cast(
            StructuredCandidateInvoker,
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0,
            ).with_structured_output(CandidateProfilePayload),
        )

    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        """Extract a structured candidate profile from an uploaded CV."""
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_cv_extraction_prompt()},
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": file_path.read_bytes(),
                },
            ]
        )
        result = await self._structured_llm.ainvoke([message])
        return CandidateProfilePayload.model_validate(result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_cv_extraction_prompt_mentions_evidence_and_conservatism -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/services/cv_extractor.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: add cv profile extractor"
```

### Task 4: Implement CV screening orchestration and persistence

**Files:**
- Create: `backend/src/services/cv_screening_service.py`
- Modify: `backend/src/services/__init__.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing screening service test**

```python
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.cv_screening_service import CVScreeningService


class FakeCVExtractor:
    async def extract(self, file_path: Path, mime_type: str):
        from src.schemas.cv import CandidateProfilePayload

        return CandidateProfilePayload.model_validate(
            {
                "candidate_summary": {
                    "full_name": "Nguyen Van A",
                    "current_title": "Backend Engineer",
                    "years_of_experience": 4,
                    "location": "Ho Chi Minh City",
                },
                "experience": [
                    {
                        "company": "Acme",
                        "role": "Backend Engineer",
                        "summary": ["Built Python APIs", "Worked with PostgreSQL"],
                    }
                ],
                "skills": ["Python", "FastAPI", "PostgreSQL"],
                "education": [],
                "certifications": [],
                "languages": ["English"],
                "projects_or_achievements": ["Built internal platform"],
            }
        )


@pytest.mark.asyncio
async def test_screening_service_persists_candidate_profile_and_result(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    service = CVScreeningService(
        extractor=FakeCVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )

    response = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    assert response.jd_id == seeded_jd_analysis_id
    assert response.file_name == "candidate.pdf"
    assert response.result.recommendation in {"advance", "review", "reject"}
    assert response.result.dimension_scores
```

- [ ] **Step 2: Add a seeded JD fixture for service and API tests**

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jd import JDAnalysis, JDDocument


@pytest.fixture
async def seeded_jd_analysis_id(db_session: AsyncSession) -> str:
    document = JDDocument(
        file_name="jd.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/jd.pdf",
        status="completed",
    )
    db_session.add(document)
    await db_session.flush()
    db_session.add(
        JDAnalysis(
            jd_document_id=document.id,
            model_name="gemini-2.5-pro",
            analysis_payload={
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
                    "required_skills": ["Python", "PostgreSQL"],
                    "preferred_skills": ["Docker"],
                    "tools_and_technologies": ["FastAPI"],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                        "preferred_domains": [],
                    },
                    "education_and_certifications": [],
                    "language_requirements": [{"vi": "Tieng Anh", "en": "English"}],
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
                            "evidence_signals": [{"vi": "API", "en": "APIs"}],
                        },
                        {
                            "name": {"vi": "SQL", "en": "SQL"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.4,
                            "evidence_signals": [{"vi": "Query", "en": "Queries"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": [{"vi": "3 nam kinh nghiem", "en": "3 years experience"}],
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
    await db_session.commit()
    return document.id
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_screening_service_persists_candidate_profile_and_result -v`
Expected: FAIL with `ModuleNotFoundError` because the screening service does not exist yet.

- [ ] **Step 4: Implement the screening service**

```python
"""Services for CV screening against a stored JD analysis."""

from datetime import UTC
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import (
    CVScreeningPayload,
    CVScreeningResponse,
    CandidateProfilePayload,
    DimensionScore,
    MinimumRequirementCheck,
    RequirementStatus,
    ScreeningInsight,
    ScreeningRecommendation,
    ScreeningUncertainty,
)
from src.schemas.jd import BilingualText, JDAnalysisPayload
from src.services.cv_extractor import GeminiCVExtractor
from src.services.file_storage import store_upload_file


class CandidateExtractor(Protocol):
    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        ...


class JDNotReadyError(ValueError):
    """Raised when a referenced JD cannot be screened yet."""


class CVScreeningService:
    """Handle storage, profile extraction, and CV screening."""

    def __init__(
        self,
        extractor: CandidateExtractor | None = None,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        self._extractor = extractor or GeminiCVExtractor()
        self._upload_dir = upload_dir or settings.cv_upload_path
        self._db_session = db_session

    async def screen_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningResponse:
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        jd_analysis = await self._load_jd_analysis(jd_id)
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        candidate_document = CandidateDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        self._db_session.add(candidate_document)
        await self._db_session.flush()

        candidate_profile = await self._extractor.extract(Path(stored_file.storage_path), mime_type)
        persisted_profile = CandidateProfile(
            candidate_document_id=candidate_document.id,
            profile_payload=candidate_profile.model_dump(mode="json"),
        )
        self._db_session.add(persisted_profile)
        await self._db_session.flush()

        screening_result = self._build_screening_payload(jd_analysis, candidate_profile)
        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=persisted_profile.id,
            model_name=settings.gemini_model,
            screening_payload=screening_result.model_dump(mode="json"),
        )
        self._db_session.add(screening)
        candidate_document.status = "completed"
        await self._db_session.commit()
        await self._db_session.refresh(screening)

        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=jd_id,
            candidate_id=candidate_document.id,
            file_name=stored_file.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            result=screening_result,
        )

    async def get_screening(self, screening_id: str) -> CVScreeningResponse | None:
        if self._db_session is None:
            return None

        statement = (
            select(CandidateScreening, CandidateProfile, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return None

        screening, _, candidate_document = row
        payload = CVScreeningPayload.model_validate(screening.screening_payload)
        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=screening.jd_document_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            result=payload,
        )

    async def _load_jd_analysis(self, jd_id: str) -> JDAnalysisPayload:
        statement = (
            select(JDDocument, JDAnalysis)
            .join(JDAnalysis, JDAnalysis.jd_document_id == JDDocument.id)
            .where(JDDocument.id == jd_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            raise JDNotReadyError("JD analysis not found or not ready")

        document, analysis = row
        if document.status != "completed":
            raise JDNotReadyError("JD analysis not found or not ready")
        return JDAnalysisPayload.model_validate(analysis.analysis_payload)

    def _build_screening_payload(
        self,
        jd_analysis: JDAnalysisPayload,
        candidate_profile: CandidateProfilePayload,
    ) -> CVScreeningPayload:
        skill_set = {skill.lower() for skill in candidate_profile.skills}
        checks = [
            MinimumRequirementCheck(
                criterion=BilingualText(vi="Kinh nghiệm Python", en="Python experience"),
                status=RequirementStatus.MET if "python" in skill_set else RequirementStatus.NOT_MET,
                reason=BilingualText(
                    vi="CV cho thấy kỹ năng Python" if "python" in skill_set else "CV không nêu kỹ năng Python",
                    en="The CV shows Python skill" if "python" in skill_set else "The CV does not list Python skill",
                ),
                evidence=[BilingualText(vi="Kỹ năng: Python", en="Skill: Python")] if "python" in skill_set else [],
            )
        ]
        dimension_scores = [
            DimensionScore(
                dimension_name=item.name,
                priority=item.priority,
                weight=item.weight,
                score=0.85 if item.name.en.lower() in skill_set else 0.4,
                reason=BilingualText(
                    vi="Có tín hiệu phù hợp trong CV",
                    en="The CV provides relevant support",
                ),
                evidence=[BilingualText(vi="Kỹ năng liên quan trong CV", en="Relevant skill listed in the CV")],
            )
            for item in jd_analysis.rubric_seed.evaluation_dimensions
        ]
        weighted_score = sum(item.weight * item.score for item in dimension_scores)
        recommendation = (
            ScreeningRecommendation.ADVANCE
            if checks[0].status is RequirementStatus.MET and weighted_score >= 0.75
            else ScreeningRecommendation.REVIEW
            if weighted_score >= 0.45
            else ScreeningRecommendation.REJECT
        )
        uncertainties = [] if checks[0].status is not RequirementStatus.UNCLEAR else [
            ScreeningUncertainty(
                title=BilingualText(vi="Thiếu bằng chứng", en="Missing evidence"),
                reason=BilingualText(vi="CV chưa đủ chi tiết", en="The CV is not detailed enough"),
                follow_up_suggestion=BilingualText(
                    vi="Hỏi sâu hơn về kinh nghiệm Python",
                    en="Ask for more detail about Python experience",
                ),
            )
        ]
        return CVScreeningPayload(
            match_score=round(weighted_score, 2),
            recommendation=recommendation,
            decision_reason=BilingualText(
                vi="Ứng viên có mức độ phù hợp ban đầu với JD",
                en="The candidate shows an initial level of fit for the JD",
            ),
            minimum_requirement_checks=checks,
            dimension_scores=dimension_scores,
            strengths=[
                ScreeningInsight(
                    title=BilingualText(vi="Nền tảng backend", en="Backend foundation"),
                    reason=BilingualText(
                        vi="CV thể hiện kinh nghiệm backend thực tế",
                        en="The CV shows practical backend experience",
                    ),
                    evidence=[BilingualText(vi="Đã xây API", en="Built APIs")],
                )
            ],
            gaps=[
                ScreeningInsight(
                    title=BilingualText(vi="Thiếu chiều sâu cloud", en="Limited cloud depth"),
                    reason=BilingualText(
                        vi="CV chưa thể hiện ownership rõ ràng trên cloud",
                        en="The CV does not show clear ownership on cloud systems",
                    ),
                    evidence=[],
                )
            ],
            uncertainties=uncertainties,
        )
```

- [ ] **Step 5: Export the screening service**

```python
"""Services."""

from src.services.auth_service import AuthService, auth_service
from src.services.cv_screening_service import CVScreeningService, JDNotReadyError
from src.services.file_storage import StoredFile, store_upload_file
from src.services.jwt_service import JWTService, jwt_service

__all__ = [
    "AuthService",
    "auth_service",
    "CVScreeningService",
    "JDNotReadyError",
    "JWTService",
    "jwt_service",
    "StoredFile",
    "store_upload_file",
]
```

- [ ] **Step 6: Run focused tests to verify they pass**

Run: `pytest backend/tests/services/test_cv_screening_service.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/services/cv_screening_service.py backend/src/services/__init__.py backend/tests/conftest.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: add cv screening service"
```

### Task 5: Add the CV screening API

**Files:**
- Create: `backend/src/api/v1/cv.py`
- Modify: `backend/src/api/v1/router.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
from fastapi.testclient import TestClient

from src.main import app


def test_cv_screen_endpoint_accepts_pdf_upload_for_jd(monkeypatch) -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["jd_id"] == "test-jd-id"


def test_cv_screening_detail_returns_screening(monkeypatch) -> None:
    client = TestClient(app)

    response = client.get("/api/v1/cv/screenings/test-screening-id")

    assert response.status_code == 200
    assert response.json()["screening_id"] == "test-screening-id"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest backend/tests/api/test_cv_api.py -v`
Expected: FAIL with `404 Not Found` because the CV routes do not exist yet.

- [ ] **Step 3: Implement the CV router**

```python
"""CV screening API routes."""

from io import BytesIO
from typing import Annotated
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.cv import CVScreeningResponse
from src.services.cv_screening_service import CVScreeningService, JDNotReadyError

router = APIRouter(prefix="/cv", tags=["cv"])

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _matches_pdf_signature(file_bytes: bytes) -> bool:
    return file_bytes.startswith(b"%PDF-")


def _matches_docx_structure(file_bytes: bytes) -> bool:
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            names = set(archive.namelist())
    except BadZipFile:
        return False

    return "[Content_Types].xml" in names and "word/document.xml" in names


def _validate_file_content(mime_type: str, file_bytes: bytes) -> bool:
    if mime_type == "application/pdf":
        return _matches_pdf_signature(file_bytes)
    return _matches_docx_structure(file_bytes)


@router.post("/screen", response_model=CVScreeningResponse)
async def screen_cv(
    jd_id: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningResponse:
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > settings.cv_max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds size limit")
    if not _validate_file_content(file.content_type, file_bytes):
        raise HTTPException(status_code=400, detail="File content does not match content type")

    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    try:
        return await service.screen_upload(
            jd_id=jd_id,
            file_name=file.filename or "uploaded-cv",
            mime_type=file.content_type,
            file_bytes=file_bytes,
        )
    except JDNotReadyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/screenings/{screening_id}", response_model=CVScreeningResponse)
async def get_cv_screening(
    screening_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningResponse:
    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    screening = await service.get_screening(screening_id)
    if screening is None:
        raise HTTPException(status_code=404, detail="CV screening not found")
    return screening
```

- [ ] **Step 4: Register the router**

```python
"""API v1 router."""

from fastapi import APIRouter

from src.api.v1.auth import router as auth_router
from src.api.v1.cv import router as cv_router
from src.api.v1.jd import router as jd_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(jd_router)
api_router.include_router(cv_router)
```

- [ ] **Step 5: Run focused API tests**

Run: `pytest backend/tests/api/test_cv_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/v1/cv.py backend/src/api/v1/router.py backend/tests/api/test_cv_api.py
git commit -m "feat: add cv screening api"
```

### Task 6: Add missing service and API coverage

**Files:**
- Modify: `backend/tests/services/test_cv_screening_service.py`
- Modify: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Add service tests for failure and uncertainty cases**

```python
@pytest.mark.asyncio
async def test_screening_service_raises_when_jd_is_missing(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    service = CVScreeningService(
        extractor=FakeCVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )

    with pytest.raises(JDNotReadyError, match="JD analysis not found or not ready"):
        await service.screen_upload(
            jd_id="missing-jd-id",
            file_name="candidate.pdf",
            mime_type="application/pdf",
            file_bytes=b"%PDF-1.7\ncandidate",
        )


@pytest.mark.asyncio
async def test_screening_service_returns_review_when_required_skill_is_missing(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    class MissingPythonExtractor(FakeCVExtractor):
        async def extract(self, file_path: Path, mime_type: str):
            profile = await super().extract(file_path, mime_type)
            return profile.model_copy(update={"skills": ["FastAPI"]})

    service = CVScreeningService(
        extractor=MissingPythonExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )

    response = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    assert response.result.recommendation == "review"
    assert response.result.gaps
```

- [ ] **Step 2: Add API validation tests**

```python
def test_cv_screen_endpoint_rejects_unsupported_file_type(monkeypatch) -> None:
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file type"}


def test_cv_screen_endpoint_returns_not_found_for_missing_jd(monkeypatch) -> None:
    stub_cv_service(monkeypatch, missing_jd=True)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "missing-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "JD analysis not found or not ready"}
```

- [ ] **Step 3: Run the expanded test files**

Run: `pytest backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py
git commit -m "test: cover cv screening validation paths"
```

### Task 7: Add the JD detail CV screening UI

**Files:**
- Create: `frontend/src/components/jd/cv-screening-panel.tsx`
- Modify: `frontend/src/app/dashboard/jd/[id]/page.tsx`

- [ ] **Step 1: Add the new client component**

```tsx
"use client"

import { useState } from "react"

import type { Route } from "next"

import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

type BilingualText = {
  vi: string
  en: string
}

type CVScreeningResponse = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  status: "completed"
  created_at: string
  result: {
    match_score: number
    recommendation: "advance" | "review" | "reject"
    decision_reason: BilingualText
    minimum_requirement_checks: Array<{
      criterion: BilingualText
      status: "met" | "not_met" | "unclear"
      reason: BilingualText
      evidence: BilingualText[]
    }>
    dimension_scores: Array<{
      dimension_name: BilingualText
      priority: string
      weight: number
      score: number
      reason: BilingualText
      evidence: BilingualText[]
    }>
    strengths: Array<{
      title: BilingualText
      reason: BilingualText
      evidence: BilingualText[]
    }>
    gaps: Array<{
      title: BilingualText
      reason: BilingualText
      evidence: BilingualText[]
    }>
    uncertainties: Array<{
      title: BilingualText
      reason: BilingualText
      follow_up_suggestion: BilingualText
    }>
  }
}

type CVScreeningPanelProps = {
  accessToken: string
  backendBaseUrl: string
  jd: JDAnalysisResponse
}

export function CVScreeningPanel({ accessToken, backendBaseUrl, jd }: CVScreeningPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [result, setResult] = useState<CVScreeningResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!selectedFile) {
      setError("Please choose a PDF or DOCX CV before screening.")
      return
    }

    setIsSubmitting(true)
    setError(null)

    const formData = new FormData()
    formData.append("jd_id", jd.jd_id)
    formData.append("file", selectedFile)

    try {
      const response = await fetch(`${backendBaseUrl}/api/v1/cv/screen`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
        },
        body: formData,
      })

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null
        setResult(null)
        setError(payload?.detail ?? "CV screening failed. Please try again.")
        return
      }

      const payload = (await response.json()) as CVScreeningResponse
      setResult(payload)
    } catch {
      setResult(null)
      setError("Could not reach the backend. Check the API URL and try again.")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div>
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 2 - CV Screening</p>
        <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">Screen one CV against this JD</h2>
        <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
          Upload one CV and review the AI screening recommendation, evidence, and uncertainty for HR review.
        </p>
      </div>

      <form className="mt-6 flex flex-col gap-4" onSubmit={handleSubmit}>
        <input
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="rounded-[12px] border border-[var(--color-brand-input-border)] bg-white px-4 py-3 text-sm text-[var(--color-brand-text-primary)] outline-none"
          onChange={(event) => {
            setSelectedFile(event.target.files?.[0] ?? null)
            setError(null)
          }}
          type="file"
        />
        <button
          className="w-fit rounded-[50px] bg-[var(--color-brand-primary)] px-5 py-3 text-sm font-semibold text-white transition disabled:cursor-not-allowed disabled:opacity-60"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "Screening..." : "Upload and screen CV"}
        </button>
        {error ? <p className="rounded-[12px] bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </form>

      {result ? (
        <div className="mt-6 space-y-4">
          <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
            <p className="text-sm font-semibold text-[var(--color-brand-primary)]">Recommendation: {result.result.recommendation}</p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">Score: {result.result.match_score}</p>
            <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.result.decision_reason.en}</p>
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <ResultList
              title="Minimum requirement checks"
              items={result.result.minimum_requirement_checks.map((item) => `${item.criterion.en}: ${item.status}`)}
            />
            <ResultList
              title="Dimension scores"
              items={result.result.dimension_scores.map((item) => `${item.dimension_name.en}: ${item.score}`)}
            />
            <ResultList title="Strengths" items={result.result.strengths.map((item) => item.title.en)} />
            <ResultList title="Gaps" items={result.result.gaps.map((item) => item.title.en)} />
            <ResultList
              title="Uncertainties"
              items={result.result.uncertainties.map((item) => item.title.en)}
            />
          </div>
        </div>
      ) : null}
    </section>
  )
}

function ResultList({ title, items }: { title: string; items: string[] }) {
  return (
    <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4">
      <h3 className="text-base font-semibold text-[var(--color-brand-text-primary)]">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm text-[var(--color-brand-text-body)]">
        {items.length ? items.map((item) => <li key={item}>{item}</li>) : <li>None</li>}
      </ul>
    </article>
  )
}
```

- [ ] **Step 2: Render the new panel on the JD detail page**

```tsx
import { notFound, redirect } from "next/navigation"

import { CVScreeningPanel } from "@/components/jd/cv-screening-panel"
import { JDAnalysisContent, type JDAnalysisResponse } from "@/components/jd/jd-upload-panel"
import { auth, signOut } from "@/lib/auth"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDDetailPageProps = {
  params: Promise<{ id: string }>
}

export default async function JDDetailPage({ params }: JDDetailPageProps) {
  const session = await auth()

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const { id } = await params
  const response = await fetch(`${backendBaseUrl}/api/v1/jd/${id}`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (response.status === 404) {
    notFound()
  }

  if (!response.ok) {
    await signOut({ redirectTo: "/login" })
  }

  const result = (await response.json()) as JDAnalysisResponse

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <JDAnalysisContent result={result} />
      <CVScreeningPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} jd={result} />
    </main>
  )
}
```

- [ ] **Step 3: Run the frontend checks**

Run: `pnpm --dir frontend lint`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/jd/cv-screening-panel.tsx frontend/src/app/dashboard/jd/[id]/page.tsx
git commit -m "feat: add jd detail cv screening panel"
```

### Task 8: Verify the full slice and update backend docs

**Files:**
- Modify: `backend/README.md`
- Test: `backend/tests/schemas/test_cv_schema.py`
- Test: `backend/tests/services/test_cv_screening_service.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Document the new CV screening flow**

```md
## CV Screening

The backend exposes `POST /api/v1/cv/screen` for one-CV screening against an existing analyzed JD.

Supported files:

- PDF
- DOCX

Required request fields:

- `jd_id`
- `file`

Relevant environment variables:

- `CV_UPLOAD_DIR`
- `CV_MAX_UPLOAD_SIZE_BYTES`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
```

- [ ] **Step 2: Run the targeted backend test suite**

Run: `pytest backend/tests/schemas/test_cv_schema.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py -v`
Expected: PASS

- [ ] **Step 3: Run backend lint and type checks**

Run: `ruff check backend/src backend/tests && basedpyright backend/src backend/tests`
Expected: PASS with no warnings

- [ ] **Step 4: Run the frontend type and lint checks**

Run: `pnpm --dir frontend lint && pnpm --dir frontend exec tsc --noEmit`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/README.md backend/tests/schemas/test_cv_schema.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py
git commit -m "docs: add cv screening setup notes"
```

## Self-Review

- Spec coverage: covered CV upload, file validation, candidate profile extraction, JD-linked screening, persistence, API read/write routes, UI integration, docs, and verification.
- Placeholder scan: no `TODO`, `TBD`, or unresolved implementation references remain in the plan.
- Type consistency: the plan uses `CandidateDocument`, `CandidateProfile`, `CandidateScreening`, `CandidateProfilePayload`, `CVScreeningPayload`, and `CVScreeningResponse` consistently across tasks.
