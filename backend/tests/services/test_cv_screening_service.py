"""CV screening service contract tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import (
    CandidateProfilePayload,
    CVScreeningEnqueueResponse,
    StoredScreeningPayload,
)
from src.schemas.jd import JDAnalysisPayload
from src.services.cv_extractor import build_cv_extraction_prompt
from src.services.cv_screening_service import (
    CVScreeningService,
    JDNotReadyError,
    build_screening_prompt,
)


def sample_candidate_profile_payload(
    *,
    profile_uncertainties: list[dict[str, object]] | None = None,
) -> CandidateProfilePayload:
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
            "profile_uncertainties": profile_uncertainties or [],
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


def sample_legacy_screening_payload() -> dict[str, object]:
    """Build a legacy screening payload fixture with stale review artifacts."""
    return {
        "match_score": 0.61,
        "recommendation": "review",
        "decision_reason": {
            "vi": "Can xac minh them.",
            "en": "Needs more verification.",
        },
        "screening_summary": {
            "vi": "Ban ghi cu khong con dang tin cay.",
            "en": "This legacy record is no longer trustworthy as-is.",
        },
        "knockout_assessments": [],
        "minimum_requirement_checks": [],
        "dimension_scores": [],
        "strengths": [],
        "gaps": [],
        "uncertainties": [],
        "follow_up_questions": [
            {
                "question": {
                    "vi": "Ban co the lam full-time khong?",
                    "en": "Can you work full-time?",
                },
                "purpose": {
                    "vi": "Du lieu cu.",
                    "en": "Legacy-only content.",
                },
            }
        ],
        "risk_flags": [
            {
                "title": {"vi": "Rui ro cu", "en": "Legacy risk"},
                "reason": {
                    "vi": "Khong con dang tin cay.",
                    "en": "No longer trustworthy.",
                },
                "severity": "medium",
            }
        ],
        "audit": {
            "extraction_model": "gpt-4o",
            "screening_model": "gpt-4o",
            "profile_schema_version": "1.0",
            "screening_schema_version": "1.0",
            "generated_at": "2025-05-20T10:00:00Z",
            "reconciliation_notes": [
                "Corrected May 2025 start date to a potential typo in analysis.",
            ],
            "consistency_flags": [],
        },
    }


def sample_legacy_profile_payload() -> dict[str, object]:
    """Build a legacy candidate profile payload fixture."""
    return {
        "skills": ["JavaScript", "Python", "Redis"],
        "education": [
            {
                "degree": "Bachelor of Information Technology",
                "institution": "Hanoi University of Industry",
                "field_of_study": "Information Technology",
            }
        ],
        "languages": ["Vietnamese", "English"],
        "experience": [
            {
                "role": "Full-Stack Engineer",
                "company": "Swork JSC",
                "summary": [
                    "Built AI workflows.",
                    "Owned the full-stack delivery.",
                ],
            }
        ],
        "certifications": [],
        "candidate_summary": {
            "location": "Hanoi, Vietnam",
            "full_name": "NGUYEN VIET LINH",
            "current_title": "AI Engineer",
            "years_of_experience": 1.5,
        },
        "projects_or_achievements": [
            "ATrips – AI Travel Planning Platform",
            "Built SSE streaming for AI responses.",
        ],
    }


def sample_current_shape_legacy_screening_payload() -> dict[str, object]:
    """Build a current-shape payload that still carries stale legacy review data."""
    payload = sample_stored_screening_payload().model_dump(mode="json")
    payload["result"]["follow_up_questions"] = [
        {
            "question": {
                "vi": "Ban co the lam full-time khong?",
                "en": "Can you work full-time?",
            },
            "purpose": {
                "vi": "Du lieu cu.",
                "en": "Legacy-only content.",
            },
            "linked_dimension": None,
        }
    ]
    payload["result"]["risk_flags"] = [
        {
            "title": {"vi": "Rui ro cu", "en": "Legacy risk"},
            "reason": {
                "vi": "Khong con dang tin cay.",
                "en": "No longer trustworthy.",
            },
            "severity": "medium",
        }
    ]
    payload["audit"] = {
        "extraction_model": "gpt-4o",
        "screening_model": "gpt-4o",
        "profile_schema_version": "1.0",
        "screening_schema_version": "1.0",
        "generated_at": "2025-05-20T10:00:00Z",
        "reconciliation_notes": [
            "Corrected May 2025 start date to a potential typo in analysis.",
        ],
        "consistency_flags": [],
    }
    return payload


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


class CaptureStructuredScreeningInvoker:
    """Capture screening prompt inputs for assertions."""

    def __init__(self) -> None:
        self.calls: list[list[HumanMessage]] = []

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Record the request and return a valid screening payload."""
        self.calls.append(input)
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
    assert "current vietnam datetime" in prompt.lower()
    assert "past year" in prompt.lower()
    assert StoredScreeningPayload.__name__ in prompt


@pytest.mark.asyncio
async def test_screening_adapter_validates_stored_screening_payload(tmp_path: Path) -> None:
    """Ensure the screening adapter validates the stored screening schema."""
    service = CVScreeningService.__new__(CVScreeningService)
    service._screening_llm = FakeStructuredScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    file_path = tmp_path / "candidate.pdf"
    _ = file_path.write_bytes(b"%PDF-1.7\ncandidate")
    payload = await service._generate_screening_payload(  # pyright: ignore[reportPrivateUsage]
        jd_analysis=JDAnalysisPayload.model_validate(sample_jd_analysis_payload()),
        file_path=file_path,
        mime_type="application/pdf",
    )

    assert payload.result.recommendation == "advance"
    assert payload.audit.profile_schema_version == "phase2.v1"


@pytest.mark.asyncio
async def test_generate_screening_payload_includes_authoritative_current_datetime(
    tmp_path: Path,
) -> None:
    """Send the concrete current Vietnam datetime into the model context."""
    service = CVScreeningService.__new__(CVScreeningService)
    capture = CaptureStructuredScreeningInvoker()
    service._screening_llm = capture  # pyright: ignore[reportPrivateUsage]

    file_path = tmp_path / "candidate.pdf"
    _ = file_path.write_bytes(b"%PDF-1.7\ncandidate")
    await service._generate_screening_payload(  # pyright: ignore[reportPrivateUsage]
        jd_analysis=JDAnalysisPayload.model_validate(sample_jd_analysis_payload()),
        file_path=file_path,
        mime_type="application/pdf",
    )

    assert capture.calls
    content = capture.calls[0][0].content
    assert isinstance(content, list)
    assert any(
        part.get("type") == "text"
        and "authoritative current vietnam datetime:" in str(part.get("text", "")).lower()
        for part in content
        if isinstance(part, dict)
    )


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


def test_reconcile_screening_removes_stale_future_timeline_uncertainty() -> None:
    """Remove timeline anomalies that are no longer future-dated."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload()
    payload = payload.model_copy(
        update={
            "candidate_profile": sample_candidate_profile_payload(
                profile_uncertainties=[
                    {
                        "title": {
                            "vi": "Mâu thuẫn về thời gian",
                            "en": "Timeline Anomaly",
                        },
                        "reason": {
                            "vi": "Work experience dates are listed as 2025 and 2026.",
                            "en": (
                                "Work experience dates are listed as 2025 and 2026, "
                                "which are in the future relative to current standard "
                                "screening periods."
                            ),
                        },
                        "impact": {
                            "vi": "Cần xác minh lại.",
                            "en": "Need to verify the timeline.",
                        },
                    }
                ]
            )
        },
        deep=True,
    )

    reconciled = service._reconcile_screening_payload(payload)  # pyright: ignore[reportPrivateUsage]

    assert reconciled.candidate_profile.profile_uncertainties == []
    assert any(
        "stale future-date timeline uncertainty" in note.lower()
        for note in reconciled.audit.reconciliation_notes
    )


def test_normalize_current_payload_overrides_untrusted_audit_metadata() -> None:
    """Use database metadata as the source of truth for current-shape payloads too."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload().model_dump(mode="json")
    payload["audit"] = {
        "extraction_model": "gpt-4o",
        "screening_model": "gpt-4o",
        "profile_schema_version": "phase2.v1",
        "screening_schema_version": "phase2.v2",
        "generated_at": "2024-05-22T10:00:00Z",
        "reconciliation_notes": [],
        "consistency_flags": [],
    }

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=payload,
        candidate_profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
        model_name="gemini-3-flash-preview",
        created_at=datetime(2026, 4, 19, 6, 0, 40, tzinfo=UTC),
    )

    assert normalized.audit.extraction_model == "gemini-3-flash-preview"
    assert normalized.audit.screening_model == "gemini-3-flash-preview"
    assert normalized.audit.generated_at == "2026-04-19T13:00:40+07:00"


def test_normalize_current_payload_removes_stale_future_timeline_review_artifacts() -> None:
    """Drop stale timeline warnings when the referenced year is no longer in the future."""
    service = CVScreeningService.__new__(CVScreeningService)
    payload = sample_stored_screening_payload().model_dump(mode="json")
    payload["candidate_profile"] = sample_candidate_profile_payload(
        profile_uncertainties=[
            {
                "title": {
                    "vi": "Mốc thời gian không nhất quán",
                    "en": "Timeline Inconsistency",
                },
                "reason": {
                    "vi": "Kinh nghiệm làm việc được ghi bắt đầu vào năm 2025, trong khi hiện tại là năm 2024.",
                    "en": "Work experience is listed as starting in 2025, while the current year is 2024.",
                },
                "impact": {
                    "vi": "Cần xác minh lại mốc thời gian.",
                    "en": "Need to verify the timeline.",
                },
            }
        ]
    ).model_dump(mode="json")
    payload["candidate_profile"]["work_experience"][0]["ambiguity_notes"] = [
        "The start date (May 2025) is in the future relative to the current date (May 2024)."
    ]
    payload["result"]["risk_flags"] = [
        {
            "title": {
                "vi": "Sai lệch thông tin thời gian",
                "en": "Timeline Discrepancy",
            },
            "reason": {
                "vi": "Ghi nhận kinh nghiệm làm việc bắt đầu từ tháng 5/2025 (tương lai).",
                "en": "Recorded work experience starting from May 2025 (future).",
            },
            "severity": "medium",
        }
    ]
    payload["audit"] = {
        "extraction_model": "gpt-4o",
        "screening_model": "gpt-4o",
        "profile_schema_version": "phase2.v1",
        "screening_schema_version": "phase2.v2",
        "generated_at": "2024-05-22T10:00:00Z",
        "reconciliation_notes": [
            "Dates in CV (2025) were treated as potential typos or future projections given the current date is May 2024."
        ],
        "consistency_flags": [
            "Role mismatch: Candidate is an Engineer applying for a BA role."
        ],
    }

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=payload,
        candidate_profile_payload=payload["candidate_profile"],
        model_name="gemini-3-flash-preview",
        created_at=datetime(2026, 4, 19, 6, 0, 40, tzinfo=UTC),
    )

    assert normalized.candidate_profile.profile_uncertainties == []
    assert normalized.candidate_profile.work_experience[0].ambiguity_notes == []
    assert normalized.result.risk_flags == []
    assert not any(
        "current date is may 2024" in note.lower()
        for note in normalized.audit.reconciliation_notes
    )
    assert normalized.audit.consistency_flags == [
        "Role mismatch: Candidate is an Engineer applying for a BA role."
    ]
    assert any(
        "stale future-date timeline" in note.lower()
        for note in normalized.audit.reconciliation_notes
    )


def test_normalize_stored_screening_payload_sanitizes_legacy_content() -> None:
    """Ensure legacy payloads are normalized before the API uses them."""
    service = CVScreeningService.__new__(CVScreeningService)
    candidate_profile = sample_candidate_profile_payload()

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=sample_legacy_screening_payload(),
        candidate_profile_payload=candidate_profile.model_dump(mode="json"),
        model_name="gemini-2.5-pro",
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    assert normalized.candidate_profile == candidate_profile
    assert normalized.result.follow_up_questions == []
    assert normalized.result.risk_flags == []
    assert normalized.audit.extraction_model == "gemini-2.5-pro"
    assert normalized.audit.screening_model == "gemini-2.5-pro"
    assert normalized.audit.generated_at == "2026-04-16T07:00:00+07:00"
    assert any(
        "legacy" in note.lower()
        for note in normalized.audit.reconciliation_notes
    )


def test_normalize_stored_screening_payload_accepts_legacy_profile_payload() -> None:
    """Ensure legacy candidate profiles are adapted before screening normalization."""
    service = CVScreeningService.__new__(CVScreeningService)

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=sample_legacy_screening_payload(),
        candidate_profile_payload=sample_legacy_profile_payload(),
        model_name="gemini-2.5-pro",
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    assert normalized.candidate_profile.candidate_summary.full_name == "NGUYEN VIET LINH"
    assert normalized.candidate_profile.candidate_summary.total_years_experience == 1.5
    assert normalized.candidate_profile.candidate_summary.seniority_signal == "unknown"
    assert normalized.candidate_profile.skills_inventory[0].skill_name == "JavaScript"
    assert normalized.candidate_profile.languages[0].language_name == "Vietnamese"


def test_normalize_stored_screening_payload_sanitizes_legacy_schema_versions() -> None:
    """Ensure current-shape payloads with legacy schema versions are sanitized too."""
    service = CVScreeningService.__new__(CVScreeningService)
    candidate_profile = sample_candidate_profile_payload()

    normalized = service._normalize_stored_screening_payload(  # pyright: ignore[reportPrivateUsage]
        screening_payload=sample_current_shape_legacy_screening_payload(),
        candidate_profile_payload=candidate_profile.model_dump(mode="json"),
        model_name="gemini-2.5-pro",
        created_at=datetime(2026, 4, 16, tzinfo=UTC),
    )

    assert normalized.result.follow_up_questions == []
    assert normalized.result.risk_flags == []
    assert normalized.audit.extraction_model == "gemini-2.5-pro"
    assert normalized.audit.generated_at == "2026-04-16T07:00:00+07:00"
    assert normalized.audit.profile_schema_version == "phase2.v1"
    assert normalized.audit.screening_schema_version == "phase2.v2"


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
async def test_enqueue_screening_creates_processing_screening_and_job(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Enqueueing screening should persist a processing screening and job."""
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

    assert isinstance(response, CVScreeningEnqueueResponse)
    assert response.status == "processing"
    assert screening is not None
    assert screening.status == "processing"
    assert job is not None
    assert job.job_type == "cv_screening"


@pytest.mark.asyncio
async def test_run_cv_job_completes_screening(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Running a CV job should persist a completed screening result."""
    service = CVScreeningService(
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


@pytest.mark.asyncio
async def test_mark_screening_failed_sets_screening_and_document_failed(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Marking a screening failed should update both screening and document."""
    service = CVScreeningService(upload_dir=tmp_path, db_session=db_session)
    response = await service.enqueue_screening_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    await service.mark_screening_failed(response.screening_id, "Gemini timeout")

    screening = await db_session.scalar(
        select(CandidateScreening).where(CandidateScreening.id == response.screening_id)
    )
    profile = await db_session.scalar(
        select(CandidateProfile).where(CandidateProfile.id == screening.candidate_profile_id)
    )
    document = await db_session.scalar(
        select(CandidateDocument).where(CandidateDocument.id == profile.candidate_document_id)
    )

    assert screening is not None
    assert profile is not None
    assert document is not None
    assert screening.status == "failed"
    assert document.status == "failed"
    assert screening.screening_payload == {}


@pytest.mark.asyncio
async def test_screening_service_persists_phase_2_profile_and_screening(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Ensure the Phase 2 service persists both profile and screening artifacts."""
    service = CVScreeningService(
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
    assert response.audit.screening_schema_version == "phase2.v2"
    assert stored_profile is not None
    assert stored_screening is not None
    assert stored_profile.profile_payload["candidate_summary"]["full_name"] == "Nguyen Van A"


@pytest.mark.asyncio
async def test_get_screening_returns_processing_response_for_inflight_row(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Return lightweight metadata for screenings that have not completed yet."""
    service = CVScreeningService(upload_dir=tmp_path, db_session=db_session)
    created = await service.enqueue_screening_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )

    fetched = await service.get_screening(created.screening_id)

    assert fetched is not None
    assert fetched.status == "processing"
    assert fetched.result is None
    assert fetched.audit is None


@pytest.mark.asyncio
async def test_get_screening_returns_phase_2_response(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Ensure the persisted screening is returned in the new response shape."""
    service = CVScreeningService(
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
async def test_list_screenings_for_jd_returns_newest_first(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Return persisted screenings for one JD in reverse chronological order."""
    service = CVScreeningService(
        upload_dir=tmp_path,
        db_session=db_session,
    )
    service._screening_llm = FakePhase2ScreeningInvoker()  # pyright: ignore[reportPrivateUsage]

    older = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="older.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\nolder",
    )
    newer = await service.screen_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="newer.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\nnewer",
    )

    items = await service.list_screenings_for_jd(seeded_jd_analysis_id)

    assert [item.screening_id for item in items] == [newer.screening_id, older.screening_id]
    assert items[0].file_name == "newer.pdf"
    assert items[0].recommendation == newer.result.recommendation
    assert items[0].match_score == newer.result.match_score


@pytest.mark.asyncio
async def test_list_screenings_for_jd_supports_legacy_screening_payload(
    db_session: AsyncSession,
    seeded_jd_analysis_id: str,
) -> None:
    """Return history items even when older screenings use the legacy payload shape."""
    candidate_document = CandidateDocument(
        file_name="legacy.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/legacy.pdf",
        status="completed",
    )
    db_session.add(candidate_document)
    await db_session.flush()

    candidate_profile = CandidateProfile(
        candidate_document_id=candidate_document.id,
        profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    legacy_screening = CandidateScreening(
        jd_document_id=seeded_jd_analysis_id,
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        screening_payload={
            "match_score": 0.61,
            "recommendation": "review",
            "decision_reason": {
                "vi": "Payload cũ vẫn còn trong DB",
                "en": "Legacy payload still exists in the database",
            },
            "gaps": [],
        },
    )
    db_session.add(legacy_screening)
    await db_session.commit()

    service = CVScreeningService(db_session=db_session)
    items = await service.list_screenings_for_jd(seeded_jd_analysis_id)

    assert any(item.screening_id == legacy_screening.id for item in items)
    legacy_item = next(item for item in items if item.screening_id == legacy_screening.id)
    assert legacy_item.recommendation == "review"
    assert legacy_item.match_score == 0.61
    assert legacy_item.file_name == "legacy.pdf"


@pytest.mark.asyncio
async def test_get_screening_normalizes_legacy_payload(
    db_session: AsyncSession,
) -> None:
    """Ensure detail loading sanitizes legacy screening records."""
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
        profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id="jd-1",
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        status="completed",
        screening_payload=sample_legacy_screening_payload(),
    )
    db_session.add(screening)
    await db_session.commit()

    service = CVScreeningService(upload_dir=Path("/tmp"), db_session=db_session)
    result = await service.get_screening(screening.id)

    assert result is not None
    assert result.audit.extraction_model == "gemini-2.5-pro"
    assert result.result.follow_up_questions == []
    assert result.result.risk_flags == []


@pytest.mark.asyncio
async def test_get_screening_returns_failed_response_with_job_error(
    db_session: AsyncSession,
    tmp_path: Path,
    seeded_jd_analysis_id: str,
) -> None:
    """Return failed metadata and job error for a failed screening."""
    service = CVScreeningService(upload_dir=tmp_path, db_session=db_session)
    created = await service.enqueue_screening_upload(
        jd_id=seeded_jd_analysis_id,
        file_name="candidate.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\ncandidate",
    )
    await service.mark_screening_failed(created.screening_id, "Gemini timeout")
    job = await db_session.scalar(select(BackgroundJob).where(BackgroundJob.id == created.job_id))
    assert job is not None
    job.status = "failed"
    job.error_message = "Gemini timeout"
    await db_session.commit()

    fetched = await service.get_screening(created.screening_id)

    assert fetched is not None
    assert fetched.status == "failed"
    assert fetched.error_message == "Gemini timeout"
    assert fetched.result is None


@pytest.mark.asyncio
async def test_backfill_legacy_screening_payload_updates_stored_row(
    db_session: AsyncSession,
) -> None:
    """Ensure backfill rewrites a legacy payload into the current stored shape."""
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
        profile_payload=sample_candidate_profile_payload().model_dump(mode="json"),
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id="jd-1",
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        screening_payload=sample_legacy_screening_payload(),
    )
    db_session.add(screening)
    await db_session.commit()

    service = CVScreeningService(upload_dir=Path("/tmp"), db_session=db_session)

    changed = await service.backfill_screening_payload(screening.id)
    await db_session.refresh(screening)

    assert changed is True
    assert "candidate_profile" in screening.screening_payload
    assert screening.screening_payload["result"]["follow_up_questions"] == []


@pytest.mark.asyncio
async def test_screening_service_raises_when_jd_is_missing(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Ensure missing JD analysis still fails before screening starts."""
    service = CVScreeningService(
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
