"""Services for CV screening against a stored JD analysis."""

import re
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol, cast

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.background_job import BackgroundJob, BackgroundJobStatus, BackgroundResourceType
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.interview import InterviewSession
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.cv import (
    CandidateProfilePayload,
    CVScreeningEnqueueResponse,
    CVScreeningHistoryItem,
    CVScreeningResponse,
    RequirementStatus,
    ScreeningRecommendation,
    StoredScreeningPayload,
)
from src.schemas.jd import JDAnalysisPayload
from src.services.cv_extractor import PROFILE_SCHEMA_VERSION
from src.services.datetime_utils import to_vietnam_isoformat, vietnam_now_isoformat
from src.services.file_storage import store_upload_file

SCREENING_SCHEMA_VERSION = "phase2.v2"
FUTURE_TIMELINE_PATTERNS = (
    "future relative to current standard screening periods",
    "projected future internships",
    "future date",
    "time contradiction",
    "mâu thuẫn về thời gian",
)


class StructuredScreeningInvoker(Protocol):
    """Minimal protocol for the LangChain structured screening client."""

    async def ainvoke(self, input: list[HumanMessage]) -> object:
        """Invoke the configured model and return structured screening artifacts."""


class JDNotReadyError(ValueError):
    """Raised when a referenced JD cannot be screened yet."""


def get_current_datetime() -> str:
    """Return the current Vietnam datetime as an ISO 8601 string."""
    return vietnam_now_isoformat()


def build_screening_prompt() -> str:
    """Return the structured screening instructions for single-call CV evaluation."""
    return (
        "You are a neutral hiring analyst evaluating one uploaded CV against one analyzed job "
        "description. Use the current Vietnam datetime (UTC+7) as the authoritative time "
        "context before "
        "making any timeline judgment. First extract a review-ready candidate profile directly "
        "from the CV using the CandidateProfilePayload shape. Then evaluate knockout criteria, "
        "minimum requirements, and rubric dimensions against the JD using only evidence "
        "explicitly present in the CV and JD. Do not infer unsupported qualifications. If "
        "evidence is missing or ambiguous, mark the item as unclear and explain why. Respect "
        "must-have, important, and nice-to-have priorities, and provide concise bilingual "
        "HR-facing reasons with evidence-backed findings only. Use high scores only when the CV "
        "contains strong direct evidence; use partial scores when evidence is incomplete or "
        "indirect. Ignore protected or non-job-related attributes, including name, age, gender, "
        "nationality, marital status, religion, photo, and other demographic signals. Do not use "
        "school prestige, location, or other proxy attributes unless the JD explicitly requires "
        "them. Never describe a past year as if it is still in the future. When dates or "
        "durations look inconsistent, use neutral ambiguity wording instead of asserting that the "
        "candidate is wrong. Return structured output only using the StoredScreeningPayload "
        "schema."
    )


class CVScreeningService:
    """Handle storage, profile extraction, and Phase 2 CV screening."""

    def __init__(
        self,
        upload_dir: Path | None = None,
        db_session: AsyncSession | None = None,
    ) -> None:
        """Initialize the screening service with optional test doubles."""
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

        persisted_profile = CandidateProfile(
            candidate_document_id=candidate_document.id,
            profile_payload={},
        )
        self._db_session.add(persisted_profile)
        await self._db_session.flush()

        generated_payload = await self._generate_screening_payload(
            jd_analysis=jd_analysis,
            file_path=Path(stored_file.storage_path),
            mime_type=mime_type,
        )
        reconciled_payload = self._reconcile_screening_payload(generated_payload)
        persisted_profile.profile_payload = reconciled_payload.candidate_profile.model_dump(
            mode="json"
        )
        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=persisted_profile.id,
            model_name=settings.gemini_model,
            status="completed",
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
            created_at=to_vietnam_isoformat(screening.created_at),
            candidate_profile=reconciled_payload.candidate_profile,
            result=reconciled_payload.result,
            audit=reconciled_payload.audit,
        )

    async def enqueue_screening_upload(
        self,
        jd_id: str,
        file_name: str,
        mime_type: str,
        file_bytes: bytes,
    ) -> CVScreeningEnqueueResponse:
        """Store the upload, persist processing rows, and enqueue screening work."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        await self._load_jd_analysis(jd_id)
        stored_file = store_upload_file(self._upload_dir, file_name, file_bytes)
        candidate_document = CandidateDocument(
            file_name=stored_file.file_name,
            mime_type=mime_type,
            storage_path=stored_file.storage_path,
            status="processing",
        )
        self._db_session.add(candidate_document)
        await self._db_session.flush()

        candidate_profile = CandidateProfile(
            candidate_document_id=candidate_document.id,
            profile_payload={},
        )
        self._db_session.add(candidate_profile)
        await self._db_session.flush()

        screening = CandidateScreening(
            jd_document_id=jd_id,
            candidate_profile_id=candidate_profile.id,
            model_name=settings.gemini_model,
            status="processing",
            screening_payload={},
        )
        self._db_session.add(screening)
        await self._db_session.flush()

        job = BackgroundJob(
            job_type="cv_screening",
            status="queued",
            resource_type="candidate_screening",
            resource_id=screening.id,
            payload={
                "screening_id": screening.id,
                "jd_id": jd_id,
                "candidate_document_id": candidate_document.id,
                "candidate_profile_id": candidate_profile.id,
                "file_name": stored_file.file_name,
                "mime_type": mime_type,
                "storage_path": stored_file.storage_path,
            },
        )
        self._db_session.add(job)
        await self._db_session.commit()
        await self._db_session.refresh(job)

        return CVScreeningEnqueueResponse(
            job_id=job.id,
            screening_id=screening.id,
            jd_id=jd_id,
            file_name=stored_file.file_name,
            status="processing",
        )

    async def run_screening_job(self, screening_id: str) -> None:
        """Execute queued screening work for one persisted screening row."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateProfile, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            raise ValueError("CV screening not found")

        screening, profile, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        screening.status = "running"
        candidate_document.status = "running"
        await self._db_session.flush()

        jd_analysis = await self._load_jd_analysis(screening.jd_document_id)
        generated_payload = await self._generate_screening_payload(
            jd_analysis=jd_analysis,
            file_path=Path(candidate_document.storage_path),
            mime_type=candidate_document.mime_type,
        )
        reconciled_payload = self._reconcile_screening_payload(generated_payload)
        profile.profile_payload = reconciled_payload.candidate_profile.model_dump(mode="json")
        screening.screening_payload = reconciled_payload.model_dump(mode="json")
        screening.status = "completed"
        candidate_document.status = "completed"
        await self._db_session.commit()

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

        screening, candidate_profile, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        interview_session_id = await self._get_interview_session_id(screening.id)
        if screening.status != "completed":
            return CVScreeningResponse(
                screening_id=screening.id,
                jd_id=screening.jd_document_id,
                candidate_id=candidate_document.id,
                file_name=candidate_document.file_name,
                status=cast(str, screening.status),
                created_at=to_vietnam_isoformat(screening.created_at),
                error_message=await self._get_screening_error_message(screening.id),
                interview_session_id=interview_session_id,
            )

        payload = self._normalize_stored_screening_payload(
            screening_payload=screening.screening_payload,
            candidate_profile_payload=candidate_profile.profile_payload,
            model_name=screening.model_name,
            created_at=screening.created_at,
        )
        return CVScreeningResponse(
            screening_id=screening.id,
            jd_id=screening.jd_document_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            status="completed",
            created_at=to_vietnam_isoformat(screening.created_at),
            interview_session_id=interview_session_id,
            candidate_profile=payload.candidate_profile,
            result=payload.result,
            audit=payload.audit,
            interview_draft=payload.interview_draft,
        )

    async def list_screenings_for_jd(self, jd_id: str) -> list[CVScreeningHistoryItem]:
        """Return persisted screenings for one JD in reverse chronological order."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.jd_document_id == jd_id)
            .order_by(CandidateScreening.created_at.desc())
        )
        rows = (await self._db_session.execute(statement)).all()

        return [
            self._build_screening_history_item(screening, candidate_document)
            for screening, candidate_document in cast(
                list[tuple[CandidateScreening, CandidateDocument]],
                cast(object, rows),
            )
        ]

    async def list_all_screenings(self) -> list[CVScreeningHistoryItem]:
        """Return all persisted screenings across every JD in reverse chronological order."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .order_by(CandidateScreening.created_at.desc())
        )
        rows = (await self._db_session.execute(statement)).all()

        return [
            self._build_screening_history_item(screening, candidate_document)
            for screening, candidate_document in cast(
                list[tuple[CandidateScreening, CandidateDocument]],
                cast(object, rows),
            )
        ]

    async def mark_screening_failed(self, screening_id: str, error_message: str) -> None:
        """Persist failed state for a screening and its document."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateProfile, CandidateDocument)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .join(CandidateDocument, CandidateDocument.id == CandidateProfile.candidate_document_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return

        screening, _, candidate_document = cast(
            tuple[CandidateScreening, CandidateProfile, CandidateDocument],
            cast(object, row),
        )
        screening.status = "failed"
        candidate_document.status = "failed"
        screening.screening_payload = {}
        await self._db_session.commit()

    def _build_screening_history_item(
        self,
        screening: CandidateScreening,
        candidate_document: CandidateDocument,
    ) -> CVScreeningHistoryItem:
        """Build a lightweight history item from a persisted screening row."""
        recommendation, match_score = self._extract_history_summary(screening.screening_payload)
        return CVScreeningHistoryItem(
            screening_id=screening.id,
            jd_id=screening.jd_document_id,
            candidate_id=candidate_document.id,
            file_name=candidate_document.file_name,
            created_at=to_vietnam_isoformat(screening.created_at),
            recommendation=recommendation,
            match_score=match_score,
        )

    def _sanitize_profile_uncertainties(
        self,
        candidate_profile: CandidateProfilePayload,
    ) -> tuple[CandidateProfilePayload, bool]:
        """Remove stale future-date timeline uncertainties from the profile."""
        current_year = datetime.now(UTC).year
        kept_uncertainties = []
        removed_stale_timeline = False

        for item in candidate_profile.profile_uncertainties:
            timeline_text = " ".join(
                filter(
                    None,
                    [item.title.en, item.title.vi, item.reason.en, item.reason.vi],
                )
            ).lower()
            years = [int(value) for value in re.findall(r"\b\d{4}\b", timeline_text)]
            mentions_future_timeline = any(
                pattern in timeline_text for pattern in FUTURE_TIMELINE_PATTERNS
            )
            stale_future_timeline = (
                mentions_future_timeline and years and max(years) <= current_year
            )
            if stale_future_timeline:
                removed_stale_timeline = True
                continue
            kept_uncertainties.append(item)

        sanitized_profile = candidate_profile.model_copy(
            update={"profile_uncertainties": kept_uncertainties},
            deep=True,
        )
        return sanitized_profile, removed_stale_timeline

    def _is_current_screening_payload(self, screening_payload: Mapping[str, object]) -> bool:
        """Return whether the stored payload already matches the Phase 2 shape."""
        return {"candidate_profile", "result", "audit"}.issubset(screening_payload.keys())

    def _has_current_schema_versions(self, screening_payload: Mapping[str, object]) -> bool:
        """Return whether a current-shape payload also uses current schema versions."""
        audit = screening_payload.get("audit")
        if not isinstance(audit, Mapping):
            return False
        return (
            audit.get("profile_schema_version") == PROFILE_SCHEMA_VERSION
            and audit.get("screening_schema_version") == SCREENING_SCHEMA_VERSION
        )

    def _normalize_candidate_profile_payload(
        self,
        candidate_profile_payload: dict[str, object],
    ) -> CandidateProfilePayload:
        """Normalize current and legacy candidate profile payloads."""
        try:
            return CandidateProfilePayload.model_validate(candidate_profile_payload)
        except Exception:
            summary = cast(
                dict[str, object],
                candidate_profile_payload.get("candidate_summary", {}),
            )
            legacy_experience = cast(
                list[dict[str, object]],
                candidate_profile_payload.get("experience", []),
            )
            legacy_projects = cast(
                list[object],
                candidate_profile_payload.get("projects_or_achievements", []),
            )
            legacy_skills = cast(list[str], candidate_profile_payload.get("skills", []))
            legacy_education = cast(
                list[dict[str, object]],
                candidate_profile_payload.get("education", []),
            )
            legacy_languages = cast(
                list[object],
                candidate_profile_payload.get("languages", []),
            )
            adapted_payload = {
                "candidate_summary": {
                    "full_name": summary.get("full_name"),
                    "current_title": summary.get("current_title"),
                    "location": summary.get("location"),
                    "total_years_experience": summary.get("years_of_experience"),
                    "seniority_signal": "unknown",
                    "professional_summary": None,
                },
                "work_experience": [
                    {
                        "company": item.get("company", "Unknown"),
                        "role": item.get("role", "Unknown"),
                        "start_date_text": None,
                        "end_date_text": None,
                        "duration_text": None,
                        "responsibilities": cast(list[str], item.get("summary", [])),
                        "achievements": [],
                        "technologies": [],
                        "evidence_excerpts": cast(list[str], item.get("summary", [])),
                        "ambiguity_notes": [],
                    }
                    for item in legacy_experience
                ],
                "projects": [
                    {
                        "name": None,
                        "role": None,
                        "summary": str(item),
                        "technologies": [],
                        "domain_context": None,
                        "evidence_excerpts": [str(item)],
                    }
                    for item in legacy_projects
                ],
                "skills_inventory": [
                    {
                        "skill_name": skill,
                        "proficiency_signal": None,
                        "evidence_excerpts": [skill],
                        "source_section": "skills",
                    }
                    for skill in legacy_skills
                ],
                "education": [
                    {
                        "institution": item.get("institution", "Unknown"),
                        "degree": item.get("degree"),
                        "field_of_study": item.get("field_of_study"),
                        "graduation_text": item.get("graduation_text"),
                        "evidence_excerpts": [
                            " | ".join(
                                str(part)
                                for part in [
                                    item.get("institution"),
                                    item.get("degree"),
                                    item.get("field_of_study"),
                                ]
                                if part
                            )
                        ],
                    }
                    for item in legacy_education
                ],
                "certifications": cast(
                    list[dict[str, object]],
                    candidate_profile_payload.get("certifications", []),
                ),
                "languages": [
                    {
                        "language_name": (
                            item
                            if isinstance(item, str)
                            else str(item.get("language_name", "Unknown"))
                        ),
                        "proficiency_signal": (
                            None
                            if isinstance(item, str)
                            else item.get("proficiency_signal")
                        ),
                        "evidence_excerpts": (
                            [item]
                            if isinstance(item, str)
                            else cast(list[str], item.get("evidence_excerpts", []))
                        ),
                    }
                    for item in legacy_languages
                ],
                "profile_uncertainties": [],
            }
            return CandidateProfilePayload.model_validate(adapted_payload)

    def _normalize_stored_screening_payload(
        self,
        *,
        screening_payload: dict[str, object],
        candidate_profile_payload: dict[str, object],
        model_name: str,
        created_at: datetime,
    ) -> StoredScreeningPayload:
        """Normalize current and legacy stored payloads into the Phase 2 schema."""
        recommendation_source = screening_payload.get("recommendation")
        if recommendation_source is None and self._is_current_screening_payload(screening_payload):
            result_payload = screening_payload.get("result")
            if isinstance(result_payload, Mapping):
                recommendation_source = result_payload.get("recommendation")

        decision_reason_source = screening_payload.get("decision_reason")
        screening_summary_source = screening_payload.get("screening_summary")
        knockout_source = screening_payload.get("knockout_assessments", [])
        minimum_requirements_source = screening_payload.get("minimum_requirement_checks", [])
        dimension_scores_source = screening_payload.get("dimension_scores", [])
        strengths_source = screening_payload.get("strengths", [])
        gaps_source = screening_payload.get("gaps", [])
        uncertainties_source = screening_payload.get("uncertainties", [])
        match_score_source = screening_payload.get("match_score", 0.0)
        if self._is_current_screening_payload(screening_payload):
            result_payload = screening_payload.get("result")
            if isinstance(result_payload, Mapping):
                decision_reason_source = result_payload.get("decision_reason")
                screening_summary_source = result_payload.get("screening_summary")
                knockout_source = result_payload.get("knockout_assessments", [])
                minimum_requirements_source = result_payload.get(
                    "minimum_requirement_checks",
                    [],
                )
                dimension_scores_source = result_payload.get("dimension_scores", [])
                strengths_source = result_payload.get("strengths", [])
                gaps_source = result_payload.get("gaps", [])
                uncertainties_source = result_payload.get("uncertainties", [])
                match_score_source = result_payload.get("match_score", 0.0)

        if self._is_current_screening_payload(
            screening_payload
        ) and self._has_current_schema_versions(screening_payload):
            payload = StoredScreeningPayload.model_validate(screening_payload)
            return self._reconcile_screening_payload(payload)

        candidate_profile = self._normalize_candidate_profile_payload(candidate_profile_payload)
        recommendation = str(recommendation_source or "review")
        interview_draft_source = screening_payload.get("interview_draft")
        sanitized_payload = {
            "candidate_profile": candidate_profile.model_dump(mode="json"),
            "result": {
                "match_score": float(match_score_source),
                "recommendation": recommendation,
                "decision_reason": decision_reason_source
                or {
                    "vi": "Ban ghi legacy da duoc lam sach de tranh hien thi noi dung cu.",
                    "en": "This legacy record was sanitized to avoid showing stale content.",
                },
                "screening_summary": screening_summary_source
                or {
                    "vi": "Ket qua screening cu da duoc chuan hoa.",
                    "en": "This legacy screening result has been normalized.",
                },
                "knockout_assessments": knockout_source,
                "minimum_requirement_checks": minimum_requirements_source,
                "dimension_scores": dimension_scores_source,
                "strengths": strengths_source,
                "gaps": gaps_source,
                "uncertainties": uncertainties_source,
                "follow_up_questions": [],
                "risk_flags": [],
            },
            "audit": {
                "extraction_model": model_name,
                "screening_model": model_name,
                "profile_schema_version": PROFILE_SCHEMA_VERSION,
                "screening_schema_version": SCREENING_SCHEMA_VERSION,
                "generated_at": to_vietnam_isoformat(created_at),
                "reconciliation_notes": [
                    "Sanitized a legacy screening payload and removed stale "
                    "follow-up questions, risk flags, and audit metadata.",
                ],
                "consistency_flags": [
                    "Legacy screening payload was normalized from a pre-phase2 schema.",
                ],
            },
            "interview_draft": interview_draft_source,
        }
        payload = StoredScreeningPayload.model_validate(sanitized_payload)
        return self._reconcile_screening_payload(payload)

    async def backfill_screening_payload(self, screening_id: str) -> bool:
        """Rewrite one stored legacy payload into the current Phase 2 shape."""
        if self._db_session is None:
            raise RuntimeError("CVScreeningService requires a database session")

        statement = (
            select(CandidateScreening, CandidateProfile)
            .join(CandidateProfile, CandidateProfile.id == CandidateScreening.candidate_profile_id)
            .where(CandidateScreening.id == screening_id)
        )
        row = (await self._db_session.execute(statement)).one_or_none()
        if row is None:
            return False

        screening, candidate_profile = cast(
            tuple[CandidateScreening, CandidateProfile],
            cast(object, row),
        )
        if self._is_current_screening_payload(
            screening.screening_payload,
        ) and self._has_current_schema_versions(screening.screening_payload):
            return False

        normalized = self._normalize_stored_screening_payload(
            screening_payload=screening.screening_payload,
            candidate_profile_payload=candidate_profile.profile_payload,
            model_name=screening.model_name,
            created_at=screening.created_at,
        )
        screening.screening_payload = normalized.model_dump(mode="json")
        await self._db_session.commit()
        return True

    async def _get_screening_error_message(self, screening_id: str) -> str | None:
        """Return the latest failed background-job error for one screening."""
        if self._db_session is None:
            return None

        statement = (
            select(BackgroundJob)
            .where(BackgroundJob.resource_type == BackgroundResourceType.CANDIDATE_SCREENING)
            .where(BackgroundJob.resource_id == screening_id)
            .where(BackgroundJob.status == BackgroundJobStatus.FAILED)
            .order_by(BackgroundJob.completed_at.desc(), BackgroundJob.created_at.desc())
            .limit(1)
        )
        job = await self._db_session.scalar(statement)
        if job is None:
            return None
        return job.error_message

    async def _get_interview_session_id(self, screening_id: str) -> str | None:
        if self._db_session is None:
            return None
        session = await self._db_session.scalar(
            select(InterviewSession.id).where(
                InterviewSession.candidate_screening_id == screening_id
            )
        )
        return cast(str | None, session)

    def _extract_history_summary(
        self,
        screening_payload: dict[str, object],
    ) -> tuple[ScreeningRecommendation, float]:
        """Extract history summary fields from new or legacy screening payloads."""
        if self._is_current_screening_payload(screening_payload):
            payload = StoredScreeningPayload.model_validate(screening_payload)
            return payload.result.recommendation, payload.result.match_score

        recommendation = ScreeningRecommendation(
            str(screening_payload.get("recommendation", "review"))
        )
        match_score = float(screening_payload.get("match_score", 0.0))
        return recommendation, match_score

    async def _generate_screening_payload(
        self,
        *,
        jd_analysis: JDAnalysisPayload,
        file_path: Path,
        mime_type: str,
    ) -> StoredScreeningPayload:
        """Generate candidate profile and screening artifacts from JD analysis and CV media."""
        message = HumanMessage(
            content=[
                {"type": "text", "text": build_screening_prompt()},
                {"type": "text", "text": jd_analysis.model_dump_json(indent=2)},
                {
                    "type": "media",
                    "mime_type": mime_type,
                    "data": file_path.read_bytes(),
                },
            ]
        )
        result = await self._screening_llm.ainvoke([message])
        return StoredScreeningPayload.model_validate(result)

    def _reconcile_screening_payload(
        self,
        payload: StoredScreeningPayload,
    ) -> StoredScreeningPayload:
        """Reconcile model output with deterministic backend rules."""
        candidate_profile, removed_stale_timeline = self._sanitize_profile_uncertainties(
            payload.candidate_profile,
        )
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
            item.status == RequirementStatus.NOT_MET for item in result.knockout_assessments
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
            audit.consistency_flags.append("Must-have dimension lacks supporting evidence.")
            if result.recommendation == ScreeningRecommendation.ADVANCE:
                result.recommendation = ScreeningRecommendation.REVIEW
                reconciliation_message = (
                    "Downgraded recommendation to review because a must-have "
                    + "dimension lacked evidence."
                )
                audit.reconciliation_notes.append(reconciliation_message)

        if removed_stale_timeline:
            audit.reconciliation_notes.append(
                "Removed stale future-date timeline uncertainty from candidate profile."
            )

        audit.profile_schema_version = PROFILE_SCHEMA_VERSION
        audit.screening_schema_version = SCREENING_SCHEMA_VERSION
        if not audit.generated_at:
            audit.generated_at = vietnam_now_isoformat()

        return StoredScreeningPayload(
            candidate_profile=candidate_profile,
            result=result,
            audit=audit,
            interview_draft=payload.interview_draft,
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
