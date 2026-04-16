"""JD service contract tests."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.jd import JDAnalysis, JDDocument
from src.schemas.jd import JDAnalysisPayload
from src.services.jd_extractor import build_jd_extraction_prompt
from src.services.jd_service import JDAnalysisService


def test_build_jd_extraction_prompt_mentions_bilingual_output() -> None:
    """Prompt should require the bilingual structured contract."""
    prompt = build_jd_extraction_prompt()

    assert "LangChain" not in prompt
    assert "bilingual" in prompt.lower()
    assert JDAnalysisPayload.__name__ in prompt


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
