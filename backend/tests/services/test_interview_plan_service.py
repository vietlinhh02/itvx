"""Tests for interview plan generation."""

import pytest

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
