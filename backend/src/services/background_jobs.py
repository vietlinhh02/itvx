"""Helpers for claiming and finalizing background jobs."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob, BackgroundJobStatus


class BackgroundJobService:
    """Database-backed queue helpers for background jobs."""

    def __init__(self, db_session: AsyncSession) -> None:
        self._db_session = db_session

    async def claim_next_job(self) -> BackgroundJob | None:
        """Claim the oldest queued job and mark it running."""
        statement = (
            select(BackgroundJob)
            .where(BackgroundJob.status == BackgroundJobStatus.QUEUED)
            .order_by(BackgroundJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = await self._db_session.scalar(statement)
        if job is None:
            await self._db_session.rollback()
            return None
        job.status = BackgroundJobStatus.RUNNING
        job.started_at = datetime.now(UTC).replace(tzinfo=None)
        job.completed_at = None
        job.error_message = None
        await self._db_session.commit()
        await self._db_session.refresh(job)
        return job

    async def mark_completed(self, job: BackgroundJob) -> None:
        """Mark a running job completed."""
        job.status = BackgroundJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC).replace(tzinfo=None)
        job.error_message = None
        await self._db_session.commit()

    async def mark_failed(self, job: BackgroundJob, error_message: str) -> None:
        """Mark a running job failed and persist the error message."""
        job.status = BackgroundJobStatus.FAILED
        job.completed_at = datetime.now(UTC).replace(tzinfo=None)
        job.error_message = error_message
        await self._db_session.commit()
