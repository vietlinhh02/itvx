import pytest

from src.models.background_job import BackgroundJob
from src.scripts import run_background_jobs


@pytest.mark.asyncio
async def test_run_once_dispatches_interview_summary_job(db_session, monkeypatch) -> None:
    called_with: list[str] = []

    class FakeBackgroundJobService:
        def __init__(self, session) -> None:
            _ = session

        async def claim_next_job(self):
            return BackgroundJob(
                job_type="interview_summary",
                status="running",
                resource_type="interview_session",
                resource_id="session-1",
                payload={"completion_reason": "candidate_left"},
            )

        async def mark_completed(self, job) -> None:
            _ = job

        async def mark_failed(self, job, error_message: str) -> None:
            raise AssertionError(error_message)

    class FakeJDAnalysisService:
        def __init__(self, db_session) -> None:
            _ = db_session

        async def run_analysis_job(self, resource_id: str) -> None:
            raise AssertionError(resource_id)

    class FakeCVScreeningService:
        def __init__(self, db_session) -> None:
            _ = db_session

        async def run_screening_job(self, resource_id: str) -> None:
            raise AssertionError(resource_id)

        async def mark_screening_failed(self, resource_id: str, error_message: str) -> None:
            raise AssertionError((resource_id, error_message))

    class FakeInterviewSessionService:
        def __init__(self, db_session) -> None:
            _ = db_session

        async def run_summary_job(self, session_id: str) -> None:
            called_with.append(session_id)

        async def mark_summary_failed(self, session_id: str, error_message: str) -> None:
            raise AssertionError((session_id, error_message))

    async def fake_session_factory():
        class FakeSessionContext:
            async def __aenter__(self):
                return object()

            async def __aexit__(self, exc_type, exc, tb):
                return False

        return FakeSessionContext()

    class FakeSessionLocal:
        def __call__(self):
            class FakeSessionContext:
                async def __aenter__(self):
                    return object()

                async def __aexit__(self, exc_type, exc, tb):
                    return False

            return FakeSessionContext()

    monkeypatch.setattr(run_background_jobs, "AsyncSessionLocal", FakeSessionLocal())
    monkeypatch.setattr(run_background_jobs, "BackgroundJobService", FakeBackgroundJobService)
    monkeypatch.setattr(run_background_jobs, "JDAnalysisService", FakeJDAnalysisService)
    monkeypatch.setattr(run_background_jobs, "CVScreeningService", FakeCVScreeningService)
    monkeypatch.setattr(run_background_jobs, "InterviewSessionService", FakeInterviewSessionService)

    handled = await run_background_jobs.run_once()

    assert handled is True
    assert called_with == ["session-1"]
