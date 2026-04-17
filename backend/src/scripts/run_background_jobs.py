"""Run queued JD analysis and CV screening jobs from the database."""

import asyncio
from collections.abc import Awaitable, Callable

from src.database import AsyncSessionLocal
from src.services.background_jobs import BackgroundJobService
from src.services.company_knowledge_service import CompanyKnowledgeService
from src.services.cv_screening_service import CVScreeningService
from src.services.interview_session_service import InterviewSessionService
from src.services.jd_service import JDAnalysisService

JobHandler = Callable[[str], Awaitable[None]]


async def run_once() -> bool:
    """Claim and execute one queued background job."""
    async with AsyncSessionLocal() as session:
        job_service = BackgroundJobService(session)
        job = await job_service.claim_next_job()
        if job is None:
            return False

        jd_service = JDAnalysisService(db_session=session)
        cv_service = CVScreeningService(db_session=session)
        interview_service = InterviewSessionService(db_session=session)
        company_knowledge_service = CompanyKnowledgeService(db_session=session)
        handlers: dict[str, JobHandler] = {
            "jd_analysis": jd_service.run_analysis_job,
            "cv_screening": cv_service.run_screening_job,
            "interview_summary": interview_service.run_summary_job,
            "company_knowledge_ingestion": company_knowledge_service.run_ingestion_job,
        }
        handler = handlers.get(job.job_type)
        if handler is None:
            await job_service.mark_failed(job, f"Unsupported job type: {job.job_type}")
            return True

        try:
            await handler(job.resource_id)
            await job_service.mark_completed(job)
        except Exception as exc:
            if job.job_type == "cv_screening":
                await cv_service.mark_screening_failed(job.resource_id, str(exc))
            if job.job_type == "interview_summary":
                await interview_service.mark_summary_failed(job.resource_id, str(exc))
            if job.job_type == "company_knowledge_ingestion":
                await company_knowledge_service.mark_ingestion_failed(job.resource_id, str(exc))
            await job_service.mark_failed(job, str(exc))
        return True


async def main() -> None:
    """Poll the database forever for queued background jobs."""
    while True:
        ran_job = await run_once()
        if not ran_job:
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
