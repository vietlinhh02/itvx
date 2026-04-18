from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_active_user
from src.config import settings
from src.database import get_db
from src.models.user import User
from src.schemas.interview import (
    CandidateJoinPreviewResponse,
    CandidateJoinRequest,
    CandidateJoinResponse,
    CompleteInterviewRequest,
    GenerateInterviewQuestionsRequest,
    GenerateInterviewQuestionsResponse,
    InterviewFeedbackPolicyCollectionResponse,
    InterviewFeedbackPolicyResponse,
    InterviewFeedbackRequest,
    InterviewFeedbackResponse,
    InterviewFeedbackSummaryResponse,
    InterviewRuntimeEventRequest,
    InterviewSchedulePayload,
    InterviewSessionDetailResponse,
    InterviewSessionReviewResponse,
    InterviewSessionRuntimeStateResponse,
    ProposeInterviewScheduleRequest,
    PublishInterviewRequest,
    PublishInterviewResponse,
    SuggestInterviewFeedbackPolicyResponse,
    TranscriptTurnRequest,
    UpdateInterviewScheduleRequest,
)
from src.schemas.jd import JDCompanyKnowledgeQueryRequest, JDCompanyKnowledgeQueryResponse
from src.services.company_knowledge_service import CompanyKnowledgeService
from src.services.interview_feedback_service import InterviewFeedbackService
from src.services.interview_runtime_service import InterviewRuntimeService
from src.services.interview_session_service import InterviewSessionService

router = APIRouter(prefix="/interviews", tags=["interviews"])
WorkerCallbackSecretHeader = Annotated[str | None, Header(alias="X-Worker-Callback-Secret")]


def _validate_worker_secret(callback_secret: str | None) -> None:
    if callback_secret != settings.worker_callback_secret:
        raise HTTPException(status_code=401, detail="Invalid worker callback secret")


def require_worker_callback_secret(
    worker_callback_secret: WorkerCallbackSecretHeader = None,
) -> None:
    _validate_worker_secret(worker_callback_secret)


def require_hr_or_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role not in {"hr", "admin"}:
        raise HTTPException(status_code=403, detail="HR or admin access required")
    return current_user


@router.post("/generate-questions", response_model=GenerateInterviewQuestionsResponse)
async def generate_interview_questions(
    payload: GenerateInterviewQuestionsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> GenerateInterviewQuestionsResponse:
    service = InterviewSessionService(db)
    try:
        return await service.generate_questions(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/publish", response_model=PublishInterviewResponse, status_code=201)
async def publish_interview(
    payload: PublishInterviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublishInterviewResponse:
    service = InterviewSessionService(db)
    try:
        return await service.publish_interview(payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "required" in message else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post("/join/{share_token}", response_model=CandidateJoinResponse)
async def join_interview(
    share_token: str,
    payload: CandidateJoinRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateJoinResponse:
    service = InterviewSessionService(db)
    try:
        return await service.resolve_join(share_token, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/join/{share_token}", response_model=CandidateJoinPreviewResponse)
async def get_join_preview(
    share_token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CandidateJoinPreviewResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_join_preview(share_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/join/{share_token}/schedule", response_model=InterviewSchedulePayload)
async def propose_interview_schedule(
    share_token: str,
    payload: ProposeInterviewScheduleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSchedulePayload:
    service = InterviewSessionService(db)
    try:
        return await service.propose_schedule(share_token, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "rescheduled" in message else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.post(
    "/sessions/{session_id}/turns",
    status_code=204,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def append_turn(
    session_id: str,
    payload: TranscriptTurnRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.append_turn(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/complete",
    status_code=204,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def complete_session(
    session_id: str,
    payload: CompleteInterviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.complete_session(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}",
    response_model=InterviewSessionDetailResponse,
)
async def get_session_detail(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionDetailResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_session_detail(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/sessions/{session_id}/runtime-state",
    response_model=InterviewSessionRuntimeStateResponse,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def get_session_runtime_state(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionRuntimeStateResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_runtime_state(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/schedule", response_model=InterviewSchedulePayload)
async def update_interview_schedule(
    session_id: str,
    payload: UpdateInterviewScheduleRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSchedulePayload:
    service = InterviewSessionService(db)
    try:
        return await service.update_schedule(session_id, payload)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "rescheduled" in message else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get(
    "/sessions/{session_id}/review",
    response_model=InterviewSessionReviewResponse,
    dependencies=[Depends(require_hr_or_admin_user)],
)
async def get_session_review(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewSessionReviewResponse:
    service = InterviewSessionService(db)
    try:
        return await service.get_session_review(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/runtime-events",
    status_code=204,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def append_runtime_event(
    session_id: str,
    payload: InterviewRuntimeEventRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewRuntimeService(db)
    try:
        await service.record_event(session_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/expire-reconnect",
    status_code=204,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def expire_reconnect(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    service = InterviewSessionService(db)
    try:
        await service.expire_reconnect_grace_period(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/sessions/{session_id}/feedback", response_model=InterviewFeedbackResponse)
async def submit_session_feedback(
    session_id: str,
    payload: InterviewFeedbackRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> InterviewFeedbackResponse:
    service = InterviewFeedbackService(db)
    try:
        return await service.submit_feedback(session_id, payload, current_user)
    except ValueError as exc:
        message = str(exc)
        status_code = 400 if "only available" in message else 404
        raise HTTPException(status_code=status_code, detail=message) from exc


@router.get(
    "/sessions/{session_id}/feedback",
    response_model=InterviewFeedbackResponse | None,
    dependencies=[Depends(require_hr_or_admin_user)],
)
async def get_session_feedback(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewFeedbackResponse | None:
    service = InterviewFeedbackService(db)
    return await service.get_feedback(session_id)


@router.get(
    "/jd/{jd_id}/feedback-summary",
    response_model=InterviewFeedbackSummaryResponse,
    dependencies=[Depends(require_hr_or_admin_user)],
)
async def get_jd_feedback_summary(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewFeedbackSummaryResponse:
    service = InterviewFeedbackService(db)
    return await service.get_feedback_summary(jd_id)


@router.get(
    "/jd/{jd_id}/feedback-policy",
    response_model=InterviewFeedbackPolicyCollectionResponse,
    dependencies=[Depends(require_hr_or_admin_user)],
)
async def get_jd_feedback_policy(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InterviewFeedbackPolicyCollectionResponse:
    service = InterviewFeedbackService(db)
    return await service.get_policy_collection(jd_id)


@router.post("/jd/{jd_id}/feedback-policy/suggest", response_model=SuggestInterviewFeedbackPolicyResponse)
async def suggest_jd_feedback_policy(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> SuggestInterviewFeedbackPolicyResponse:
    service = InterviewFeedbackService(db)
    return await service.suggest_policy(jd_id, current_user)


@router.post("/jd/{jd_id}/feedback-policy/{policy_id}/apply", response_model=InterviewFeedbackPolicyResponse)
async def apply_jd_feedback_policy(
    jd_id: str,
    policy_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> InterviewFeedbackPolicyResponse:
    service = InterviewFeedbackService(db)
    try:
        return await service.apply_policy(jd_id, policy_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/jd/{jd_id}/feedback-policy/{policy_id}/reject", response_model=InterviewFeedbackPolicyResponse)
async def reject_jd_feedback_policy(
    jd_id: str,
    policy_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> InterviewFeedbackPolicyResponse:
    service = InterviewFeedbackService(db)
    try:
        return await service.reject_policy(jd_id, policy_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/sessions/{session_id}/knowledge-query",
    response_model=JDCompanyKnowledgeQueryResponse,
    dependencies=[Depends(require_worker_callback_secret)],
)
async def query_session_company_knowledge(
    session_id: str,
    payload: JDCompanyKnowledgeQueryRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JDCompanyKnowledgeQueryResponse:
    session_service = InterviewSessionService(db)
    company_service = CompanyKnowledgeService(db_session=db)
    try:
        jd_id = await session_service.get_jd_id_for_session(session_id)
        return await company_service.query_knowledge(jd_id, payload.query)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
