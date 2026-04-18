from __future__ import annotations

import asyncio
import importlib
import json
import logging
from collections.abc import Mapping, Sequence
from typing import Protocol, cast

from src.config import settings
from src.schemas.interview import InterviewSemanticAnswerEvaluation


class GeminiGenerateContentResponse(Protocol):
    text: str | None


class GeminiGenerateContentInvoker(Protocol):
    async def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config: object,
    ) -> GeminiGenerateContentResponse: ...


class GeminiAioClient(Protocol):
    models: GeminiGenerateContentInvoker


class GeminiClient(Protocol):
    aio: GeminiAioClient


class GeminiClientFactory(Protocol):
    def __call__(self, *, api_key: str) -> GeminiClient: ...


class GeminiModule(Protocol):
    Client: GeminiClientFactory


class GenerateContentConfigFactory(Protocol):
    def __call__(
        self,
        *,
        response_mime_type: str,
        response_schema: type[InterviewSemanticAnswerEvaluation],
    ) -> object: ...


class GeminiTypesModule(Protocol):
    GenerateContentConfig: GenerateContentConfigFactory


types = cast(GeminiTypesModule, cast(object, importlib.import_module("google.genai.types")))
genai = cast(GeminiModule, cast(object, importlib.import_module("google.genai")))


logger = logging.getLogger(__name__)


class InterviewAnswerEvaluatorService:
    """Semantic evaluator for interview answers using Gemini structured output."""

    def __init__(
        self,
        client: GeminiClient | None = None,
        *,
        model_name: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._client: GeminiClient = client or genai.Client(api_key=settings.gemini_api_key)
        self._model_name: str = (
            model_name or settings.interview_semantic_evaluator_model or settings.gemini_model
        )
        self._timeout_seconds: float = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.interview_semantic_evaluator_timeout_seconds
        )

    async def evaluate(
        self,
        *,
        plan_payload: Mapping[str, object],
        current_question: Mapping[str, object],
        current_competency: Mapping[str, object] | None,
        answer_text: str,
        recent_plan_events: Sequence[Mapping[str, object]],
        transcript_context: Sequence[Mapping[str, object]],
    ) -> InterviewSemanticAnswerEvaluation:
        if not settings.gemini_api_key:
            raise ValueError("Semantic answer evaluation requires a configured Gemini API key")

        prompt = self._build_prompt(
            plan_payload=plan_payload,
            current_question=current_question,
            current_competency=current_competency,
            answer_text=answer_text,
            recent_plan_events=recent_plan_events,
            transcript_context=transcript_context,
        )
        try:
            response: GeminiGenerateContentResponse = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=InterviewSemanticAnswerEvaluation,
                    ),
                ),
                timeout=self._timeout_seconds,
            )
        except TimeoutError as exc:
            logger.warning("Semantic answer evaluation timed out", extra={"model": self._model_name})
            raise ValueError("Semantic answer evaluation timed out") from exc
        except Exception:
            logger.exception("Semantic answer evaluation failed", extra={"model": self._model_name})
            raise

        text = (response.text or "").strip()
        if not text:
            raise ValueError("Semantic answer evaluation returned an empty response")
        try:
            payload_obj = cast(object, json.loads(text))
        except json.JSONDecodeError as exc:
            raise ValueError("Semantic answer evaluation did not return valid JSON") from exc
        if not isinstance(payload_obj, Mapping):
            raise ValueError("Semantic answer evaluation did not return an object")
        payload = cast(Mapping[str, object], payload_obj)
        return InterviewSemanticAnswerEvaluation.model_validate(payload)

    def _build_prompt(
        self,
        *,
        plan_payload: Mapping[str, object],
        current_question: Mapping[str, object],
        current_competency: Mapping[str, object] | None,
        answer_text: str,
        recent_plan_events: Sequence[Mapping[str, object]],
        transcript_context: Sequence[Mapping[str, object]],
    ) -> str:
        return (
            "You are the semantic answer evaluator for an adaptive interview system.\n"
            "Return JSON only and follow the provided response schema exactly.\n"
            "Judge the candidate's answer semantically, not by keyword overlap.\n"
            "A good answer may use different words from the question while still giving usable evidence.\n"
            "A weak answer may sound fluent but still be off-topic, low-signal, evasive, or unresolved.\n"
            "Use these labels carefully:\n"
            "- answer_quality=strong: directly answers the competency with concrete evidence or a credible example.\n"
            "- answer_quality=partial: relevant answer with some evidence, but still incomplete.\n"
            "- answer_quality=low_signal: vague, generic, or too abstract to score well.\n"
            "- answer_quality=off_topic: mostly answers something else, even if articulate.\n"
            "- answer_quality=explicit_gap: clearly implies the candidate does not have direct experience for this competency.\n"
            "- answer_quality=inconsistent: the answer introduces timeline, ownership, or claim inconsistencies.\n"
            "Use evidence_progress=improved when this answer adds usable evidence for the current competency, unchanged when it does not materially help, and regressed when it weakens prior confidence.\n"
            "Use recommended_action=continue when the answer is useful and the interviewer should keep probing the same competency.\n"
            "Use recommended_action=clarify when the answer is somewhat relevant but still needs a tighter follow-up.\n"
            "Use recommended_action=move_on when the interviewer should stop spending turns on this competency, either because enough evidence was gathered or because the competency is currently unresolvable.\n"
            "Use recommended_action=recovery when the answer should trigger a neutral recovery question about inconsistency.\n"
            "Use recommended_action=wrap_up only when the interview is effectively ready to close.\n"
            "Lower confidence instead of forcing an aggressive action.\n"
            "Set needs_hr_review=true only when ambiguity or inconsistency should remain visible to HR.\n"
            "The reason must be short, factual, and bilingual.\n"
            f"Current question: {json.dumps(current_question, ensure_ascii=False)}\n"
            f"Current competency: {json.dumps(current_competency, ensure_ascii=False)}\n"
            f"Recent plan events: {json.dumps(recent_plan_events, ensure_ascii=False)}\n"
            f"Transcript context: {json.dumps(transcript_context, ensure_ascii=False)}\n"
            f"Plan snapshot: {json.dumps(plan_payload, ensure_ascii=False)}\n"
            f"Candidate answer: {answer_text}"
        )
