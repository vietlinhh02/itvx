"""JD service contract tests."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.jd import JDAnalysisEnqueueResponse, JDAnalysisPayload
from src.services.background_jobs import BackgroundJobService
from src.services.jd_extractor import GeminiJDExtractor, build_jd_extraction_prompt
from src.services.jd_service import JDAnalysisService


def test_build_jd_extraction_prompt_mentions_bilingual_output() -> None:
    """Prompt should require the bilingual structured contract."""
    prompt = build_jd_extraction_prompt()

    assert "LangChain" not in prompt
    assert "bilingual" in prompt.lower()
    assert JDAnalysisPayload.__name__ in prompt


def build_docx_bytes(text: str) -> bytes:
    """Build a minimal DOCX payload containing plain paragraph text."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            (
                "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\">"
                "<w:body>"
                f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
                "</w:body>"
                "</w:document>"
            ),
        )
    return buffer.getvalue()


class FakeExtractor:
    """Test double that records the stored upload passed to extraction."""

    def __init__(self) -> None:
        """Initialize recorded extractor inputs."""
        self.file_path: Path | None = None
        self.mime_type: str | None = None
        self.file_bytes: bytes | None = None

    async def extract(self, file_path: Path, mime_type: str) -> JDAnalysisPayload:
        """Capture call details and return a valid JD analysis payload."""
        self.file_path = file_path
        self.mime_type = mime_type
        self.file_bytes = file_path.read_bytes()

        return JDAnalysisPayload.model_validate(
            {
                "job_overview": {
                    "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                    "department": {"vi": "Ky thuat", "en": "Engineering"},
                    "seniority_level": "senior",
                    "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                    "work_mode": "hybrid",
                    "role_summary": {"vi": "Tom tat", "en": "Summary"},
                    "company_benefits": [],
                },
                "requirements": {
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "tools_and_technologies": [],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                        "preferred_domains": [],
                    },
                    "education_and_certifications": [],
                    "language_requirements": [],
                    "key_responsibilities": [],
                    "screening_knockout_criteria": [],
                },
                "rubric_seed": {
                    "evaluation_dimensions": [
                        {
                            "name": {"vi": "Python", "en": "Python"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "must_have",
                            "weight": 0.4,
                            "evidence_signals": [{"vi": "Du an", "en": "Projects"}],
                        },
                        {
                            "name": {"vi": "API", "en": "API"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.2,
                            "evidence_signals": [{"vi": "REST", "en": "REST"}],
                        },
                        {
                            "name": {"vi": "SQL", "en": "SQL"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Query", "en": "Query"}],
                        },
                        {
                            "name": {"vi": "Docker", "en": "Docker"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "nice_to_have",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Container", "en": "Container"}],
                        },
                        {
                            "name": {"vi": "Giao tiep", "en": "Communication"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "Phoi hop", "en": "Collaboration"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": [
                            {"vi": "3 nam kinh nghiem", "en": "3+ years experience"},
                        ],
                        "scoring_principle": {
                            "vi": "Khong bu tru must-have bang nice-to-have.",
                            "en": "Nice-to-have cannot replace must-have.",
                        },
                    },
                    "ambiguities_for_human_review": [],
                },
            }
        )


class FakeStructuredJDInvoker:
    """Structured invoker that records Gemini message payloads."""

    def __init__(self) -> None:
        """Initialize the recorded Gemini messages."""
        self.messages: list[HumanMessage] = []

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Capture the structured invocation input and return a valid payload."""
        self.messages = input
        return {
            "job_overview": {
                "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                "department": {"vi": "Ky thuat", "en": "Engineering"},
                "seniority_level": "senior",
                "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                "work_mode": "hybrid",
                "role_summary": {"vi": "Tom tat", "en": "Summary"},
                "company_benefits": [],
            },
            "requirements": {
                "required_skills": ["Python"],
                "preferred_skills": [],
                "tools_and_technologies": [],
                "experience_requirements": {
                    "minimum_years": 3,
                    "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                    "preferred_domains": [],
                },
                "education_and_certifications": [],
                "language_requirements": [],
                "key_responsibilities": [],
                "screening_knockout_criteria": [],
            },
            "rubric_seed": {
                "evaluation_dimensions": [
                    {
                        "name": {"vi": "Python", "en": "Python"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "must_have",
                        "weight": 0.4,
                        "evidence_signals": [{"vi": "Du an", "en": "Projects"}],
                    },
                    {
                        "name": {"vi": "API", "en": "API"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "important",
                        "weight": 0.2,
                        "evidence_signals": [{"vi": "REST", "en": "REST"}],
                    },
                    {
                        "name": {"vi": "SQL", "en": "SQL"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "important",
                        "weight": 0.15,
                        "evidence_signals": [{"vi": "Query", "en": "Query"}],
                    },
                    {
                        "name": {"vi": "Docker", "en": "Docker"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "nice_to_have",
                        "weight": 0.15,
                        "evidence_signals": [{"vi": "Container", "en": "Container"}],
                    },
                    {
                        "name": {"vi": "Giao tiep", "en": "Communication"},
                        "description": {"vi": "Mo ta", "en": "Description"},
                        "priority": "important",
                        "weight": 0.1,
                        "evidence_signals": [{"vi": "Phoi hop", "en": "Collaboration"}],
                    },
                ],
                "screening_rules": {
                    "minimum_requirements": [
                        {"vi": "3 nam kinh nghiem", "en": "3+ years experience"},
                    ],
                    "scoring_principle": {
                        "vi": "Khong bu tru must-have bang nice-to-have.",
                        "en": "Nice-to-have cannot replace must-have.",
                    },
                },
                "ambiguities_for_human_review": [],
            },
        }


@pytest.mark.asyncio
async def test_jd_extractor_sends_docx_as_text(tmp_path: Path) -> None:
    """DOCX uploads should be converted to text before Gemini invocation."""
    file_path = tmp_path / "jd.docx"
    file_path.write_bytes(build_docx_bytes("Python engineer"))
    invoker = FakeStructuredJDInvoker()
    extractor = GeminiJDExtractor.__new__(GeminiJDExtractor)
    extractor._structured_llm = invoker  # pyright: ignore[reportPrivateUsage]

    await extractor.extract(
        file_path,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    content = invoker.messages[0].content
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "text"
    assert "Python engineer" in str(content[1]["text"])


@pytest.mark.asyncio
async def test_service_returns_completed_response(tmp_path: Path) -> None:
    """Service should store the upload and return a completed response."""
    extractor = FakeExtractor()
    service = JDAnalysisService(extractor=extractor, upload_dir=tmp_path)

    response = await service.analyze_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"file-content",
    )

    assert response.file_name == "jd.pdf"
    assert response.status == "completed"
    assert response.analysis.job_overview.seniority_level == "senior"
    assert extractor.mime_type == "application/pdf"
    assert extractor.file_bytes == b"file-content"
    assert extractor.file_path is not None
    assert extractor.file_path.parent == tmp_path
    assert extractor.file_path.exists()


@pytest.mark.asyncio
async def test_service_persists_document_and_analysis(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Service should persist both the stored document and analysis payload."""
    service = JDAnalysisService(
        extractor=FakeExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )

    response = await service.analyze_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"file-content",
    )

    stored_document: JDDocument | None = await db_session.scalar(
        select(JDDocument).where(JDDocument.id == response.jd_id)
    )
    stored_analysis: JDAnalysis | None = await db_session.scalar(
        select(JDAnalysis).where(JDAnalysis.jd_document_id == response.jd_id)
    )

    assert stored_document is not None
    assert stored_document.status == "completed"
    assert stored_analysis is not None
    assert stored_analysis.model_name


@pytest.mark.asyncio
async def test_claim_next_job_marks_job_running(db_session: AsyncSession) -> None:
    """Claiming a queued job should mark it running and stamp the start time."""
    db_session.add(
        BackgroundJob(
            job_type="jd_analysis",
            status="queued",
            resource_type="jd_document",
            resource_id="jd-1",
            payload={"jd_id": "jd-1"},
            completed_at=datetime.now(UTC).replace(tzinfo=None),
            error_message="old error",
        )
    )
    await db_session.commit()

    service = BackgroundJobService(db_session)
    job = await service.claim_next_job()

    assert job is not None
    assert job.status == "running"
    assert job.started_at is not None
    assert job.completed_at is None
    assert job.error_message is None


@pytest.mark.asyncio
async def test_enqueue_analysis_creates_processing_document_and_job(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Enqueueing analysis should persist a processing document and job."""
    service = JDAnalysisService(upload_dir=tmp_path, db_session=db_session)

    response = await service.enqueue_analysis_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\njd",
    )

    document = await db_session.scalar(select(JDDocument).where(JDDocument.id == response.jd_id))
    job = await db_session.scalar(select(BackgroundJob).where(BackgroundJob.id == response.job_id))

    assert isinstance(response, JDAnalysisEnqueueResponse)
    assert response.status == "processing"
    assert document is not None
    assert document.status == "processing"
    assert job is not None
    assert job.job_type == "jd_analysis"


@pytest.mark.asyncio
async def test_run_jd_job_completes_document_and_analysis(
    db_session: AsyncSession,
    tmp_path: Path,
) -> None:
    """Running a JD job should persist analysis and complete the document."""
    service = JDAnalysisService(
        extractor=FakeExtractor(),
        upload_dir=tmp_path,
        db_session=db_session,
    )
    response = await service.enqueue_analysis_upload(
        file_name="jd.pdf",
        mime_type="application/pdf",
        file_bytes=b"%PDF-1.7\njd",
    )

    await service.run_analysis_job(response.jd_id)

    document = await db_session.scalar(select(JDDocument).where(JDDocument.id == response.jd_id))
    analysis = await db_session.scalar(
        select(JDAnalysis).where(JDAnalysis.jd_document_id == response.jd_id)
    )

    assert document is not None
    assert document.status == "completed"
    assert analysis is not None
