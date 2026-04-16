"""JD analysis API routes."""

from io import BytesIO
from typing import Annotated
from zipfile import BadZipFile, ZipFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.database import get_db
from src.schemas.jd import JDAnalysisResponse, JDRecentItem
from src.services.jd_service import JDAnalysisService

router = APIRouter(prefix="/jd", tags=["jd"])

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


@router.get("", response_model=list[JDRecentItem])
async def list_recent_jd_analyses(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[JDRecentItem]:
    """Return recent JD uploads for the dashboard."""
    service = JDAnalysisService(upload_dir=settings.jd_upload_path, db_session=db)
    return await service.list_recent_analyses()


@router.post("/analyze", response_model=JDAnalysisResponse)
async def analyze_jd(
    file: Annotated[UploadFile, File(...)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JDAnalysisResponse:
    """Upload a JD file, validate it, and return the extracted analysis."""
    if file.content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(file_bytes) > settings.jd_max_upload_size_bytes:
        raise HTTPException(status_code=400, detail="File exceeds size limit")
    if not _validate_file_content(file.content_type, file_bytes):
        raise HTTPException(status_code=400, detail="File content does not match content type")

    service = JDAnalysisService(upload_dir=settings.jd_upload_path, db_session=db)
    return await service.analyze_upload(
        file_name=file.filename or "uploaded.jd",
        mime_type=file.content_type,
        file_bytes=file_bytes,
    )


@router.get("/{jd_id}", response_model=JDAnalysisResponse)
async def get_jd_analysis(
    jd_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JDAnalysisResponse:
    """Return a stored JD analysis by id."""
    service = JDAnalysisService(upload_dir=settings.jd_upload_path, db_session=db)
    analysis = await service.get_analysis(jd_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="JD analysis not found")
    return analysis
