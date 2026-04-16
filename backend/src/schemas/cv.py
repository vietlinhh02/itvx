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


__all__ = [
    "CVScreeningPayload",
    "CVScreeningResponse",
    "CandidateProfilePayload",
    "CandidateSummary",
    "DimensionScore",
    "EducationItem",
    "ExperienceItem",
    "MinimumRequirementCheck",
    "RequirementStatus",
    "ScreeningInsight",
    "ScreeningRecommendation",
    "ScreeningUncertainty",
]
