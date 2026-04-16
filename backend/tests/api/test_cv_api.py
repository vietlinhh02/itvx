"""API tests for CV screening endpoints."""

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
from src.schemas.cv import CVScreeningResponse


class FakeCVScreeningService:
    """Offline test double for the CV screening service."""

    captured_init: ClassVar[dict[str, object] | None] = None
    missing_jd: ClassVar[bool] = False

    def __init__(self, **kwargs: object) -> None:
        """Capture constructor arguments from the route."""
        type(self).captured_init = kwargs

    async def screen_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningResponse:
        """Return a stable Phase 2 response for route tests."""
        _ = (mime_type, file_bytes)
        if type(self).missing_jd:
            from src.services.cv_screening_service import JDNotReadyError

            raise JDNotReadyError("JD analysis not found or not ready")

        return CVScreeningResponse.model_validate(
            {
                "screening_id": "test-screening-id",
                "jd_id": jd_id,
                "candidate_id": "candidate-id",
                "file_name": file_name,
                "status": "completed",
                "created_at": "2026-04-16T00:00:00Z",
                "candidate_profile": {
                    "candidate_summary": {
                        "full_name": "Nguyen Van A",
                        "current_title": "Backend Engineer",
                        "location": "Ho Chi Minh City",
                        "total_years_experience": 4,
                        "seniority_signal": "mid",
                        "professional_summary": {
                            "vi": "Kỹ sư backend tập trung vào Python.",
                            "en": "Backend engineer focused on Python.",
                        },
                    },
                    "work_experience": [],
                    "projects": [],
                    "skills_inventory": [],
                    "education": [],
                    "certifications": [],
                    "languages": [],
                    "profile_uncertainties": [],
                },
                "result": {
                    "match_score": 0.72,
                    "recommendation": "review",
                    "decision_reason": {
                        "vi": "Có tín hiệu phù hợp.",
                        "en": "The candidate shows fit signals.",
                    },
                    "screening_summary": {
                        "vi": "Phù hợp tốt với nền tảng backend.",
                        "en": "Strong fit for backend fundamentals.",
                    },
                    "knockout_assessments": [],
                    "minimum_requirement_checks": [],
                    "dimension_scores": [],
                    "strengths": [],
                    "gaps": [],
                    "uncertainties": [],
                    "follow_up_questions": [],
                    "risk_flags": [],
                },
                "audit": {
                    "extraction_model": "gemini-2.5-pro",
                    "screening_model": "gemini-2.5-pro",
                    "profile_schema_version": "phase2.v1",
                    "screening_schema_version": "phase2.v1",
                    "generated_at": "2026-04-16T00:00:00Z",
                    "reconciliation_notes": [],
                    "consistency_flags": [],
                },
            }
        )

    async def get_screening(self, screening_id: str) -> CVScreeningResponse | None:
        """Return one stored screening fixture when the id matches."""
        if screening_id != "test-screening-id":
            return None
        return await self.screen_upload(
            jd_id="test-jd-id",
            file_name="candidate.pdf",
            mime_type="application/pdf",
            file_bytes=b"%PDF-1.7\ncandidate",
        )


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


def stub_cv_service(monkeypatch: MonkeyPatch, *, missing_jd: bool = False) -> None:
    """Replace the CV service with an offline test double."""
    FakeCVScreeningService.missing_jd = missing_jd
    cv_api = import_module("src.api.v1.cv")
    monkeypatch.setattr(cv_api, "CVScreeningService", FakeCVScreeningService)


def build_docx_bytes() -> bytes:
    """Build a minimal DOCX-like zip payload for upload tests."""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def test_cv_screen_endpoint_returns_phase_2_payload(monkeypatch: MonkeyPatch) -> None:
    """Return the Phase 2 payload from the create screening route."""
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 200
    payload = CVScreeningResponse.model_validate(response.json())
    assert payload.candidate_profile.candidate_summary.full_name == "Nguyen Van A"
    assert payload.result.screening_summary.en == "Strong fit for backend fundamentals."
    assert payload.audit.profile_schema_version == "phase2.v1"


def test_cv_screen_endpoint_rejects_unsupported_file_type(
    monkeypatch: MonkeyPatch,
) -> None:
    """Reject uploads outside the supported CV MIME types."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={"file": ("candidate.txt", b"plain-text", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unsupported file type"}


def test_cv_screen_endpoint_rejects_invalid_docx_content(
    monkeypatch: MonkeyPatch,
) -> None:
    """Reject DOCX uploads whose bytes are not valid DOCX content."""
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={
            "file": (
                "candidate.docx",
                b"not-a-docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "File content does not match content type"}


def test_cv_screen_endpoint_accepts_valid_docx_upload(monkeypatch: MonkeyPatch) -> None:
    """Accept valid DOCX uploads for CV screening."""
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "test-jd-id"},
        files={
            "file": (
                "candidate.docx",
                build_docx_bytes(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert response.json()["file_name"] == "candidate.docx"


def test_cv_screen_endpoint_returns_not_found_for_missing_jd(
    monkeypatch: MonkeyPatch,
) -> None:
    """Return 404 when the target JD is not ready for screening."""
    stub_cv_service(monkeypatch, missing_jd=True)
    client = build_client(monkeypatch)

    response = client.post(
        "/api/v1/cv/screen",
        data={"jd_id": "missing-jd-id"},
        files={"file": ("candidate.pdf", b"%PDF-1.7\ncandidate", "application/pdf")},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "JD analysis not found or not ready"}


def test_cv_screening_detail_returns_phase_2_payload(monkeypatch: MonkeyPatch) -> None:
    """Return the Phase 2 payload from the screening detail route."""
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/cv/screenings/test-screening-id")

    assert response.status_code == 200
    payload = CVScreeningResponse.model_validate(response.json())
    assert payload.result.recommendation == "review"
    assert payload.audit.screening_schema_version == "phase2.v1"


def test_cv_screening_detail_returns_not_found(monkeypatch: MonkeyPatch) -> None:
    """Return 404 when a screening id does not exist."""
    stub_cv_service(monkeypatch)
    client = build_client(monkeypatch)

    response = client.get("/api/v1/cv/screenings/missing-screening-id")

    assert response.status_code == 404
    assert response.json() == {"detail": "CV screening not found"}
