"""JD schema and model tests."""

from collections.abc import Callable
from datetime import datetime
from typing import cast

import pytest
from pydantic import ValidationError

from src.models import JDAnalysis, JDDocument
from src.models.base import TimestampMixin
from src.schemas.jd import BilingualText, EvaluationDimension, JDAnalysisPayload


def test_jd_models_are_exported() -> None:
    """JD models should be exported from the models package."""
    assert JDDocument.__tablename__ == "jd_documents"
    assert JDAnalysis.__tablename__ == "jd_analyses"


def test_bilingual_text_requires_vi_and_en() -> None:
    """Bilingual text should reject payloads missing one language."""
    with pytest.raises(ValidationError):
        _ = BilingualText.model_validate({"vi": "Ky su Backend"})


def test_jd_analysis_payload_accepts_bilingual_hr_facing_fields() -> None:
    """HR-facing requirement fields should accept bilingual values."""
    payload = JDAnalysisPayload.model_validate(
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
                    "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                    "preferred_domains": [
                        {"vi": "Tai chinh", "en": "Finance"},
                    ],
                },
                "education_and_certifications": [
                    {"vi": "Cu nhan CNTT", "en": "BS in Computer Science"},
                ],
                "language_requirements": [
                    {"vi": "Tieng Anh giao tiep", "en": "Conversational English"},
                ],
                "key_responsibilities": [],
                "screening_knockout_criteria": [
                    {"vi": "Khong co kinh nghiem Python", "en": "No Python experience"},
                ],
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
                        "weight": 0.2,
                        "evidence_signals": [{"vi": "Query", "en": "Query"}],
                    },
                    {
                        "name": {"vi": "API", "en": "API"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "important",
                        "weight": 0.1,
                        "evidence_signals": [{"vi": "REST", "en": "REST"}],
                    },
                    {
                        "name": {"vi": "Cloud", "en": "Cloud"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "nice_to_have",
                        "weight": 0.1,
                        "evidence_signals": [{"vi": "AWS", "en": "AWS"}],
                    },
                ],
                "screening_rules": {
                    "minimum_requirements": [
                        {"vi": "3 nam kinh nghiem", "en": "3 years of experience"},
                    ],
                    "scoring_principle": {
                        "vi": "Khong bu tru must-have bang nice-to-have",
                        "en": "Nice-to-have cannot replace must-have",
                    },
                },
                "ambiguities_for_human_review": [],
            },
        }
    )

    relevant_role = payload.requirements.experience_requirements.relevant_roles[0]
    scoring_principle = payload.rubric_seed.screening_rules.scoring_principle

    assert isinstance(relevant_role, BilingualText)
    assert isinstance(scoring_principle, BilingualText)
    assert relevant_role.vi == "Ky su Backend"
    assert scoring_principle.en == "Nice-to-have cannot replace must-have"


def test_evaluation_dimension_rejects_invalid_priority() -> None:
    """Evaluation dimensions should reject unsupported priority values."""
    with pytest.raises(ValidationError):
        _ = EvaluationDimension.model_validate(
            {
                "name": {"vi": "Ky nang Python", "en": "Python Skill"},
                "description": {"vi": "Mo ta", "en": "Description"},
                "priority": "critical",
                "weight": 0.5,
                "evidence_signals": [{"vi": "Da lam API", "en": "Built APIs"}],
            }
        )


def test_jd_analysis_payload_requires_weights_to_sum_to_one() -> None:
    """Rubric dimensions should reject weight totals that do not sum to one."""
    with pytest.raises(ValidationError):
        _ = JDAnalysisPayload.model_validate(
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
                        {
                            "name": {"vi": "API", "en": "API"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "REST", "en": "REST"}],
                        },
                        {
                            "name": {"vi": "Cloud", "en": "Cloud"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "nice_to_have",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "AWS", "en": "AWS"}],
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


def test_timestamp_mixin_uses_naive_utc_defaults() -> None:
    """Timestamp defaults should match TIMESTAMP WITHOUT TIME ZONE columns."""
    created_default_factory = cast(
        Callable[[object | None], datetime],
        TimestampMixin.created_at.column.default.arg,  # pyright: ignore[reportAny]
    )
    updated_default_factory = cast(
        Callable[[object | None], datetime],
        TimestampMixin.updated_at.column.default.arg,  # pyright: ignore[reportAny]
    )
    created_at_default = created_default_factory(None)
    updated_at_default = updated_default_factory(None)

    assert created_at_default.tzinfo is None
    assert updated_at_default.tzinfo is None
