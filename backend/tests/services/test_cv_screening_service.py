"""CV screening service contract tests."""

from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cv import CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import CandidateProfilePayload, StoredScreeningPayload
from src.schemas.jd import JDAnalysisPayload
from src.services.cv_extractor import build_cv_extraction_prompt
from src.services.cv_screening_service import (
    CVScreeningService,
    JDNotReadyError,
    build_screening_prompt,
)


def sample_candidate_profile_payload() -> CandidateProfilePayload:
    """Build a valid Phase 2 candidate profile fixture."""
    return CandidateProfilePayload.model_validate(
        {
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
            "work_experience": [
                {
                    "company": "Acme",
                    "role": "Backend Engineer",
                    "start_date_text": "2021",
                    "end_date_text": "2024",
                    "duration_text": "3 years",
                    "responsibilities": ["Built APIs"],
                    "achievements": ["Improved latency"],
                    "technologies": ["Python", "FastAPI", "PostgreSQL"],
                    "evidence_excerpts": ["Built Python APIs"],
                    "ambiguity_notes": [],
                }
            ],
            "projects": [
                {
                    "name": "Internal Platform",
                    "role": "Backend Engineer",
                    "summary": "Built a Python service platform.",
                    "technologies": ["Python", "FastAPI"],
                    "domain_context": "Internal tools",
                    "evidence_excerpts": ["Built internal platform"],
                }
            ],
            "skills_inventory": [
                {
                    "skill_name": "Python",
                    "proficiency_signal": "Strong",
                    "evidence_excerpts": ["Built Python APIs"],
                    "source_section": "experience",
                }
            ],
            "education": [],
            "certifications": [],
            "languages": [
                {
                    "language_name": "English",
                    "proficiency_signal": "Professional",
                    "evidence_excerpts": ["English"],
                }
            ],
            "profile_uncertainties": [],
        }
    )


def sample_jd_analysis_payload() -> dict[str, object]:
    """Build a JD payload fixture that passes the current JD schema."""
    return {
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
            "screening_knockout_criteria": [
                {"vi": "Bat buoc Python", "en": "Python required"}
            ],
        },
        "rubric_seed": {
            "evaluation_dimensions": [
                {
                    "name": {"vi": "Python", "en": "Python"},
                    "description": {"vi": "Mo ta", "en": "Description"},
                    "priority": "must_have",
                    "weight": 0.3,
                    "evidence_signals": [{"vi": "API", "en": "APIs"}],
                },
                {
                    "name": {"vi": "SQL", "en": "SQL"},
                    "description": {"vi": "Mo ta", "en": "Description"},
                    "priority": "important",
                    "weight": 0.2,
                    "evidence_signals": [{"vi": "Query", "en": "Queries"}],
                },
                {
                    "name": {"vi": "FastAPI", "en": "FastAPI"},
                    "description": {"vi": "Mo ta", "en": "Description"},
                    "priority": "important",
                    "weight": 0.2,
                    "evidence_signals": [{"vi": "Service", "en": "Services"}],
                },
                {
                    "name": {"vi": "English", "en": "English"},
                    "description": {"vi": "Mo ta", "en": "Description"},
                    "priority": "important",
                    "weight": 0.15,
                    "evidence_signals": [
                        {"vi": "Giao tiep", "en": "Communication"}
                    ],
                },
                {
                    "name": {"vi": "Docker", "en": "Docker"},
                    "description": {"vi": "Mo ta", "en": "Description"},
                    "priority": "nice_to_have",
                    "weight": 0.15,
                    "evidence_signals": [{"vi": "Container", "en": "Containers"}],
                },
            ],
            "screening_rules": {
                "minimum_requirements": [
                    {"vi": "3 nam kinh nghiem", "en": "3 years experience"}
                ],
                "scoring_principle": {
                    "vi": "Khong bu tru must-have bang nice-to-have",
                    "en": "Nice-to-have cannot replace must-have",
                },
            },
            "ambiguities_for_human_review": [],
        },
    }


def sample_dimension_score(
    *,
    priority: str = "important",
    weight: float = 1.0,
    score: float = 0.4,
    evidence: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    """Build a dimension-score fixture for reconciliation tests."""
    return {
        "dimension_name": {"vi": "Python", "en": "Python"},
        "priority": priority,
        "weight": weight,
        "score": score,
        "reason": {"vi": "Ly do", "en": "Reason"},
        "evidence": (
            evidence if evidence is not None else [{"vi": "API", "en": "API"}]
        ),
        "confidence_note": None,
    }


def sample_stored_screening_payload(
    *,
    recommendation: str = "advance",
    knockout_status: str = "met",
    match_score: float = 0.82,
    dimension_scores: list[dict[str, object]] | None = None,
) -> StoredScreeningPayload:
    """Build a stored screening payload fixture for adapter and guard tests."""
    return StoredScreeningPayload.model_validate(
        {
            "candidate_profile": sample_candidate_profile_payload().model_dump(mode="json"),
            "result": {
                "match_score": match_score,
                "recommendation": recommendation,
                "decision_reason": {"vi": "Ung vien phu hop", "en": "Candidate fits"},
                "screening_summary": {
                    "vi": "Phu hop tot voi nen tang backend.",
                    "en": "Strong fit for backend fundamentals.",
                },
                "knockout_assessments": [
                    {
                        "criterion": {
                            "vi": "Bat buoc Python",
                            "en": "Python required",
                        },
                        "status": knockout_status,
                        "reason": {"vi": "Co bang chung", "en": "Evidence exists"},
                        "evidence": [{"vi": "Python", "en": "Python"}],
                    }
                ],
                "minimum_requirement_checks": [],
                "dimension_scores": (
                    dimension_scores
                    if dimension_scores is not None
                    else [
                        sample_dimension_score(weight=0.6, score=0.8),
                        sample_dimension_score(weight=0.4, score=0.85),
                    ]
                ),
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


class FakePhase2CVExtractor:
    """Return a stable Phase 2 candidate profile for service tests."""

    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        """Return a valid Phase 2 candidate profile."""
        _ = (file_path, mime_type)
        return sample_candidate_profile_payload()


class FakePhase2ScreeningInvoker:
    """Return a stable Phase 2 screening payload for service tests."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Return a persisted screening payload fixture."""
        _ = input
        return sample_stored_screening_payload().model_dump(mode="json")


class FakeStructuredProfileInvoker:
    """Return a stable candidate profile for extractor tests."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Return a candidate profile fixture."""
        _ = input
        return sample_candidate_profile_payload().model_dump(mode="json")


class FakeStructuredScreeningInvoker:
    """Return a stable screening payload for adapter tests."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Return a screening payload fixture."""
        _ = input
        return sample_stored_screening_payload().model_dump(mode="json")


def test_build_cv_extraction_prompt_mentions_phase_2_review_artifacts() -> None:
    """Ensure the extraction prompt calls out Phase 2 review requirements."""
    prompt = build_cv_extraction_prompt()

    assert "review-ready" in prompt.lower()
    assert "evidence" in prompt.lower()
    assert "ambiguities" in prompt.lower()
    assert CandidateProfilePayload.__name__ in prompt


@pytest.mark.asyncio
async def test_extractor_validates_phase_2_candidate_profile(tmp_path: Path) -> None:
    """Ensure the extractor validates the Phase 2 candidate profile schema."""
    from src.services.cv_extractor import GeminiCVExtractor

    extractor = GeminiCVExtractor.__new__(GeminiCVExtractor)
    extractor._structured_llm = FakeStructuredProfileInvoker()  # pyright: ignore[reportPrivateUsage]

    file_path = tmp_path / "candidate.pdf"
    _ = file_path.write_bytes(b"%PDF-1.7\ncandidate")

    result = await extractor.extract(file_path, "application/pdf")

    assert result.candidate_summary.full_name == "Nguyen Van A"
    assert result.candidate_summary.seniority_signal == "mid"


def test_build_screening_prompt_mentions_knockouts_and_must_have_rules() -> None:
    """Ensure the screening prompt encodes the Phase 2 screening rules."""
    prompt = build_screening_prompt()

    assert "knockout" in prompt.lower()
    assert "must-have" in prompt.lower()
    assert "structured output" in prompt.lower()
    assert StoredScreeningPayload.__name__ in prompt


@pytest.mark.asyncio
async def test_screening_adapter_validates_stored_screening_payload() -> None:
    """Ensure the screening adapter validates the stored screening schema."""
    service = CVScreeningService.__new__(CVScreeningService)
    service._screening_llm = FakeStructuredScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    payload = await service._generate_screening_payload(  # pyright: ignore[reportPrivateUsage]
        jd_analysis=JDAnalysisPayload.model_validate(sample_jd_analysis_payload()),
        candidate_profile=sample_candidate_profile_payload(),
    )

    assert payload.result.recommendation == "advance"
    assert payload.audit.profile_schema_version == "phase2.v1"


def test_reconcile_screening_downgrades_advance_on_knockout_failure() -> None:
    """Ensure knockout failure forces a reject recommendation."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        recommendation="advance",
        knockout_status="not_met",
        match_score=0.82,
    )

    reconciled = service._reconcile_screening_payload(payload)  # pyright: ignore[reportPrivateUsage]

    assert reconciled.result.recommendation == "reject"
    assert any(
        "knockout" in note.lower()
        for note in reconciled.audit.reconciliation_notes
    )


def test_reconcile_screening_recomputes_match_score_from_dimensions() -> None:
    """Ensure reconciliation recomputes the weighted match score."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        match_score=0.99,
        dimension_scores=[
            sample_dimension_score(weight=0.6, score=0.5),
            sample_dimension_score(weight=0.4, score=0.25),
        ],
    )

    reconciled = service._reconcile_screening_payload(payload)  # pyright: ignore[reportPrivateUsage]

    assert reconciled.result.match_score == 0.4


def test_reconcile_screening_marks_missing_must_have_evidence_as_unclear() -> None:
    """Ensure missing evidence on a must-have dimension downgrades advance."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload(
        recommendation="advance",
        dimension_scores=[
            sample_dimension_score(priority="must_have", score=0.9, evidence=[])
        ],
    )

    reconciled = service._reconcile_screening_payload(payload)  # pyright: ignore[reportPrivateUsage]

    assert reconciled.result.recommendation == "review"
    assert any(
        "must-have" in flag.lower()
        for flag in reconciled.audit.consistency_flags
    )


@pytest.fixture
async def seeded_jd_analysis_id(db_session: AsyncSession) -> str:
    """Seed one completed JD analysis for Phase 2 screening tests."""
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
            analysis_payload=sample_jd_analysis_payload(),
        )
    )
    await db_session.commit()
    return document.id


@pytest.mark.asyncio
async def test_screening_service_persists_phase_2_profile_and_screening(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Ensure the Phase 2 service persists both profile and screening artifacts."""
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    response = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    stored_profile = await db_session.scalar(
        select(CandidateProfile).where(
            CandidateProfile.candidate_document_id == response.candidate_id
        )
    )
    stored_screening = await db_session.scalar(
        select(CandidateScreening).where(
            CandidateScreening.id == response.screening_id
        )
    )

    assert response.candidate_profile.candidate_summary.full_name == "Nguyen Van A"
    assert response.audit.profile_schema_version == "phase2.v1"
    assert stored_profile is not None
    assert stored_screening is not None


@pytest.mark.asyncio
async def test_get_screening_returns_phase_2_response(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Ensure the persisted screening is returned in the new response shape."""
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

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
    tmp_path: Path,
) -> None:
    """Ensure missing JD analysis still fails before screening starts."""
    service = CVScreeningService(
        extractor=FakePhase2CVExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    with pytest.raises(JDNotReadyError, match="JD analysis not found or not ready"):
        _ = await service.screen_upload(
            jd_id="missing-jd-id",
            file_name="candidate.pdf",
            mime_type="application/pdf",
            file_bytes=b"%PDF-1.7\ncandidate",
        )
