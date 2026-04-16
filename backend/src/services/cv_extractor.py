"""LangChain-based Gemini extractor for CV screening phase 2."""

from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.cv import CandidateProfilePayload

PROFILE_SCHEMA_VERSION = "phase2.v1"


def build_cv_extraction_prompt() -> str:
    """Return the structured extraction instructions for Phase 2 CV parsing."""
    return (
        "You are a conservative recruiting analyst. "
        "Read the uploaded CV and produce a review-ready candidate profile "
        "for HR screening. Extract only claims supported directly by the document, "
        "preserve evidence-bearing statements, keep important ambiguities explicit, "
        "prefer omission over unsupported inference, and return the "
        "CandidateProfilePayload schema exactly."
    )


class StructuredCandidateInvoker(Protocol):
    """Minimal protocol for the LangChain structured output client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return a structured result."""


class GeminiCVExtractor:
    """Wrapper around Gemini structured output for Phase 2 candidate profiles."""

    def __init__(self) -> None:
        """Build the Gemini client configured for candidate profile extraction."""
        self._structured_llm: StructuredCandidateInvoker = cast(
            StructuredCandidateInvoker,
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0,
                # Pyright cannot fully model LangChain's dynamic structured output wrapper.
            ).with_structured_output(CandidateProfilePayload),  # pyright: ignore[reportUnknownMemberType]
        )

    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        """Extract a structured Phase 2 candidate profile from an uploaded CV."""
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_cv_extraction_prompt()},
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": file_path.read_bytes(),
                },
            ]
        )
        result = await self._structured_llm.ainvoke([message])
        return CandidateProfilePayload.model_validate(result)
