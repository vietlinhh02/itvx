from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateScreening
from src.models.interview import InterviewRuntimeEvent, InterviewSession
from src.schemas.interview import InterviewRuntimeEventRequest
from src.services.datetime_utils import to_vietnam_isoformat
from src.services.interview_worker_launcher import InterviewWorkerLauncher
from src.services.livekit_service import LiveKitService


RECOVERABLE_WORKER_FAILURE_MARKERS = (
    "go_away",
    "disconnection soon",
    "readtimeout",
    "read timeout",
    "connection reset",
    "connection closed",
    "server disconnected",
)


class InterviewRuntimeService:
    def __init__(
        self,
        db_session: AsyncSession,
        *,
        worker_launcher: InterviewWorkerLauncher | None = None,
        livekit_service: LiveKitService | None = None,
    ) -> None:
        self._db_session = db_session
        self._worker_launcher = worker_launcher or InterviewWorkerLauncher(
            settings.interview_worker_service_url,
            settings.interview_worker_dispatch_timeout_seconds,
        )
        self._livekit = livekit_service or LiveKitService()

    async def record_event(self, session_id: str, payload: InterviewRuntimeEventRequest) -> None:
        session = await self._db_session.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id)
        )
        if session is None:
            raise ValueError("Interview session not found")

        event_time = datetime.now(UTC)
        session.status = payload.session_status or session.status
        session.worker_status = payload.worker_status or session.worker_status
        session.provider_status = payload.provider_status or session.provider_status
        session.last_runtime_event_at = event_time
        if payload.provider_status is not None:
            session.last_provider_event_at = event_time
        if payload.event_type == "agent.session_started":
            session.started_at = session.started_at or event_time
        if payload.event_type == "candidate.left":
            session.disconnect_deadline_at = event_time
            session.last_disconnect_reason = str(payload.payload.get("reason", "candidate_left"))
        if payload.event_type == "candidate.rejoined":
            session.disconnect_deadline_at = None
            session.last_disconnect_reason = None
        if payload.event_type.endswith("failed"):
            session.last_error_code = payload.event_type
            session.last_error_message = str(payload.payload.get("message", "Runtime failure"))
        if payload.event_type == "session.completed":
            session.completed_at = session.completed_at or event_time
            session.disconnect_deadline_at = None

        recovery_event = await self._recover_worker_failure(
            session=session,
            payload=payload,
            event_time=event_time,
        )

        self._db_session.add(
            InterviewRuntimeEvent(
                interview_session_id=session.id,
                event_type=payload.event_type,
                event_source=payload.event_source,
                session_status=payload.session_status,
                worker_status=payload.worker_status,
                provider_status=payload.provider_status,
                payload=payload.payload,
            )
        )
        if recovery_event is not None:
            self._db_session.add(recovery_event)
        await self._db_session.commit()

    async def _recover_worker_failure(
        self,
        *,
        session: InterviewSession,
        payload: InterviewRuntimeEventRequest,
        event_time: datetime,
    ) -> InterviewRuntimeEvent | None:
        if payload.event_type != "worker.failed":
            return None
        if session.summary_payload or session.status in {"completed", "finishing"}:
            return None

        message = str(payload.payload.get("message", ""))
        if not self._is_recoverable_worker_failure(message):
            return None

        deadline = event_time + timedelta(seconds=settings.interview_reconnect_grace_seconds)
        session.status = "reconnecting"
        session.worker_status = "waiting_for_candidate"
        session.provider_status = "provider_reconnecting"
        session.disconnect_deadline_at = deadline
        session.last_disconnect_reason = "provider_disconnect"

        recovery_payload: dict[str, object] = {
            "accepted": False,
            "status": "dispatch_skipped",
            "trigger": "recoverable_worker_failure",
            "reason": "provider_disconnect",
            "source_event_type": payload.event_type,
            "disconnect_deadline_at": to_vietnam_isoformat(deadline),
            "original_message": message,
        }

        screening = await self._db_session.scalar(
            select(CandidateScreening).where(CandidateScreening.id == session.candidate_screening_id)
        )
        if screening is None:
            recovery_payload["status"] = "screening_missing"
            return self._build_recovery_event(session, recovery_payload)

        worker_identity = session.worker_identity or self._livekit.create_worker_identity(session.id)
        session.worker_identity = worker_identity
        worker_token = self._livekit.create_worker_token(
            room_name=session.livekit_room_name,
            identity=worker_identity,
        )

        try:
            dispatch = await self._worker_launcher.launch(
                session_id=session.id,
                room_name=session.livekit_room_name,
                opening_question=session.opening_question,
                worker_token=worker_token,
                jd_id=screening.jd_document_id,
            )
        except Exception as exc:
            recovery_payload["status"] = "dispatch_failed"
            recovery_payload["message"] = str(exc)
            return self._build_recovery_event(session, recovery_payload)

        recovery_payload["accepted"] = dispatch.accepted
        recovery_payload["status"] = dispatch.status
        if dispatch.accepted:
            session.worker_status = "queued"

        return self._build_recovery_event(session, recovery_payload)

    def _build_recovery_event(
        self,
        session: InterviewSession,
        payload: dict[str, object],
    ) -> InterviewRuntimeEvent:
        return InterviewRuntimeEvent(
            interview_session_id=session.id,
            event_type="worker.redispatch_requested",
            event_source="backend",
            session_status=session.status,
            worker_status=session.worker_status,
            provider_status=session.provider_status,
            payload=payload,
        )

    def _is_recoverable_worker_failure(self, message: str) -> bool:
        normalized = message.strip().casefold()
        return any(marker in normalized for marker in RECOVERABLE_WORKER_FAILURE_MARKERS)
