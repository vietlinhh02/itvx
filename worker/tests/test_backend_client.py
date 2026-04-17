from src.backend_client import BackendClient


def test_build_turn_payload_returns_expected_shape() -> None:
    client = BackendClient(base_url="http://backend", callback_secret="secret")

    payload = client.build_turn_payload(
        speaker="agent",
        sequence_number=0,
        transcript_text="Xin chào, chúng ta bắt đầu nhé.",
        provider_event_id=None,
    )

    assert payload["speaker"] == "agent"
    assert payload["sequence_number"] == 0
    assert payload["transcript_text"] == "Xin chào, chúng ta bắt đầu nhé."


def test_turn_endpoint_path_uses_session_id() -> None:
    client = BackendClient(base_url="http://backend", callback_secret="secret")

    endpoint = client.turns_endpoint("session-1")

    assert endpoint == "http://backend/api/v1/interviews/sessions/session-1/turns"


def test_build_turn_payload_includes_provider_event_id() -> None:
    client = BackendClient("http://localhost:8000", "callback-secret")

    payload = client.build_turn_payload(
        speaker="agent",
        sequence_number=2,
        transcript_text="Xin chào.",
        provider_event_id="evt-2",
    )

    assert payload["provider_event_id"] == "evt-2"


def test_build_runtime_event_payload_sets_all_status_fields() -> None:
    client = BackendClient("http://localhost:8000", "callback-secret")

    payload = client.build_runtime_event_payload(
        event_type="worker.connected",
        event_source="worker",
        session_status="connecting",
        worker_status="room_connected",
        provider_status="livekit_connected",
        payload={"attempt": 1},
    )

    assert payload["worker_status"] == "room_connected"
    assert payload["provider_status"] == "livekit_connected"


def test_complete_endpoint_path_uses_session_id() -> None:
    client = BackendClient(base_url="http://backend", callback_secret="secret")

    endpoint = client.complete_endpoint("session-1")

    assert endpoint == "http://backend/api/v1/interviews/sessions/session-1/complete"


def test_runtime_state_endpoint_path_uses_session_id() -> None:
    client = BackendClient(base_url="http://backend", callback_secret="secret")

    endpoint = client.runtime_state_endpoint("session-1")

    assert endpoint == "http://backend/api/v1/interviews/sessions/session-1/runtime-state"
