"""CV schema tests."""

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
