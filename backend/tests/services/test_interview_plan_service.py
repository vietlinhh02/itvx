"""Tests for interview plan generation."""

import pytest

from src.schemas.interview import InterviewScopeConfig
from src.schemas.interview import InterviewPlanPayload
from src.services.interview_plan_service import InterviewPlanService


class _FakeGenerateResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModelAPI:
    def __init__(self, text: str) -> None:
        self._text = text
        self.last_model: str | None = None
        self.last_contents: str | None = None
        self.last_config = None

    async def generate_content(
        self,
        *,
        model: str,
        contents: str,
        config=None,
    ) -> _FakeGenerateResponse:
        self.last_model = model
        self.last_contents = contents
        self.last_config = config
        return _FakeGenerateResponse(self._text)


class _FakeAioClient:
    def __init__(self, text: str) -> None:
        self.models = _FakeModelAPI(text)


class _FakeGenAIClient:
    def __init__(self, text: str) -> None:
        self.aio = _FakeAioClient(text)


def test_build_plan_uses_screening_dimensions_and_followups() -> None:
    """Build the plan from screening follow-ups before dimension fallback."""
    service = InterviewPlanService(client=_FakeGenAIClient('{"generated_questions": []}'))

    plan = service.build_plan(
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "priority": "must_have",
                        "weight": 0.5,
                        "score": 0.82,
                        "reason": {"vi": "Có kinh nghiệm tốt", "en": "Strong experience"},
                        "evidence": [],
                        "confidence_note": None,
                    }
                ],
                "follow_up_questions": [
                    {
                        "question": {
                            "vi": "Mô tả một API bạn đã tối ưu.",
                            "en": "Describe one API you optimized.",
                        },
                        "purpose": {"vi": "Đào sâu kỹ thuật", "en": "Probe technical depth"},
                        "linked_dimension": {"vi": "Kỹ thuật", "en": "Technical"},
                    }
                ],
            }
        }
    )

    assert isinstance(plan, InterviewPlanPayload)
    assert len(plan.questions) == 1
    assert plan.questions[0].dimension_name.en == "Technical"
    assert plan.questions[0].source == "screening"
    assert plan.questions[0].question_type == "planned"
    assert plan.questions[0].target_competency is not None
    assert plan.current_phase == "competency_validation"
    assert plan.current_competency_index == 0
    assert plan.interview_decision_status == "continue"
    assert plan.next_intended_step is not None
    assert plan.competencies[0].name.en == "Technical"
    assert plan.competencies[0].status == "in_progress"
    assert plan.competencies[0].target_question_count == 2
    assert plan.plan_events[0].event_type == "plan.created"


def test_build_plan_filters_to_hr_selected_scope() -> None:
    service = InterviewPlanService(client=_FakeGenAIClient('{"generated_questions": []}'))

    plan = service.build_plan(
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "priority": "must_have",
                        "weight": 0.5,
                        "score": 0.82,
                        "reason": {"vi": "Có kinh nghiệm tốt", "en": "Strong experience"},
                        "evidence": [],
                        "confidence_note": None,
                    },
                    {
                        "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
                        "priority": "important",
                        "weight": 0.2,
                        "score": 0.7,
                        "reason": {"vi": "Giao tiếp ổn", "en": "Good communication"},
                        "evidence": [],
                        "confidence_note": None,
                    },
                ],
                "follow_up_questions": [
                    {
                        "question": {
                            "vi": "Mô tả một API bạn đã tối ưu.",
                            "en": "Describe one API you optimized.",
                        },
                        "purpose": {"vi": "Đào sâu kỹ thuật", "en": "Probe technical depth"},
                        "linked_dimension": {"vi": "Kỹ thuật", "en": "Technical"},
                    },
                    {
                        "question": {
                            "vi": "Bạn truyền đạt trade-off thế nào?",
                            "en": "How do you communicate trade-offs?",
                        },
                        "purpose": {"vi": "Đào sâu giao tiếp", "en": "Probe communication"},
                        "linked_dimension": {"vi": "Giao tiếp", "en": "Communication"},
                    },
                ],
            }
        },
        interview_scope=InterviewScopeConfig(
            preset="basic",
            enabled_competencies=["Communication"],
        ),
    )

    assert plan.interview_scope is not None
    assert [item.name.en for item in plan.competencies] == ["Communication"]
    assert [item.target_competency.en for item in plan.questions if item.target_competency is not None] == [
        "Communication"
    ]
    assert "Giao tiếp" in plan.session_goal.vi


def test_build_plan_supports_intro_only_scope() -> None:
    service = InterviewPlanService(client=_FakeGenAIClient('{"generated_questions": []}'))

    plan = service.build_plan(
        screening_payload={"result": {"dimension_scores": [], "follow_up_questions": []}},
        interview_scope=InterviewScopeConfig(
            preset="intro_only",
            enabled_competencies=["__intro__"],
        ),
    )

    assert plan.interview_scope is not None
    assert [item.name.en for item in plan.competencies] == ["Self introduction"]
    assert len(plan.questions) == 1
    assert plan.questions[0].target_competency is not None
    assert plan.questions[0].target_competency.en == "Self introduction"


@pytest.mark.asyncio
async def test_generate_questions_uses_llm_output_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prefer parsed LLM output when the model returns valid JSON."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewPlanService(
        client=_FakeGenAIClient(
            '{"generated_questions": ['
            '{"question_text": "Bạn từng scale API nào lên production?", '
            '"rationale": "Probe backend scale experience."}'
            ']}'
        )
    )

    response = await service.generate_questions(
        screening_id="screening-1",
        screening_payload={"result": {"follow_up_questions": []}},
        manual_questions=["Bạn đang tự hào nhất về dự án nào gần đây?"],
        question_guidance="Tập trung vào backend scale",
    )

    assert response.generated_questions[0].source == "manual"
    assert response.generated_questions[0].question_type == "manual"
    assert response.generated_questions[1].source == "llm"
    assert response.generated_questions[1].question_type == "planned"
    assert "scale API" in response.generated_questions[1].question_text


@pytest.mark.asyncio
async def test_generate_questions_rebinds_llm_output_to_selected_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewPlanService(
        client=_FakeGenAIClient(
            '{"generated_questions": ['
            '{"question_text": "Bạn đã dùng Figma trong công việc như thế nào?", '
            '"rationale": "Probe design tooling.", '
            '"target_competency": {"vi": "Figma", "en": "Figma"}}'
            ']}'
        )
    )

    response = await service.generate_questions(
        screening_id="screening-1",
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
                        "score": 0.7,
                    }
                ],
                "follow_up_questions": [
                    {
                        "question": {
                            "vi": "Bạn truyền đạt trade-off kỹ thuật thế nào?",
                            "en": "How do you communicate technical trade-offs?",
                        },
                        "purpose": {"vi": "Đào sâu giao tiếp", "en": "Probe communication"},
                        "linked_dimension": {"vi": "Giao tiếp", "en": "Communication"},
                    }
                ],
            }
        },
        manual_questions=[],
        question_guidance="Tập trung vào giao tiếp với stakeholder",
        interview_scope=InterviewScopeConfig(
            preset="basic",
            enabled_competencies=["Communication"],
        ),
    )

    llm_question = next(item for item in response.generated_questions if item.source == "llm")
    assert llm_question.target_competency is not None
    assert llm_question.target_competency.en == "Communication"
    assert llm_question.selection_reason is not None
    assert "scope" in llm_question.selection_reason.en.lower()
    assert llm_question.evidence_gap is not None


@pytest.mark.asyncio
async def test_generate_questions_falls_back_when_llm_output_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fall back to deterministic questions when the model output is invalid."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewPlanService(client=_FakeGenAIClient("not-json"))

    response = await service.generate_questions(
        screening_id="screening-1",
        screening_payload={
            "result": {
                "follow_up_questions": [
                    {
                        "question": {
                            "vi": "Mô tả một API bạn đã tối ưu.",
                            "en": "Describe one API you optimized.",
                        },
                        "purpose": {"vi": "Đào sâu kỹ thuật", "en": "Probe technical depth"},
                        "linked_dimension": {"vi": "Kỹ thuật", "en": "Technical"},
                    }
                ]
            }
        },
        manual_questions=[],
        question_guidance="Tập trung vào backend scale",
    )

    assert response.generated_questions[0].source == "screening"
    assert response.generated_questions[0].question_type == "planned"
    assert any(item.source == "guidance" for item in response.generated_questions)
    assert any(item.evidence_gap is not None for item in response.generated_questions)


@pytest.mark.asyncio
async def test_generate_questions_links_guidance_fallback_to_selected_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewPlanService(client=_FakeGenAIClient("not-json"))

    response = await service.generate_questions(
        screening_id="screening-1",
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
                        "score": 0.7,
                    }
                ],
                "follow_up_questions": [],
            }
        },
        manual_questions=[],
        question_guidance="Tập trung vào giao tiếp với stakeholder",
        interview_scope=InterviewScopeConfig(
            preset="basic",
            enabled_competencies=["Communication"],
        ),
    )

    guidance_question = next(item for item in response.generated_questions if item.source == "guidance")
    assert guidance_question.target_competency is not None
    assert guidance_question.target_competency.en == "Communication"
    assert guidance_question.selection_reason is not None
    assert guidance_question.evidence_gap is not None


def test_generation_prompt_instructs_model_to_use_datetime_tool() -> None:
    """Prompt the model to use the datetime tool for timeline reasoning."""
    service = InterviewPlanService(client=_FakeGenAIClient('{"generated_questions": []}'))
    plan = service.build_plan(screening_payload={"result": {"follow_up_questions": []}})

    prompt = service._build_generation_prompt(
        screening_payload={"result": {}},
        plan=plan,
        manual_questions=[],
        question_guidance="Hỏi về timeline làm việc",
    )

    assert "Use the get_current_datetime tool" in prompt
    assert "authoritative time context" in prompt
    assert "Never describe a past year as if it is still in the future." in prompt
    assert "ask neutral clarification questions about the timeline" in prompt
    assert "Preserve competency coverage" in prompt
    assert "question_type, target_competency, selection_reason, priority, evidence_gap" in prompt


@pytest.mark.asyncio
async def test_generate_questions_registers_datetime_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Register the datetime tool in the GenAI request config."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _FakeGenAIClient('{"generated_questions": []}')
    service = InterviewPlanService(client=client)

    await service.generate_questions(
        screening_id="screening-1",
        screening_payload={"result": {"follow_up_questions": []}},
        manual_questions=[],
        question_guidance=None,
    )

    assert client.aio.models.last_config is not None
    tools = client.aio.models.last_config.tools
    assert tools is not None
    assert any(getattr(tool, "__name__", None) == "get_current_datetime" for tool in tools)
