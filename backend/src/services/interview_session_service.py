import asyncio
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.background_job import BackgroundJob, BackgroundJobStatus, BackgroundJobType
from src.models.cv import CandidateProfile, CandidateScreening
from src.models.interview import InterviewRuntimeEvent, InterviewSession, InterviewTurn
from src.models.jd import JDDocument
from src.schemas.interview import (
    CandidateJoinPreviewResponse,
    CandidateJoinRequest,
    CandidateJoinResponse,
    CompleteInterviewRequest,
    GenerateInterviewQuestionsRequest,
    GenerateInterviewQuestionsResponse,
    InterviewCompetencyPlan,
    InterviewCompetencyPolicyOverride,
    InterviewPlanEvent,
    InterviewPlanPayload,
    InterviewPolicyThresholds,
    InterviewQuestion,
    InterviewQuestionCandidate,
    InterviewRuntimeEventResponse,
    InterviewSchedulePayload,
    InterviewSemanticAnswerEvaluation,
    InterviewSessionDetailResponse,
    InterviewSessionReviewResponse,
    InterviewSessionRuntimeStateResponse,
    ProposeInterviewScheduleRequest,
    PublishInterviewRequest,
    PublishInterviewResponse,
    TranscriptTurnRequest,
    TranscriptTurnResponse,
    UpdateInterviewScheduleRequest,
)
from src.schemas.jd import BilingualText
from src.services.datetime_utils import (
    VIETNAM_TIME_ZONE_NAME,
    parse_client_datetime_to_utc,
    to_vietnam_isoformat,
)
from src.services.interview_answer_evaluator_service import InterviewAnswerEvaluatorService
from src.services.interview_feedback_service import InterviewFeedbackService
from src.services.interview_plan_service import InterviewPlanService
from src.services.interview_summary_service import InterviewSummaryService
from src.services.interview_worker_launcher import InterviewWorkerLauncher
from src.services.livekit_service import LiveKitService

logger = logging.getLogger(__name__)


def _as_object_mapping(value: object) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    return cast(Mapping[str, object], value)


def _as_object_dict(value: object) -> dict[str, object] | None:
    mapping = _as_object_mapping(value)
    return dict(mapping) if mapping is not None else None


def _as_object_list(value: object) -> list[object] | None:
    if not isinstance(value, list):
        return None
    return cast(list[object], value)


class SemanticAnswerEvaluator(Protocol):
    async def evaluate(
        self,
        *,
        plan_payload: Mapping[str, object],
        current_question: Mapping[str, object],
        current_competency: Mapping[str, object] | None,
        answer_text: str,
        recent_plan_events: Sequence[Mapping[str, object]],
        transcript_context: Sequence[Mapping[str, object]],
    ) -> InterviewSemanticAnswerEvaluation: ...


@dataclass(slots=True)
class AnswerEvaluation:
    coverage_gain: float
    evidence_increment: int
    is_generic: bool
    has_inconsistency: bool
    should_advance: bool
    should_wrap_up: bool
    should_escalate: bool
    chosen_action: str
    confidence: float
    reason: BilingualText
    next_intended_step: BilingualText
    decision_status: str
    next_phase: str
    decision_rule: str
    evidence_excerpt: BilingualText
    adaptive_question_type: str | None = None
    semantic_evaluation: InterviewSemanticAnswerEvaluation | None = None


class InterviewSessionService:
    def __init__(
        self,
        db_session: AsyncSession,
        worker_launcher: InterviewWorkerLauncher | None = None,
        plan_service: InterviewPlanService | None = None,
        semantic_evaluator: SemanticAnswerEvaluator | None = None,
    ) -> None:
        self._db_session: AsyncSession = db_session
        self._livekit: LiveKitService = LiveKitService()
        self._worker_launcher: InterviewWorkerLauncher = worker_launcher or InterviewWorkerLauncher(
            settings.interview_worker_service_url,
            settings.interview_worker_dispatch_timeout_seconds,
        )
        self._plan_service: InterviewPlanService = plan_service or InterviewPlanService()
        self._semantic_evaluator: SemanticAnswerEvaluator = (
            semantic_evaluator or InterviewAnswerEvaluatorService()
        )
        self._feedback_service: InterviewFeedbackService = InterviewFeedbackService(db_session)

    @property
    def livekit_service(self) -> LiveKitService:
        return self._livekit

    async def _delete_room_in_background(self, session_id: str, room_name: str) -> None:
        try:
            await self._livekit.delete_room(room_name)
        except Exception:
            logger.exception(
                "failed to delete LiveKit room for session_id=%s room_name=%s",
                session_id,
                room_name,
            )

    async def _dispatch_worker_for_session(
        self,
        session: InterviewSession,
        *,
        jd_id: str,
    ):
        worker_identity = session.worker_identity or self._livekit.create_worker_identity(session.id)
        worker_token = self._livekit.create_worker_token(
            room_name=session.livekit_room_name,
            identity=worker_identity,
        )
        session.worker_identity = worker_identity
        return await self._worker_launcher.launch(
            session_id=session.id,
            room_name=session.livekit_room_name,
            opening_question=session.opening_question,
            worker_token=worker_token,
            jd_id=jd_id,
        )

    async def generate_questions(
        self,
        payload: GenerateInterviewQuestionsRequest,
    ) -> GenerateInterviewQuestionsResponse:
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == payload.screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        if screening.status != "completed":
            raise ValueError("CV screening is not ready for interview")

        generated = await self._plan_service.generate_questions(
            screening_id=screening.id,
            screening_payload=screening.screening_payload,
            manual_questions=payload.manual_questions,
            question_guidance=payload.question_guidance,
        )
        screening.screening_payload = self._merge_interview_draft(
            screening.screening_payload,
            manual_questions=generated.manual_questions,
            question_guidance=generated.question_guidance,
            approved_questions=[item.question_text for item in generated.generated_questions],
            generated_questions=generated.generated_questions,
        )
        await self._db_session.commit()
        return generated

    async def publish_interview(self, payload: PublishInterviewRequest) -> PublishInterviewResponse:
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == payload.screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        if screening.status != "completed":
            raise ValueError("CV screening is not ready for interview")

        approved_questions = [question.strip() for question in payload.approved_questions if question.strip()]
        if not approved_questions:
            raise ValueError("Approved interview questions are required")

        existing_session = await self._db_session.scalar(
            select(InterviewSession)
            .where(InterviewSession.candidate_screening_id == screening.id)
            .order_by(InterviewSession.created_at.desc())
        )
        if existing_session is not None and existing_session.status not in {"finishing", "completed"}:
            return PublishInterviewResponse(
                session_id=existing_session.id,
                share_link=f"{settings.next_public_app_url}/interviews/join/{existing_session.share_token}",
                room_name=existing_session.livekit_room_name,
                status=existing_session.status,
                schedule=self._build_schedule_payload(existing_session),
            )

        jd_document = await self._db_session.scalar(
            select(JDDocument).where(JDDocument.id == screening.jd_document_id)
        )
        if jd_document is None:
            raise ValueError("JD analysis not found")

        candidate_profile = await self._db_session.scalar(
            select(CandidateProfile).where(CandidateProfile.id == screening.candidate_profile_id)
        )
        room_name = self._livekit.build_room_name(
            self._extract_candidate_name(candidate_profile.profile_payload if candidate_profile is not None else {})
        )
        share_token = self._livekit.build_share_token()
        worker_dispatch_token = self._livekit.build_worker_dispatch_token()
        plan_payload = await self._build_session_plan_payload(
            jd_id=jd_document.id,
            screening_payload=screening.screening_payload,
            approved_questions=approved_questions,
        )
        session = InterviewSession(
            candidate_screening_id=screening.id,
            status="published",
            share_token=share_token,
            worker_dispatch_token=worker_dispatch_token,
            livekit_room_name=room_name,
            worker_status="idle",
            provider_status="room_not_connected",
            opening_question=approved_questions[0],
            approved_questions=approved_questions,
            manual_questions=[question.strip() for question in payload.manual_questions if question.strip()],
            question_guidance=payload.question_guidance.strip() if payload.question_guidance else None,
            plan_payload=plan_payload.model_dump(mode="json"),
        )
        self._db_session.add(session)
        await self._db_session.commit()
        await self._db_session.refresh(session)
        dispatch = await self._dispatch_worker_for_session(session, jd_id=jd_document.id)
        session.worker_status = "queued"
        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="planning.published",
                event_source="backend",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload={
                    "question_count": len(plan_payload.questions),
                    "competency_count": len(plan_payload.competencies),
                    "plan_version": "v2",
                    "question_sources": [item.source for item in plan_payload.questions if item.source],
                    "current_phase": plan_payload.current_phase,
                },
            )
        )
        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="worker.dispatch_requested",
                event_source="backend",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload={
                    "accepted": dispatch.accepted,
                    "status": dispatch.status,
                    "approved_questions": approved_questions,
                },
            )
        )
        await self._db_session.commit()

        return PublishInterviewResponse(
            session_id=session.id,
            share_link=f"{settings.next_public_app_url}/interviews/join/{share_token}",
            room_name=room_name,
            status=session.status,
            schedule=self._build_schedule_payload(session),
        )

    async def resolve_join(
        self,
        share_token: str,
        payload: CandidateJoinRequest,
    ) -> CandidateJoinResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload or session.status in {"finishing", "completed"}:
            raise ValueError("Interview session has ended")

        candidate_identity = self._livekit.create_candidate_identity(
            session.id,
            payload.candidate_name,
        )
        participant_token = self._livekit.create_candidate_token(
            room_name=session.livekit_room_name,
            identity=candidate_identity,
        )
        previous_status = session.status
        session.status = "waiting" if session.status != "completed" else session.status
        session.candidate_identity = candidate_identity
        session.disconnect_deadline_at = None
        session.last_disconnect_reason = None
        should_dispatch_worker = previous_status == "reconnecting" or session.worker_status == "waiting_for_candidate"
        if should_dispatch_worker:
            screening = await self._db_session.scalar(
                select(CandidateScreening).where(CandidateScreening.id == session.candidate_screening_id)
            )
            if screening is None:
                raise ValueError("CV screening not found")
            dispatch = await self._dispatch_worker_for_session(session, jd_id=screening.jd_document_id)
            if dispatch.status == "queued":
                session.worker_status = "queued"
            self._db_session.add(
                InterviewRuntimeEvent(
                    interview_session_id=session.id,
                    event_type="worker.dispatch_requested",
                    event_source="backend",
                    session_status=session.status,
                    worker_status=session.worker_status,
                    provider_status=session.provider_status,
                    payload={
                        "accepted": dispatch.accepted,
                        "status": dispatch.status,
                        "trigger": "candidate.rejoined" if previous_status == "reconnecting" else "candidate.join_requested",
                    },
                )
            )

        event_type = "candidate.rejoined" if previous_status == "reconnecting" else "candidate.join_requested"
        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type=event_type,
                event_source="candidate",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload={
                    "candidate_name": payload.candidate_name,
                    "candidate_identity": candidate_identity,
                },
            )
        )
        await self._db_session.commit()

        return CandidateJoinResponse(
            session_id=session.id,
            room_name=session.livekit_room_name,
            participant_token=participant_token,
            candidate_identity=candidate_identity,
            schedule=self._build_schedule_payload(session),
        )

    async def get_join_preview(self, share_token: str) -> CandidateJoinPreviewResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload or session.status in {"finishing", "completed"}:
            raise ValueError("Interview session has ended")

        return CandidateJoinPreviewResponse(
            session_id=session.id,
            status=session.status,
            schedule=self._build_schedule_payload(session),
        )

    async def append_turn(self, session_id: str, payload: TranscriptTurnRequest) -> None:
        session = await self._db_session.scalar(select(InterviewSession).where(InterviewSession.id == session_id))
        if session is None:
            raise ValueError("Interview session not found")

        if payload.provider_event_id:
            existing_turn = await self._db_session.scalar(
                select(InterviewTurn).where(
                    InterviewTurn.interview_session_id == session.id,
                    InterviewTurn.provider_event_id == payload.provider_event_id,
                )
            )
            if existing_turn is not None:
                return

        self._db_session.add(
            InterviewTurn(
                interview_session_id=session.id,
                speaker=payload.speaker,
                sequence_number=payload.sequence_number,
                transcript_text=payload.transcript_text,
                provider_event_id=payload.provider_event_id,
                event_payload=payload.event_payload,
            )
        )

        adaptive_event = await self._build_adaptive_plan_event(session, payload)
        if adaptive_event is not None:
            session.plan_payload = self._apply_adaptive_plan_update(session.plan_payload, adaptive_event)
            self._db_session.add(
                InterviewRuntimeEvent(
                    interview_session_id=session.id,
                    event_type=adaptive_event.event_type,
                    event_source="backend",
                    session_status=session.status,
                    worker_status=session.worker_status,
                    provider_status=session.provider_status,
                    payload={
                        "reason": adaptive_event.reason.model_dump(mode="json"),
                        "chosen_action": adaptive_event.chosen_action,
                        "affected_competency": adaptive_event.affected_competency.model_dump(mode="json")
                        if adaptive_event.affected_competency is not None
                        else None,
                        "confidence": adaptive_event.confidence,
                        "question_index": adaptive_event.question_index,
                        "semantic_evaluation": adaptive_event.semantic_evaluation.model_dump(mode="json")
                        if adaptive_event.semantic_evaluation is not None
                        else None,
                    },
                )
            )

        await self._db_session.commit()

    async def list_turns(self, session_id: str) -> list[InterviewTurn]:
        return list(
            (
                await self._db_session.scalars(
                    select(InterviewTurn)
                    .where(InterviewTurn.interview_session_id == session_id)
                    .order_by(InterviewTurn.sequence_number.asc())
                )
            ).all()
        )

    async def store_summary(self, session_id: str, summary_payload: dict[str, object]) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload:
            return
        session.summary_payload = summary_payload
        session.status = "completed"
        session.worker_status = "completed"
        session.provider_status = "completed"
        session.completed_at = datetime.now(UTC)
        session.last_error_code = None
        session.last_error_message = None
        await self._db_session.commit()

    async def complete_session(
        self,
        session_id: str,
        payload: CompleteInterviewRequest,
        *,
        summary_generator: InterviewSummaryService | None = None,
    ) -> None:
        _ = summary_generator
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload:
            return
        if await self._has_active_summary_job(session.id):
            return

        session.status = "finishing"
        session.worker_status = "summarizing"
        session.provider_status = "closing"
        session.disconnect_deadline_at = None
        session.last_disconnect_reason = payload.reason
        session.last_error_code = None
        session.last_error_message = None
        session.share_token = self._livekit.build_share_token()
        self._db_session.add(
            BackgroundJob(
                job_type="interview_summary",
                status="queued",
                resource_type="interview_session",
                resource_id=session.id,
                payload={"completion_reason": payload.reason},
            )
        )
        await self._db_session.commit()
        _ = asyncio.create_task(
            self._delete_room_in_background(session.id, session.livekit_room_name),
            name=f"interview-room-delete:{session.id}",
        )

    async def run_summary_job(
        self,
        session_id: str,
        *,
        summary_generator: InterviewSummaryService | None = None,
    ) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload:
            return

        turns = await self.list_turns(session_id)
        generator = summary_generator or InterviewSummaryService()
        summary_payload = await generator.generate(
            opening_question=session.opening_question,
            turns=[
                {
                    "sequence_number": turn.sequence_number,
                    "speaker": turn.speaker,
                    "transcript_text": turn.transcript_text,
                    "provider_event_id": turn.provider_event_id,
                }
                for turn in turns
            ],
            plan_payload=session.plan_payload,
        )
        summary_payload["completion_reason"] = await self._get_completion_reason(session_id)
        await self.store_summary(session_id, summary_payload)

    async def start_reconnect_grace_period(
        self,
        session_id: str,
        *,
        participant_identity: str | None,
        reason: str,
    ) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload:
            return
        if session.status == "completed":
            return

        deadline = datetime.now(UTC) + timedelta(seconds=settings.interview_reconnect_grace_seconds)
        session.status = "reconnecting"
        session.worker_status = "waiting_for_candidate"
        session.disconnect_deadline_at = deadline
        session.last_disconnect_reason = reason
        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="session.reconnect_grace_started",
                event_source="backend",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload={
                    "participant_identity": participant_identity,
                    "reason": reason,
                    "disconnect_deadline_at": to_vietnam_isoformat(deadline),
                },
            )
        )
        self._db_session.add(
            BackgroundJob(
                job_type=BackgroundJobType.INTERVIEW_DISCONNECT_TIMEOUT,
                status=BackgroundJobStatus.QUEUED,
                resource_type="interview_session",
                resource_id=session.id,
                payload={
                    "participant_identity": participant_identity,
                    "reason": reason,
                    "disconnect_deadline_at": to_vietnam_isoformat(deadline),
                },
            )
        )
        await self._db_session.commit()

    async def expire_reconnect_grace_period(self, session_id: str) -> bool:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.summary_payload or session.status == "completed":
            return False
        if session.status != "reconnecting" or session.disconnect_deadline_at is None:
            return False
        if session.disconnect_deadline_at > datetime.now(UTC):
            return False

        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="session.reconnect_grace_expired",
                event_source="backend",
                session_status="finishing",
                worker_status="finishing",
                provider_status=session.provider_status,
                payload={
                    "reason": session.last_disconnect_reason,
                    "disconnect_deadline_at": to_vietnam_isoformat(session.disconnect_deadline_at),
                },
            )
        )
        await self._db_session.commit()
        await self.complete_session(
            session.id,
            CompleteInterviewRequest(reason=session.last_disconnect_reason or "disconnect_timeout"),
        )
        return True

    async def get_session_detail(self, session_id: str) -> InterviewSessionDetailResponse:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")

        turns = await self.list_turns(session_id)
        events = list(
            (
                await self._db_session.scalars(
                    select(InterviewRuntimeEvent)
                    .where(InterviewRuntimeEvent.interview_session_id == session_id)
                    .order_by(InterviewRuntimeEvent.created_at.asc())
                )
            ).all()
        )
        plan = self._load_plan_payload(session.plan_payload)
        total_questions = len(plan.questions) if plan is not None else len(session.approved_questions)
        current_question_index = self._build_current_question_index(turns=turns, total_questions=total_questions)
        recommendation = session.summary_payload.get("recommendation")
        return InterviewSessionDetailResponse(
            session_id=session.id,
            status=session.status,
            worker_status=session.worker_status,
            provider_status=session.provider_status,
            livekit_room_name=session.livekit_room_name,
            opening_question=session.opening_question,
            approved_questions=session.approved_questions,
            manual_questions=session.manual_questions,
            question_guidance=session.question_guidance,
            plan=plan,
            current_question_index=current_question_index,
            total_questions=total_questions,
            recommendation=recommendation if isinstance(recommendation, str) else None,
            schedule=self._build_schedule_payload(session),
            disconnect_deadline_at=to_vietnam_isoformat(session.disconnect_deadline_at),
            last_disconnect_reason=session.last_disconnect_reason,
            last_error_code=session.last_error_code,
            last_error_message=session.last_error_message,
            transcript_turns=[
                TranscriptTurnResponse(
                    speaker=turn.speaker,
                    sequence_number=turn.sequence_number,
                    transcript_text=turn.transcript_text,
                    provider_event_id=turn.provider_event_id,
                    event_payload=turn.event_payload,
                )
                for turn in turns
            ],
            runtime_events=[
                InterviewRuntimeEventResponse(
                    event_type=event.event_type,
                    event_source=event.event_source,
                    session_status=event.session_status,
                    worker_status=event.worker_status,
                    provider_status=event.provider_status,
                    payload=event.payload,
                )
                for event in events
            ],
        )

    async def get_runtime_state(self, session_id: str) -> InterviewSessionRuntimeStateResponse:
        detail = await self.get_session_detail(session_id)
        decision_status = detail.plan.interview_decision_status if detail.plan is not None else None
        current_question = (
            detail.plan.questions[detail.current_question_index]
            if detail.plan is not None and detail.plan.questions and detail.current_question_index < len(detail.plan.questions)
            else None
        )
        if decision_status == "ready_to_wrap":
            current_question = None
        last_plan_event = detail.plan.plan_events[-1] if detail.plan is not None and detail.plan.plan_events else None
        return InterviewSessionRuntimeStateResponse(
            session_id=detail.session_id,
            status=detail.status,
            worker_status=detail.worker_status,
            provider_status=detail.provider_status,
            current_question_index=detail.current_question_index,
            current_question=current_question,
            next_intended_step=detail.plan.next_intended_step if detail.plan is not None else None,
            interview_decision_status=decision_status,
            needs_hr_review=self._plan_needs_hr_review(detail.plan),
            current_phase=detail.plan.current_phase if detail.plan is not None else None,
            last_plan_event=last_plan_event,
        )

    async def get_session_review(self, session_id: str) -> InterviewSessionReviewResponse:
        detail = await self.get_session_detail(session_id)
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")

        return InterviewSessionReviewResponse(
            session_id=detail.session_id,
            status=detail.status,
            summary_payload=session.summary_payload,
            transcript_turns=detail.transcript_turns,
            ai_competency_assessments=self._feedback_service._derive_ai_competency_assessments(session),  # pyright: ignore[reportPrivateUsage]
        )

    async def get_jd_id_for_session(self, session_id: str) -> str:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == session.candidate_screening_id)
        )
        if screening is None:
            raise ValueError("CV screening not found")
        return screening.jd_document_id

    async def update_schedule(
        self,
        session_id: str,
        payload: UpdateInterviewScheduleRequest,
    ) -> InterviewSchedulePayload:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.status == "completed":
            raise ValueError("Completed interviews cannot be rescheduled")

        if payload.confirm_candidate_proposal and session.candidate_proposed_start_at is not None:
            session.scheduled_start_at = session.candidate_proposed_start_at
            session.schedule_note = session.candidate_proposed_note
            session.schedule_status = "confirmed"
            session.candidate_proposed_start_at = None
            session.candidate_proposed_note = None
        elif payload.scheduled_start_at:
            session.scheduled_start_at = parse_client_datetime_to_utc(payload.scheduled_start_at)
            session.schedule_note = payload.schedule_note.strip() if payload.schedule_note else None
            session.schedule_status = "confirmed"
        else:
            session.scheduled_start_at = None
            session.schedule_note = payload.schedule_note.strip() if payload.schedule_note else None
            session.schedule_status = "unscheduled"

        session.schedule_timezone = VIETNAM_TIME_ZONE_NAME
        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="schedule.updated",
                event_source="backend",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload=self._build_schedule_payload(session).model_dump(mode="json"),
            )
        )
        await self._db_session.commit()
        return self._build_schedule_payload(session)

    async def propose_schedule(
        self,
        share_token: str,
        payload: ProposeInterviewScheduleRequest,
    ) -> InterviewSchedulePayload:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.share_token == share_token)
        )
        if session is None:
            raise ValueError("Interview session not found")
        if session.status == "completed":
            raise ValueError("Completed interviews cannot be rescheduled")

        session.candidate_proposed_start_at = parse_client_datetime_to_utc(payload.proposed_start_at)
        session.candidate_proposed_note = payload.note.strip() if payload.note else None
        session.schedule_timezone = VIETNAM_TIME_ZONE_NAME
        if session.schedule_status == "unscheduled":
            session.schedule_status = "proposed"

        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type="schedule.proposed",
                event_source="candidate",
                session_status=session.status,
                worker_status=session.worker_status,
                provider_status=session.provider_status,
                payload=self._build_schedule_payload(session).model_dump(mode="json"),
            )
        )
        await self._db_session.commit()
        return self._build_schedule_payload(session)

    async def mark_summary_failed(self, session_id: str, error_message: str) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            return
        session.worker_status = "failed"
        session.last_error_code = "interview_summary_failed"
        session.last_error_message = error_message
        await self._db_session.commit()

    async def _has_active_summary_job(self, session_id: str) -> bool:
        job = await self._db_session.scalar(
            select(BackgroundJob).where(
                BackgroundJob.resource_id == session_id,
                BackgroundJob.job_type == "interview_summary",
                BackgroundJob.status.in_((BackgroundJobStatus.QUEUED, BackgroundJobStatus.RUNNING)),
            )
        )
        return job is not None

    async def _get_completion_reason(self, session_id: str) -> str:
        job = await self._db_session.scalar(
            select(BackgroundJob)
            .where(
                BackgroundJob.resource_id == session_id,
                BackgroundJob.job_type == "interview_summary",
            )
            .order_by(BackgroundJob.created_at.desc())
        )
        if job is None:
            return "completed"
        completion_reason = job.payload.get("completion_reason")
        return completion_reason if isinstance(completion_reason, str) and completion_reason else "completed"

    def _extract_candidate_name(self, profile_payload: object) -> str | None:
        profile = _as_object_mapping(profile_payload)
        if profile is None:
            return None

        candidate_summary = _as_object_mapping(profile.get("candidate_summary"))
        if candidate_summary is None:
            return None

        full_name = candidate_summary.get("full_name")
        return full_name.strip() if isinstance(full_name, str) and full_name.strip() else None

    def _runtime_decision_status(self, *, needs_hr_review: bool, default_status: str) -> str:
        if default_status == "ready_to_wrap":
            return "ready_to_wrap"
        return "continue_with_hr_flag" if needs_hr_review else default_status

    def _plan_needs_hr_review(self, plan: InterviewPlanPayload | None) -> bool:
        if plan is None:
            return False
        if plan.interview_decision_status in {"continue_with_hr_flag", "escalate_hr"}:
            return True
        if any(item.status == "needs_recovery" for item in plan.competencies):
            return True
        return any(
            event.semantic_evaluation is not None and event.semantic_evaluation.needs_hr_review
            for event in plan.plan_events
        )

    def _build_schedule_payload(self, session: InterviewSession) -> InterviewSchedulePayload:
        return InterviewSchedulePayload(
            scheduled_start_at=to_vietnam_isoformat(session.scheduled_start_at),
            schedule_timezone=session.schedule_timezone or VIETNAM_TIME_ZONE_NAME,
            schedule_status=session.schedule_status,
            schedule_note=session.schedule_note,
            candidate_proposed_start_at=to_vietnam_isoformat(session.candidate_proposed_start_at),
            candidate_proposed_note=session.candidate_proposed_note,
        )

    async def _build_session_plan_payload(
        self,
        *,
        jd_id: str,
        screening_payload: dict[str, object],
        approved_questions: list[str],
    ) -> InterviewPlanPayload:
        plan = self._plan_service.build_plan(screening_payload)
        policy_version, active_policy, policy_summary = await self._feedback_service.get_active_policy_payload(jd_id)
        if active_policy is not None:
            plan.active_policy = active_policy
            plan.policy_version = policy_version
            plan.policy_summary = policy_summary
            self._apply_policy_to_plan(plan)
        dimension_by_question = {
            item.prompt.vi.strip().casefold(): item
            for item in plan.questions
            if item.prompt.vi.strip()
        }
        interview_draft = _as_object_dict(screening_payload.get("interview_draft")) or {}
        generated_questions_payload = interview_draft.get("generated_questions")
        generated_questions_by_text: dict[str, dict[str, object]] = {}
        generated_questions = _as_object_list(generated_questions_payload)
        if generated_questions is not None:
            for item_value in generated_questions:
                item = _as_object_mapping(item_value)
                if item is None:
                    continue
                question_text = item.get("question_text")
                if isinstance(question_text, str) and question_text.strip():
                    generated_questions_by_text[question_text.strip().casefold()] = dict(item)

        question_items: list[InterviewQuestion] = []
        for index, question_text in enumerate(approved_questions):
            normalized_question = question_text.strip()
            if not normalized_question:
                continue
            existing_item = dimension_by_question.get(normalized_question.casefold())
            generated_item = generated_questions_by_text.get(normalized_question.casefold(), {})

            dimension_name = (
                existing_item.dimension_name
                if existing_item is not None
                else BilingualText(vi="Năng lực trọng tâm", en="Core competency")
            )
            purpose = (
                existing_item.purpose
                if existing_item is not None
                else BilingualText(
                    vi="Xác minh tín hiệu đã được HR duyệt cho buổi phỏng vấn này.",
                    en="Validate the approved interview signal for this session.",
                )
            )
            source: str | None = None
            generated_source = generated_item.get("source")
            if isinstance(generated_source, str):
                source = generated_source

            question_type: str | None = existing_item.question_type if existing_item is not None else "planned"
            generated_question_type = generated_item.get("question_type")
            if isinstance(generated_question_type, str):
                question_type = generated_question_type

            rationale: str | None = existing_item.rationale if existing_item is not None else None
            generated_rationale = generated_item.get("rationale")
            if isinstance(generated_rationale, str):
                rationale = generated_rationale
            priority = generated_item.get("priority")
            target_competency_payload = generated_item.get("target_competency")
            selection_reason_payload = generated_item.get("selection_reason")
            evidence_gap_payload = generated_item.get("evidence_gap")

            question_items.append(
                InterviewQuestion(
                    question_index=index,
                    dimension_name=dimension_name,
                    prompt=BilingualText(vi=normalized_question, en=normalized_question),
                    purpose=purpose,
                    source=source or (existing_item.source if existing_item is not None else "approved"),
                    question_type=question_type,
                    rationale=rationale,
                    priority=priority if isinstance(priority, int) and priority > 0 else index + 1,
                    target_competency=BilingualText.model_validate(target_competency_payload)
                    if isinstance(target_competency_payload, Mapping)
                    else (existing_item.target_competency if existing_item is not None else dimension_name),
                    selection_reason=BilingualText.model_validate(selection_reason_payload)
                    if isinstance(selection_reason_payload, Mapping)
                    else (existing_item.selection_reason if existing_item is not None else None),
                    evidence_gap=BilingualText.model_validate(evidence_gap_payload)
                    if isinstance(evidence_gap_payload, Mapping)
                    else (existing_item.evidence_gap if existing_item is not None else None),
                    transition_on_strong_answer=(
                        existing_item.transition_on_strong_answer
                        if existing_item is not None
                        else "advance_to_next_competency"
                    ),
                    transition_on_weak_answer=(
                        existing_item.transition_on_weak_answer
                        if existing_item is not None
                        else "ask_clarification"
                    ),
                )
            )
        if question_items:
            plan.questions = question_items
        plan.plan_events.append(
            InterviewPlanEvent(
                event_type="plan.started",
                reason=BilingualText(
                    vi="Đã cố định plan khi publish session phỏng vấn.",
                    en="The plan was finalized when the interview session was published.",
                ),
                chosen_action="freeze_published_plan",
                affected_competency=(
                    question_items[0].target_competency
                    if question_items and question_items[0].target_competency is not None
                    else None
                ),
                confidence=0.82 if question_items else None,
                question_index=0 if question_items else None,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        return plan

    def _load_plan_payload(self, payload: dict[str, object]) -> InterviewPlanPayload | None:
        if not payload:
            return None
        try:
            return InterviewPlanPayload.model_validate(payload)
        except ValueError:
            return None

    async def _build_adaptive_plan_event(
        self,
        session: InterviewSession,
        payload: TranscriptTurnRequest,
    ) -> InterviewPlanEvent | None:
        if not payload.speaker.casefold().startswith("candidate"):
            return None
        plan = self._load_plan_payload(session.plan_payload)
        if plan is None or not plan.questions:
            return None

        current_question, current_competency_index = self._get_current_plan_context(
            plan=plan,
            payload=payload,
        )
        transcript_context = await self._build_transcript_context(
            session_id=session.id,
            payload=payload,
        )
        evaluation = await self._evaluate_answer(
            plan=plan,
            current_competency_index=current_competency_index,
            current_question=current_question,
            answer_text=payload.transcript_text,
            transcript_context=transcript_context,
        )
        event_type = (
            "plan.phase_completed"
            if evaluation.should_advance or evaluation.should_wrap_up
            else "plan.adjusted"
        )
        return InterviewPlanEvent(
            event_type=event_type,
            reason=evaluation.reason,
            chosen_action=evaluation.chosen_action,
            affected_competency=current_question.target_competency or current_question.dimension_name,
            confidence=evaluation.confidence,
            question_index=current_question.question_index,
            evidence_excerpt=evaluation.evidence_excerpt,
            decision_rule=evaluation.decision_rule,
            next_question_type=evaluation.adaptive_question_type,
            semantic_evaluation=evaluation.semantic_evaluation,
            created_at=datetime.now(UTC).isoformat(),
        )

    async def _build_transcript_context(
        self,
        *,
        session_id: str,
        payload: TranscriptTurnRequest,
    ) -> list[dict[str, object]]:
        turns = await self.list_turns(session_id)
        prior_turns = [
            turn
            for turn in turns
            if (
                payload.provider_event_id is None
                or turn.provider_event_id != payload.provider_event_id
            )
            and not (
                turn.sequence_number == payload.sequence_number
                and turn.speaker == payload.speaker
                and turn.transcript_text == payload.transcript_text
            )
        ]
        transcript_context: list[dict[str, object]] = [
            {
                "speaker": turn.speaker,
                "sequence_number": turn.sequence_number,
                "transcript_text": turn.transcript_text,
            }
            for turn in prior_turns[-4:]
        ]
        transcript_context.append(
            {
                "speaker": payload.speaker,
                "sequence_number": payload.sequence_number,
                "transcript_text": payload.transcript_text,
            }
        )
        return transcript_context

    def _get_current_plan_context(
        self,
        *,
        plan: InterviewPlanPayload,
        payload: TranscriptTurnRequest,
    ) -> tuple[InterviewQuestion, int]:
        fallback_competency_index = min(
            plan.current_competency_index,
            max(len(plan.competencies) - 1, 0),
        )
        current_index = min(payload.sequence_number // 2, len(plan.questions) - 1)
        current_question = plan.questions[current_index]
        return current_question, self._get_competency_index_for_question(
            plan=plan,
            question=current_question,
            fallback_index=fallback_competency_index,
        )

    def _get_competency_index_for_question(
        self,
        *,
        plan: InterviewPlanPayload,
        question: InterviewQuestion,
        fallback_index: int,
    ) -> int:
        current_target_name = (
            question.target_competency.en.casefold()
            if question.target_competency is not None
            else question.dimension_name.en.casefold()
        )

        for competency_index, competency in enumerate(plan.competencies):
            if competency.name.en.casefold() == current_target_name:
                return competency_index

        return fallback_index

    async def _evaluate_answer(
        self,
        *,
        plan: InterviewPlanPayload,
        current_competency_index: int,
        current_question: InterviewQuestion,
        answer_text: str,
        transcript_context: Sequence[Mapping[str, object]],
    ) -> AnswerEvaluation:
        semantic_evaluation = await self._evaluate_answer_semantically(
            plan=plan,
            current_competency_index=current_competency_index,
            current_question=current_question,
            answer_text=answer_text,
            transcript_context=transcript_context,
        )
        if semantic_evaluation is not None:
            return semantic_evaluation
        return self._evaluate_answer_heuristically(
            plan=plan,
            current_competency_index=current_competency_index,
            current_question=current_question,
            answer_text=answer_text,
        )

    async def _evaluate_answer_semantically(
        self,
        *,
        plan: InterviewPlanPayload,
        current_competency_index: int,
        current_question: InterviewQuestion,
        answer_text: str,
        transcript_context: Sequence[Mapping[str, object]],
    ) -> AnswerEvaluation | None:
        current_competency = (
            plan.competencies[current_competency_index]
            if current_competency_index < len(plan.competencies)
            else None
        )
        try:
            semantic = await self._semantic_evaluator.evaluate(
                plan_payload=plan.model_dump(mode="json"),
                current_question=current_question.model_dump(mode="json"),
                current_competency=current_competency.model_dump(mode="json")
                if current_competency is not None
                else None,
                answer_text=answer_text,
                recent_plan_events=[
                    event.model_dump(mode="json")
                    for event in plan.plan_events[-4:]
                ],
                transcript_context=transcript_context,
            )
        except Exception:
            logger.debug("semantic answer evaluation unavailable; falling back to heuristics", exc_info=True)
            return None

        return self._translate_semantic_evaluation(
            plan=plan,
            current_competency_index=current_competency_index,
            current_question=current_question,
            answer_text=answer_text,
            semantic=semantic,
        )

    def _translate_semantic_evaluation(
        self,
        *,
        plan: InterviewPlanPayload,
        current_competency_index: int,
        current_question: InterviewQuestion,
        answer_text: str,
        semantic: InterviewSemanticAnswerEvaluation,
    ) -> AnswerEvaluation | None:
        thresholds = (
            plan.active_policy.global_thresholds
            if plan.active_policy is not None
            else InterviewPolicyThresholds()
        )
        default_threshold = thresholds.semantic_default_confidence_threshold
        move_on_threshold = thresholds.semantic_move_on_confidence_threshold
        recovery_threshold = thresholds.semantic_recovery_confidence_threshold
        wrap_up_threshold = max(
            thresholds.wrap_up_confidence_threshold,
            thresholds.semantic_default_confidence_threshold,
        )
        confidence_gate = {
            "continue": default_threshold,
            "clarify": default_threshold,
            "move_on": move_on_threshold,
            "recovery": recovery_threshold,
            "wrap_up": wrap_up_threshold,
        }
        if semantic.confidence < confidence_gate[semantic.recommended_action]:
            return None

        evidence_excerpt = BilingualText(
            vi=answer_text.strip()[:220],
            en=answer_text.strip()[:220],
        )
        competency = (
            plan.competencies[current_competency_index]
            if current_competency_index < len(plan.competencies)
            else None
        )
        current_coverage = competency.current_coverage if competency is not None else 0.0
        has_more_competencies = current_competency_index < max(len(plan.competencies) - 1, 0)
        next_competency_name = (
            plan.competencies[current_competency_index + 1].name
            if has_more_competencies and current_competency_index + 1 < len(plan.competencies)
            else current_question.target_competency or current_question.dimension_name
        )
        coverage_gain_map = {
            "strong": 0.36,
            "partial": 0.22,
            "low_signal": 0.06,
            "off_topic": 0.0,
            "explicit_gap": 0.0,
            "inconsistent": 0.08,
        }
        coverage_gain = coverage_gain_map[semantic.answer_quality]
        if semantic.evidence_progress == "unchanged":
            coverage_gain = min(coverage_gain, 0.08)
        if semantic.evidence_progress == "regressed":
            coverage_gain = 0.0
        evidence_increment = (
            1
            if semantic.evidence_progress == "improved"
            and semantic.answer_quality in {"strong", "partial"}
            else 0
        )

        if semantic.recommended_action == "recovery":
            return AnswerEvaluation(
                coverage_gain=max(coverage_gain, 0.12),
                evidence_increment=0,
                is_generic=False,
                has_inconsistency=True,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=semantic.needs_hr_review,
                chosen_action="ask_recovery",
                confidence=semantic.confidence,
                reason=semantic.reason,
                next_intended_step=BilingualText(
                    vi="Làm rõ timeline, vai trò sở hữu và kết quả thực tế trước khi tiếp tục.",
                    en="Clarify the timeline, ownership, and actual outcome before continuing.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=semantic.needs_hr_review,
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule="semantic_answer_recovery",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="recovery",
                semantic_evaluation=semantic,
            )

        if semantic.recommended_action == "clarify":
            return AnswerEvaluation(
                coverage_gain=max(coverage_gain, 0.08),
                evidence_increment=0,
                is_generic=semantic.answer_quality in {"low_signal", "off_topic"},
                has_inconsistency=False,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=semantic.needs_hr_review,
                chosen_action="ask_clarification",
                confidence=semantic.confidence,
                reason=semantic.reason,
                next_intended_step=BilingualText(
                    vi="Yêu cầu ứng viên bổ sung bối cảnh, hành động và kết quả đo được.",
                    en="Ask the candidate to add context, actions, and measurable outcomes.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=semantic.needs_hr_review,
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule="semantic_answer_clarify",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="clarification",
                semantic_evaluation=semantic,
            )

        if semantic.recommended_action == "wrap_up":
            return AnswerEvaluation(
                coverage_gain=max(coverage_gain, 1.0 - current_coverage),
                evidence_increment=max(1, evidence_increment),
                is_generic=False,
                has_inconsistency=False,
                should_advance=True,
                should_wrap_up=True,
                should_escalate=semantic.needs_hr_review,
                chosen_action="prepare_wrap_up",
                confidence=semantic.confidence,
                reason=semantic.reason,
                next_intended_step=BilingualText(
                    vi="Tóm tắt tín hiệu chính và kết thúc buổi phỏng vấn.",
                    en="Summarize the key signals and close the interview.",
                ),
                decision_status="ready_to_wrap",
                next_phase="wrap_up",
                decision_rule="semantic_answer_wrap_up",
                evidence_excerpt=evidence_excerpt,
                semantic_evaluation=semantic,
            )

        if semantic.recommended_action == "move_on":
            resolved_move_on = (
                semantic.answer_quality in {"strong", "partial"}
                and semantic.evidence_progress == "improved"
            )
            if resolved_move_on:
                if has_more_competencies:
                    return AnswerEvaluation(
                        coverage_gain=max(coverage_gain, 0.24),
                        evidence_increment=max(1, evidence_increment),
                        is_generic=False,
                        has_inconsistency=False,
                        should_advance=True,
                        should_wrap_up=False,
                        should_escalate=semantic.needs_hr_review,
                        chosen_action="advance_to_next_competency",
                        confidence=semantic.confidence,
                        reason=semantic.reason,
                        next_intended_step=BilingualText(
                            vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                            en=f"Move on to validate the next competency: {next_competency_name.en}.",
                        ),
                        decision_status=self._runtime_decision_status(
                            needs_hr_review=semantic.needs_hr_review,
                            default_status="continue",
                        ),
                        next_phase="deep_dive",
                        decision_rule="semantic_answer_move_on",
                        evidence_excerpt=evidence_excerpt,
                        semantic_evaluation=semantic,
                    )
                return AnswerEvaluation(
                    coverage_gain=max(coverage_gain, 1.0 - current_coverage),
                    evidence_increment=max(1, evidence_increment),
                    is_generic=False,
                    has_inconsistency=False,
                    should_advance=True,
                    should_wrap_up=True,
                    should_escalate=semantic.needs_hr_review,
                    chosen_action="prepare_wrap_up",
                    confidence=semantic.confidence,
                    reason=semantic.reason,
                    next_intended_step=BilingualText(
                        vi="Tóm tắt tín hiệu chính và kết thúc buổi phỏng vấn.",
                        en="Summarize the key signals and close the interview.",
                    ),
                    decision_status="ready_to_wrap",
                    next_phase="wrap_up",
                    decision_rule="semantic_answer_move_on",
                    evidence_excerpt=evidence_excerpt,
                    semantic_evaluation=semantic,
                )
            return AnswerEvaluation(
                coverage_gain=0.0,
                evidence_increment=0,
                is_generic=semantic.answer_quality in {"low_signal", "off_topic"},
                has_inconsistency=False,
                should_advance=has_more_competencies,
                should_wrap_up=not has_more_competencies,
                should_escalate=semantic.needs_hr_review,
                chosen_action="move_on_from_unresolved_competency",
                confidence=semantic.confidence,
                reason=semantic.reason,
                next_intended_step=(
                    BilingualText(
                        vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                        en=f"Move on to validate the next competency: {next_competency_name.en}.",
                    )
                    if has_more_competencies
                    else BilingualText(
                        vi="Tổng kết các khoảng trống bằng chứng còn lại rồi kết thúc buổi phỏng vấn.",
                        en="Summarize the remaining evidence gaps and close the interview.",
                    )
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=semantic.needs_hr_review,
                    default_status="adjust" if has_more_competencies else "ready_to_wrap",
                ),
                next_phase="deep_dive" if has_more_competencies else "wrap_up",
                decision_rule="semantic_answer_move_on",
                evidence_excerpt=evidence_excerpt,
                semantic_evaluation=semantic,
            )

        return AnswerEvaluation(
            coverage_gain=max(coverage_gain, 0.14),
            evidence_increment=evidence_increment,
            is_generic=semantic.answer_quality == "low_signal",
            has_inconsistency=False,
            should_advance=False,
            should_wrap_up=False,
            should_escalate=semantic.needs_hr_review,
            chosen_action="continue_current_competency",
            confidence=semantic.confidence,
            reason=semantic.reason,
            next_intended_step=BilingualText(
                vi="Tiếp tục đào sâu năng lực hiện tại để hoàn thiện coverage.",
                en="Keep probing the current competency to complete coverage.",
            ),
            decision_status=self._runtime_decision_status(
                needs_hr_review=semantic.needs_hr_review,
                default_status="continue",
            ),
            next_phase="deep_dive",
            decision_rule="semantic_answer_continue",
            evidence_excerpt=evidence_excerpt,
            semantic_evaluation=semantic,
        )

    def _evaluate_answer_heuristically(
        self,
        *,
        plan: InterviewPlanPayload,
        current_competency_index: int,
        current_question: InterviewQuestion,
        answer_text: str,
    ) -> AnswerEvaluation:
        normalized_answer = answer_text.strip()
        lowered_text = normalized_answer.casefold()
        thresholds = plan.active_policy.global_thresholds if plan.active_policy is not None else InterviewPolicyThresholds()
        competency_override = self._get_competency_override(plan, current_question)
        evidence_excerpt = BilingualText(
            vi=normalized_answer[:220],
            en=normalized_answer[:220],
        )
        token_hits = sum(
            1
            for token in ["%", "percent", "x", "ms", "million", "kpi", "because", "therefore"]
            if token in lowered_text
        )
        example_hits = sum(
            1
            for token in [
                "ví dụ",
                "example",
                "for example",
                "chẳng hạn",
                "bối cảnh",
                "context",
                "kết quả",
                "result",
                "action",
                "hành động",
            ]
            if token in lowered_text
        )
        has_inconsistency = self._has_recovery_signal(lowered_text)
        specificity_score = min(len(normalized_answer) / 180, 1.0)
        evidence_strength = min(
            1.0,
            specificity_score * 0.45
            + token_hits * thresholds.measurable_signal_bonus
            + example_hits * thresholds.example_signal_bonus,
        )
        generic_min_length = thresholds.generic_answer_min_length
        generic_threshold = thresholds.generic_answer_evidence_threshold
        strong_threshold = thresholds.strong_evidence_threshold
        if competency_override is not None:
            generic_threshold = min(1.0, generic_threshold + competency_override.clarification_bias * 0.1)
            strong_threshold = min(1.0, strong_threshold + competency_override.escalation_bias * 0.05)
        if competency_override is not None and competency_override.require_measurable_outcome and token_hits == 0:
            evidence_strength = max(0.0, evidence_strength - 0.12)
        is_generic = len(normalized_answer) < generic_min_length or evidence_strength < generic_threshold
        has_capability_gap = self._has_capability_gap_signal(lowered_text)

        competency = (
            plan.competencies[current_competency_index]
            if current_competency_index < len(plan.competencies)
            else None
        )
        target_question_count = competency.target_question_count if competency is not None else 1
        if competency_override is not None:
            target_question_count = max(
                1,
                round(target_question_count * competency_override.coverage_target_multiplier),
            )
        current_coverage = competency.current_coverage if competency is not None else 0.0
        evidence_increment = 1 if evidence_strength >= strong_threshold else 0
        coverage_gain = min(0.7, max(0.18, evidence_strength * 0.6)) if not is_generic else 0.08
        next_coverage = min(1.0, current_coverage + coverage_gain)
        should_advance = next_coverage >= 1.0 or (
            competency is not None
            and (
                competency.evidence_collected_count + evidence_increment >= target_question_count
                or evidence_strength >= min(1.0, strong_threshold + 0.05)
            )
            and evidence_strength >= strong_threshold
        )
        all_remaining_covered = current_competency_index >= max(len(plan.competencies) - 1, 0)
        should_wrap_up = should_advance and all_remaining_covered
        consecutive_adjustments = sum(
            1
            for event in plan.plan_events[-thresholds.escalate_after_consecutive_adjustments :]
            if event.chosen_action in {"ask_clarification", "ask_recovery"}
        )
        should_escalate = has_inconsistency or (
            len(plan.plan_events) >= thresholds.escalate_after_consecutive_adjustments
            and consecutive_adjustments >= thresholds.escalate_after_consecutive_adjustments
        )
        has_more_competencies = current_competency_index < max(len(plan.competencies) - 1, 0)
        clarification_attempts_for_competency = self._count_competency_adjustments(
            plan=plan,
            competency_name=current_question.target_competency or current_question.dimension_name,
            chosen_actions={"ask_clarification"},
        )

        if has_inconsistency:
            return AnswerEvaluation(
                coverage_gain=0.12,
                evidence_increment=0,
                is_generic=False,
                has_inconsistency=True,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=current_question.question_type == "recovery",
                chosen_action="ask_recovery",
                confidence=0.66,
                reason=BilingualText(
                    vi="Câu trả lời có tín hiệu mâu thuẫn về timeline hoặc mức độ sở hữu nên cần hỏi recovery trung tính.",
                    en="The answer shows timeline or ownership inconsistencies, so the plan adds a neutral recovery question.",
                ),
                next_intended_step=BilingualText(
                    vi="Làm rõ timeline, vai trò sở hữu và kết quả thực tế trước khi tiếp tục.",
                    en="Clarify the timeline, ownership, and actual outcome before continuing.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=current_question.question_type == "recovery",
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule="recovery_signal_detected",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="recovery",
            )
        if has_capability_gap:
            next_competency_name = (
                plan.competencies[current_competency_index + 1].name
                if has_more_competencies and current_competency_index + 1 < len(plan.competencies)
                else current_question.target_competency or current_question.dimension_name
            )
            return AnswerEvaluation(
                coverage_gain=0.0,
                evidence_increment=0,
                is_generic=False,
                has_inconsistency=False,
                should_advance=has_more_competencies,
                should_wrap_up=not has_more_competencies,
                should_escalate=False,
                chosen_action="move_on_from_unresolved_competency",
                confidence=0.78,
                reason=BilingualText(
                    vi="Ứng viên nói rõ chưa có kinh nghiệm với chủ đề này, nên plan ghi nhận gap và chuyển sang competency khác.",
                    en="The candidate explicitly lacks experience with this topic, so the plan records the gap and moves on.",
                ),
                next_intended_step=(
                    BilingualText(
                        vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                        en=f"Move on to validate the next competency: {next_competency_name.en}.",
                    )
                    if has_more_competencies
                    else BilingualText(
                        vi="Tổng kết các khoảng trống bằng chứng còn lại rồi kết thúc buổi phỏng vấn.",
                        en="Summarize the remaining evidence gaps and close the interview.",
                    )
                ),
                decision_status="adjust" if has_more_competencies else "ready_to_wrap",
                next_phase="deep_dive" if has_more_competencies else "wrap_up",
                decision_rule="explicit_capability_gap_move_on",
                evidence_excerpt=evidence_excerpt,
            )
        if (
            is_generic
            and clarification_attempts_for_competency
            >= thresholds.max_clarification_turns_per_competency
        ):
            next_competency_name = (
                plan.competencies[current_competency_index + 1].name
                if has_more_competencies and current_competency_index + 1 < len(plan.competencies)
                else current_question.target_competency or current_question.dimension_name
            )
            return AnswerEvaluation(
                coverage_gain=0.0,
                evidence_increment=0,
                is_generic=True,
                has_inconsistency=False,
                should_advance=has_more_competencies,
                should_wrap_up=not has_more_competencies,
                should_escalate=False,
                chosen_action="move_on_from_unresolved_competency",
                confidence=0.74,
                reason=BilingualText(
                    vi="Ứng viên đã được hỏi làm rõ nhưng vẫn chưa tạo thêm bằng chứng đủ dùng, nên plan chuyển sang competency khác để tránh lặp.",
                    en="The candidate was already asked to clarify but still did not add usable evidence, so the plan moves on to avoid looping.",
                ),
                next_intended_step=(
                    BilingualText(
                        vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                        en=f"Move on to validate the next competency: {next_competency_name.en}.",
                    )
                    if has_more_competencies
                    else BilingualText(
                        vi="Tổng kết các khoảng trống bằng chứng còn lại rồi kết thúc buổi phỏng vấn.",
                        en="Summarize the remaining evidence gaps and close the interview.",
                    )
                ),
                decision_status="adjust" if has_more_competencies else "ready_to_wrap",
                next_phase="deep_dive" if has_more_competencies else "wrap_up",
                decision_rule="low_signal_answer_after_clarification_move_on",
                evidence_excerpt=evidence_excerpt,
            )
        if is_generic:
            return AnswerEvaluation(
                coverage_gain=coverage_gain,
                evidence_increment=0,
                is_generic=True,
                has_inconsistency=False,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=should_escalate,
                chosen_action="ask_clarification",
                confidence=0.72,
                reason=BilingualText(
                    vi="Câu trả lời còn chung chung nên plan chuyển sang câu hỏi làm rõ sâu hơn.",
                    en="The answer is still generic, so the plan shifts to a deeper clarification question.",
                ),
                next_intended_step=BilingualText(
                    vi="Yêu cầu ứng viên bổ sung bối cảnh, hành động và kết quả đo được.",
                    en="Ask the candidate to add context, actions, and measurable outcomes.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=should_escalate,
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule="generic_answer_needs_clarification",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="clarification",
            )
        if should_wrap_up:
            return AnswerEvaluation(
                coverage_gain=coverage_gain,
                evidence_increment=max(1, evidence_increment),
                is_generic=False,
                has_inconsistency=False,
                should_advance=True,
                should_wrap_up=True,
                should_escalate=False,
                chosen_action="prepare_wrap_up",
                confidence=thresholds.wrap_up_confidence_threshold,
                reason=BilingualText(
                    vi="Các năng lực trọng tâm đã có đủ bằng chứng nên plan chuyển sang bước wrap-up.",
                    en="The core competencies have enough evidence, so the plan moves to wrap-up.",
                ),
                next_intended_step=BilingualText(
                    vi="Tóm tắt tín hiệu chính và kết thúc buổi phỏng vấn.",
                    en="Summarize the key signals and close the interview.",
                ),
                decision_status="ready_to_wrap",
                next_phase="wrap_up",
                decision_rule="all_competencies_covered_prepare_wrap_up",
                evidence_excerpt=evidence_excerpt,
            )
        if should_advance:
            next_competency_name = (
                plan.competencies[current_competency_index + 1].name
                if current_competency_index + 1 < len(plan.competencies)
                else current_question.target_competency or current_question.dimension_name
            )
            return AnswerEvaluation(
                coverage_gain=coverage_gain,
                evidence_increment=max(1, evidence_increment),
                is_generic=False,
                has_inconsistency=False,
                should_advance=True,
                should_wrap_up=False,
                should_escalate=False,
                chosen_action="advance_to_next_competency",
                confidence=0.84,
                reason=BilingualText(
                    vi="Đã có đủ ví dụ cụ thể cho năng lực hiện tại nên plan chuyển sang năng lực ưu tiên tiếp theo.",
                    en="Enough concrete evidence was collected for the current competency, so the plan advances to the next priority competency.",
                ),
                next_intended_step=BilingualText(
                    vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                    en=f"Move on to validate the next competency: {next_competency_name.en}.",
                ),
                decision_status="continue",
                next_phase="deep_dive",
                decision_rule="advance_after_sufficient_evidence",
                evidence_excerpt=evidence_excerpt,
            )
        return AnswerEvaluation(
            coverage_gain=coverage_gain,
            evidence_increment=max(1, evidence_increment),
            is_generic=False,
            has_inconsistency=False,
            should_advance=False,
            should_wrap_up=False,
            should_escalate=False,
            chosen_action="continue_current_competency",
            confidence=0.79,
            reason=BilingualText(
                vi="Câu trả lời có tín hiệu cụ thể nhưng chưa đủ để đóng competency, nên tiếp tục đào sâu.",
                en="The answer is concrete but not sufficient to close the competency, so the plan keeps probing.",
            ),
            next_intended_step=BilingualText(
                vi="Tiếp tục đào sâu năng lực hiện tại để hoàn thiện coverage.",
                en="Keep probing the current competency to complete coverage.",
            ),
            decision_status="continue",
            next_phase="deep_dive",
            decision_rule="continue_current_competency",
            evidence_excerpt=evidence_excerpt,
        )

    def _has_recovery_signal(self, lowered_text: str) -> bool:
        recovery_markers = [
            "mâu thuẫn",
            "contradict",
            "timeline",
            "thời gian",
            "actually",
            "thực ra",
            "i alone",
            "một mình",
            "lead toàn bộ",
            "tự làm hết",
        ]
        return any(marker in lowered_text for marker in recovery_markers)

    def _has_capability_gap_signal(self, lowered_text: str) -> bool:
        capability_gap_markers = [
            "không biết",
            "chua biet",
            "chưa biết",
            "không rành",
            "chưa dùng",
            "chua dung",
            "chưa làm",
            "chua lam",
            "không làm",
            "không có kinh nghiệm",
            "chưa có kinh nghiệm",
            "never used",
            "have not used",
            "haven't used",
            "don't know",
            "do not know",
            "not familiar",
            "no experience",
        ]
        return any(marker in lowered_text for marker in capability_gap_markers)

    def _count_competency_adjustments(
        self,
        *,
        plan: InterviewPlanPayload,
        competency_name: BilingualText,
        chosen_actions: set[str],
    ) -> int:
        return sum(
            1
            for event in plan.plan_events
            if event.chosen_action in chosen_actions
            and event.affected_competency is not None
            and event.affected_competency.en.casefold() == competency_name.en.casefold()
        )

    def _get_competency_override(
        self,
        plan: InterviewPlanPayload,
        current_question: InterviewQuestion,
    ) -> InterviewCompetencyPolicyOverride | None:
        if plan.active_policy is None:
            return None
        target_name = (
            current_question.target_competency.en.casefold()
            if current_question.target_competency is not None
            else current_question.dimension_name.en.casefold()
        )
        for item in plan.active_policy.competency_overrides:
            if item.competency_name.en.casefold() == target_name:
                return item
        return None

    def _apply_policy_to_plan(self, plan: InterviewPlanPayload) -> None:
        if plan.active_policy is None:
            return
        overrides = {
            item.competency_name.en.casefold(): item
            for item in plan.active_policy.competency_overrides
            if item.competency_name.en.strip()
        }
        updated_competencies: list[InterviewCompetencyPlan] = []
        for competency in plan.competencies:
            override = overrides.get(competency.name.en.casefold())
            if override is None:
                updated_competencies.append(competency)
                continue
            updated = competency.model_copy(deep=True)
            updated.target_question_count = max(
                1,
                round(updated.target_question_count * override.coverage_target_multiplier),
            )
            updated.priority = max(1, updated.priority - round(override.priority_boost))
            updated.evidence_needed.append(
                BilingualText(
                    vi="Ưu tiên thêm ví dụ đo được do competency này từng có sai lệch giữa AI và HR.",
                    en="Prioritize more measurable examples because this competency previously showed AI-HR disagreement.",
                )
            )
            updated_competencies.append(updated)
        plan.competencies = updated_competencies

    def _derive_evaluation_from_event(
        self,
        *,
        plan: InterviewPlanPayload,
        current_competency_index: int,
        current_question: InterviewQuestion,
        event: InterviewPlanEvent,
    ) -> AnswerEvaluation:
        competency = (
            plan.competencies[current_competency_index]
            if current_competency_index < len(plan.competencies)
            else None
        )
        current_coverage = competency.current_coverage if competency is not None else 0.0
        evidence_excerpt = event.evidence_excerpt or BilingualText(
            vi=event.reason.vi,
            en=event.reason.en,
        )
        next_competency_name = (
            plan.competencies[current_competency_index + 1].name
            if current_competency_index + 1 < len(plan.competencies)
            else current_question.target_competency or current_question.dimension_name
        )
        if event.chosen_action == "ask_recovery":
            return AnswerEvaluation(
                coverage_gain=0.12,
                evidence_increment=0,
                is_generic=False,
                has_inconsistency=True,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=current_question.question_type == "recovery",
                chosen_action=event.chosen_action,
                confidence=event.confidence or 0.66,
                reason=event.reason,
                next_intended_step=BilingualText(
                    vi="Làm rõ timeline, vai trò sở hữu và kết quả thực tế trước khi tiếp tục.",
                    en="Clarify the timeline, ownership, and actual outcome before continuing.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=(
                        event.semantic_evaluation.needs_hr_review
                        if event.semantic_evaluation is not None
                        else current_question.question_type == "recovery"
                    ),
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule=event.decision_rule or "recovery_signal_detected",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="recovery",
                semantic_evaluation=event.semantic_evaluation,
            )
        if event.chosen_action == "ask_clarification":
            return AnswerEvaluation(
                coverage_gain=0.08,
                evidence_increment=0,
                is_generic=True,
                has_inconsistency=False,
                should_advance=False,
                should_wrap_up=False,
                should_escalate=False,
                chosen_action=event.chosen_action,
                confidence=event.confidence or 0.72,
                reason=event.reason,
                next_intended_step=BilingualText(
                    vi="Yêu cầu ứng viên bổ sung bối cảnh, hành động và kết quả đo được.",
                    en="Ask the candidate to add context, actions, and measurable outcomes.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=(
                        event.semantic_evaluation is not None and event.semantic_evaluation.needs_hr_review
                    ),
                    default_status="adjust",
                ),
                next_phase=plan.current_phase or "competency_validation",
                decision_rule=event.decision_rule or "generic_answer_needs_clarification",
                evidence_excerpt=evidence_excerpt,
                adaptive_question_type="clarification",
                semantic_evaluation=event.semantic_evaluation,
            )
        if event.chosen_action == "move_on_from_unresolved_competency":
            has_more_competencies = current_competency_index + 1 < len(plan.competencies)
            return AnswerEvaluation(
                coverage_gain=0.0,
                evidence_increment=0,
                is_generic=False,
                has_inconsistency=False,
                should_advance=has_more_competencies,
                should_wrap_up=not has_more_competencies,
                should_escalate=False,
                chosen_action=event.chosen_action,
                confidence=event.confidence or 0.78,
                reason=event.reason,
                next_intended_step=(
                    BilingualText(
                        vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                        en=f"Move on to validate the next competency: {next_competency_name.en}.",
                    )
                    if has_more_competencies
                    else BilingualText(
                        vi="Tổng kết các khoảng trống bằng chứng còn lại rồi kết thúc buổi phỏng vấn.",
                        en="Summarize the remaining evidence gaps and close the interview.",
                    )
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=(
                        event.semantic_evaluation is not None and event.semantic_evaluation.needs_hr_review
                    ),
                    default_status="adjust" if has_more_competencies else "ready_to_wrap",
                ),
                next_phase="deep_dive" if has_more_competencies else "wrap_up",
                decision_rule=event.decision_rule or "explicit_capability_gap_move_on",
                evidence_excerpt=evidence_excerpt,
                semantic_evaluation=event.semantic_evaluation,
            )
        if event.chosen_action == "prepare_wrap_up":
            return AnswerEvaluation(
                coverage_gain=max(0.0, 1.0 - current_coverage),
                evidence_increment=1,
                is_generic=False,
                has_inconsistency=False,
                should_advance=True,
                should_wrap_up=True,
                should_escalate=False,
                chosen_action=event.chosen_action,
                confidence=event.confidence or 0.91,
                reason=event.reason,
                next_intended_step=BilingualText(
                    vi="Tóm tắt tín hiệu chính và kết thúc buổi phỏng vấn.",
                    en="Summarize the key signals and close the interview.",
                ),
                decision_status="ready_to_wrap",
                next_phase="wrap_up",
                decision_rule=event.decision_rule or "all_competencies_covered_prepare_wrap_up",
                evidence_excerpt=evidence_excerpt,
                semantic_evaluation=event.semantic_evaluation,
            )
        if event.chosen_action == "advance_to_next_competency":
            return AnswerEvaluation(
                coverage_gain=max(0.0, 1.0 - current_coverage),
                evidence_increment=1,
                is_generic=False,
                has_inconsistency=False,
                should_advance=True,
                should_wrap_up=False,
                should_escalate=False,
                chosen_action=event.chosen_action,
                confidence=event.confidence or 0.84,
                reason=event.reason,
                next_intended_step=BilingualText(
                    vi=f"Chuyển sang xác minh năng lực tiếp theo: {next_competency_name.vi}.",
                    en=f"Move on to validate the next competency: {next_competency_name.en}.",
                ),
                decision_status=self._runtime_decision_status(
                    needs_hr_review=(
                        event.semantic_evaluation is not None and event.semantic_evaluation.needs_hr_review
                    ),
                    default_status="continue",
                ),
                next_phase="deep_dive",
                decision_rule=event.decision_rule or "advance_after_sufficient_evidence",
                evidence_excerpt=evidence_excerpt,
                semantic_evaluation=event.semantic_evaluation,
            )
        return AnswerEvaluation(
            coverage_gain=0.2,
            evidence_increment=1,
            is_generic=False,
            has_inconsistency=False,
            should_advance=False,
            should_wrap_up=False,
            should_escalate=False,
            chosen_action=event.chosen_action,
            confidence=event.confidence or 0.79,
            reason=event.reason,
            next_intended_step=BilingualText(
                vi="Tiếp tục đào sâu năng lực hiện tại để hoàn thiện coverage.",
                en="Keep probing the current competency to complete coverage.",
            ),
            decision_status=self._runtime_decision_status(
                needs_hr_review=(
                    event.semantic_evaluation is not None and event.semantic_evaluation.needs_hr_review
                ),
                default_status="continue",
            ),
            next_phase="deep_dive",
            decision_rule=event.decision_rule or "continue_current_competency",
            evidence_excerpt=evidence_excerpt,
            semantic_evaluation=event.semantic_evaluation,
        )

    def _build_contextual_adaptive_prompt(
        self,
        *,
        current_question: InterviewQuestion,
        adaptive_question_type: str | None,
    ) -> BilingualText:
        reference_vi = current_question.prompt.vi.strip() or "câu hỏi vừa rồi"
        reference_en = current_question.prompt.en.strip() or "the previous question"
        if adaptive_question_type == "recovery":
            return BilingualText(
                vi=(
                    f'Quay lại câu hỏi "{reference_vi}", tôi muốn làm rõ timeline và phần bạn trực tiếp sở hữu '
                    "trong ví dụ này. Bạn có thể trình bày theo thứ tự thời gian, tách rõ việc bạn trực tiếp làm, "
                    "phần phối hợp với người khác và kết quả cuối cùng không?"
                ),
                en=(
                    f'Going back to the question "{reference_en}", I want to clarify the timeline and the part you '
                    "directly owned in that example. Can you walk through it chronologically, separate what you did "
                    "yourself from what was collaborative, and explain the final outcome?"
                ),
            )
        return BilingualText(
            vi=(
                f'Quay lại câu hỏi "{reference_vi}", bạn hãy đưa một ví dụ thật cụ thể, nêu rõ bối cảnh, '
                "hành động trực tiếp của bạn và kết quả đo được."
            ),
            en=(
                f'Going back to the question "{reference_en}", please share one concrete example with the context, '
                "your direct actions, and a measurable outcome."
            ),
        )

    def _build_adaptive_question(
        self,
        *,
        current_question: InterviewQuestion,
        event: InterviewPlanEvent,
        evaluation: AnswerEvaluation,
    ) -> dict[str, object]:
        prompt = self._build_contextual_adaptive_prompt(
            current_question=current_question,
            adaptive_question_type=evaluation.adaptive_question_type,
        )
        if evaluation.adaptive_question_type == "recovery":
            return {
                "question_index": (event.question_index or 0) + 1,
                "dimension_name": event.affected_competency.model_dump(mode="json")
                if event.affected_competency is not None
                else {"vi": "Recovery", "en": "Recovery"},
                "prompt": prompt.model_dump(mode="json"),
                "purpose": {
                    "vi": "Làm rõ tín hiệu mâu thuẫn về timeline hoặc ownership mà không giả định ứng viên sai.",
                    "en": "Clarify timeline or ownership inconsistencies without assuming the candidate is wrong.",
                },
                "source": "adaptive",
                "question_type": "recovery",
                "rationale": event.reason.en,
                "priority": (event.question_index or 0) + 1,
                "target_competency": event.affected_competency.model_dump(mode="json")
                if event.affected_competency is not None
                else None,
                "evidence_gap": {
                    "vi": "Cần làm rõ timeline, ownership hoặc claim để xác minh bằng chứng.",
                    "en": "Need to clarify the timeline, ownership, or claim before trusting the evidence.",
                },
                "selection_reason": event.reason.model_dump(mode="json"),
                "transition_on_strong_answer": "advance_to_next_competency",
                "transition_on_weak_answer": "ask_recovery",
            }
        return {
            "question_index": (event.question_index or 0) + 1,
            "dimension_name": event.affected_competency.model_dump(mode="json")
            if event.affected_competency is not None
            else {"vi": "Làm rõ", "en": "Clarification"},
            "prompt": prompt.model_dump(mode="json"),
            "purpose": {
                "vi": "Bổ sung bằng chứng cụ thể cho năng lực hiện tại.",
                "en": "Collect more concrete evidence for the current competency.",
            },
            "source": "adaptive",
            "question_type": "clarification",
            "rationale": event.reason.en,
            "priority": (event.question_index or 0) + 1,
            "target_competency": event.affected_competency.model_dump(mode="json")
            if event.affected_competency is not None
            else None,
            "evidence_gap": {
                "vi": "Câu trả lời trước còn thiếu ví dụ và kết quả đo được.",
                "en": "The previous answer still lacks a concrete example and measurable outcome.",
            },
            "selection_reason": event.reason.model_dump(mode="json"),
            "transition_on_strong_answer": "advance_to_next_competency",
            "transition_on_weak_answer": "ask_clarification",
        }

    def _append_plan_event_to_payload(
        self,
        payload: dict[str, object],
        event: InterviewPlanEvent,
    ) -> dict[str, object]:
        next_payload = dict(payload)
        plan_events = list(_as_object_list(next_payload.get("plan_events")) or [])
        plan_events.append(event.model_dump(mode="json"))
        next_payload["plan_events"] = plan_events
        return next_payload

    def _apply_adaptive_plan_update(
        self,
        payload: dict[str, object],
        event: InterviewPlanEvent,
    ) -> dict[str, object]:
        next_payload = self._append_plan_event_to_payload(payload, event)
        plan = self._load_plan_payload(next_payload)
        if plan is None:
            return next_payload

        fallback_competency_index = min(
            plan.current_competency_index,
            max(len(plan.competencies) - 1, 0),
        )
        current_question = (
            plan.questions[min(event.question_index, len(plan.questions) - 1)]
            if event.question_index is not None and plan.questions
            else (plan.questions[0] if plan.questions else None)
        )
        if current_question is None:
            return next_payload
        current_competency_index = self._get_competency_index_for_question(
            plan=plan,
            question=current_question,
            fallback_index=fallback_competency_index,
        )

        evaluation = self._derive_evaluation_from_event(
            plan=plan,
            current_competency_index=current_competency_index,
            current_question=current_question,
            event=event,
        )
        competencies_payload = _as_object_list(next_payload.get("competencies"))
        if competencies_payload is not None and current_competency_index < len(competencies_payload):
            updated_competencies: list[object] = list(competencies_payload)
            current_competency_payload = _as_object_mapping(updated_competencies[current_competency_index])
            if current_competency_payload is not None:
                updated_competency = dict(current_competency_payload)
                prior_coverage = updated_competency.get("current_coverage")
                safe_prior_coverage = prior_coverage if isinstance(prior_coverage, int | float) else 0.0
                updated_competency["current_coverage"] = min(
                    1.0,
                    float(safe_prior_coverage) + evaluation.coverage_gain,
                )
                prior_count = updated_competency.get("evidence_collected_count")
                safe_prior_count = prior_count if isinstance(prior_count, int) else 0
                updated_competency["evidence_collected_count"] = (
                    safe_prior_count + evaluation.evidence_increment
                )
                updated_competency["last_updated_at"] = event.created_at
                updated_competency["status"] = (
                    "needs_recovery"
                    if evaluation.adaptive_question_type == "recovery"
                    or event.chosen_action == "move_on_from_unresolved_competency"
                    else "covered"
                    if evaluation.should_advance or evaluation.should_wrap_up
                    else "in_progress"
                )
                updated_competencies[current_competency_index] = updated_competency
            next_competency_payload = (
                _as_object_mapping(updated_competencies[current_competency_index + 1])
                if evaluation.should_advance and current_competency_index + 1 < len(updated_competencies)
                else None
            )
            if next_competency_payload is not None:
                next_competency = dict(next_competency_payload)
                if next_competency.get("status") == "not_started":
                    next_competency["status"] = "in_progress"
                updated_competencies[current_competency_index + 1] = next_competency
            next_payload["competencies"] = updated_competencies

        next_payload["current_phase"] = evaluation.next_phase
        next_payload["next_intended_step"] = evaluation.next_intended_step.model_dump(mode="json")
        next_payload["interview_decision_status"] = evaluation.decision_status
        if evaluation.should_wrap_up:
            next_payload["current_competency_index"] = current_competency_index
        elif evaluation.should_advance and plan.competencies:
            next_payload["current_competency_index"] = min(
                current_competency_index + 1,
                len(plan.competencies) - 1,
            )
        else:
            next_payload["current_competency_index"] = current_competency_index

        if event.event_type != "plan.adjusted" or event.question_index is None:
            return next_payload

        questions_payload = _as_object_list(next_payload.get("questions"))
        if questions_payload is None:
            return next_payload

        adaptive_question = self._build_adaptive_question(
            current_question=current_question,
            event=event,
            evaluation=evaluation,
        )
        insert_index = min(event.question_index + 1, len(questions_payload))
        prompt_payload = _as_object_mapping(adaptive_question.get("prompt"))
        existing_prompt_value = prompt_payload.get("en") if prompt_payload is not None else None
        existing_prompt = existing_prompt_value if isinstance(existing_prompt_value, str) else None
        existing_type = adaptive_question["question_type"]
        target_payload = _as_object_mapping(adaptive_question.get("target_competency"))
        existing_target_value = target_payload.get("en") if target_payload is not None else None
        existing_target = existing_target_value if isinstance(existing_target_value, str) else None
        for item_value in questions_payload:
            item = _as_object_mapping(item_value)
            if item is None:
                continue
            item_prompt = _as_object_mapping(item.get("prompt"))
            item_target = _as_object_mapping(item.get("target_competency"))
            item_prompt_value = item_prompt.get("en") if item_prompt is not None else None
            item_target_value = item_target.get("en") if item_target is not None else None
            item_prompt_en = item_prompt_value if isinstance(item_prompt_value, str) else None
            item_target_en = item_target_value if isinstance(item_target_value, str) else None
            if (
                item_prompt_en == existing_prompt
                and item.get("question_type") == existing_type
                and item_target_en == existing_target
            ):
                return next_payload

        updated_questions: list[object] = list(questions_payload)
        updated_questions.insert(insert_index, adaptive_question)
        for index, item_value in enumerate(updated_questions):
            item = _as_object_mapping(item_value)
            if item is not None:
                updated_item = dict(item)
                updated_item["question_index"] = index
                updated_questions[index] = updated_item
        next_payload["questions"] = updated_questions
        return next_payload

    def _build_current_question_index(
        self,
        *,
        turns: list[InterviewTurn],
        total_questions: int,
    ) -> int:
        if total_questions <= 0:
            return 0

        answered_count = 0
        last_candidate_text: str | None = None

        for turn in turns:
            if not turn.speaker.casefold().startswith("candidate"):
                continue
            normalized_text = turn.transcript_text.strip().casefold()
            if not normalized_text:
                continue
            if last_candidate_text is not None and (
                normalized_text == last_candidate_text
                or normalized_text in last_candidate_text
                or last_candidate_text in normalized_text
            ):
                continue
            answered_count += 1
            last_candidate_text = normalized_text

        return min(answered_count, total_questions - 1)

    def _merge_interview_draft(
        self,
        screening_payload: dict[str, object],
        *,
        manual_questions: list[str],
        question_guidance: str | None,
        approved_questions: list[str],
        generated_questions: list[InterviewQuestionCandidate],
    ) -> dict[str, object]:
        normalized_manual_questions = [
            question.strip() for question in manual_questions if question.strip()
        ]
        normalized_approved_questions = [
            question.strip() for question in approved_questions if question.strip()
        ]
        normalized_guidance = (
            question_guidance.strip()
            if question_guidance and question_guidance.strip()
            else None
        )

        payload = dict(screening_payload)
        interview_draft = _as_object_dict(payload.get("interview_draft")) or {}
        interview_draft["manual_questions"] = normalized_manual_questions
        interview_draft["question_guidance"] = normalized_guidance
        interview_draft["approved_questions"] = normalized_approved_questions
        interview_draft["generated_questions"] = [
            question.model_dump(mode="json") for question in generated_questions
        ]
        payload["interview_draft"] = interview_draft
        return payload
