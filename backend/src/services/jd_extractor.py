"""LangChain-based Gemini extractor for JD analysis."""

from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr

from src.config import settings
from src.schemas.jd import JDAnalysisPayload


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
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_jd_extraction_prompt()},
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": file_path.read_bytes(),
                },
            ]
        )
        result = await self._structured_llm.ainvoke([message])
        return JDAnalysisPayload.model_validate(result)
