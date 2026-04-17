"""Services for JD-scoped company knowledge ingestion and retrieval."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.background_job import BackgroundJob, BackgroundJobType, BackgroundResourceType
from src.models.jd import JDCompanyChunk, JDCompanyDocument, JDDocument
from src.schemas.jd import (
    JDCompanyDocumentItem,
    JDCompanyDocumentUploadResponse,
    JDCompanyKnowledgeCitation,
    JDCompanyKnowledgeQueryResponse,
)
from src.services.company_knowledge_parser import CompanyKnowledgeParser
from src.services.company_knowledge_retriever import CompanyKnowledgeRetriever
from src.services.datetime_utils import to_vietnam_isoformat
from src.services.file_storage import store_upload_file


class CompanyKnowledgeService:
    """Persist, ingest, and query company knowledge documents for one JD."""

    def __init__(
        self,
        db_session: AsyncSession,
        upload_dir: Path | None = None,
        parser: CompanyKnowledgeParser | None = None,
    ) -> None:
        self._db_session = db_session
        self._upload_dir = upload_dir or settings.company_doc_upload_path
        self._parser = parser or CompanyKnowledgeParser()
        self._retriever = CompanyKnowledgeRetriever(db_session)

    async def upload_document(
        self,
        *,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> JDCompanyDocumentUploadResponse:
        """Store an uploaded company document and enqueue ingestion."""
        await self._require_jd(jd_id)
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        document = JDCompanyDocument(
            jd_document_id=jd_id,
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="queued",
            error_message=None,
            chunk_count=0,
        )
        self._db_session.add(document)
        await self._db_session.flush()

        job = BackgroundJob(
            job_type=BackgroundJobType.COMPANY_KNOWLEDGE_INGESTION,
            status="queued",
            resource_type=BackgroundResourceType.JD_COMPANY_DOCUMENT,
            resource_id=document.id,
            payload={
                "jd_id": jd_id,
                "document_id": document.id,
                "file_name": stored_file.file_name,
                "mime_type": mime_type,
            },
        )
        self._db_session.add(job)
        await self._db_session.commit()
        await self._db_session.refresh(job)
        await self._db_session.refresh(document)
        return JDCompanyDocumentUploadResponse(
            job_id=job.id,
            document=self._to_document_item(document),
        )

    async def list_documents(self, jd_id: str) -> list[JDCompanyDocumentItem]:
        """Return all company knowledge documents for one JD."""
        await self._require_jd(jd_id)
        documents = list(
            (
                await self._db_session.scalars(
                    select(JDCompanyDocument)
                    .where(JDCompanyDocument.jd_document_id == jd_id)
                    .order_by(JDCompanyDocument.created_at.desc())
                )
            ).all()
        )
        return [self._to_document_item(document) for document in documents]

    async def delete_document(self, jd_id: str, document_id: str) -> bool:
        """Delete one company knowledge document for a JD."""
        document = await self._db_session.scalar(
            select(JDCompanyDocument).where(
                JDCompanyDocument.id == document_id,
                JDCompanyDocument.jd_document_id == jd_id,
            )
        )
        if document is None:
            return False
        await self._db_session.execute(
            delete(BackgroundJob).where(BackgroundJob.resource_id == document.id)
        )
        await self._db_session.delete(document)
        await self._db_session.commit()
        return True

    async def run_ingestion_job(self, document_id: str) -> None:
        """Parse one queued company document and persist chunks."""
        document = await self._db_session.scalar(
            select(JDCompanyDocument).where(JDCompanyDocument.id == document_id)
        )
        if document is None:
            raise ValueError("Company document not found")

        document.status = "processing"
        document.error_message = None
        await self._db_session.commit()

        chunks = self._parser.parse(Path(document.storage_path), document.mime_type)
        await self._db_session.execute(
            delete(JDCompanyChunk).where(JDCompanyChunk.jd_company_document_id == document.id)
        )
        for chunk in chunks:
            self._db_session.add(
                JDCompanyChunk(
                    jd_company_document_id=document.id,
                    jd_document_id=document.jd_document_id,
                    chunk_index=chunk.chunk_index,
                    section_title=chunk.section_title,
                    page_number=chunk.page_number,
                    content=chunk.content,
                    search_text=chunk.search_text,
                )
            )
        document.chunk_count = len(chunks)
        document.status = "ready"
        document.error_message = None
        await self._db_session.commit()

    async def mark_ingestion_failed(self, document_id: str, error_message: str) -> None:
        """Persist a failed company document ingestion state."""
        document = await self._db_session.scalar(
            select(JDCompanyDocument).where(JDCompanyDocument.id == document_id)
        )
        if document is None:
            return
        document.status = "failed"
        document.error_message = error_message
        await self._db_session.commit()

    async def query_knowledge(self, jd_id: str, query: str) -> JDCompanyKnowledgeQueryResponse:
        """Return grounded citations for one company knowledge query."""
        await self._require_jd(jd_id)
        results = await self._retriever.retrieve(jd_id=jd_id, query=query)
        return JDCompanyKnowledgeQueryResponse(
            query=query,
            citations=[
                JDCompanyKnowledgeCitation(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    file_name=result.file_name,
                    section_title=result.section_title,
                    page_number=result.page_number,
                    excerpt=result.excerpt,
                )
                for result in results
            ],
        )

    def _to_document_item(self, document: JDCompanyDocument) -> JDCompanyDocumentItem:
        """Convert one ORM row into an API response item."""
        return JDCompanyDocumentItem(
            document_id=document.id,
            jd_id=document.jd_document_id,
            file_name=document.file_name,
            status=document.status,
            chunk_count=document.chunk_count,
            error_message=document.error_message,
            created_at=to_vietnam_isoformat(document.created_at),
        )

    async def _require_jd(self, jd_id: str) -> JDDocument:
        """Ensure a referenced JD exists before mutating knowledge docs."""
        document = await self._db_session.scalar(select(JDDocument).where(JDDocument.id == jd_id))
        if document is None:
            raise ValueError("JD analysis not found")
        return document
