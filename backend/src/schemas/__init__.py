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
