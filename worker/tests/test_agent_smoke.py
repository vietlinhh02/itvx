import asyncio
from pathlib import Path
from unittest.mock import patch

from livekit.agents import llm

from src.agent import (
    SessionRuntimeController,
    TranscriptForwarder,
    build_audio_transcription_config,
    build_realtime_model,
    build_turn_handling,
    model_supports_prompted_turns,
    required_runtime_env,
)
from src.config import WorkerConfig


class FakeBackendClient:
    def __init__(self) -> None:
        self.posted_events: list[dict[str, object]] = []
        self.posted_turns: list[dict[str, object]] = []
        self.completed_sessions: list[tuple[str, dict[str, object]]] = []

    def build_runtime_event_payload(
        self,
        event_type: str,
        event_source: str,
        session_status: str | None,
        worker_status: str | None,
        provider_status: str | None,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "event_type": event_type,
            "event_source": event_source,
            "session_status": session_status,
            "worker_status": worker_status,
            "provider_status": provider_status,
            "payload": payload,
        }

    def build_turn_payload(
        self,
        speaker: str,
        sequence_number: int,
        transcript_text: str,
        provider_event_id: str | None,
    ) -> dict[str, object]:
        return {
            "speaker": speaker,
            "sequence_number": sequence_number,
            "transcript_text": transcript_text,
            "provider_event_id": provider_event_id,
            "event_payload": {},
        }

    async def post_runtime_event(self, session_id: str, payload: dict[str, object]) -> None:
        _ = session_id
        self.posted_events.append(payload)

    async def post_turn(self, session_id: str, payload: dict[str, object]) -> None:
        _ = session_id
        self.posted_turns.append(payload)

    async def complete_session(self, session_id: str, payload: dict[str, object]) -> None:
        self.completed_sessions.append((session_id, payload))


class FakeRoom:
    def __init__(self) -> None:
        self.connected_with: tuple[str, str] | None = None

    async def connect(self, livekit_url: str, worker_token: str) -> None:
        self.connected_with = (livekit_url, worker_token)


def test_worker_entry_file_exists() -> None:
    agent_path = Path(__file__).resolve().parents[1] / "src" / "agent.py"
    assert agent_path.exists()


def test_required_runtime_env_lists_all_session_variables() -> None:
    assert required_runtime_env() == (
        "INTERVIEW_ROOM_NAME",
        "OPENING_QUESTION",
        "INTERVIEW_SESSION_ID",
        "LIVEKIT_WORKER_TOKEN",
    )


def test_transcript_forwarder_posts_agent_and_candidate_turns() -> None:
    backend_client = FakeBackendClient()
    forwarder = TranscriptForwarder(backend_client=backend_client, session_id="session-1")

    asyncio.run(
        forwarder.handle_conversation_item(
            llm.ChatMessage(role="assistant", content=["Xin chào, tôi là AI phỏng vấn viên."])
        )
    )
    asyncio.run(
        forwarder.handle_conversation_item(
            llm.ChatMessage(role="user", content=["Em có 4 năm kinh nghiệm backend."])
        )
    )

    assert backend_client.posted_turns[0]["speaker"] == "agent"
    assert backend_client.posted_turns[1]["speaker"] == "candidate"


def test_transcript_forwarder_waits_for_candidate_turn_settle_before_follow_up() -> None:
    backend_client = FakeBackendClient()
    triggered = 0

    async def on_candidate_turn() -> None:
        nonlocal triggered
        triggered += 1

    forwarder = TranscriptForwarder(
        backend_client=backend_client,
        session_id="session-1",
        on_candidate_turn=on_candidate_turn,
        candidate_turn_debounce_seconds=0.05,
    )

    async def scenario() -> None:
        await forwarder.handle_conversation_item(
            llm.ChatMessage(role="user", content=["Em đã làm backend"])
        )
        assert triggered == 0

        await asyncio.sleep(0.02)

        await forwarder.handle_conversation_item(
            llm.ChatMessage(role="user", content=["gần bốn năm rồi."])
        )
        assert triggered == 0

        await asyncio.sleep(0.08)

    asyncio.run(scenario())

    assert triggered == 1


def test_transcript_forwarder_can_skip_first_candidate_turn_for_user_initiated_models() -> None:
    backend_client = FakeBackendClient()
    triggered = 0

    async def on_candidate_turn() -> None:
        nonlocal triggered
        triggered += 1

    forwarder = TranscriptForwarder(
        backend_client=backend_client,
        session_id="session-1",
        on_candidate_turn=on_candidate_turn,
        skip_initial_candidate_turn=True,
        candidate_turn_debounce_seconds=0.01,
    )

    async def scenario() -> None:
        await forwarder.handle_conversation_item(
            llm.ChatMessage(role="user", content=["Alo, bắt đầu phỏng vấn nhé."])
        )
        await asyncio.sleep(0.02)
        await forwarder.handle_conversation_item(
            llm.ChatMessage(role="assistant", content=["Chào bạn, bạn hãy giới thiệu ngắn về bản thân."])
        )
        await forwarder.handle_conversation_item(
            llm.ChatMessage(role="user", content=["Em có bốn năm làm backend."])
        )
        await asyncio.sleep(0.03)

    asyncio.run(scenario())

    assert len(backend_client.posted_turns) == 2
    assert backend_client.posted_turns[0]["speaker"] == "agent"
    assert backend_client.posted_turns[1]["speaker"] == "candidate"
    assert triggered == 1


def test_build_audio_transcription_config_avoids_unsupported_language_codes() -> None:
    config = build_audio_transcription_config()

    assert getattr(config, "language_codes") is None


def test_build_realtime_model_uses_gemini_language_field_for_vietnamese() -> None:
    captured: dict[str, object] = {}

    def fake_realtime_model(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    with patch("src.agent.google.realtime.RealtimeModel", side_effect=fake_realtime_model):
        build_realtime_model(
            WorkerConfig(
                gemini_api_key="test-key",
                gemini_model="gemini-2.5-flash-native-audio-preview-12-2025",
            )
        )

    input_transcription = captured["input_audio_transcription"]
    output_transcription = captured["output_audio_transcription"]

    assert captured["language"] == "vi-VN"
    assert getattr(input_transcription, "language_codes") is None
    assert getattr(output_transcription, "language_codes") is None


def test_build_realtime_model_keeps_configured_gemini_3_1_preview() -> None:
    captured: dict[str, object] = {}

    def fake_realtime_model(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    with patch("src.agent.google.realtime.RealtimeModel", side_effect=fake_realtime_model):
        build_realtime_model(
            WorkerConfig(
                gemini_api_key="test-key",
                gemini_model="gemini-3.1-flash-live-preview",
            )
        )

    assert captured["model"] == "gemini-3.1-flash-live-preview"


def test_model_supports_prompted_turns_matches_gemini_capabilities() -> None:
    assert model_supports_prompted_turns("gemini-2.5-flash-native-audio-preview-12-2025") is True
    assert model_supports_prompted_turns("gemini-3.1-flash-live-preview") is False


def test_build_turn_handling_requires_real_speech_to_interrupt() -> None:
    interruption = build_turn_handling()["interruption"]

    assert interruption["enabled"] is True
    assert interruption["mode"] == "vad"
    assert interruption["min_duration"] == 0.8
    assert interruption["min_words"] == 2


def test_runtime_controller_marks_session_reconnecting_when_candidate_leaves() -> None:
    backend_client = FakeBackendClient()
    controller = SessionRuntimeController(
        backend_client=backend_client,
        session_id="session-1",
        room_name="interview-room-1",
    )

    asyncio.run(controller.mark_connected())
    asyncio.run(controller.handle_candidate_left("candidate-session-1"))

    assert backend_client.posted_events[0]["event_type"] == "worker.connected"
    assert backend_client.posted_events[1]["event_type"] == "candidate.left"
    assert backend_client.posted_events[1]["session_status"] == "reconnecting"
    assert backend_client.completed_sessions == []
