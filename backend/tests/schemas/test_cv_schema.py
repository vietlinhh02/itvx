"""Schema and model contract tests for CV screening phase 2."""

from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import JSON

from src.config import Settings
from src.models import CandidateDocument, CandidateProfile, CandidateScreening


def test_cv_settings_expose_upload_path_from_directory() -> None:
    """Expose the configured upload directory as a Path helper."""
    settings = Settings(_env_file=None, cv_upload_dir="storage/custom_cv_uploads")

    assert settings.cv_upload_dir == "storage/custom_cv_uploads"
    assert settings.cv_upload_path == Path("storage/custom_cv_uploads")


def test_candidate_profile_columns_enforce_task_1_contract() -> None:
    """Keep candidate profile persistence fields aligned with Task 1."""
    candidate_document_column = CandidateProfile.__table__.c.candidate_document_id
    profile_payload_column = CandidateProfile.__table__.c.profile_payload

    assert not candidate_document_column.nullable
    assert candidate_document_column.unique
    assert {fk.target_fullname for fk in candidate_document_column.foreign_keys} == {
        "candidate_documents.id"
    }

    assert not profile_payload_column.nullable
    assert isinstance(profile_payload_column.type, JSON)


def test_candidate_screening_foreign_keys_target_task_1_tables() -> None:
    """Keep screening foreign keys pointed at the Task 1 tables."""
    jd_document_column = CandidateScreening.__table__.c.jd_document_id
    candidate_profile_column = CandidateScreening.__table__.c.candidate_profile_id

    assert {fk.target_fullname for fk in jd_document_column.foreign_keys} == {"jd_documents.id"}
    assert {fk.target_fullname for fk in candidate_profile_column.foreign_keys} == {
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


def test_minimum_requirement_check_rejects_invalid_status() -> None:
    """Reject minimum requirement statuses outside the enum contract."""
    with pytest.raises(ValidationError):
        from src.schemas.cv import MinimumRequirementCheck

        MinimumRequirementCheck(
            criterion={"vi": "Có Python", "en": "Has Python"},
            status="invalid",
            reason={"vi": "Không hợp lệ", "en": "Invalid"},
            evidence=[],
        )


def test_cv_screening_payload_rejects_match_score_out_of_range() -> None:
    """Reject screening payloads with match scores outside 0.0 to 1.0."""
    with pytest.raises(ValidationError):
        from src.schemas.cv import CVScreeningPayload

        CVScreeningPayload(
            match_score=1.1,
            recommendation="review",
            decision_reason={"vi": "Cần xem xét", "en": "Needs review"},
            minimum_requirement_checks=[],
            dimension_scores=[],
            strengths=[],
            gaps=[],
            uncertainties=[],
        )


def test_screening_recommendation_enum_values_are_stable() -> None:
    """Keep recommendation enum values stable for API consumers."""
    from src.schemas.cv import ScreeningRecommendation

    assert ScreeningRecommendation.ADVANCE.value == "advance"
    assert ScreeningRecommendation.REVIEW.value == "review"
    assert ScreeningRecommendation.REJECT.value == "reject"
