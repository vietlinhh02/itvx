"""Background job status API routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.models.background_job import BackgroundJob
from src.schemas.cv import BackgroundJobResponse
from src.services.datetime_utils import to_vietnam_isoformat

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=BackgroundJobResponse)
async def get_background_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BackgroundJobResponse:
    """Return the current status for one background job."""
    job = await db.scalar(select(BackgroundJob).where(BackgroundJob.id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="Background job not found")
    poll_after_ms = 1500
    status_message = "Queued for background processing."
    if job.status == "running":
        poll_after_ms = 2500
        status_message = "Background processing is in progress."
    if job.status == "failed":
        poll_after_ms = 0
        status_message = "Background processing failed."
    if job.status == "completed":
        poll_after_ms = 0
        status_message = "Background processing completed."

    return BackgroundJobResponse(
        job_id=job.id,
        job_type=job.job_type,
        status=job.status,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        error_message=job.error_message,
        queued_at=to_vietnam_isoformat(job.created_at),
        started_at=to_vietnam_isoformat(job.started_at),
        completed_at=to_vietnam_isoformat(job.completed_at),
        poll_after_ms=poll_after_ms,
        status_message=status_message,
    )
