"""Schemas."""

from src.schemas.auth import GoogleTokenRequest as GoogleAuthRequest
from src.schemas.auth import TokenResponse
from src.schemas.cv import (
    CandidateProfilePayload,
    CVScreeningPayload,
    CVScreeningResponse,
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
