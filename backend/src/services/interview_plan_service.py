from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime

from google import genai
from google.genai import types

from src.config import settings
from src.schemas.interview import (
    GenerateInterviewQuestionsResponse,
    InterviewCompetencyPlan,
    InterviewPlanEvent,
    InterviewPlanPayload,
    InterviewQuestion,
    InterviewQuestionCandidate,
    InterviewScopeConfig,
)
from src.schemas.jd import BilingualText

INTERVIEW_SCOPE_INTRO_KEY = "__intro__"
INTRO_COMPETENCY_NAME = BilingualText(vi="Giới thiệu bản thân", en="Self introduction")


def get_current_datetime() -> str:
    """Return the current UTC datetime as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


class InterviewPlanService:
    """Build interview question suggestions from a completed screening payload."""

    def __init__(self, client: genai.Client | None = None) -> None:
        """Initialize the service with an optional GenAI client."""
        self._client = client or genai.Client(api_key=settings.gemini_api_key)

    def build_plan(
        self,
        screening_payload: dict[str, object],
        interview_scope: InterviewScopeConfig | None = None,
    ) -> InterviewPlanPayload:
        """Build a baseline interview plan from stored screening data."""
        result = screening_payload.get("result", {})
        if not isinstance(result, Mapping):
            result = {}

        follow_up_questions = result.get("follow_up_questions", [])
        dimension_scores = result.get("dimension_scores", [])
        competencies = self._build_competencies(dimension_scores)

        questions: list[InterviewQuestion] = []
        if isinstance(follow_up_questions, list):
            for index, item in enumerate(follow_up_questions):
                if not isinstance(item, Mapping):
                    continue
                linked_dimension = item.get("linked_dimension") or {"vi": "Chung", "en": "General"}
                question_payload = item.get("question")
                purpose_payload = item.get("purpose")
                if (
                    not isinstance(question_payload, Mapping)
                    or not isinstance(purpose_payload, Mapping)
                ):
                    continue
                dimension_name = BilingualText.model_validate(linked_dimension)
                purpose = BilingualText.model_validate(purpose_payload)
                questions.append(
                    InterviewQuestion(
                        question_index=index,
                        dimension_name=dimension_name,
                        prompt=BilingualText.model_validate(question_payload),
                        purpose=purpose,
                        source="screening",
                        question_type="planned",
                        rationale=purpose.en,
                        priority=index + 1,
                        target_competency=dimension_name,
                        evidence_gap=self._build_evidence_gap(dimension_name),
                        selection_reason=self._build_selection_reason(purpose),
                        transition_on_strong_answer="advance_to_next_competency",
                        transition_on_weak_answer="ask_clarification",
                    )
                )

        if not questions and isinstance(dimension_scores, list):
            for index, dimension in enumerate(dimension_scores[:3]):
                if not isinstance(dimension, Mapping):
                    continue
                dimension_name_payload = dimension.get("dimension_name")
                if not isinstance(dimension_name_payload, Mapping):
                    continue
                dimension_name = BilingualText.model_validate(dimension_name_payload)
                purpose = BilingualText(
                    vi="Xác minh tín hiệu từ CV screening",
                    en="Verify the signal from CV screening",
                )
                questions.append(
                    InterviewQuestion(
                        question_index=index,
                        dimension_name=dimension_name,
                        prompt=BilingualText(
                            vi=f"Hãy chia sẻ một ví dụ cụ thể về {dimension_name.vi.lower()}.",
                            en=f"Share one concrete example of your {dimension_name.en.lower()}.",
                        ),
                        purpose=purpose,
                        source="screening",
                        question_type="planned",
                        rationale=purpose.en,
                        priority=index + 1,
                        target_competency=dimension_name,
                        evidence_gap=self._build_evidence_gap(dimension_name),
                        selection_reason=self._build_selection_reason(purpose),
                        transition_on_strong_answer="advance_to_next_competency",
                        transition_on_weak_answer="ask_clarification",
                    )
                )

        session_goal = self._build_session_goal(result=result, questions=questions)
        plan = InterviewPlanPayload(
            session_goal=session_goal,
            opening_script=BilingualText(
                vi="Cảm ơn bạn đã tham gia. Tôi sẽ hỏi một vài câu ngắn dựa trên CV của bạn.",
                en="Thanks for joining. I will ask a few short questions based on your CV.",
            ),
            overall_strategy=self._build_overall_strategy(questions),
            current_phase="competency_validation",
            current_competency_index=0,
            next_intended_step=self._build_next_intended_step(competencies),
            interview_decision_status="continue",
            question_selection_policy=BilingualText(
                vi="Ưu tiên năng lực có bằng chứng còn thiếu rõ nhất trong CV screening.",
                en="Prioritize the competency with the clearest missing evidence from CV screening.",
            ),
            transition_rules=[
                BilingualText(
                    vi="Nếu câu trả lời chung chung, đặt câu hỏi làm rõ tiếp theo.",
                    en="If the answer is generic, ask a clarification question next.",
                ),
                BilingualText(
                    vi="Nếu câu trả lời có ví dụ cụ thể, chuyển sang năng lực ưu tiên tiếp theo.",
                    en="If the answer includes a concrete example, move to the next priority competency.",
                ),
            ],
            completion_criteria=[
                BilingualText(
                    vi="Thu thập đủ bằng chứng cho các năng lực trọng tâm trước khi kết thúc session.",
                    en="Collect enough evidence for the core competencies before closing the session.",
                )
            ],
            competencies=competencies,
            plan_events=self._build_plan_events(competencies),
            questions=questions,
        )
        return self._apply_scope_to_plan(plan, interview_scope)

    async def generate_questions(
        self,
        *,
        screening_id: str,
        screening_payload: dict[str, object],
        manual_questions: list[str],
        question_guidance: str | None,
        interview_scope: InterviewScopeConfig | None = None,
    ) -> GenerateInterviewQuestionsResponse:
        """Generate interview questions from HR input and screening evidence."""
        normalized_manual_questions = [
            question.strip() for question in manual_questions if question.strip()
        ]
        plan = self.build_plan(screening_payload, interview_scope=interview_scope)
        llm_generated_questions = await self._generate_llm_questions(
            screening_payload=screening_payload,
            plan=plan,
            manual_questions=normalized_manual_questions,
            question_guidance=question_guidance,
        )

        generated_questions: list[InterviewQuestionCandidate] = []
        seen_questions: set[str] = set()

        for question in normalized_manual_questions:
            dedupe_key = question.casefold()
            if dedupe_key in seen_questions:
                continue
            seen_questions.add(dedupe_key)
            generated_questions.append(
                InterviewQuestionCandidate(
                    question_text=question,
                    source="manual",
                    rationale="Provided directly by HR.",
                    question_type="manual",
                    selection_reason=BilingualText(
                        vi="Câu hỏi do HR cung cấp trực tiếp cho buổi phỏng vấn này.",
                        en="This question was provided directly by HR for this interview.",
                    ),
                )
            )

        for item in llm_generated_questions:
            question_text = item.question_text.strip()
            dedupe_key = question_text.casefold()
            if not question_text or dedupe_key in seen_questions:
                continue
            seen_questions.add(dedupe_key)
            generated_questions.append(item)

        if len(generated_questions) < 3:
            for item in self._fallback_generated_questions(plan, question_guidance):
                question_text = item.question_text.strip()
                dedupe_key = question_text.casefold()
                if not question_text or dedupe_key in seen_questions:
                    continue
                seen_questions.add(dedupe_key)
                generated_questions.append(item)
                if len(generated_questions) >= 3:
                    break

        normalized_guidance = (
            question_guidance.strip()
            if question_guidance and question_guidance.strip()
            else None
        )
        return GenerateInterviewQuestionsResponse(
            screening_id=screening_id,
            manual_questions=normalized_manual_questions,
            question_guidance=normalized_guidance,
            generated_questions=generated_questions,
        )

    def normalize_question_candidate_for_scope(
        self,
        candidate: InterviewQuestionCandidate,
        plan: InterviewPlanPayload,
    ) -> InterviewQuestionCandidate:
        target_competency, was_rebound = self._resolve_scope_target_competency(
            plan=plan,
            target_competency=candidate.target_competency,
        )
        if target_competency is None:
            return candidate

        selection_reason = candidate.selection_reason
        if selection_reason is None or was_rebound:
            selection_reason = BilingualText(
                vi=(
                    "Câu hỏi này được gắn lại vào scope đánh giá mà HR đã bật cho phiên này: "
                    f"{target_competency.vi}."
                ),
                en=(
                    "This question was aligned to the HR-configured interview scope for this "
                    f"session: {target_competency.en}."
                ),
            )

        evidence_gap = candidate.evidence_gap or self._build_evidence_gap(target_competency)
        return candidate.model_copy(
            update={
                "target_competency": target_competency,
                "selection_reason": selection_reason,
                "evidence_gap": evidence_gap,
            }
        )

    async def _generate_llm_questions(
        self,
        *,
        screening_payload: dict[str, object],
        plan: InterviewPlanPayload,
        manual_questions: list[str],
        question_guidance: str | None,
    ) -> list[InterviewQuestionCandidate]:
        if not settings.gemini_api_key:
            return self._fallback_generated_questions(plan, question_guidance)

        prompt = self._build_generation_prompt(
            screening_payload=screening_payload,
            plan=plan,
            manual_questions=manual_questions,
            question_guidance=question_guidance,
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(tools=[get_current_datetime]),
            )
        except Exception:
            return self._fallback_generated_questions(plan, question_guidance)

        text = (response.text or "").strip()
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return self._fallback_generated_questions(plan, question_guidance)
        if not isinstance(payload, dict):
            return self._fallback_generated_questions(plan, question_guidance)

        raw_questions = payload.get("generated_questions", [])
        if not isinstance(raw_questions, list):
            return self._fallback_generated_questions(plan, question_guidance)

        generated_questions: list[InterviewQuestionCandidate] = []
        for item in raw_questions:
            if not isinstance(item, Mapping):
                continue
            question_text = item.get("question_text")
            rationale = item.get("rationale")
            question_type = item.get("question_type")
            target_competency = item.get("target_competency")
            selection_reason = item.get("selection_reason")
            priority = item.get("priority")
            evidence_gap = item.get("evidence_gap")
            if not isinstance(question_text, str) or not question_text.strip():
                continue
            normalized_rationale = (
                rationale.strip()
                if isinstance(rationale, str) and rationale.strip()
                else None
            )
            generated_questions.append(
                self.normalize_question_candidate_for_scope(
                    InterviewQuestionCandidate(
                        question_text=question_text.strip(),
                        source="llm",
                        rationale=normalized_rationale,
                        question_type=question_type.strip()
                        if isinstance(question_type, str) and question_type.strip()
                        else "planned",
                        target_competency=BilingualText.model_validate(target_competency)
                        if isinstance(target_competency, Mapping)
                        else None,
                        selection_reason=BilingualText.model_validate(selection_reason)
                        if isinstance(selection_reason, Mapping)
                        else None,
                        priority=priority if isinstance(priority, int) and priority > 0 else 1,
                        evidence_gap=BilingualText.model_validate(evidence_gap)
                        if isinstance(evidence_gap, Mapping)
                        else None,
                    ),
                    plan,
                )
            )
        return generated_questions or self._fallback_generated_questions(plan, question_guidance)

    def _build_competencies(
        self,
        dimension_scores: object,
    ) -> list[InterviewCompetencyPlan]:
        if not isinstance(dimension_scores, list):
            return []

        competencies: list[InterviewCompetencyPlan] = []
        for index, dimension in enumerate(dimension_scores[:4]):
            if not isinstance(dimension, Mapping):
                continue
            dimension_name_payload = dimension.get("dimension_name")
            if not isinstance(dimension_name_payload, Mapping):
                continue
            dimension_name = BilingualText.model_validate(dimension_name_payload)
            evidence_needed = [
                BilingualText(
                    vi=f"Cần ví dụ cụ thể để xác minh {dimension_name.vi.lower()}.",
                    en=f"Need a concrete example to validate {dimension_name.en.lower()}.",
                )
            ]
            competencies.append(
                InterviewCompetencyPlan(
                    name=dimension_name,
                    priority=index + 1,
                    target_question_count=2 if index == 0 else 1,
                    current_coverage=0.0,
                    status="in_progress" if index == 0 else "not_started",
                    evidence_collected_count=0,
                    evidence_needed=evidence_needed,
                    stop_condition=BilingualText(
                        vi="Có đủ ví dụ và ngữ cảnh để đánh giá năng lực này.",
                        en="Enough examples and context are available to assess this competency.",
                    ),
                )
            )
        return competencies

    def _build_overall_strategy(self, questions: list[InterviewQuestion]) -> BilingualText:
        top_dimension = questions[0].dimension_name if questions else BilingualText(vi="năng lực trọng tâm", en="core competency")
        return BilingualText(
            vi=(
                "Bắt đầu với năng lực ưu tiên cao nhất, sau đó mở rộng sang các tín hiệu còn thiếu "
                f"xung quanh {top_dimension.vi.lower()}."
            ),
            en=(
                "Start with the highest-priority competency, then expand into the remaining evidence gaps "
                f"around {top_dimension.en.lower()}."
            ),
        )

    def _build_selection_reason(self, purpose: BilingualText) -> BilingualText:
        return BilingualText(
            vi=f"Câu hỏi này được chọn vì mục tiêu là: {purpose.vi}",
            en=f"This question was selected because the goal is to: {purpose.en}",
        )

    def _build_next_intended_step(
        self,
        competencies: list[InterviewCompetencyPlan],
    ) -> BilingualText:
        if not competencies:
            return BilingualText(
                vi="Bắt đầu với câu hỏi mở đầu đã được duyệt.",
                en="Start with the approved opening question.",
            )
        next_competency = competencies[0].name
        return BilingualText(
            vi=f"Xác minh năng lực ưu tiên đầu tiên: {next_competency.vi}.",
            en=f"Validate the highest-priority competency first: {next_competency.en}.",
        )

    def _resolve_enabled_competencies(
        self,
        competencies: list[InterviewCompetencyPlan],
        interview_scope: InterviewScopeConfig,
    ) -> list[str]:
        explicit = [item.strip() for item in interview_scope.enabled_competencies if item.strip()]
        if explicit:
            return explicit
        if interview_scope.preset == "intro_only":
            return [INTERVIEW_SCOPE_INTRO_KEY]
        competency_names = [item.name.en for item in competencies if item.name.en.strip()]
        if interview_scope.preset == "basic":
            return competency_names[:2]
        return competency_names

    def _build_intro_competency(self) -> InterviewCompetencyPlan:
        return InterviewCompetencyPlan(
            name=INTRO_COMPETENCY_NAME,
            priority=1,
            target_question_count=1,
            current_coverage=0.0,
            status="in_progress",
            evidence_collected_count=0,
            evidence_needed=[
                BilingualText(
                    vi="Cần câu trả lời mạch lạc về kinh nghiệm phù hợp nhất với vị trí.",
                    en="Need a clear explanation of the candidate's most relevant experience.",
                )
            ],
            stop_condition=BilingualText(
                vi="Có đủ ngữ cảnh về bản thân, vai trò gần nhất và mức độ phù hợp ban đầu.",
                en="Enough context about the candidate, the latest role, and initial relevance is available.",
            ),
        )

    def _build_intro_question(self, *, has_more_competencies: bool) -> InterviewQuestion:
        return InterviewQuestion(
            question_index=0,
            dimension_name=INTRO_COMPETENCY_NAME,
            prompt=BilingualText(
                vi="Bạn có thể giới thiệu ngắn về bản thân và kinh nghiệm phù hợp nhất với vị trí này không?",
                en="Can you briefly introduce yourself and the experience most relevant to this role?",
            ),
            purpose=BilingualText(
                vi="Lấy bối cảnh mở đầu để HR hiểu ứng viên muốn được đánh giá theo hướng nào.",
                en="Collect opening context so HR understands which experience should anchor the interview.",
            ),
            source="scope",
            question_type="intro",
            rationale="Opening question derived from the HR-configured interview scope.",
            priority=1,
            target_competency=INTRO_COMPETENCY_NAME,
            evidence_gap=BilingualText(
                vi="Chưa có đủ ngữ cảnh giới thiệu bản thân cho scope phỏng vấn hiện tại.",
                en="There is not enough self-introduction context for the current interview scope.",
            ),
            selection_reason=BilingualText(
                vi="HR đã cấu hình scope ưu tiên phần giới thiệu bản thân.",
                en="HR configured this interview scope to prioritize self-introduction.",
            ),
            transition_on_strong_answer="advance_to_next_competency" if has_more_competencies else "prepare_wrap_up",
            transition_on_weak_answer="ask_clarification",
        )

    def _build_scope_completion_criteria(
        self,
        competencies: list[InterviewCompetencyPlan],
    ) -> list[BilingualText]:
        if not competencies:
            return [
                BilingualText(
                    vi="Thu thập đủ bối cảnh cho scope phỏng vấn hiện tại trước khi kết thúc session.",
                    en="Collect enough context for the current interview scope before closing the session.",
                )
            ]
        competency_names = ", ".join(item.name.vi for item in competencies if item.name.vi.strip())
        return [
            BilingualText(
                vi=f"Chỉ cần thu thập đủ bằng chứng cho các năng lực HR đã chọn: {competency_names}.",
                en=f"Only collect enough evidence for the competencies selected by HR: {competency_names}.",
            )
        ]

    def _build_scope_competency_lookup(
        self,
        plan: InterviewPlanPayload,
    ) -> dict[str, BilingualText]:
        lookup: dict[str, BilingualText] = {}
        for competency in plan.competencies:
            normalized_name = competency.name.model_copy(deep=True)
            for raw_key in {competency.name.en, competency.name.vi}:
                key = raw_key.strip().casefold()
                if key:
                    lookup[key] = normalized_name
        return lookup

    def _resolve_scope_target_competency(
        self,
        *,
        plan: InterviewPlanPayload,
        target_competency: BilingualText | None,
    ) -> tuple[BilingualText | None, bool]:
        lookup = self._build_scope_competency_lookup(plan)
        if target_competency is not None:
            for raw_key in {target_competency.en, target_competency.vi}:
                key = raw_key.strip().casefold()
                if key and key in lookup:
                    return lookup[key].model_copy(deep=True), False

        if not plan.competencies:
            return target_competency, False

        return plan.competencies[0].name.model_copy(deep=True), True

    def _build_fallback_question_for_competency(
        self,
        competency: InterviewCompetencyPlan,
        *,
        index: int,
    ) -> InterviewQuestion:
        return InterviewQuestion(
            question_index=index,
            dimension_name=competency.name,
            prompt=BilingualText(
                vi=f"Bạn hãy chia sẻ một ví dụ cụ thể về {competency.name.vi.lower()}.",
                en=f"Share one concrete example of your {competency.name.en.lower()}.",
            ),
            purpose=BilingualText(
                vi="Xác minh năng lực nằm trong scope HR đã cấu hình.",
                en="Validate the competency included in the HR-configured scope.",
            ),
            source="scope",
            question_type="planned",
            rationale="Fallback question derived from the HR-configured scope.",
            priority=index + 1,
            target_competency=competency.name,
            evidence_gap=self._build_evidence_gap(competency.name),
            selection_reason=BilingualText(
                vi="Câu hỏi dự phòng được tạo từ competency mà HR đã bật cho phiên này.",
                en="Fallback question derived from the competency HR enabled for this session.",
            ),
            transition_on_strong_answer="advance_to_next_competency",
            transition_on_weak_answer="ask_clarification",
        )

    def _apply_scope_to_plan(
        self,
        plan: InterviewPlanPayload,
        interview_scope: InterviewScopeConfig | None,
    ) -> InterviewPlanPayload:
        if interview_scope is None:
            return plan

        enabled_keys = self._resolve_enabled_competencies(plan.competencies, interview_scope)
        if not enabled_keys:
            return plan

        competency_by_key = {
            item.name.en.casefold(): item.model_copy(deep=True)
            for item in plan.competencies
            if item.name.en.strip()
        }
        question_groups: dict[str, list[InterviewQuestion]] = {}
        for question in plan.questions:
            target = question.target_competency or question.dimension_name
            key = target.en.casefold()
            question_groups.setdefault(key, []).append(question.model_copy(deep=True))

        scoped_competencies: list[InterviewCompetencyPlan] = []
        scoped_questions: list[InterviewQuestion] = []
        for key in enabled_keys:
            normalized_key = key.casefold()
            if normalized_key == INTERVIEW_SCOPE_INTRO_KEY:
                scoped_competencies.append(self._build_intro_competency())
                continue
            competency = competency_by_key.get(normalized_key)
            if competency is not None:
                scoped_competencies.append(competency)
                scoped_questions.extend(question_groups.get(normalized_key, []))

        if not scoped_competencies:
            return plan

        include_intro = any(key.casefold() == INTERVIEW_SCOPE_INTRO_KEY for key in enabled_keys)
        if include_intro:
            scoped_questions.insert(
                0,
                self._build_intro_question(has_more_competencies=len(scoped_competencies) > 1),
            )

        if not scoped_questions:
            scoped_questions = [
                self._build_fallback_question_for_competency(competency, index=index)
                for index, competency in enumerate(scoped_competencies)
            ]

        for index, competency in enumerate(scoped_competencies):
            competency.priority = index + 1
            competency.status = "in_progress" if index == 0 else "not_started"

        for index, question in enumerate(scoped_questions):
            question.question_index = index
            question.priority = index + 1

        plan.competencies = scoped_competencies
        plan.questions = scoped_questions
        plan.current_competency_index = 0
        plan.current_phase = "competency_validation"
        plan.interview_scope = interview_scope.model_copy(deep=True)
        plan.plan_events = self._build_plan_events(scoped_competencies)
        plan.session_goal = self._build_session_goal(result={}, questions=scoped_questions)
        plan.overall_strategy = self._build_overall_strategy(scoped_questions)
        plan.next_intended_step = self._build_next_intended_step(scoped_competencies)
        plan.completion_criteria = self._build_scope_completion_criteria(scoped_competencies)
        return plan

    def _build_evidence_gap(self, dimension_name: BilingualText) -> BilingualText:
        return BilingualText(
            vi=f"Chưa có đủ bằng chứng cụ thể về {dimension_name.vi.lower()}.",
            en=f"There is not enough concrete evidence about {dimension_name.en.lower()} yet.",
        )

    def _build_plan_events(
        self,
        competencies: list[InterviewCompetencyPlan],
    ) -> list[InterviewPlanEvent]:
        primary_competency = competencies[0].name if competencies else None
        return [
            InterviewPlanEvent(
                event_type="plan.created",
                reason=BilingualText(
                    vi="Khởi tạo interview plan từ tín hiệu screening và các năng lực ưu tiên.",
                    en="Initialized the interview plan from screening signals and priority competencies.",
                ),
                chosen_action="start_with_priority_competency",
                affected_competency=primary_competency,
                confidence=0.8 if primary_competency is not None else None,
                question_index=0 if primary_competency is not None else None,
                created_at=get_current_datetime(),
            )
        ]

    def _build_session_goal(
        self,
        *,
        result: Mapping[str, object],
        questions: list[InterviewQuestion],
    ) -> BilingualText:
        top_dimensions = [item.dimension_name.vi for item in questions[:3] if item.dimension_name.vi.strip()]
        if top_dimensions:
            joined_dimensions = ", ".join(top_dimensions)
            return BilingualText(
                vi=(
                    "Đánh giá mức độ phù hợp của ứng viên với JD hiện tại bằng cách xác minh các "
                    f"năng lực trọng tâm: {joined_dimensions}."
                ),
                en=(
                    "Assess the candidate's fit for the current JD by validating these core "
                    f"competencies: {joined_dimensions}."
                ),
            )

        recommendation = result.get("recommendation")
        if isinstance(recommendation, str) and recommendation.strip():
            return BilingualText(
                vi="Đánh giá mức độ phù hợp của ứng viên với JD hiện tại trước khi ra khuyến nghị tiếp theo.",
                en="Assess the candidate's fit for the current JD before making the next recommendation.",
            )
        return BilingualText(
            vi="Xác minh các tín hiệu chính của ứng viên để đánh giá mức độ phù hợp với JD hiện tại.",
            en="Validate the candidate's key signals to assess fit for the current JD.",
        )

    def _build_generation_prompt(
        self,
        *,
        screening_payload: dict[str, object],
        plan: InterviewPlanPayload,
        manual_questions: list[str],
        question_guidance: str | None,
    ) -> str:
        return (
            "You are helping HR prepare a short Vietnamese screening interview.\n"
            "Use the get_current_datetime tool as the authoritative time context "
            "for any time-aware reasoning before making timeline judgments.\n"
            "Generate 3 to 5 concise interview questions in Vietnamese.\n"
            "Respect HR guidance, use the CV screening evidence, avoid duplicates, "
            "and do not repeat manual questions verbatim.\n"
            "Preserve competency coverage from the existing interview plan and "
            "prioritize unresolved evidence gaps before introducing new topics.\n"
            "Explain why each generated question should be asked now and classify "
            "whether it is planned, follow_up, or clarification.\n"
            "If the screening payload contains stale timeline judgments, normalize "
            "them against the current datetime instead of repeating them blindly.\n"
            "Never describe a past year as if it is still in the future.\n"
            "When dates or durations look inconsistent, ask neutral clarification "
            "questions about the timeline instead of asserting that the candidate "
            "is wrong.\n"
            "Do not reuse phrases like 'future date', 'time contradiction', or "
            "'have you really completed it' unless the current datetime still "
            "supports that conclusion.\n"
            "Return strict JSON with one top-level key: generated_questions.\n"
            "Each generated_questions item must be an object with keys: "
            "question_text, rationale, question_type, target_competency, selection_reason, priority, evidence_gap.\n"
            f"HR manual questions: {json.dumps(manual_questions, ensure_ascii=False)}\n"
            f"HR question guidance: {json.dumps(question_guidance, ensure_ascii=False)}\n"
            f"Existing interview plan: {plan.model_dump_json(indent=2)}\n"
            f"CV screening payload: {json.dumps(screening_payload, ensure_ascii=False)}"
        )

    def _fallback_generated_questions(
        self,
        plan: InterviewPlanPayload,
        question_guidance: str | None,
    ) -> list[InterviewQuestionCandidate]:
        generated_questions = [
            InterviewQuestionCandidate(
                question_text=item.prompt.vi.strip(),
                source="screening",
                rationale=item.purpose.vi,
                question_type=item.question_type or "planned",
                target_competency=item.target_competency,
                selection_reason=item.selection_reason,
                priority=item.priority,
                evidence_gap=item.evidence_gap,
            )
            for item in plan.questions
        ]
        if question_guidance and question_guidance.strip():
            generated_questions.append(
                self.normalize_question_candidate_for_scope(
                    InterviewQuestionCandidate(
                        question_text=(
                            "Bạn hãy chia sẻ ví dụ cụ thể phù hợp với định hướng mà HR đã cấu hình: "
                            f"{question_guidance.strip()}"
                        ),
                        source="guidance",
                        rationale="Fallback question derived from HR guidance.",
                        question_type="planned",
                        selection_reason=BilingualText(
                            vi="Câu hỏi dự phòng được suy ra từ định hướng HR.",
                            en="Fallback question derived from HR guidance.",
                        ),
                        evidence_gap=BilingualText(
                            vi="Cần thêm bằng chứng theo định hướng do HR cấu hình.",
                            en="Need more evidence aligned with the HR guidance.",
                        ),
                    ),
                    plan,
                )
            )
        return generated_questions
