"""Schema and model contract tests for CV screening phase 2."""

from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON

from src.config import Settings
from src.models import CandidateDocument, CandidateProfile, CandidateScreening
from src.schemas.cv import (
    AuditMetadata,
    CandidateProfilePayload,
    CVScreeningHistoryResponse,
    CVScreeningResponse,
    FollowUpQuestion,
    KnockoutAssessment,
    RiskFlag,
    ScreeningRecommendation,
)


def test_cv_settings_expose_upload_path_from_directory() -> None:
    """Expose the configured upload directory as a path helper."""
    settings = Settings.model_construct(cv_upload_dir="storage/custom_cv_uploads")

    assert settings.cv_upload_dir == "storage/custom_cv_uploads"
    assert settings.cv_upload_path == Path("storage/custom_cv_uploads")


def test_candidate_profile_columns_enforce_task_1_contract() -> None:
    """Keep candidate profile persistence fields aligned with Task 1."""
    candidate_document_column = CandidateProfile.__table__.c.candidate_document_id
    profile_payload_column = CandidateProfile.__table__.c.profile_payload

    assert not cast(bool, candidate_document_column.nullable)
    assert cast(bool | None, candidate_document_column.unique)
    assert {cast(str, fk.target_fullname) for fk in candidate_document_column.foreign_keys} == {
        "candidate_documents.id"
    }
    assert not cast(bool, profile_payload_column.nullable)
    assert isinstance(profile_payload_column.type, JSON)


def test_candidate_screening_foreign_keys_target_task_1_tables() -> None:
    """Keep screening foreign keys pointed at the Task 1 tables."""
    jd_document_column = CandidateScreening.__table__.c.jd_document_id
    candidate_profile_column = CandidateScreening.__table__.c.candidate_profile_id

    assert {cast(str, fk.target_fullname) for fk in jd_document_column.foreign_keys} == {
        "jd_documents.id"
    }
    assert {cast(str, fk.target_fullname) for fk in candidate_profile_column.foreign_keys} == {
        "candidate_profiles.id"
    }


def test_cv_model_relationship_names_match_task_1_contract() -> None:
    """Keep relationship names stable for downstream CV screening code."""
    candidate_document_relationships = CandidateDocument.__mapper__.relationships.keys()
    candidate_profile_relationships = CandidateProfile.__mapper__.relationships.keys()
    candidate_screening_relationships = CandidateScreening.__mapper__.relationships.keys()

    assert "profile" in candidate_document_relationships
    assert "document" in candidate_profile_relationships
    assert "screenings" in candidate_profile_relationships
    assert "candidate_profile" in candidate_screening_relationships


def test_candidate_profile_requires_phase_2_sections() -> None:
    """Reject candidate profiles that omit required Phase 2 sections."""
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
    """Reject knockout statuses outside the enum contract."""
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
    """Reject risk severities outside the enum contract."""
    with pytest.raises(ValidationError):
        _ = RiskFlag.model_validate(
            {
                "title": {"vi": "Rủi ro", "en": "Risk"},
                "reason": {"vi": "Lý do", "en": "Reason"},
                "severity": "critical",
            }
        )


def test_audit_metadata_requires_schema_versions() -> None:
    """Require both schema versions in the audit payload."""
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
    """Reject screening responses missing Phase 2 top-level sections."""
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
    """Allow follow-up questions that are not tied to a single rubric dimension."""
    question = FollowUpQuestion.model_validate(
        {
            "question": {
                "vi": "Bạn đã dùng Python ở đâu?",
                "en": "Where did you use Python?",
            },
            "purpose": {"vi": "Xác minh kinh nghiệm", "en": "Verify experience"},
            "linked_dimension": None,
        }
    )

    assert question.linked_dimension is None


def test_screening_recommendation_enum_values_are_stable() -> None:
    """Keep recommendation enum values stable for API consumers."""
    assert ScreeningRecommendation.ADVANCE == "advance"
    assert ScreeningRecommendation.REVIEW == "review"
    assert ScreeningRecommendation.REJECT == "reject"


def test_cv_screening_history_response_validates() -> None:
    """Validate the lightweight history response for saved screenings."""
    payload = {
        "items": [
            {
                "screening_id": "screening-1",
                "jd_id": "jd-1",
                "candidate_id": "candidate-1",
                "file_name": "candidate.pdf",
                "created_at": "2026-04-16T10:00:00+00:00",
                "recommendation": "review",
                "match_score": 0.76,
            }
        ]
    }

    validated = CVScreeningHistoryResponse.model_validate(payload)

    assert validated.items[0].screening_id == "screening-1"
    assert validated.items[0].recommendation == "review"
