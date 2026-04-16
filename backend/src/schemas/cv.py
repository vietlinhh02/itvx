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
