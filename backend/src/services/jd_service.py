"""Orchestration service for JD upload and analysis."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.jd import JDAnalysisPayload, JDAnalysisResponse, JDRecentItem
from src.services.file_storage import store_upload_file
from src.services.jd_extractor import GeminiJDExtractor


class JDExtractor(Protocol):
    """Interface for JD extraction implementations."""

    async def extract(self, file_path: Path, mime_type: str) -> JDAnalysisPayload:
        """Extract structured JD data from a stored upload."""
        ...


class JDAnalysisService:
    """Handle storage and extraction for uploaded JD files."""

    def __init__(
        self,
        extractor: JDExtractor | None = None,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        """Initialize the service with optional test doubles and upload directory."""
        self._extractor: JDExtractor
        self._upload_dir: Path
        self._db_session: AsyncSession | None
        self._extractor = extractor or GeminiJDExtractor()
        self._upload_dir = upload_dir or settings.jd_upload_path
        self._db_session = db_session

    async def analyze_upload(
        self,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> JDAnalysisResponse:
        """Store the upload, extract a JD payload, and return the API response."""
        stored_file = store_upload_file(
            upload_dir=self._upload_dir,
            file_name=file_name,
            file_bytes=file_bytes,
        )
        document = JDDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        if self._db_session is not None:
            self._db_session.add(document)
            await self._db_session.flush()

        analysis = await self._extractor.extract(Path(stored_file.storage_path), mime_type)

        if self._db_session is not None:
            self._db_session.add(
                JDAnalysis(
                    jd_document_id=document.id,
                    model_name=settings.gemini_model,
                    analysis_payload=analysis.model_dump(mode="json"),
                )
            )
            document.status = "completed"
            await self._db_session.commit()
            await self._db_session.refresh(document)
            jd_id = document.id
            created_at = document.created_at.replace(tzinfo=UTC).isoformat()
        else:
            jd_id = str(uuid4())
            created_at = datetime.now(UTC).isoformat()

        return JDAnalysisResponse(
            jd_id=jd_id,
            file_name=stored_file.file_name,
            status="completed",
            created_at=created_at,
            analysis=analysis,
        )

    async def get_analysis(self, jd_id: str) -> JDAnalysisResponse | None:
        """Return a persisted JD analysis by id when available."""
        if self._db_session is None:
            return None

        statement = (
            select(JDDocument, JDAnalysis)
            .join(JDAnalysis, JDAnalysis.jd_document_id == JDDocument.id)
            .where(JDDocument.id == jd_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return None

        document, analysis_record = row
        created_at = document.created_at.replace(tzinfo=UTC).isoformat()
        analysis = JDAnalysisPayload.model_validate(analysis_record.analysis_payload)
        return JDAnalysisResponse(
            jd_id=document.id,
            file_name=document.file_name,
            status="completed",
            created_at=created_at,
            analysis=analysis,
        )

    async def list_recent_analyses(self, limit: int = 10) -> list[JDRecentItem]:
        """Return recent JD uploads for dashboard navigation."""
        if self._db_session is None:
            return []

        statement = (
            select(JDDocument, JDAnalysis)
            .join(JDAnalysis, JDAnalysis.jd_document_id == JDDocument.id)
            .order_by(JDDocument.created_at.desc())
            .limit(limit)
        )
        rows = (await self._db_session.execute(statement)).all()

        recent_items: list[JDRecentItem] = []
        for document, analysis_record in rows:
            analysis_payload = JDAnalysisPayload.model_validate(analysis_record.analysis_payload)
            recent_items.append(
                JDRecentItem(
                    jd_id=document.id,
                    file_name=document.file_name,
                    status=document.status,
                    created_at=document.created_at.replace(tzinfo=UTC).isoformat(),
                    job_title=analysis_payload.job_overview.job_title.en,
                )
            )
        return recent_items
