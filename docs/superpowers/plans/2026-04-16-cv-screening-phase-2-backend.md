# CV Screening Phase 2 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current MVP CV screening backend with a Phase 2 backend that extracts a review-ready candidate profile, generates structured Gemini screening artifacts, reconciles them with deterministic rules, persists the artifacts, and returns the new Phase 2 response contract.

**Architecture:** Keep the existing `/api/v1/cv/screen` and `/api/v1/cv/screenings/{screening_id}` endpoints, but replace the CV schema and screening flow behind them. Split the work into three focused units: Phase 2 schemas, Gemini extraction/screening adapters, and orchestration logic with deterministic guards. Persist the new candidate profile and screening payloads in the existing `candidate_profiles` and `candidate_screenings` tables.

**Tech Stack:** FastAPI, SQLAlchemy async ORM, PostgreSQL JSON/JSONB, Pydantic v2, LangChain, langchain-google-genai, pytest, pytest-asyncio, httpx

---

## Planned File Structure

- Modify: `backend/src/schemas/cv.py`
  - Replace the Phase 1 profile and response contracts with Phase 2 profile, result, and audit schemas.
- Modify: `backend/src/schemas/__init__.py`
  - Export the new CV schema symbols used by the API and tests.
- Modify: `backend/src/services/cv_extractor.py`
  - Replace the old candidate-profile prompt and implement a typed extractor for the new profile schema.
- Modify: `backend/src/services/cv_screening_service.py`
  - Add a second Gemini screening step, deterministic reconciliation helpers, audit assembly, and the new response builder.
- Modify: `backend/src/services/__init__.py`
  - Export any new screening error or helper types if needed.
- Modify: `backend/src/api/v1/cv.py`
  - Keep the endpoints but return the new Phase 2 response model and updated failure behavior.
- Modify: `backend/src/config.py`
  - Add optional schema-version settings only if needed by implementation.
- Test: `backend/tests/schemas/test_cv_schema.py`
  - Replace the Phase 1 schema tests with Phase 2 contract tests.
- Test: `backend/tests/services/test_cv_screening_service.py`
  - Add tests for extraction prompt, screening prompt, reconciliation, persistence, and retrieval.
- Test: `backend/tests/api/test_cv_api.py`
  - Update route tests to match the new Phase 2 payload shape.

### Task 1: Replace the CV schema contract with Phase 2 models

**Files:**
- Modify: `backend/src/schemas/cv.py`
- Modify: `backend/src/schemas/__init__.py`
- Test: `backend/tests/schemas/test_cv_schema.py`

- [ ] **Step 1: Write the failing schema tests for the new candidate profile and response contract**

```python
"""Schema and model contract tests for CV screening phase 2."""

import pytest
from pydantic import ValidationError

from src.schemas.cv import (
    AuditMetadata,
    CandidateProfilePayload,
    CVScreeningResponse,
    FollowUpQuestion,
    KnockoutAssessment,
    RiskFlag,
)


def test_candidate_profile_requires_phase_2_sections() -> None:
    with pytest.raises(ValidationError):
        _ = CandidateProfilePayload.model_validate(
            {
                "candidate_summary": {
                    "full_name": "Nguyen Van A",
                    "seniority_signal": "mid",
                },
                "work_experience": [],
                "skills_inventory": [],
            }
        )


def test_knockout_assessment_rejects_invalid_status() -> None:
    with pytest.raises(ValidationError):
        _ = KnockoutAssessment.model_validate(
            {
                "criterion": {"vi": "Bắt buộc Python", "en": "Python required"},
                "status": "partial",
                "reason": {"vi": "Thiếu dữ liệu", "en": "Missing evidence"},
                "evidence": [],
            }
        )


def test_risk_flag_rejects_invalid_severity() -> None:
    with pytest.raises(ValidationError):
        _ = RiskFlag.model_validate(
            {
                "title": {"vi": "Rủi ro", "en": "Risk"},
                "reason": {"vi": "Lý do", "en": "Reason"},
                "severity": "critical",
            }
        )


def test_audit_metadata_requires_schema_versions() -> None:
    with pytest.raises(ValidationError):
        _ = AuditMetadata.model_validate(
            {
                "extraction_model": "gemini-2.5-pro",
                "screening_model": "gemini-2.5-pro",
                "generated_at": "2026-04-16T00:00:00Z",
                "reconciliation_notes": [],
                "consistency_flags": [],
            }
        )


def test_cv_screening_response_requires_candidate_profile_result_and_audit() -> None:
    with pytest.raises(ValidationError):
        _ = CVScreeningResponse.model_validate(
            {
                "screening_id": "screening-id",
                "jd_id": "jd-id",
                "candidate_id": "candidate-id",
                "file_name": "candidate.pdf",
                "status": "completed",
                "created_at": "2026-04-16T00:00:00Z",
            }
        )


def test_follow_up_question_allows_null_linked_dimension() -> None:
    question = FollowUpQuestion.model_validate(
        {
            "question": {"vi": "Bạn đã dùng Python ở đâu?", "en": "Where did you use Python?"},
            "purpose": {"vi": "Xác minh kinh nghiệm", "en": "Verify experience"},
            "linked_dimension": None,
        }
    )

    assert question.linked_dimension is None
```

- [ ] **Step 2: Run the schema tests to verify they fail**

Run: `pytest backend/tests/schemas/test_cv_schema.py -v`
Expected: FAIL with `ImportError` or `ValidationError` because the new Phase 2 schema symbols do not exist yet.

- [ ] **Step 3: Replace `backend/src/schemas/cv.py` with the Phase 2 schema contract**

```python
"""Schemas for candidate profile extraction and CV screening phase 2."""

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
    """Status for knockout and requirement checks."""

    MET = "met"
    NOT_MET = "not_met"
    UNCLEAR = "unclear"


class RiskSeverity(StrEnum):
    """Severity marker for a screening risk flag."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CandidateSummary(BaseModel):
    """High-level identity and career summary."""

    full_name: str | None = None
    current_title: str | None = None
    location: str | None = None
    total_years_experience: float | None = Field(default=None, ge=0)
    seniority_signal: Literal["intern", "junior", "mid", "senior", "lead", "manager", "unknown"]
    professional_summary: BilingualText | None = None


class WorkExperienceItem(BaseModel):
    """One structured work history entry."""

    company: str
    role: str
    start_date_text: str | None = None
    end_date_text: str | None = None
    duration_text: str | None = None
    responsibilities: list[str]
    achievements: list[str]
    technologies: list[str]
    evidence_excerpts: list[str]
    ambiguity_notes: list[str]


class ProjectItem(BaseModel):
    """One project-based evidence entry."""

    name: str | None = None
    role: str | None = None
    summary: str
    technologies: list[str]
    domain_context: str | None = None
    evidence_excerpts: list[str]


class SkillEvidenceItem(BaseModel):
    """One normalized skill with supporting evidence."""

    skill_name: str
    proficiency_signal: str | None = None
    evidence_excerpts: list[str]
    source_section: Literal["experience", "project", "summary", "skills", "other"]


class EducationItem(BaseModel):
    """One education entry."""

    institution: str
    degree: str | None = None
    field_of_study: str | None = None
    graduation_text: str | None = None
    evidence_excerpts: list[str]


class CertificationItem(BaseModel):
    """One certification entry."""

    name: str
    issuer: str | None = None
    date_text: str | None = None
    evidence_excerpts: list[str]


class LanguageItem(BaseModel):
    """One language capability entry."""

    language_name: str
    proficiency_signal: str | None = None
    evidence_excerpts: list[str]


class ProfileUncertainty(BaseModel):
    """One important ambiguity in the extracted profile."""

    title: BilingualText
    reason: BilingualText
    impact: BilingualText


class CandidateProfilePayload(BaseModel):
    """Review-ready candidate profile extracted from the uploaded CV."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    candidate_summary: CandidateSummary
    work_experience: list[WorkExperienceItem]
    projects: list[ProjectItem]
    skills_inventory: list[SkillEvidenceItem]
    education: list[EducationItem]
    certifications: list[CertificationItem]
    languages: list[LanguageItem]
    profile_uncertainties: list[ProfileUncertainty]


class KnockoutAssessment(BaseModel):
    """Assessment for one knockout criterion."""

    criterion: BilingualText
    status: RequirementStatus
    reason: BilingualText
    evidence: list[BilingualText]


class MinimumRequirementCheck(BaseModel):
    """Assessment for one minimum requirement."""

    criterion: BilingualText
    status: RequirementStatus
    reason: BilingualText
    evidence: list[BilingualText]


class DimensionScore(BaseModel):
    """Assessment for one rubric dimension."""

    dimension_name: BilingualText
    priority: Literal["must_have", "important", "nice_to_have"]
    weight: float = Field(ge=0, le=1)
    score: float = Field(ge=0, le=1)
    reason: BilingualText
    evidence: list[BilingualText]
    confidence_note: BilingualText | None = None


class ScreeningInsight(BaseModel):
    """Evidence-backed screening insight."""

    title: BilingualText
    reason: BilingualText
    evidence: list[BilingualText]


class ScreeningUncertainty(BaseModel):
    """Important unresolved screening uncertainty."""

    title: BilingualText
    reason: BilingualText
    follow_up_suggestion: BilingualText


class FollowUpQuestion(BaseModel):
    """Suggested interviewer follow-up question."""

    question: BilingualText
    purpose: BilingualText
    linked_dimension: BilingualText | None = None


class RiskFlag(BaseModel):
    """Explicit screening warning for HR review."""

    title: BilingualText
    reason: BilingualText
    severity: RiskSeverity


class ScreeningResultPayload(BaseModel):
    """Full Phase 2 screening result payload."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    match_score: float = Field(ge=0, le=1)
    recommendation: ScreeningRecommendation
    decision_reason: BilingualText
    screening_summary: BilingualText
    knockout_assessments: list[KnockoutAssessment]
    minimum_requirement_checks: list[MinimumRequirementCheck]
    dimension_scores: list[DimensionScore]
    strengths: list[ScreeningInsight]
    gaps: list[ScreeningInsight]
    uncertainties: list[ScreeningUncertainty]
    follow_up_questions: list[FollowUpQuestion]
    risk_flags: list[RiskFlag]


class AuditMetadata(BaseModel):
    """Safe audit metadata for extraction and screening."""

    extraction_model: str
    screening_model: str
    profile_schema_version: str
    screening_schema_version: str
    generated_at: str
    reconciliation_notes: list[str]
    consistency_flags: list[str]


class StoredScreeningPayload(BaseModel):
    """Persisted screening document stored in the database."""

    candidate_profile: CandidateProfilePayload
    result: ScreeningResultPayload
    audit: AuditMetadata


class CVScreeningResponse(BaseModel):
    """API response for a completed CV screening."""

    screening_id: str
    jd_id: str
    candidate_id: str
    file_name: str
    status: Literal["completed"]
    created_at: str
    candidate_profile: CandidateProfilePayload
    result: ScreeningResultPayload
    audit: AuditMetadata


__all__ = [
    "AuditMetadata",
    "CandidateProfilePayload",
    "CandidateSummary",
    "CertificationItem",
    "CVScreeningResponse",
    "DimensionScore",
    "EducationItem",
    "FollowUpQuestion",
    "KnockoutAssessment",
    "LanguageItem",
    "MinimumRequirementCheck",
    "ProfileUncertainty",
    "ProjectItem",
    "RequirementStatus",
    "RiskFlag",
    "RiskSeverity",
    "ScreeningInsight",
    "ScreeningRecommendation",
    "ScreeningResultPayload",
    "ScreeningUncertainty",
    "SkillEvidenceItem",
    "StoredScreeningPayload",
    "WorkExperienceItem",
]
```

- [ ] **Step 4: Export the new CV schema symbols from `backend/src/schemas/__init__.py`**

```python
"""Schemas."""

from src.schemas.auth import GoogleTokenRequest as GoogleAuthRequest
from src.schemas.auth import TokenResponse
from src.schemas.cv import (
    AuditMetadata,
    CandidateProfilePayload,
    CVScreeningResponse,
    FollowUpQuestion,
    KnockoutAssessment,
    MinimumRequirementCheck,
    RequirementStatus,
    RiskFlag,
    RiskSeverity,
    ScreeningRecommendation,
    ScreeningResultPayload,
    ScreeningUncertainty,
    StoredScreeningPayload,
)
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse, JDRecentItem
from src.schemas.user import UserResponse

__all__ = [
    "AuditMetadata",
    "CandidateProfilePayload",
    "CVScreeningResponse",
    "FollowUpQuestion",
    "GoogleAuthRequest",
    "JDAnalysisPayload",
    "JDAnalysisResponse",
    "JDRecentItem",
    "KnockoutAssessment",
    "MinimumRequirementCheck",
    "RequirementStatus",
    "RiskFlag",
    "RiskSeverity",
    "ScreeningRecommendation",
    "ScreeningResultPayload",
    "ScreeningUncertainty",
    "StoredScreeningPayload",
    "TokenResponse",
    "UserResponse",
]
```

- [ ] **Step 5: Run the schema tests to verify they pass**

Run: `pytest backend/tests/schemas/test_cv_schema.py -v`
Expected: PASS

- [ ] **Step 6: Commit the schema contract change**

```bash
git add backend/src/schemas/cv.py backend/src/schemas/__init__.py backend/tests/schemas/test_cv_schema.py
git commit -m "feat: add phase 2 cv screening schemas"
```

### Task 2: Upgrade the CV extractor to produce the Phase 2 candidate profile

**Files:**
- Modify: `backend/src/services/cv_extractor.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing extractor prompt and validation tests**

```python
from pathlib import Path

from src.schemas.cv import CandidateProfilePayload
from src.services.cv_extractor import build_cv_extraction_prompt


def test_build_cv_extraction_prompt_mentions_phase_2_review_artifacts() -> None:
    prompt = build_cv_extraction_prompt()

    assert "review-ready" in prompt.lower()
    assert "evidence" in prompt.lower()
    assert "ambiguities" in prompt.lower()
    assert CandidateProfilePayload.__name__ in prompt


class FakeStructuredProfileInvoker:
    async def ainvoke(self, _: list[object]) -> object:
        return {
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
        }


async def test_extractor_validates_phase_2_candidate_profile(tmp_path: Path) -> None:
    extractor = GeminiCVExtractor.__new__(GeminiCVExtractor)
    extractor._structured_llm = FakeStructuredProfileInvoker()

    file_path = tmp_path / "candidate.pdf"
    file_path.write_bytes(b"%PDF-1.7\ncandidate")

    result = await extractor.extract(file_path, "application/pdf")

    assert result.candidate_summary.full_name == "Nguyen Van A"
    assert result.candidate_summary.seniority_signal == "mid"
```

- [ ] **Step 2: Run the focused extractor tests to verify they fail**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_cv_extraction_prompt_mentions_phase_2_review_artifacts backend/tests/services/test_cv_screening_service.py::test_extractor_validates_phase_2_candidate_profile -v`
Expected: FAIL because the old prompt and schema no longer match the new test expectations.

- [ ] **Step 3: Rewrite `backend/src/services/cv_extractor.py` for the Phase 2 profile schema**

```python
"""LangChain-based Gemini extractor for CV screening phase 2."""

from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.cv import CandidateProfilePayload


PROFILE_SCHEMA_VERSION = "phase2.v1"


def build_cv_extraction_prompt() -> str:
    """Return the structured extraction instructions for Phase 2 CV parsing."""
    return (
        "You are a conservative recruiting analyst. Read the uploaded CV and produce a review-ready "
        "candidate profile for HR screening. Extract only claims supported directly by the document, "
        "preserve evidence-bearing statements, keep important ambiguities explicit, prefer omission over "
        "unsupported inference, and return the CandidateProfilePayload schema exactly."
    )


class StructuredCandidateInvoker(Protocol):
    """Minimal protocol for the LangChain structured output client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return a structured result."""


class GeminiCVExtractor:
    """Wrapper around Gemini structured output for Phase 2 candidate profiles."""

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
        """Extract a structured Phase 2 candidate profile from an uploaded CV."""
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

- [ ] **Step 4: Run the extractor tests to verify they pass**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_cv_extraction_prompt_mentions_phase_2_review_artifacts backend/tests/services/test_cv_screening_service.py::test_extractor_validates_phase_2_candidate_profile -v`
Expected: PASS

- [ ] **Step 5: Commit the extractor upgrade**

```bash
git add backend/src/services/cv_extractor.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: upgrade cv extraction for phase 2 screening"
```

### Task 3: Add a Gemini screening adapter for structured screening artifacts

**Files:**
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing tests for the screening prompt and adapter contract**

```python
from src.schemas.cv import StoredScreeningPayload
from src.services.cv_screening_service import build_screening_prompt


def test_build_screening_prompt_mentions_knockouts_and_must_have_rules() -> None:
    prompt = build_screening_prompt()

    assert "knockout" in prompt.lower()
    assert "must-have" in prompt.lower()
    assert "structured output" in prompt.lower()
    assert StoredScreeningPayload.__name__ in prompt


class FakeStructuredScreeningInvoker:
    async def ainvoke(self, _: list[object]) -> object:
        return {
            "candidate_profile": {
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
            "result": {
                "match_score": 0.78,
                "recommendation": "advance",
                "decision_reason": {
                    "vi": "Ứng viên phù hợp với JD.",
                    "en": "The candidate aligns with the JD.",
                },
                "screening_summary": {
                    "vi": "Phù hợp tốt với nền tảng backend.",
                    "en": "Strong fit for backend fundamentals.",
                },
                "knockout_assessments": [],
                "minimum_requirement_checks": [],
                "dimension_scores": [],
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
        }


async def test_screening_adapter_validates_stored_screening_payload() -> None:
    service = CVScreeningService.__new__(CVScreeningService)
    service._screening_llm = FakeStructuredScreeningInvoker()

    payload = await service._generate_screening_payload(
        jd_analysis=sample_jd_analysis_payload(),
        candidate_profile=sample_candidate_profile_payload(),
    )

    assert payload.result.recommendation == "advance"
    assert payload.audit.profile_schema_version == "phase2.v1"
```

- [ ] **Step 2: Run the focused screening-adapter tests to verify they fail**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_screening_prompt_mentions_knockouts_and_must_have_rules backend/tests/services/test_cv_screening_service.py::test_screening_adapter_validates_stored_screening_payload -v`
Expected: FAIL because the service does not yet expose a Phase 2 screening adapter.

- [ ] **Step 3: Add the screening prompt and `_generate_screening_payload()` helper to `backend/src/services/cv_screening_service.py`**

```python
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.schemas.cv import CandidateProfilePayload, StoredScreeningPayload
from src.schemas.jd import JDAnalysisPayload


SCREENING_SCHEMA_VERSION = "phase2.v1"


def build_screening_prompt() -> str:
    """Return the structured screening instructions for Phase 2 candidate evaluation."""
    return (
        "You are a hiring analyst comparing one candidate to one analyzed job description. Evaluate "
        "knockout criteria first, then minimum requirements, then rubric dimensions. Respect must-have, "
        "important, and nice-to-have priorities, keep ambiguities explicit, provide bilingual HR-facing "
        "reasons, and return structured output only using the StoredScreeningPayload schema."
    )


class StructuredScreeningInvoker(Protocol):
    """Minimal protocol for the LangChain structured screening client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return structured screening artifacts."""


class CVScreeningService:
    def __init__(
        self,
        extractor: CandidateExtractor | None = None,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        self._extractor = extractor or GeminiCVExtractor()
        self._upload_dir = upload_dir or settings.cv_upload_path
        self._db_session = db_session
        self._screening_llm: StructuredScreeningInvoker = cast(
            StructuredScreeningInvoker,
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0,
            ).with_structured_output(StoredScreeningPayload),
        )

    async def _generate_screening_payload(
        self,
        jd_analysis: JDAnalysisPayload,
        candidate_profile: CandidateProfilePayload,
    ) -> StoredScreeningPayload:
        """Generate structured screening artifacts from the JD analysis and candidate profile."""
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_screening_prompt()},
                {
                    "type": "text",
                    "text": JDAnalysisPayload.model_validate(jd_analysis).model_dump_json(indent=2),
                },
                {
                    "type": "text",
                    "text": CandidateProfilePayload.model_validate(candidate_profile).model_dump_json(indent=2),
                },
            ]
        )
        result = await self._screening_llm.ainvoke([message])
        return StoredScreeningPayload.model_validate(result)
```

- [ ] **Step 4: Run the screening-adapter tests to verify they pass**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_build_screening_prompt_mentions_knockouts_and_must_have_rules backend/tests/services/test_cv_screening_service.py::test_screening_adapter_validates_stored_screening_payload -v`
Expected: PASS

- [ ] **Step 5: Commit the screening adapter**

```bash
git add backend/src/services/cv_screening_service.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: add phase 2 screening artifact generation"
```

### Task 4: Implement deterministic reconciliation and final response assembly

**Files:**
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing reconciliation tests**

```python
import pytest

from src.schemas.cv import StoredScreeningPayload
from src.services.cv_screening_service import CVScreeningService


def test_reconcile_screening_downgrades_advance_on_knockout_failure() -> None:
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        recommendation="advance",
        knockout_status="not_met",
        match_score=0.82,
    )

    reconciled = service._reconcile_screening_payload(payload)

    assert reconciled.result.recommendation == "reject"
    assert any("knockout" in note.lower() for note in reconciled.audit.reconciliation_notes)


def test_reconcile_screening_recomputes_match_score_from_dimensions() -> None:
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        match_score=0.99,
        dimension_scores=[
            sample_dimension_score(weight=0.6, score=0.5),
            sample_dimension_score(weight=0.4, score=0.25),
        ],
    )

    reconciled = service._reconcile_screening_payload(payload)

    assert reconciled.result.match_score == pytest.approx(0.4)


def test_reconcile_screening_marks_missing_must_have_evidence_as_unclear() -> None:
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        recommendation="advance",
        dimension_scores=[
            sample_dimension_score(
                priority="must_have",
                score=0.9,
                evidence=[],
            )
        ],
    )

    reconciled = service._reconcile_screening_payload(payload)

    assert reconciled.result.recommendation == "review"
    assert any("must-have" in flag.lower() for flag in reconciled.audit.consistency_flags)
```

- [ ] **Step 2: Run the reconciliation tests to verify they fail**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_downgrades_advance_on_knockout_failure backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_recomputes_match_score_from_dimensions backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_marks_missing_must_have_evidence_as_unclear -v`
Expected: FAIL because the service does not yet reconcile model output.

- [ ] **Step 3: Add the deterministic reconciliation helpers to `backend/src/services/cv_screening_service.py`**

```python
from copy import deepcopy

from src.schemas.cv import RequirementStatus, ScreeningRecommendation, StoredScreeningPayload


class CVScreeningService:
    def _reconcile_screening_payload(
        self,
        payload: StoredScreeningPayload,
    ) -> StoredScreeningPayload:
        """Reconcile model output with deterministic backend rules."""
        data = payload.model_dump(mode="json")
        result = data["result"]
        audit = data["audit"]

        recomputed_score = round(
            sum(item["weight"] * item["score"] for item in result["dimension_scores"]),
            2,
        )
        if result["match_score"] != recomputed_score:
            result["match_score"] = recomputed_score
            audit["reconciliation_notes"].append("Recomputed weighted match score from dimension scores.")

        has_knockout_failure = any(
            item["status"] == RequirementStatus.NOT_MET
            for item in result["knockout_assessments"]
        )
        if has_knockout_failure and result["recommendation"] != ScreeningRecommendation.REJECT:
            result["recommendation"] = ScreeningRecommendation.REJECT
            audit["reconciliation_notes"].append(
                "Downgraded recommendation to reject because a knockout criterion was not met."
            )

        missing_must_have_evidence = any(
            item["priority"] == "must_have" and item["score"] > 0 and not item["evidence"]
            for item in result["dimension_scores"]
        )
        if missing_must_have_evidence:
            audit["consistency_flags"].append("Must-have dimension lacks supporting evidence.")
            if result["recommendation"] == ScreeningRecommendation.ADVANCE:
                result["recommendation"] = ScreeningRecommendation.REVIEW
                audit["reconciliation_notes"].append(
                    "Downgraded recommendation to review because a must-have dimension lacked evidence."
                )

        return StoredScreeningPayload.model_validate(data)
```

- [ ] **Step 4: Run the reconciliation tests to verify they pass**

Run: `pytest backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_downgrades_advance_on_knockout_failure backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_recomputes_match_score_from_dimensions backend/tests/services/test_cv_screening_service.py::test_reconcile_screening_marks_missing_must_have_evidence_as_unclear -v`
Expected: PASS

- [ ] **Step 5: Commit the reconciliation logic**

```bash
git add backend/src/services/cv_screening_service.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: add deterministic phase 2 screening guards"
```

### Task 5: Replace the end-to-end screening service flow with the Phase 2 pipeline

**Files:**
- Modify: `backend/src/services/cv_screening_service.py`
- Test: `backend/tests/services/test_cv_screening_service.py`

- [ ] **Step 1: Write the failing end-to-end service tests for persistence and retrieval**

```python
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateProfile, CandidateScreening
from src.services.cv_screening_service import CVScreeningService, JDNotReadyError


@pytest.mark.asyncio
async def test_screening_service_persists_phase_2_profile_and_screening(
    db_session: AsyncSession,
    tmp_path,
    seeded_jd_analysis_id: str,
) -> None:
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()

    response = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    stored_profile = await db_session.scalar(
        select(CandidateProfile).where(CandidateProfile.candidate_document_id == response.candidate_id)
    )
    stored_screening = await db_session.scalar(
        select(CandidateScreening).where(CandidateScreening.id == response.screening_id)
    )

    assert response.candidate_profile.candidate_summary.full_name == "Nguyen Van A"
    assert response.audit.profile_schema_version == "phase2.v1"
    assert stored_profile is not None
    assert stored_screening is not None


@pytest.mark.asyncio
async def test_get_screening_returns_phase_2_response(
    db_session: AsyncSession,
    tmp_path,
    seeded_jd_analysis_id: str,
) -> None:
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()

    created = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    fetched = await service.get_screening(created.screening_id)

    assert fetched is not None
    assert fetched.result.screening_summary.en == created.result.screening_summary.en


@pytest.mark.asyncio
async def test_screening_service_raises_when_jd_is_missing(
    db_session: AsyncSession,
    tmp_path,
) -> None:
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()

    with pytest.raises(JDNotReadyError, match="JD analysis not found or not ready"):
        await service.screen_upload(
            jd_id="missing-jd-id",
            file_name="candidate.pdf",
            mime_type="application/pdf",
            file_bytes=b"%PDF-1.7\ncandidate",
        )
```

- [ ] **Step 2: Run the service tests to verify they fail**

Run: `pytest backend/tests/services/test_cv_screening_service.py -v`
Expected: FAIL because the service still persists the old payload structure and returns the old response model.

- [ ] **Step 3: Replace `screen_upload()` and `get_screening()` in `backend/src/services/cv_screening_service.py` with the Phase 2 orchestration flow**

```python
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import (
    AuditMetadata,
    CandidateProfilePayload,
    CVScreeningResponse,
    StoredScreeningPayload,
)
from src.schemas.jd import JDAnalysisPayload
from src.services.cv_extractor import GeminiCVExtractor
from src.services.file_storage import store_upload_file


class CandidateExtractor(Protocol):
    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        ...


class JDNotReadyError(ValueError):
    """Raised when a referenced JD cannot be screened yet."""


class CVScreeningService:
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

        generated_payload = await self._generate_screening_payload(jd_analysis, candidate_profile)
        reconciled_payload = self._reconcile_screening_payload(generated_payload)
        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=persisted_profile.id,
            model_name=settings.gemini_model,
            screening_payload=reconciled_payload.model_dump(mode="json"),
        )
        self._db_session.add(screening)
        candidate_document.status = "completed"
        await self._db_session.commit()
        await self._db_session.refresh(screening)

        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=jd_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            candidate_profile=reconciled_payload.candidate_profile,
            result=reconciled_payload.result,
            audit=reconciled_payload.audit,
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

        screening, _, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        payload = StoredScreeningPayload.model_validate(screening.screening_payload)
        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=screening.jd_document_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            candidate_profile=payload.candidate_profile,
            result=payload.result,
            audit=payload.audit,
        )
```

- [ ] **Step 4: Run the service tests to verify they pass**

Run: `pytest backend/tests/services/test_cv_screening_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit the Phase 2 orchestration service**

```bash
git add backend/src/services/cv_screening_service.py backend/tests/services/test_cv_screening_service.py
git commit -m "feat: implement phase 2 cv screening service"
```

### Task 6: Update the API layer to serve the new Phase 2 contract

**Files:**
- Modify: `backend/src/api/v1/cv.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Write the failing API tests for the new response shape**

```python
from fastapi.testclient import TestClient


def test_cv_screen_endpoint_returns_phase_2_payload(monkeypatch) -> None:
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["candidate_profile"]["candidate_summary"]["full_name"] == "Nguyen Van A"
    assert payload["result"]["screening_summary"]["en"] == "Strong fit for backend fundamentals."
    assert payload["audit"]["profile_schema_version"] == "phase2.v1"


def test_cv_screening_detail_returns_phase_2_payload(monkeypatch) -> None:
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/cv/screenings/test-screening-id")

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"]["recommendation"] == "review"
    assert "audit" in payload
```

- [ ] **Step 2: Run the API tests to verify they fail**

Run: `pytest backend/tests/api/test_cv_api.py -v`
Expected: FAIL because the route test doubles and expectations still use the old payload shape.

- [ ] **Step 3: Update the test double and route contract in `backend/tests/api/test_cv_api.py` and `backend/src/api/v1/cv.py`**

```python
# backend/tests/api/test_cv_api.py
from src.schemas.cv import CandidateProfilePayload, CVScreeningResponse, ScreeningResultPayload, AuditMetadata


class FakeCVScreeningService:
    async def screen_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningResponse:
        _ = (mime_type, file_bytes)
        return CVScreeningResponse.model_validate(
            {
                "screening_id": "test-screening-id",
                "jd_id": jd_id,
                "candidate_id": "candidate-id",
                "file_name": file_name,
                "status": "completed",
                "created_at": "2026-04-16T00:00:00Z",
                "candidate_profile": {
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
                "result": {
                    "match_score": 0.72,
                    "recommendation": "review",
                    "decision_reason": {"vi": "Có tín hiệu phù hợp.", "en": "The candidate shows fit signals."},
                    "screening_summary": {
                        "vi": "Phù hợp tốt với nền tảng backend.",
                        "en": "Strong fit for backend fundamentals.",
                    },
                    "knockout_assessments": [],
                    "minimum_requirement_checks": [],
                    "dimension_scores": [],
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
            }
        )
```

```python
# backend/src/api/v1/cv.py
@router.post("/screen", response_model=CVScreeningResponse)
async def screen_cv(
    jd_id: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningResponse:
    """Upload one CV and return the Phase 2 screening response."""
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
```

- [ ] **Step 4: Run the API tests to verify they pass**

Run: `pytest backend/tests/api/test_cv_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit the API contract update**

```bash
git add backend/src/api/v1/cv.py backend/tests/api/test_cv_api.py
git commit -m "feat: expose phase 2 cv screening api contract"
```

### Task 7: Run the targeted verification suite and clean exports

**Files:**
- Modify: `backend/src/services/__init__.py`
- Test: `backend/tests/schemas/test_cv_schema.py`
- Test: `backend/tests/services/test_cv_screening_service.py`
- Test: `backend/tests/api/test_cv_api.py`

- [ ] **Step 1: Add any missing service exports needed by the updated implementation**

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

- [ ] **Step 2: Run the full targeted test suite**

Run: `pytest backend/tests/schemas/test_cv_schema.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py -v`
Expected: PASS

- [ ] **Step 3: Run lint and type checks for the touched backend files**

Run: `ruff check backend/src/schemas/cv.py backend/src/services/cv_extractor.py backend/src/services/cv_screening_service.py backend/src/api/v1/cv.py backend/tests/schemas/test_cv_schema.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py && basedpyright backend/src backend/tests`
Expected: PASS with no warnings

- [ ] **Step 4: Commit the final verification changes**

```bash
git add backend/src/services/__init__.py backend/tests/schemas/test_cv_schema.py backend/tests/services/test_cv_screening_service.py backend/tests/api/test_cv_api.py
git commit -m "test: verify phase 2 cv screening backend"
```

## Self-Review

- Spec coverage: the plan covers schema replacement, extraction redesign, Gemini screening artifacts, deterministic guards, persistence, API contract updates, and targeted tests.
- Placeholder scan: no `TODO`, `TBD`, or vague “handle appropriately” steps remain.
- Type consistency: the same Phase 2 types are used throughout the plan: `CandidateProfilePayload`, `StoredScreeningPayload`, `CVScreeningResponse`, `KnockoutAssessment`, `FollowUpQuestion`, and `AuditMetadata`.
