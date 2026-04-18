import asyncio
from contextlib import suppress
from pathlib import Path
from unittest.mock import patch

from livekit.agents import llm

from src.agent import (
    InterviewRealtimeAgent,
    SessionRuntimeHandler,
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
        self.closed = False
        self.runtime_state: dict[str, object] = {
            "session_id": "session-1",
            "status": "in_progress",
            "worker_status": "responding",
            "provider_status": "gemini_live",
            "current_question_index": 0,
            "interview_decision_status": "continue",
            "current_phase": "competency_validation",
            "current_question": {
                "prompt": {
                    "vi": "Bạn có thể giới thiệu ngắn về bản thân không?",
                }
            },
        }

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

    async def get_runtime_state(self, session_id: str) -> dict[str, object]:
        _ = session_id
        return self.runtime_state

    async def aclose(self) -> None:
        self.closed = True


class FakeRoom:
    def __init__(self) -> None:
        self.connected_with: tuple[str, str] | None = None
        self.disconnect_called = False
        self.remote_participants: dict[str, object] = {}
        self.local_participant = type("LocalParticipant", (), {"identity": "worker-1"})()
        self._handlers: dict[str, list[object]] = {}

    async def connect(self, livekit_url: str, worker_token: str) -> None:
        self.connected_with = (livekit_url, worker_token)

    def on(self, event_name: str, handler: object) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    def emit(self, event_name: str, *args: object) -> None:
        for handler in self._handlers.get(event_name, []):
            handler(*args)

    async def disconnect(self) -> None:
        self.disconnect_called = True


class FakeAgentSession:
    def __init__(self, **_: object) -> None:
        self.closed = False
        self._handlers: dict[str, list[object]] = {}

    def on(self, event_name: str, handler: object) -> None:
        self._handlers.setdefault(event_name, []).append(handler)

    async def start(self, agent: object, *, room: FakeRoom, room_options: object) -> None:
        _ = agent
        _ = room_options
        asyncio.get_running_loop().call_soon(room.emit, "disconnected", "room_deleted")

    async def aclose(self) -> None:
        self.closed = True


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
    compression = captured["context_window_compression"]
    assert compression.trigger_tokens == 24000
    assert compression.sliding_window is not None
    assert compression.sliding_window.target_tokens == 12000


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


def test_session_runtime_handler_exits_when_room_disconnects() -> None:
    backend_client = FakeBackendClient()
    room = FakeRoom()
    created_sessions: list[FakeAgentSession] = []

    def build_fake_session(**kwargs: object) -> FakeAgentSession:
        session = FakeAgentSession(**kwargs)
        created_sessions.append(session)
        return session

    class FakeRealtimeModel:
        model = "gemini-2.5-flash-native-audio-preview-12-2025"

    class FakeInterviewAgent:
        def __init__(self, *args: object, **kwargs: object) -> None:
            _ = args
            _ = kwargs

    handler = SessionRuntimeHandler(
        room_name="interview-room-1",
        opening_question="Bạn có thể giới thiệu ngắn về bản thân không?",
        session_id="session-1",
        jd_id="jd-1",
        livekit_url="wss://livekit.example",
        worker_token="worker-token",
        backend_client=backend_client,
        config=WorkerConfig(
            backend_base_url="http://localhost:8000",
            backend_callback_secret="secret",
            gemini_api_key="test-key",
            gemini_model="gemini-2.5-flash-native-audio-preview-12-2025",
            livekit_url="wss://livekit.example",
        ),
        room=room,
    )

    async def scenario() -> None:
        with (
            patch("src.agent.AgentSession", side_effect=build_fake_session),
            patch("src.agent.build_realtime_model", return_value=FakeRealtimeModel()),
            patch("src.agent.InterviewRealtimeAgent", FakeInterviewAgent),
        ):
            task = asyncio.create_task(handler.run())
            try:
                await asyncio.sleep(0.05)
                assert task.done() is True
                await task
            finally:
                if not task.done():
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task

    asyncio.run(scenario())

    assert len(created_sessions) == 1
    assert created_sessions[0].closed is True
    assert room.disconnect_called is True
    assert backend_client.closed is True
    assert [event["event_type"] for event in backend_client.posted_events] == [
        "worker.connected",
        "agent.session_started",
    ]


def test_prompted_agent_on_enter_resumes_current_question_after_reconnect() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def generate_reply(self, *, instructions: str, input_modality: str) -> None:
            self.calls.append({
                "instructions": instructions,
                "input_modality": input_modality,
            })

    class FakeRealtimeModel:
        model = "gemini-2.5-flash-native-audio-preview-12-2025"

    class FakeActivity:
        def __init__(self, session: FakeSession) -> None:
            self.session = session

    backend_client = FakeBackendClient()
    backend_client.runtime_state = {
        "session_id": "session-1",
        "status": "waiting",
        "worker_status": "queued",
        "provider_status": "gemini_live",
        "current_question_index": 1,
        "interview_decision_status": "continue",
        "current_phase": "competency_validation",
        "current_question": {
            "prompt": {
                "vi": "Bạn đã xử lý trade-off kỹ thuật đó như thế nào?",
            }
        },
    }

    with patch("src.agent.Agent.__init__", return_value=None):
        agent = InterviewRealtimeAgent(
            "Bạn có thể giới thiệu ngắn về bản thân không?",
            FakeRealtimeModel(),
            backend_client,
            "session-1",
        )

    fake_session = FakeSession()
    agent._activity = FakeActivity(fake_session)

    asyncio.run(agent.on_enter())

    assert len(fake_session.calls) == 1
    assert fake_session.calls[0]["input_modality"] == "audio"
    assert "Bạn đã xử lý trade-off kỹ thuật đó như thế nào?" in fake_session.calls[0]["instructions"]
    assert "Bạn có thể giới thiệu ngắn về bản thân không?" not in fake_session.calls[0]["instructions"]


def test_prompted_agent_on_enter_continues_when_hr_review_flag_is_set() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.calls: list[dict[str, str]] = []

        def generate_reply(self, *, instructions: str, input_modality: str) -> None:
            self.calls.append({
                "instructions": instructions,
                "input_modality": input_modality,
            })

    class FakeRealtimeModel:
        model = "gemini-2.5-flash-native-audio-preview-12-2025"

    class FakeActivity:
        def __init__(self, session: FakeSession) -> None:
            self.session = session

    backend_client = FakeBackendClient()
    backend_client.runtime_state = {
        "session_id": "session-1",
        "status": "in_progress",
        "worker_status": "responding",
        "provider_status": "gemini_live",
        "current_question_index": 1,
        "interview_decision_status": "continue_with_hr_flag",
        "current_phase": "deep_dive",
        "current_question": {
            "question_type": "recovery",
            "prompt": {
                "vi": "Bạn có thể nói rõ hơn phần việc bạn trực tiếp chịu trách nhiệm không?",
            },
        },
    }

    with patch("src.agent.Agent.__init__", return_value=None):
        agent = InterviewRealtimeAgent(
            "Bạn có thể giới thiệu ngắn về bản thân không?",
            FakeRealtimeModel(),
            backend_client,
            "session-1",
        )

    fake_session = FakeSession()
    agent._activity = FakeActivity(fake_session)

    asyncio.run(agent.on_enter())

    assert len(fake_session.calls) == 1
    assert "Bạn có thể nói rõ hơn phần việc bạn trực tiếp chịu trách nhiệm không?" in fake_session.calls[0]["instructions"]


def test_nonprompted_agent_instructions_treat_hr_review_flag_as_continue_state() -> None:
    class FakeRealtimeModel:
        model = "gemini-3.1-flash-live-preview"

    captured: dict[str, object] = {}

    def fake_agent_init(*, instructions: str, llm: object) -> None:
        captured["instructions"] = instructions
        captured["llm"] = llm

    with patch("src.agent.Agent.__init__", side_effect=fake_agent_init):
        InterviewRealtimeAgent(
            "Bạn có thể giới thiệu ngắn về bản thân không?",
            FakeRealtimeModel(),
            FakeBackendClient(),
            "session-1",
        )

    instructions = str(captured["instructions"])
    assert "continue_with_hr_flag" in instructions
    assert "Nếu decision_status là escalate_hr" not in instructions
