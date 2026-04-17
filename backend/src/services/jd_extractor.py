"""LangChain-based Gemini extractor for JD analysis."""

import logging
from pathlib import Path
from typing import Protocol, cast
from xml.etree import ElementTree
from zipfile import ZipFile

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.jd import JDAnalysisPayload

logger = logging.getLogger(__name__)


def build_jd_extraction_prompt() -> str:
    """Return the structured extraction instructions for JD analysis."""
    return (
        "You are a hiring analyst. Read the uploaded job description and extract only job-relevant "
        "criteria for candidate screening. Return bilingual output with Vietnamese and English "
        "text for human-facing fields, keep schema keys and enums normalized in English, "
        "separate required and preferred requirements, generate a rubric seed for CV screening, "
        "list any uncertainty under ambiguities_for_human_review, and use the "
        "JDAnalysisPayload schema exactly."
    )


class StructuredJDInvoker(Protocol):
    """Minimal protocol for the LangChain structured output client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return a structured result."""


class GeminiJDExtractor:
    """Wrapper around LangChain Gemini structured output for JD analysis."""

    def __init__(self) -> None:
        """Build the Gemini client configured for JD structured output."""
        self._structured_llm: StructuredJDInvoker = cast(
            StructuredJDInvoker,
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0,
                # Pyright cannot fully model LangChain's dynamic structured output wrapper.
            ).with_structured_output(JDAnalysisPayload),  # pyright: ignore[reportUnknownMemberType]
        )

    async def extract(self, file_path: Path, mime_type: str) -> JDAnalysisPayload:
        """Extract a structured JD payload from an uploaded file."""
        logger.info("Starting JD extraction with Gemini", extra={
            "file_path": str(file_path),
            "mime_type": mime_type,
        })

        message = HumanMessage(content=self._build_message_content(file_path, mime_type))

        logger.info("Calling Gemini structured output for JD extraction", extra={
            "model": settings.gemini_model,
            "file_path": str(file_path),
            "mime_type": mime_type,
        })
        try:
            result = await self._structured_llm.ainvoke([message])
        except Exception:
            logger.exception("Gemini JD extraction failed", extra={
                "model": settings.gemini_model,
                "file_path": str(file_path),
                "mime_type": mime_type,
            })
            raise

        logger.info("Received Gemini JD extraction response", extra={
            "model": settings.gemini_model,
            "file_path": str(file_path),
        })
        payload = JDAnalysisPayload.model_validate(result)
        logger.info("Validated JD extraction payload", extra={
            "file_path": str(file_path),
            "job_title_en": payload.job_overview.job_title.en,
        })
        return payload

    def _build_message_content(
        self,
        file_path: Path,
        mime_type: str,
    ) -> list[dict[str, str | bytes]]:
        """Build Gemini message parts for supported JD input formats."""
        prompt = {"type": "text", "text": build_jd_extraction_prompt()}
        if mime_type == "application/pdf":
            file_bytes = file_path.read_bytes()
            logger.info("Loaded JD PDF bytes", extra={
                "file_path": str(file_path),
                "mime_type": mime_type,
                "file_size_bytes": len(file_bytes),
            })
            return [
                prompt,
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": file_bytes,
                },
            ]

        if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            extracted_text = self._extract_docx_text(file_path)
            logger.info("Extracted JD DOCX text", extra={
                "file_path": str(file_path),
                "mime_type": mime_type,
                "text_length": len(extracted_text),
            })
            return [
                prompt,
                {"type": "text", "text": f"Job description document text:\n\n{extracted_text}"},
            ]

        raise ValueError(f"Unsupported JD file type: {mime_type}")

    def _extract_docx_text(self, file_path: Path) -> str:
        """Extract paragraph text from a DOCX archive for Gemini ingestion."""
        with ZipFile(file_path) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs: list[str] = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            merged = "".join(texts).strip()
            if merged:
                paragraphs.append(merged)

        extracted_text = "\n".join(paragraphs).strip()
        if not extracted_text:
            raise ValueError("JD DOCX file does not contain extractable text")
        return extracted_text
