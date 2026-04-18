from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import UTC, datetime
import json

from google import genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.cv import CandidateProfile, CandidateScreening
from src.models.interview import (
    InterviewFeedbackMemory,
    InterviewFeedbackPolicy,
    InterviewFeedbackPolicyAudit,
    InterviewFeedbackRecord,
    InterviewSession,
)
from src.models.user import User
from src.schemas.interview import (
    InterviewCompetencyPolicyOverride,
    InterviewFeedbackCompetencyResponse,
    InterviewFeedbackPolicyCollectionResponse,
    InterviewFeedbackPolicyPayload,
    InterviewFeedbackPolicyResponse,
    InterviewFeedbackRequest,
    InterviewFeedbackResponse,
    InterviewFeedbackFailureReason,
    InterviewFeedbackMemoryResponse,
    InterviewFeedbackMetricItem,
    InterviewFeedbackPolicyAuditResponse,
    InterviewFeedbackSessionDisagreementItem,
    InterviewFeedbackSummaryResponse,
    InterviewPolicySummaryPayload,
    InterviewPolicyThresholds,
    InterviewSessionCompetencyAssessment,
    SuggestInterviewFeedbackPolicyResponse,
)
from src.schemas.jd import BilingualText
from src.services.datetime_utils import to_vietnam_isoformat


class InterviewFeedbackService:
    """Capture HR feedback, compute analytics, and manage JD interview policies."""

    def __init__(self, db_session: AsyncSession, client: genai.Client | None = None) -> None:
        self._db_session = db_session
        self._client = client or genai.Client(api_key=settings.gemini_api_key)

    async def submit_feedback(
        self,
        session_id: str,
        payload: InterviewFeedbackRequest,
        current_user: User,
    ) -> InterviewFeedbackResponse:
        session, screening = await self._load_session_screening(session_id)
        if session.status != "completed":
            raise ValueError("Interview feedback is only available after the session is completed")

        ai_recommendation = self._derive_ai_recommendation(session, screening)
        ai_competencies = self._derive_ai_competency_assessments(session)
        ai_competency_by_name = {
            item.competency_name.en.casefold(): item for item in ai_competencies if item.competency_name.en.strip()
        }

        competency_feedback: list[InterviewFeedbackCompetencyResponse] = []
        for item in payload.competencies:
            key = item.competency_name.en.casefold()
            ai_item = ai_competency_by_name.get(key)
            ai_score = ai_item.ai_score if ai_item is not None else None
            delta = None if ai_score is None or item.hr_score is None else round(ai_score - item.hr_score, 4)
            competency_feedback.append(
                InterviewFeedbackCompetencyResponse(
                    competency_name=item.competency_name,
                    ai_score=ai_score,
                    hr_score=item.hr_score,
                    delta=delta,
                    judgement=item.judgement,
                    missing_evidence=item.missing_evidence,
                    notes=item.notes,
                )
            )

        feedback = await self._db_session.scalar(
            select(InterviewFeedbackRecord).where(InterviewFeedbackRecord.interview_session_id == session.id)
        )
        if feedback is None:
            feedback = InterviewFeedbackRecord(
                interview_session_id=session.id,
                jd_document_id=screening.jd_document_id,
            )
            self._db_session.add(feedback)

        feedback.submitted_by_user_id = current_user.id
        feedback.submitted_by_email = current_user.email
        feedback.overall_agreement_score = payload.overall_agreement_score
        feedback.ai_recommendation = ai_recommendation
        feedback.hr_recommendation = payload.hr_recommendation
        feedback.recommendation_agreement = bool(
            ai_recommendation
            and payload.hr_recommendation
            and ai_recommendation.casefold() == payload.hr_recommendation.casefold()
        )
        feedback.overall_notes = payload.overall_notes
        feedback.missing_evidence_notes = payload.missing_evidence_notes
        feedback.false_positive_notes = payload.false_positive_notes
        feedback.false_negative_notes = payload.false_negative_notes
        feedback.feedback_payload = {
            "competencies": [item.model_dump(mode="json") for item in competency_feedback],
            "ai_competency_assessments": [item.model_dump(mode="json") for item in ai_competencies],
        }
        await self._write_feedback_memories(
            session=session,
            screening=screening,
            feedback=feedback,
            competency_feedback=competency_feedback,
        )
        await self._db_session.commit()
        await self._db_session.refresh(feedback)
        return self._build_feedback_response(feedback)

    async def get_feedback(self, session_id: str) -> InterviewFeedbackResponse | None:
        feedback = await self._db_session.scalar(
            select(InterviewFeedbackRecord).where(InterviewFeedbackRecord.interview_session_id == session_id)
        )
        return None if feedback is None else self._build_feedback_response(feedback)

    async def get_feedback_summary(self, jd_id: str) -> InterviewFeedbackSummaryResponse:
        feedback_records = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackRecord)
                    .where(InterviewFeedbackRecord.jd_document_id == jd_id)
                    .order_by(InterviewFeedbackRecord.created_at.desc())
                )
            ).all()
        )
        active_policy = await self._get_latest_policy(jd_id, statuses=("active",))
        latest_suggested_policy = await self._get_latest_policy(jd_id, statuses=("suggested",))
        audits = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackPolicyAudit)
                    .where(InterviewFeedbackPolicyAudit.jd_document_id == jd_id)
                    .order_by(InterviewFeedbackPolicyAudit.created_at.desc())
                )
            ).all()
        )

        if not feedback_records:
            return InterviewFeedbackSummaryResponse(
                jd_id=jd_id,
                feedback_count=0,
                agreement_rate=0.0,
                recommendation_agreement_rate=0.0,
                average_score_delta=0.0,
                active_policy=self._build_policy_response(active_policy) if active_policy else None,
                latest_suggested_policy=self._build_policy_response(latest_suggested_policy)
                if latest_suggested_policy
                else None,
                policy_audit_trail=[self._build_audit_response(item) for item in audits[:10]],
            )

        competency_delta_total: dict[str, list[float]] = defaultdict(list)
        judgement_counter: Counter[str] = Counter()
        failure_counter: Counter[str] = Counter()
        disagreement_sessions: list[InterviewFeedbackSessionDisagreementItem] = []
        score_deltas: list[float] = []
        recommendation_agreements = 0
        agreement_hits = 0

        for record in feedback_records:
            if record.overall_agreement_score >= 0.7:
                agreement_hits += 1
            if record.recommendation_agreement:
                recommendation_agreements += 1
            competencies = self._parse_feedback_competencies(record.feedback_payload)
            delta_magnitude = 0.0
            for competency in competencies:
                judgement_counter[competency.judgement] += 1
                if competency.delta is not None:
                    competency_delta_total[competency.competency_name.en].append(abs(competency.delta))
                    score_deltas.append(abs(competency.delta))
                    delta_magnitude += abs(competency.delta)
                if competency.missing_evidence:
                    failure_counter[competency.missing_evidence.strip()] += 1
                if competency.notes:
                    failure_counter[competency.notes.strip()] += 1
            for note in [record.missing_evidence_notes, record.false_positive_notes, record.false_negative_notes]:
                if note:
                    failure_counter[note.strip()] += 1

            session = await self._db_session.get(InterviewSession, record.interview_session_id)
            disagreement_sessions.append(
                InterviewFeedbackSessionDisagreementItem(
                    session_id=record.interview_session_id,
                    candidate_name=session.candidate_identity if session is not None else None,
                    overall_agreement_score=record.overall_agreement_score,
                    recommendation_agreement=record.recommendation_agreement,
                    delta_magnitude=round(delta_magnitude, 4),
                    created_at=to_vietnam_isoformat(record.created_at) or "",
                )
            )

        return InterviewFeedbackSummaryResponse(
            jd_id=jd_id,
            feedback_count=len(feedback_records),
            agreement_rate=round(agreement_hits / len(feedback_records), 4),
            recommendation_agreement_rate=round(recommendation_agreements / len(feedback_records), 4),
            average_score_delta=round(sum(score_deltas) / len(score_deltas), 4) if score_deltas else 0.0,
            competency_deltas=[
                InterviewFeedbackMetricItem(
                    label=label,
                    value=round(sum(values) / len(values), 4),
                )
                for label, values in sorted(
                    competency_delta_total.items(),
                    key=lambda item: sum(item[1]) / len(item[1]),
                    reverse=True,
                )
            ],
            judgement_breakdown=[
                InterviewFeedbackMetricItem(label=label, value=float(count))
                for label, count in judgement_counter.most_common()
            ],
            failure_reasons=[
                InterviewFeedbackFailureReason(reason=reason, count=count)
                for reason, count in failure_counter.most_common(8)
            ],
            disagreement_sessions=sorted(
                disagreement_sessions,
                key=lambda item: item.delta_magnitude,
                reverse=True,
            )[:8],
            active_policy=self._build_policy_response(active_policy) if active_policy else None,
            latest_suggested_policy=self._build_policy_response(latest_suggested_policy)
            if latest_suggested_policy
            else None,
            policy_audit_trail=[self._build_audit_response(item) for item in audits[:10]],
        )

    async def get_policy_collection(self, jd_id: str) -> InterviewFeedbackPolicyCollectionResponse:
        active_policy = await self._get_latest_policy(jd_id, statuses=("active",))
        latest_suggested_policy = await self._get_latest_policy(jd_id, statuses=("suggested",))
        audits = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackPolicyAudit)
                    .where(InterviewFeedbackPolicyAudit.jd_document_id == jd_id)
                    .order_by(InterviewFeedbackPolicyAudit.created_at.desc())
                )
            ).all()
        )
        return InterviewFeedbackPolicyCollectionResponse(
            jd_id=jd_id,
            active_policy=self._build_policy_response(active_policy) if active_policy else None,
            latest_suggested_policy=self._build_policy_response(latest_suggested_policy)
            if latest_suggested_policy
            else None,
            memory_context=await self.get_memory_context(jd_id),
            policy_audit_trail=[self._build_audit_response(item) for item in audits[:10]],
        )

    async def suggest_policy(
        self,
        jd_id: str,
        current_user: User,
    ) -> SuggestInterviewFeedbackPolicyResponse:
        if not settings.gemini_api_key:
            raise ValueError("AI policy suggestion requires a configured Gemini API key")

        summary = await self.get_feedback_summary(jd_id)
        version = await self._next_policy_version(jd_id)
        active_policy = await self._get_latest_policy(jd_id, statuses=("active",))
        memory_context = await self.get_memory_context(jd_id)
        policy_payload, summary_payload = await self._generate_llm_policy(
            jd_id=jd_id,
            summary=summary,
            active_policy=active_policy,
            memory_context=memory_context,
        )
        policy = InterviewFeedbackPolicy(
            jd_document_id=jd_id,
            status="suggested",
            version=version,
            source_feedback_count=summary.feedback_count,
            policy_payload=policy_payload.model_dump(mode="json"),
            summary_payload=summary_payload.model_dump(mode="json"),
        )
        self._db_session.add(policy)
        await self._db_session.flush()
        audit = InterviewFeedbackPolicyAudit(
            jd_document_id=jd_id,
            policy_id=policy.id,
            event_type="policy.suggested",
            payload={
                "version": version,
                "source_feedback_count": summary.feedback_count,
                "generated_by_user_id": current_user.id,
                "generated_by_email": current_user.email,
                "generation_mode": "llm",
                "model_name": settings.gemini_model,
            },
        )
        self._db_session.add(audit)
        await self._db_session.commit()
        await self._db_session.refresh(policy)
        await self._db_session.refresh(audit)
        return SuggestInterviewFeedbackPolicyResponse(
            policy=self._build_policy_response(policy),
            audit_event=self._build_audit_response(audit),
        )

    async def apply_policy(
        self,
        jd_id: str,
        policy_id: str,
        current_user: User,
    ) -> InterviewFeedbackPolicyResponse:
        policy = await self._db_session.get(InterviewFeedbackPolicy, policy_id)
        if policy is None or policy.jd_document_id != jd_id:
            raise ValueError("Interview feedback policy not found")

        active_policies = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackPolicy).where(
                        InterviewFeedbackPolicy.jd_document_id == jd_id,
                        InterviewFeedbackPolicy.status == "active",
                    )
                )
            ).all()
        )
        for item in active_policies:
            item.status = "superseded"
        policy.status = "active"
        policy.approved_by_user_id = current_user.id
        policy.approved_by_email = current_user.email
        policy.approved_at = datetime.now(UTC)
        self._db_session.add(
            InterviewFeedbackPolicyAudit(
                jd_document_id=jd_id,
                policy_id=policy.id,
                event_type="policy.activated",
                payload={
                    "version": policy.version,
                    "approved_by_user_id": current_user.id,
                    "approved_by_email": current_user.email,
                },
            )
        )
        await self._db_session.commit()
        await self._db_session.refresh(policy)
        return self._build_policy_response(policy)

    async def reject_policy(
        self,
        jd_id: str,
        policy_id: str,
        current_user: User,
    ) -> InterviewFeedbackPolicyResponse:
        policy = await self._db_session.get(InterviewFeedbackPolicy, policy_id)
        if policy is None or policy.jd_document_id != jd_id:
            raise ValueError("Interview feedback policy not found")
        policy.status = "superseded"
        self._db_session.add(
            InterviewFeedbackPolicyAudit(
                jd_document_id=jd_id,
                policy_id=policy.id,
                event_type="policy.rejected",
                payload={
                    "version": policy.version,
                    "rejected_by_user_id": current_user.id,
                    "rejected_by_email": current_user.email,
                },
            )
        )
        await self._db_session.commit()
        await self._db_session.refresh(policy)
        return self._build_policy_response(policy)

    async def get_active_policy_payload(self, jd_id: str) -> tuple[int | None, InterviewFeedbackPolicyPayload | None, InterviewPolicySummaryPayload | None]:
        policy = await self._get_latest_policy(jd_id, statuses=("active",))
        if policy is None:
            return None, None, None
        return (
            policy.version,
            InterviewFeedbackPolicyPayload.model_validate(policy.policy_payload),
            InterviewPolicySummaryPayload.model_validate(policy.summary_payload),
        )

    def _derive_ai_recommendation(
        self,
        session: InterviewSession,
        screening: CandidateScreening,
    ) -> str | None:
        recommendation = session.summary_payload.get("recommendation")
        if isinstance(recommendation, str) and recommendation.strip():
            return recommendation.strip()
        result = screening.screening_payload.get("result")
        if isinstance(result, Mapping):
            screening_recommendation = result.get("recommendation")
            if isinstance(screening_recommendation, str) and screening_recommendation.strip():
                return screening_recommendation.strip()
        return None

    def _derive_ai_competency_assessments(
        self,
        session: InterviewSession,
    ) -> list[InterviewSessionCompetencyAssessment]:
        summary_assessments = session.summary_payload.get("competency_assessments")
        if isinstance(summary_assessments, list):
            parsed: list[InterviewSessionCompetencyAssessment] = []
            for item in summary_assessments:
                if not isinstance(item, Mapping):
                    continue
                try:
                    parsed.append(InterviewSessionCompetencyAssessment.model_validate(item))
                except ValueError:
                    continue
            if parsed:
                return parsed

        plan_payload = session.plan_payload
        competencies_payload = plan_payload.get("competencies") if isinstance(plan_payload, Mapping) else None
        plan_events_payload = plan_payload.get("plan_events") if isinstance(plan_payload, Mapping) else None
        plan_events = list(plan_events_payload) if isinstance(plan_events_payload, list) else []
        assessments: list[InterviewSessionCompetencyAssessment] = []
        if not isinstance(competencies_payload, list):
            return assessments

        for item in competencies_payload:
            if not isinstance(item, Mapping):
                continue
            name_payload = item.get("name")
            if not isinstance(name_payload, Mapping):
                continue
            name = BilingualText.model_validate(name_payload)
            coverage = item.get("current_coverage")
            base_score = float(coverage) if isinstance(coverage, int | float) else 0.0
            status = item.get("status") if isinstance(item.get("status"), str) else "not_started"
            event_penalty = 0.0
            for event in plan_events:
                if not isinstance(event, Mapping):
                    continue
                affected = event.get("affected_competency")
                if not isinstance(affected, Mapping):
                    continue
                affected_en = affected.get("en")
                if affected_en != name.en:
                    continue
                chosen_action = event.get("chosen_action")
                if chosen_action == "ask_clarification":
                    event_penalty += 0.08
                if chosen_action == "ask_recovery":
                    event_penalty += 0.15
                if chosen_action == "move_on_from_unresolved_competency":
                    event_penalty += 0.18
            if status == "needs_recovery":
                event_penalty += 0.1
            ai_score = max(0.0, min(1.0, base_score - event_penalty))
            assessments.append(
                InterviewSessionCompetencyAssessment(
                    competency_name=name,
                    ai_score=round(ai_score, 4),
                    evidence_strength=round(base_score, 4),
                    needs_hr_review=status == "needs_recovery" or event_penalty >= 0.15,
                    notes=f"Derived from plan coverage={round(base_score, 2)} and runtime adjustment penalties.",
                )
            )
        return assessments

    async def _write_feedback_memories(
        self,
        *,
        session: InterviewSession,
        screening: CandidateScreening,
        feedback: InterviewFeedbackRecord,
        competency_feedback: list[InterviewFeedbackCompetencyResponse],
    ) -> None:
        existing_memories = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackMemory).where(
                        InterviewFeedbackMemory.feedback_record_id == feedback.id,
                    )
                )
            ).all()
        )
        for item in existing_memories:
            await self._db_session.delete(item)

        episodic_text = (
            f"Session {session.id} received HR feedback with agreement score {feedback.overall_agreement_score}. "
            f"AI recommendation={feedback.ai_recommendation}, HR recommendation={feedback.hr_recommendation}."
        )
        self._db_session.add(
            InterviewFeedbackMemory(
                jd_document_id=screening.jd_document_id,
                interview_session_id=session.id,
                feedback_record_id=feedback.id,
                memory_type="episodic",
                title="HR feedback session episode",
                memory_text=episodic_text,
                importance_score=max(0.4, abs(1 - feedback.overall_agreement_score)),
                source_event_at=feedback.updated_at,
                payload={
                    "session_id": session.id,
                    "agreement_score": feedback.overall_agreement_score,
                    "recommendation_agreement": feedback.recommendation_agreement,
                },
            )
        )
        for item in competency_feedback:
            if item.delta is None:
                continue
            self._db_session.add(
                InterviewFeedbackMemory(
                    jd_document_id=screening.jd_document_id,
                    interview_session_id=session.id,
                    feedback_record_id=feedback.id,
                    memory_type="episodic",
                    title=f"Competency disagreement: {item.competency_name.en}",
                    memory_text=(
                        f"For competency {item.competency_name.en}, AI score={item.ai_score}, "
                        f"HR score={item.hr_score}, judgement={item.judgement}, delta={item.delta}."
                    ),
                    importance_score=min(1.0, abs(item.delta) + 0.2),
                    source_event_at=feedback.updated_at,
                    payload=item.model_dump(mode="json"),
                )
            )

        semantic_counter = Counter(item.competency_name.en for item in competency_feedback if item.judgement != "accurate")
        for competency_name, count in semantic_counter.items():
            matching = [item for item in competency_feedback if item.competency_name.en == competency_name]
            top_judgements = Counter(item.judgement for item in matching).most_common(1)
            primary_judgement = top_judgements[0][0] if top_judgements else "accurate"
            self._db_session.add(
                InterviewFeedbackMemory(
                    jd_document_id=screening.jd_document_id,
                    interview_session_id=session.id,
                    feedback_record_id=feedback.id,
                    memory_type="semantic",
                    title=f"Learned pattern: {competency_name}",
                    memory_text=(
                        f"Recent HR feedback suggests competency {competency_name} is often judged as {primary_judgement}."
                    ),
                    importance_score=min(1.0, 0.3 + count * 0.15),
                    source_event_at=feedback.updated_at,
                    payload={
                        "competency_name": competency_name,
                        "primary_judgement": primary_judgement,
                        "sample_count": count,
                    },
                )
            )

    async def _load_session_screening(
        self,
        session_id: str,
    ) -> tuple[InterviewSession, CandidateScreening]:
        session = await self._db_session.get(InterviewSession, session_id)
        if session is None:
            raise ValueError("Interview session not found")
        screening = await self._db_session.get(CandidateScreening, session.candidate_screening_id)
        if screening is None:
            raise ValueError("CV screening not found")
        return session, screening

    async def get_memory_context(self, jd_id: str) -> list[InterviewFeedbackMemoryResponse]:
        memories = list(
            (
                await self._db_session.scalars(
                    select(InterviewFeedbackMemory)
                    .where(InterviewFeedbackMemory.jd_document_id == jd_id)
                    .order_by(
                        InterviewFeedbackMemory.importance_score.desc(),
                        InterviewFeedbackMemory.created_at.desc(),
                    )
                )
            ).all()
        )
        return [self._build_memory_response(item) for item in memories[:8]]

    async def _generate_llm_policy(
        self,
        *,
        jd_id: str,
        summary: InterviewFeedbackSummaryResponse,
        active_policy: InterviewFeedbackPolicy | None,
        memory_context: list[InterviewFeedbackMemoryResponse],
    ) -> tuple[InterviewFeedbackPolicyPayload, InterviewPolicySummaryPayload]:
        prompt = self._build_policy_generation_prompt(
            jd_id=jd_id,
            summary=summary,
            active_policy=active_policy,
            memory_context=memory_context,
        )
        response = await self._client.aio.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        text = (response.text or "").strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("AI policy suggestion could not be parsed as JSON") from exc
        if not isinstance(payload, Mapping):
            raise ValueError("AI policy suggestion could not be validated")
        raw_policy_payload = payload.get("policy_payload")
        raw_summary_payload = payload.get("summary_payload")
        if not isinstance(raw_policy_payload, Mapping) or not isinstance(raw_summary_payload, Mapping):
            raise ValueError("AI policy suggestion could not be validated")
        try:
            policy_payload = InterviewFeedbackPolicyPayload.model_validate(raw_policy_payload)
            summary_payload = InterviewPolicySummaryPayload.model_validate(raw_summary_payload)
        except ValueError as exc:
            raise ValueError("AI policy suggestion could not be validated") from exc
        return policy_payload, summary_payload

    def _build_policy_generation_prompt(
        self,
        *,
        jd_id: str,
        summary: InterviewFeedbackSummaryResponse,
        active_policy: InterviewFeedbackPolicy | None,
        memory_context: list[InterviewFeedbackMemoryResponse],
    ) -> str:
        active_policy_payload = (
            {
                "policy_payload": active_policy.policy_payload,
                "summary_payload": active_policy.summary_payload,
                "version": active_policy.version,
            }
            if active_policy is not None
            else None
        )
        schema_hint = {
            "policy_payload": {
                "global_thresholds": InterviewPolicyThresholds().model_dump(mode="json"),
                "competency_overrides": [
                    InterviewCompetencyPolicyOverride(
                        competency_name=BilingualText(vi="Example", en="Example"),
                        coverage_target_multiplier=1.0,
                        clarification_bias=0.0,
                        escalation_bias=0.0,
                        priority_boost=0.0,
                        preferred_question_types=["clarification"],
                        require_measurable_outcome=False,
                        adjustment_reason="Example only",
                    ).model_dump(mode="json")
                ],
                "questioning_rules": {
                    "prefer_more_examples_for_overrated_competencies": True,
                    "require_measurable_outcome_before_advance": True,
                },
                "application_scope": {
                    "jd_id": jd_id,
                    "effective_from": datetime.now(UTC).isoformat(),
                },
            },
            "summary_payload": InterviewPolicySummaryPayload(
                source_feedback_count=summary.feedback_count,
                top_overrated_competencies=[],
                top_underrated_competencies=[],
                top_failure_reasons=[],
                expected_effects=[],
                recommendation_agreement_rate=summary.recommendation_agreement_rate,
            ).model_dump(mode="json"),
        }
        return (
            "You are generating an interview feedback policy for one JD in InterviewX.\n"
            "Return strict JSON with exactly two top-level keys: policy_payload and summary_payload.\n"
            "Do not wrap the JSON in markdown.\n"
            "Only create competency overrides for competencies that appear in competency_deltas.\n"
            "Keep all numeric values inside the schema ranges implied by the example schema.\n"
            "Make the policy more conservative when disagreement is high, but do not invent unsupported competencies.\n"
            "Avoid repeated clarification loops. When a competency keeps producing low-signal answers after the clarification budget is exhausted, prefer moving on while recording an unresolved evidence gap.\n"
            "Use semantic confidence thresholds to control when the semantic evaluator may override heuristics. Keep semantic_move_on_confidence_threshold stricter than semantic_default_confidence_threshold when the JD is sensitive to false positives.\n"
            "Expected effects must be short, factual, and demo-friendly.\n"
            f"JD id: {jd_id}\n"
            f"Feedback summary: {json.dumps(summary.model_dump(mode='json'), ensure_ascii=False)}\n"
            f"Retrieved memory context: {json.dumps([item.model_dump(mode='json') for item in memory_context], ensure_ascii=False)}\n"
            f"Active policy: {json.dumps(active_policy_payload, ensure_ascii=False)}\n"
            f"Schema example: {json.dumps(schema_hint, ensure_ascii=False)}"
        )

    async def _get_latest_policy(
        self,
        jd_id: str,
        *,
        statuses: tuple[str, ...],
    ) -> InterviewFeedbackPolicy | None:
        return await self._db_session.scalar(
            select(InterviewFeedbackPolicy)
            .where(
                InterviewFeedbackPolicy.jd_document_id == jd_id,
                InterviewFeedbackPolicy.status.in_(statuses),
            )
            .order_by(
                InterviewFeedbackPolicy.version.desc(),
                InterviewFeedbackPolicy.created_at.desc(),
            )
        )

    async def _next_policy_version(self, jd_id: str) -> int:
        latest_policy = await self._db_session.scalar(
            select(InterviewFeedbackPolicy)
            .where(InterviewFeedbackPolicy.jd_document_id == jd_id)
            .order_by(InterviewFeedbackPolicy.version.desc())
        )
        return 1 if latest_policy is None else latest_policy.version + 1

    def _build_feedback_response(self, record: InterviewFeedbackRecord) -> InterviewFeedbackResponse:
        return InterviewFeedbackResponse(
            session_id=record.interview_session_id,
            jd_id=record.jd_document_id,
            submitted_by_user_id=record.submitted_by_user_id,
            submitted_by_email=record.submitted_by_email,
            overall_agreement_score=record.overall_agreement_score,
            ai_recommendation=record.ai_recommendation,
            hr_recommendation=record.hr_recommendation,
            recommendation_agreement=record.recommendation_agreement,
            overall_notes=record.overall_notes,
            missing_evidence_notes=record.missing_evidence_notes,
            false_positive_notes=record.false_positive_notes,
            false_negative_notes=record.false_negative_notes,
            competencies=self._parse_feedback_competencies(record.feedback_payload),
            created_at=to_vietnam_isoformat(record.created_at) or "",
            updated_at=to_vietnam_isoformat(record.updated_at) or "",
        )

    def _parse_feedback_competencies(
        self,
        payload: dict[str, object],
    ) -> list[InterviewFeedbackCompetencyResponse]:
        raw_items = payload.get("competencies") if isinstance(payload, Mapping) else None
        if not isinstance(raw_items, list):
            return []
        parsed: list[InterviewFeedbackCompetencyResponse] = []
        for item in raw_items:
            if not isinstance(item, Mapping):
                continue
            try:
                parsed.append(InterviewFeedbackCompetencyResponse.model_validate(item))
            except ValueError:
                continue
        return parsed

    def _build_memory_response(self, memory: InterviewFeedbackMemory) -> InterviewFeedbackMemoryResponse:
        return InterviewFeedbackMemoryResponse(
            memory_id=memory.id,
            jd_id=memory.jd_document_id,
            session_id=memory.interview_session_id,
            feedback_record_id=memory.feedback_record_id,
            memory_type=memory.memory_type,
            title=memory.title,
            memory_text=memory.memory_text,
            importance_score=memory.importance_score,
            source_event_at=to_vietnam_isoformat(memory.source_event_at),
            payload=memory.payload,
            created_at=to_vietnam_isoformat(memory.created_at) or "",
        )

    def _build_policy_response(self, policy: InterviewFeedbackPolicy) -> InterviewFeedbackPolicyResponse:
        return InterviewFeedbackPolicyResponse(
            policy_id=policy.id,
            jd_id=policy.jd_document_id,
            status=policy.status,
            version=policy.version,
            source_feedback_count=policy.source_feedback_count,
            policy_payload=InterviewFeedbackPolicyPayload.model_validate(policy.policy_payload),
            summary_payload=InterviewPolicySummaryPayload.model_validate(policy.summary_payload),
            approved_by_user_id=policy.approved_by_user_id,
            approved_by_email=policy.approved_by_email,
            approved_at=to_vietnam_isoformat(policy.approved_at),
            created_at=to_vietnam_isoformat(policy.created_at) or "",
            updated_at=to_vietnam_isoformat(policy.updated_at) or "",
        )

    def _build_audit_response(
        self,
        audit: InterviewFeedbackPolicyAudit,
    ) -> InterviewFeedbackPolicyAuditResponse:
        return InterviewFeedbackPolicyAuditResponse(
            event_type=audit.event_type,
            payload=audit.payload,
            created_at=to_vietnam_isoformat(audit.created_at) or "",
        )
