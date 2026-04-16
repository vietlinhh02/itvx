"""Schemas."""

from src.schemas.auth import GoogleTokenRequest as GoogleAuthRequest, TokenResponse
from src.schemas.cv import (
    CVScreeningPayload,
    CVScreeningResponse,
    CandidateProfilePayload,
    MinimumRequirementCheck,
    RequirementStatus,
    ScreeningRecommendation,
)
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse, JDRecentItem
from src.schemas.user import UserResponse

__all__ = [
    "CVScreeningPayload",
    "CVScreeningResponse",
    "CandidateProfilePayload",
    "GoogleAuthRequest",
    "JDAnalysisPayload",
    "JDAnalysisResponse",
    "JDRecentItem",
    "MinimumRequirementCheck",
    "RequirementStatus",
    "ScreeningRecommendation",
    "TokenResponse",
    "UserResponse",
]
