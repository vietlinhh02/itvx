"""API tests for JD analysis upload endpoint."""

from contextlib import asynccontextmanager
from importlib import import_module
from io import BytesIO
from typing import ClassVar
from zipfile import ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.database import get_db
from src.main import app
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse


class FakeJDAnalysisService:
    """Offline test double for the JD analysis service."""

    captured_call: ClassVar[dict[str, str | bytes] | None] = None
    captured_init: ClassVar[dict[str, object] | None] = None

    def __init__(self, **kwargs: object) -> None:
        """Accept route constructor arguments without side effects."""
        type(self).captured_init = kwargs

    async def analyze_upload(
        self,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> JDAnalysisResponse:
        """Record the upload call and return a valid response payload."""
        type(self).captured_call = {
            "file_name": file_name,
            "mime_type": mime_type,
            "file_bytes": file_bytes,
        }
        return JDAnalysisResponse(
            jd_id="test-jd-id",
            file_name=file_name,
            status="completed",
            created_at="2026-04-16T00:00:00Z",
            analysis=JDAnalysisPayload.model_validate(
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
            ),
        )

    async def get_analysis(self, jd_id: str) -> JDAnalysisResponse | None:
        """Return a stored JD analysis when the requested id matches the fixture."""
        if jd_id != "test-jd-id":
            return None

        return await self.analyze_upload(
            file_name="stored-jd.pdf",
            mime_type="application/pdf",
            file_bytes=b"%PDF-1.7\nstored",
        )

    async def list_recent_analyses(self, limit: int = 10) -> list[dict[str, str]]:
        """Return a fixed recent-JD list fixture."""
        if limit <= 0:
            return []

        return [
            {
                "jd_id": "test-jd-id",
                "file_name": "stored-jd.pdf",
                "status": "completed",
                "created_at": "2026-04-16T00:00:00Z",
                "job_title": "Backend Engineer",
            },
            {
                "jd_id": "second-jd-id",
                "file_name": "ml-jd.docx",
                "status": "completed",
                "created_at": "2026-04-15T12:00:00Z",
                "job_title": "ML Engineer Intern",
            },
        ]


def build_client(monkeypatch: MonkeyPatch) -> TestClient:
    """Create a test client without running real startup work."""

    @asynccontextmanager
    async def fake_lifespan(_: FastAPI):
        yield

    async def fake_db_session():
        yield object()

    monkeypatch.setattr(app.router, "lifespan_context", fake_lifespan)
    app.dependency_overrides[get_db] = fake_db_session
    return TestClient(app)


def stub_jd_service(monkeypatch: MonkeyPatch) -> None:
    """Replace the route service with an offline test double when available."""
    try:
        jd_api = import_module("src.api.v1.jd")
    except ModuleNotFoundError:
        return
    monkeypatch.setattr(jd_api, "JDAnalysisService", FakeJDAnalysisService)


def build_docx_bytes() -> bytes:
    """Build a minimal DOCX-like zip payload for upload tests."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def test_jd_analyze_endpoint_accepts_pdf_upload(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should accept a supported PDF upload."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"%PDF-1.7\npdf-content", "application/pdf")},
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "jd.pdf"


def test_jd_analyze_endpoint_passes_db_session(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should wire the request DB session into the JD service."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"%PDF-1.7\npdf-content", "application/pdf")},
    )

    assert response.status_code == 200
    assert FakeJDAnalysisService.captured_init is not None
    assert "db_session" in FakeJDAnalysisService.captured_init
    assert FakeJDAnalysisService.captured_init["db_session"] is not None


def test_jd_analyze_endpoint_rejects_unsupported_file_type(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should reject non-PDF and non-DOCX uploads."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file type"}


def test_jd_analyze_endpoint_rejects_empty_file(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should reject empty uploads."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Empty file"}


def test_jd_analyze_endpoint_rejects_invalid_pdf_content(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should reject a PDF upload whose bytes are not actually a PDF."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"not-a-pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File content does not match content type"}


def test_jd_analyze_endpoint_rejects_invalid_docx_content(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should reject a DOCX upload whose bytes are not a valid DOCX zip."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={
            "file": (
                "jd.docx",
                b"not-a-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File content does not match content type"}


def test_jd_analyze_endpoint_accepts_valid_docx_upload(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should accept DOCX uploads with valid zip-based structure."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={
            "file": (
                "jd.docx",
                build_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "jd.docx"


def test_jd_analyze_endpoint_rejects_oversized_file(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should reject uploads above the configured size limit."""
    monkeypatch.setattr("src.config.settings.jd_max_upload_size_bytes", 3)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/jd/analyze",
        files={"file": ("jd.pdf", b"four", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File exceeds size limit"}


def test_jd_detail_endpoint_returns_stored_analysis(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return an existing JD analysis by id."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/jd/test-jd-id")

    assert response.status_code == 200
    assert response.json()["jd_id"] == "test-jd-id"


def test_jd_detail_endpoint_returns_not_found(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return 404 when a JD id does not exist."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/jd/missing-jd-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "JD analysis not found"}


def test_recent_jd_endpoint_returns_recent_uploads(monkeypatch: MonkeyPatch) -> None:
    """Endpoint should return recent JD uploads for the dashboard."""
    stub_jd_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/jd")

    assert response.status_code == 200
    assert response.json()[0]["jd_id"] == "test-jd-id"
    assert response.json()[1]["job_title"] == "ML Engineer Intern"
