from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.interview import InterviewRuntimeEvent, InterviewSession
from src.schemas.interview import InterviewRuntimeEventRequest


class InterviewRuntimeService:
    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

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
        await self._db_session.commit()
