"""Schemas for JD analysis."""

from typing import ClassVar, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BilingualText(BaseModel):
    """Human-readable text available in Vietnamese and English."""

    vi: str = Field(min_length=1)
    en: str = Field(min_length=1)


type HumanReadableText = str | BilingualText


class JobOverview(BaseModel):
    """High-level job metadata for HR review."""

    job_title: BilingualText
    department: BilingualText
    seniority_level: Literal["intern", "junior", "mid", "senior", "lead", "manager", "unknown"]
    location: BilingualText
    work_mode: Literal["onsite", "hybrid", "remote", "unknown"]
    role_summary: BilingualText
    company_benefits: list[BilingualText]


class ExperienceRequirements(BaseModel):
    """Experience requirements extracted from the JD."""

    minimum_years: int | None = Field(default=None, ge=0)
    relevant_roles: list[HumanReadableText]
    preferred_domains: list[HumanReadableText]


class Requirements(BaseModel):
    """Structured hiring requirements for screening."""

    required_skills: list[str]
    preferred_skills: list[str]
    tools_and_technologies: list[str]
    experience_requirements: ExperienceRequirements
    education_and_certifications: list[HumanReadableText]
    language_requirements: list[HumanReadableText]
    key_responsibilities: list[BilingualText]
    screening_knockout_criteria: list[HumanReadableText]


class EvaluationDimension(BaseModel):
    """A weighted screening dimension derived from the JD."""

    name: BilingualText
    description: BilingualText
    priority: Literal["must_have", "important", "nice_to_have"]
    weight: float = Field(gt=0, le=1)
    evidence_signals: list[BilingualText]


class ScreeningRules(BaseModel):
    """Rules that govern early candidate screening."""

    minimum_requirements: list[HumanReadableText]
    scoring_principle: HumanReadableText


class RubricSeed(BaseModel):
    """Scoring blueprint used by downstream candidate screening."""

    evaluation_dimensions: list[EvaluationDimension]
    screening_rules: ScreeningRules
    ambiguities_for_human_review: list[BilingualText]

    @model_validator(mode="after")
    def validate_dimensions(self) -> Self:
        """Validate rubric dimension count, weights, and must-have coverage."""
        total_weight = sum(item.weight for item in self.evaluation_dimensions)
        if not 4 <= len(self.evaluation_dimensions) <= 6:
            raise ValueError("evaluation_dimensions must contain between 4 and 6 items")
        if round(total_weight, 6) != 1.0:
            raise ValueError("evaluation_dimensions weights must sum to 1.0")
        if not any(item.priority == "must_have" for item in self.evaluation_dimensions):
            raise ValueError("at least one evaluation dimension must be must_have")
        return self


class JDAnalysisPayload(BaseModel):
    """Top-level structured output returned by Gemini."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    job_overview: JobOverview
    requirements: Requirements
    rubric_seed: RubricSeed


class JDAnalysisEnqueueResponse(BaseModel):
    """API response for an enqueued JD analysis job."""

    job_id: str
    jd_id: str
    file_name: str
    status: Literal["processing"]


class JDAnalysisResponse(BaseModel):
    """API response for a completed JD analysis."""

    jd_id: str
    file_name: str
    status: Literal["completed"]
    created_at: str
    analysis: JDAnalysisPayload


class JDRecentItem(BaseModel):
    """Compact JD summary for recent upload lists."""

    jd_id: str
    file_name: str
    status: str
    created_at: str
    job_title: str | None = None


class JDCompanyDocumentItem(BaseModel):
    """Persisted company knowledge document metadata for one JD."""

    document_id: str
    jd_id: str
    file_name: str
    status: str
    chunk_count: int = Field(ge=0)
    error_message: str | None = None
    created_at: str


class JDCompanyDocumentListResponse(BaseModel):
    """Company knowledge document list for one JD."""

    items: list[JDCompanyDocumentItem]


class JDCompanyDocumentUploadResponse(BaseModel):
    """Response for an enqueued company document upload."""

    job_id: str
    document: JDCompanyDocumentItem


class JDCompanyKnowledgeCitation(BaseModel):
    """Citation metadata for one retrieved knowledge chunk."""

    chunk_id: str
    document_id: str
    file_name: str
    section_title: str | None = None
    page_number: int | None = None
    excerpt: str


class JDCompanyKnowledgeQueryRequest(BaseModel):
    """Question used to query JD-scoped company knowledge."""

    query: str = Field(min_length=1)


class JDCompanyKnowledgeQueryResponse(BaseModel):
    """Retrieved citations for a company knowledge question."""

    query: str
    citations: list[JDCompanyKnowledgeCitation]


__all__ = [
    "BilingualText",
    "EvaluationDimension",
    "ExperienceRequirements",
    "HumanReadableText",
    "JDAnalysisEnqueueResponse",
    "JDAnalysisPayload",
    "JDAnalysisResponse",
    "JDCompanyDocumentItem",
    "JDCompanyDocumentListResponse",
    "JDCompanyDocumentUploadResponse",
    "JDCompanyKnowledgeCitation",
    "JDCompanyKnowledgeQueryRequest",
    "JDCompanyKnowledgeQueryResponse",
    "JDRecentItem",
    "JobOverview",
    "Requirements",
    "RubricSeed",
    "ScreeningRules",
]
