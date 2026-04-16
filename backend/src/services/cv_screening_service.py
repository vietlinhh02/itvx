"""Services for CV screening against a stored JD analysis."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import (
    CandidateProfilePayload,
    CVScreeningResponse,
    RequirementStatus,
    ScreeningRecommendation,
    StoredScreeningPayload,
)
from src.schemas.jd import JDAnalysisPayload
from src.services.cv_extractor import PROFILE_SCHEMA_VERSION, GeminiCVExtractor
from src.services.file_storage import store_upload_file

SCREENING_SCHEMA_VERSION = "phase2.v1"


class CandidateExtractor(Protocol):
    """Interface for candidate extraction implementations."""

    async def extract(self, file_path: Path, mime_type: str) -> CandidateProfilePayload:
        """Extract a structured candidate profile from a stored CV."""
        ...


class StructuredScreeningInvoker(Protocol):
    """Minimal protocol for the LangChain structured screening client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return structured screening artifacts."""


class JDNotReadyError(ValueError):
    """Raised when a referenced JD cannot be screened yet."""


def build_screening_prompt() -> str:
    """Return the structured screening instructions for Phase 2 candidate evaluation."""
    return (
        "You are a hiring analyst comparing one candidate to one analyzed job description. "
        "Evaluate knockout criteria first, then minimum requirements, then rubric dimensions. "
        "Respect must-have, important, and nice-to-have priorities, keep ambiguities explicit, "
        "provide bilingual HR-facing reasons, and return structured output only "
        "using the StoredScreeningPayload schema."
    )


class CVScreeningService:
    """Handle storage, profile extraction, and Phase 2 CV screening."""

    def __init__(
        self,
        extractor: CandidateExtractor | None = None,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        """Initialize the screening service with optional test doubles."""
        self._extractor: CandidateExtractor = extractor or GeminiCVExtractor()
        self._upload_dir: Path = upload_dir or settings.cv_upload_path
        self._db_session: AsyncSession | None = db_session
        self._screening_llm: StructuredScreeningInvoker = cast(
            StructuredScreeningInvoker,
            ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                api_key=SecretStr(settings.gemini_api_key),
                temperature=0,
                # Pyright cannot fully model LangChain's dynamic structured output wrapper.
            ).with_structured_output(StoredScreeningPayload),  # pyright: ignore[reportUnknownMemberType]
        )

    async def screen_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningResponse:
        """Store the CV, extract a profile, screen it, and return the response."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        jd_analysis = await self._load_jd_analysis(jd_id)
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        candidate_document = CandidateDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        self._db_session.add(candidate_document)
        await self._db_session.flush()

        candidate_profile = await self._extractor.extract(
            Path(stored_file.storage_path),
            mime_type,
        )
        persisted_profile = CandidateProfile(
            candidate_document_id=candidate_document.id,
            profile_payload=candidate_profile.model_dump(mode="json"),
        )
        self._db_session.add(persisted_profile)
        await self._db_session.flush()

        generated_payload = await self._generate_screening_payload(
            jd_analysis,
            candidate_profile,
        )
        reconciled_payload = self._reconcile_screening_payload(generated_payload)
        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=persisted_profile.id,
            model_name=settings.gemini_model,
            screening_payload=reconciled_payload.model_dump(mode="json"),
        )
        self._db_session.add(screening)
        candidate_document.status = "completed"
        await self._db_session.commit()
        await self._db_session.refresh(screening)

        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=jd_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            candidate_profile=reconciled_payload.candidate_profile,
            result=reconciled_payload.result,
            audit=reconciled_payload.audit,
        )

    async def get_screening(self, screening_id: str) -> CVScreeningResponse | None:
        """Return a persisted screening by id when available."""
        if self._db_session is None:
            return None

        statement = (
            select(CandidateScreening, CandidateProfile, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return None

        screening, _, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        payload = StoredScreeningPayload.model_validate(screening.screening_payload)
        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=screening.jd_document_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=screening.created_at.replace(tzinfo=UTC).isoformat(),
            candidate_profile=payload.candidate_profile,
            result=payload.result,
            audit=payload.audit,
        )

    async def _generate_screening_payload(
        self,
        jd_analysis: JDAnalysisPayload,
        candidate_profile: CandidateProfilePayload,
    ) -> StoredScreeningPayload:
        """Generate structured screening artifacts from JD analysis and candidate profile."""
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_screening_prompt()},
                {"type": "text", "text": jd_analysis.model_dump_json(indent=2)},
                {"type": "text", "text": candidate_profile.model_dump_json(indent=2)},
            ]
        )
        result = await self._screening_llm.ainvoke([message])
        return StoredScreeningPayload.model_validate(result)

    def _reconcile_screening_payload(
        self,
        payload: StoredScreeningPayload,
    ) -> StoredScreeningPayload:
        """Reconcile model output with deterministic backend rules."""
        result = payload.result.model_copy(deep=True)
        audit = payload.audit.model_copy(deep=True)

        recomputed_score = round(
            sum(item.weight * item.score for item in result.dimension_scores),
            2,
        )
        if result.match_score != recomputed_score:
            result.match_score = recomputed_score
            audit.reconciliation_notes.append(
                "Recomputed weighted match score from dimension scores."
            )

        has_knockout_failure = any(
            item.status == RequirementStatus.NOT_MET
            for item in result.knockout_assessments
        )
        if has_knockout_failure and result.recommendation != ScreeningRecommendation.REJECT:
            result.recommendation = ScreeningRecommendation.REJECT
            audit.reconciliation_notes.append(
                "Downgraded recommendation to reject because a knockout criterion was not met."
            )

        missing_must_have_evidence = any(
            item.priority == "must_have" and item.score > 0 and not item.evidence
            for item in result.dimension_scores
        )
        if missing_must_have_evidence:
            audit.consistency_flags.append(
                "Must-have dimension lacks supporting evidence."
            )
            if result.recommendation == ScreeningRecommendation.ADVANCE:
                result.recommendation = ScreeningRecommendation.REVIEW
                reconciliation_message = (
                    "Downgraded recommendation to review because a must-have "
                    + "dimension lacked evidence."
                )
                audit.reconciliation_notes.append(reconciliation_message)

        if not audit.profile_schema_version:
            audit.profile_schema_version = PROFILE_SCHEMA_VERSION
        if not audit.screening_schema_version:
            audit.screening_schema_version = SCREENING_SCHEMA_VERSION
        if not audit.generated_at:
            audit.generated_at = datetime.now(UTC).isoformat()

        return StoredScreeningPayload(
            candidate_profile=payload.candidate_profile,
            result=result,
            audit=audit,
        )

    async def _load_jd_analysis(self, jd_id: str) -> JDAnalysisPayload:
        """Load and validate the stored JD analysis for a screening request."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(JDDocument, JDAnalysis)
            .join(JDAnalysis, JDAnalysis.jd_document_id == JDDocument.id)
            .where(JDDocument.id == jd_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            raise JDNotReadyError("JD analysis not found or not ready")

        document, analysis = cast(tuple[JDDocument, JDAnalysis], cast(object, row))
        if document.status != "completed":
            raise JDNotReadyError("JD analysis not found or not ready")
        return JDAnalysisPayload.model_validate(analysis.analysis_payload)
