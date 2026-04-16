"""CV screening API routes."""

from io import BytesIO
from typing import Annotated
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.cv import CVScreeningHistoryResponse, CVScreeningResponse
from src.services.cv_screening_service import CVScreeningService, JDNotReadyError

router = APIRouter(prefix="/cv", tags=["cv"])

SUPPORTED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _matches_pdf_signature(file_bytes: bytes) -> bool:
    """Return whether the upload starts with a PDF file header."""
    return file_bytes.startswith(b"%PDF-")


def _matches_docx_structure(file_bytes: bytes) -> bool:
    """Return whether the upload is a DOCX-style zip with required entries."""
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            names = set(archive.namelist())
    except BadZipFile:
        return False

    return "[Content_Types].xml" in names and "word/document.xml" in names


def _validate_file_content(mime_type: str, file_bytes: bytes) -> bool:
    """Return whether the uploaded bytes match the declared MIME type."""
    if mime_type == "application/pdf":
        return _matches_pdf_signature(file_bytes)
    return _matches_docx_structure(file_bytes)


@router.post("/screen", response_model=CVScreeningResponse)
async def screen_cv(
    jd_id: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningResponse:
    """Upload one CV and return the Phase 2 screening response."""
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > settings.cv_max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds size limit")
    if not _validate_file_content(file.content_type, file_bytes):
        raise HTTPException(status_code=400, detail="File content does not match content type")

    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    try:
        return await service.screen_upload(
            jd_id=jd_id,
            file_name=file.filename or "uploaded-cv",
            mime_type=file.content_type,
            file_bytes=file_bytes,
        )
    except JDNotReadyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/jd/{jd_id}/screenings", response_model=CVScreeningHistoryResponse)
async def list_cv_screenings_for_jd(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningHistoryResponse:
    """Return all stored CV screenings for one JD."""
    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    items = await service.list_screenings_for_jd(jd_id)
    return CVScreeningHistoryResponse(items=items)


@router.get("/screenings/{screening_id}", response_model=CVScreeningResponse)
async def get_cv_screening(
    screening_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CVScreeningResponse:
    """Return a stored CV screening by id."""
    service = CVScreeningService(upload_dir=settings.cv_upload_path, db_session=db)
    screening = await service.get_screening(screening_id)
    if screening is None:
        raise HTTPException(status_code=404, detail="CV screening not found")
    return screening
