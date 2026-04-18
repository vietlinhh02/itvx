import pytest

from src.services.interview_answer_evaluator_service import InterviewAnswerEvaluatorService
from src.schemas.interview import InterviewSemanticAnswerEvaluation


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


@pytest.mark.asyncio
async def test_evaluate_uses_structured_output_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = _FakeGenAIClient(
        (
            '{"answer_quality":"partial","evidence_progress":"improved","recommended_action":"clarify",'
            '"reason":{"vi":"Cần làm rõ thêm ví dụ.","en":"Need a more specific example."},'
            '"confidence":0.74,"needs_hr_review":false}'
        )
    )
    service = InterviewAnswerEvaluatorService(client=client)

    await service.evaluate(
        plan_payload={"current_phase": "competency_validation"},
        current_question={"prompt": {"vi": "Kể về một dự án backend.", "en": "Describe a backend project."}},
        current_competency={"name": {"vi": "Backend", "en": "Backend"}},
        answer_text="Em có làm backend nhưng chưa nêu ví dụ rõ.",
        recent_plan_events=[],
        transcript_context=[],
    )

    assert client.aio.models.last_config is not None
    assert client.aio.models.last_config.response_mime_type == "application/json"
    assert client.aio.models.last_config.response_schema is InterviewSemanticAnswerEvaluation


@pytest.mark.asyncio
async def test_evaluate_parses_semantic_answer_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewAnswerEvaluatorService(
        client=_FakeGenAIClient(
            (
                '{"answer_quality":"strong","evidence_progress":"improved","recommended_action":"move_on",'
                '"reason":{"vi":"Ứng viên đưa ví dụ cụ thể đúng competency.","en":"The candidate gave a concrete competency-aligned example."},'
                '"confidence":0.89,"needs_hr_review":false}'
            )
        )
    )

    result = await service.evaluate(
        plan_payload={"current_phase": "deep_dive"},
        current_question={"prompt": {"vi": "Kể về một dự án backend.", "en": "Describe a backend project."}},
        current_competency={"name": {"vi": "Backend", "en": "Backend"}},
        answer_text="Em tách queue xử lý email khỏi luồng chính để giảm nghẽn hệ thống.",
        recent_plan_events=[],
        transcript_context=[],
    )

    assert result.answer_quality == "strong"
    assert result.recommended_action == "move_on"
    assert result.reason.en == "The candidate gave a concrete competency-aligned example."


@pytest.mark.asyncio
async def test_evaluate_rejects_invalid_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    service = InterviewAnswerEvaluatorService(client=_FakeGenAIClient("not-json"))

    with pytest.raises(ValueError, match="valid JSON"):
        await service.evaluate(
            plan_payload={"current_phase": "deep_dive"},
            current_question={"prompt": {"vi": "Kể về một dự án backend.", "en": "Describe a backend project."}},
            current_competency={"name": {"vi": "Backend", "en": "Backend"}},
            answer_text="Em tách queue xử lý email khỏi luồng chính để giảm nghẽn hệ thống.",
            recent_plan_events=[],
            transcript_context=[],
        )
