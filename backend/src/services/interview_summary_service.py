from __future__ import annotations

import json
from typing import Any

from google import genai

from src.config import settings


class InterviewSummaryService:
    def __init__(self, client: genai.Client | None = None) -> None:
        self._client = client or genai.Client(api_key=settings.gemini_api_key)

    async def generate(
        self,
        *,
        opening_question: str,
        turns: list[dict[str, object]],
        plan_payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        if not settings.gemini_api_key:
            return self._fallback_summary(opening_question=opening_question, turns=turns, plan_payload=plan_payload)

        prompt = (
            "You are summarizing a Vietnamese interview transcript.\n"
            "Return strict JSON with keys: final_summary, strengths, concerns, recommendation, turn_breakdown, competency_assessments, feedback_readiness.\n"
            "Each turn_breakdown item must include sequence_number, speaker, transcript_text, assessment.\n"
            "Each competency_assessments item must include competency_name, ai_score, evidence_strength, needs_hr_review, notes.\n"
            "Use the interview plan state to explain what competencies were covered, whether clarification or recovery was required, and whether the recommendation still needs HR review.\n"
            f"Opening question: {opening_question}\n"
            f"Plan payload: {json.dumps(plan_payload or {}, ensure_ascii=False)}\n"
            f"Transcript turns: {json.dumps(turns, ensure_ascii=False)}"
        )
        response = await self._client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        text = (response.text or "").strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_summary(
                opening_question=opening_question,
                turns=turns,
                plan_payload=plan_payload,
                raw_text=text,
            )
        if not isinstance(payload, dict):
            return self._fallback_summary(
                opening_question=opening_question,
                turns=turns,
                plan_payload=plan_payload,
                raw_text=text,
            )
        payload.setdefault("turn_breakdown", turns)
        return payload

    def _fallback_summary(
        self,
        *,
        opening_question: str,
        turns: list[dict[str, object]],
        plan_payload: dict[str, object] | None = None,
        raw_text: str | None = None,
    ) -> dict[str, Any]:
        candidate_turns = [turn for turn in turns if turn.get("speaker") == "candidate"]
        final_plan = plan_payload or {}
        competencies = final_plan.get("competencies", []) if isinstance(final_plan, dict) else []
        plan_events = final_plan.get("plan_events", []) if isinstance(final_plan, dict) else []
        decision_status = final_plan.get("interview_decision_status") if isinstance(final_plan, dict) else None
        covered_competencies = [
            item.get("name", {}).get("en")
            for item in competencies
            if isinstance(item, dict)
            and isinstance(item.get("name"), dict)
            and item.get("status") == "covered"
        ]
        required_follow_up = any(
            isinstance(event, dict) and event.get("chosen_action") in {"ask_clarification", "ask_recovery"}
            for event in plan_events
        )
        concerns = [] if candidate_turns else ["Chưa ghi nhận đủ câu trả lời từ ứng viên"]
        if required_follow_up:
            concerns.append("The interview required clarification or recovery follow-up before closing.")
        if decision_status == "escalate_hr":
            concerns.append("The final recommendation should stay in HR review because the plan escalated the session.")
        competency_assessments = []
        for item in competencies:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, dict):
                continue
            coverage = item.get("current_coverage")
            status = item.get("status")
            competency_assessments.append(
                {
                    "competency_name": name,
                    "ai_score": round(float(coverage), 4) if isinstance(coverage, int | float) else None,
                    "evidence_strength": round(float(coverage), 4) if isinstance(coverage, int | float) else None,
                    "needs_hr_review": status == "needs_recovery",
                    "notes": "Derived from the final plan coverage and adjustment status.",
                }
            )
        return {
            "final_summary": raw_text or "Buổi phỏng vấn đã kết thúc khi ứng viên rời phòng.",
            "strengths": [turn["transcript_text"] for turn in candidate_turns[:2]],
            "concerns": concerns,
            "recommendation": (
                "HR review is required before making the final decision."
                if decision_status == "escalate_hr"
                else "HR nên xem lại transcript chi tiết trước khi quyết định."
            ),
            "turn_breakdown": [
                {
                    "sequence_number": turn["sequence_number"],
                    "speaker": turn["speaker"],
                    "transcript_text": turn["transcript_text"],
                    "assessment": "Captured from realtime transcript.",
                }
                for turn in turns
            ],
            "opening_question": opening_question,
            "covered_competencies": [item for item in covered_competencies if isinstance(item, str)],
            "decision_status": decision_status,
            "competency_assessments": competency_assessments,
            "feedback_readiness": {
                "ready": True,
                "recommended_scope": "jd",
                "notes": "HR can score each competency and compare it against the AI baseline.",
            },
        }
