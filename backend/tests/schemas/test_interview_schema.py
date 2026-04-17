from src.models.interview import InterviewRuntimeEvent, InterviewSession, InterviewTurn
from src.schemas.interview import (
    CandidateJoinResponse,
    GenerateInterviewQuestionsResponse,
    InterviewRuntimeEventRequest,
    InterviewSchedulePayload,
    InterviewSessionDetailResponse,
    InterviewSessionReviewResponse,
    ProposeInterviewScheduleRequest,
    PublishInterviewRequest,
    PublishInterviewResponse,
    TranscriptTurnRequest,
    UpdateInterviewScheduleRequest,
)


def test_interview_session_and_turn_models_define_expected_columns() -> None:
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c

    assert "status" in session_columns
    assert "share_token" in session_columns
    assert "livekit_room_name" in session_columns
    assert "worker_status" in session_columns
    assert "worker_dispatch_token" in session_columns
    assert "opening_question" in session_columns
    assert "approved_questions" in session_columns
    assert "manual_questions" in session_columns
    assert "question_guidance" in session_columns
    assert "plan_payload" in session_columns

    assert "interview_session_id" in turn_columns
    assert "speaker" in turn_columns
    assert "sequence_number" in turn_columns
    assert "transcript_text" in turn_columns


def test_publish_join_and_transcript_schemas_accept_valid_payloads() -> None:
    publish_request = PublishInterviewRequest.model_validate(
        {
            "screening_id": "screening-1",
            "approved_questions": ["Giới thiệu ngắn về bản thân bạn."],
            "manual_questions": ["Bạn đã làm dự án nào gần đây?"],
            "question_guidance": "Tập trung vào backend và ownership",
        }
    )
    publish_response = PublishInterviewResponse.model_validate(
        {
            "session_id": "session-1",
            "share_link": "http://localhost:3000/interviews/join/share-token-1",
            "room_name": "interview-room-1",
            "status": "published",
            "schedule": InterviewSchedulePayload().model_dump(),
        }
    )
    join_response = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "interview-room-1",
            "participant_token": "token-1",
            "candidate_identity": "candidate-session-1",
            "schedule": InterviewSchedulePayload().model_dump(),
        }
    )
    transcript_turn = TranscriptTurnRequest.model_validate(
        {
            "speaker": "agent",
            "sequence_number": 0,
            "transcript_text": "Xin chào, chúng ta bắt đầu nhé.",
            "provider_event_id": None,
            "event_payload": {},
        }
    )

    assert publish_request.approved_questions[0] == "Giới thiệu ngắn về bản thân bạn."
    assert publish_response.status == "published"
    assert join_response.room_name == "interview-room-1"
    assert transcript_turn.sequence_number == 0


def test_interview_models_define_runtime_and_review_columns() -> None:
    session_columns = InterviewSession.__table__.c
    turn_columns = InterviewTurn.__table__.c
    event_columns = InterviewRuntimeEvent.__table__.c

    assert "status" in session_columns
    assert "worker_status" in session_columns
    assert "provider_status" in session_columns
    assert "candidate_identity" in session_columns
    assert "worker_identity" in session_columns
    assert "last_error_code" in session_columns
    assert "last_error_message" in session_columns
    assert "last_provider_event_at" in session_columns
    assert "last_runtime_event_at" in session_columns
    assert "summary_payload" in session_columns
    assert "approved_questions" in session_columns
    assert "manual_questions" in session_columns
    assert "question_guidance" in session_columns
    assert "plan_payload" in session_columns

    assert "speaker" in turn_columns
    assert "sequence_number" in turn_columns
    assert "transcript_text" in turn_columns
    assert "provider_event_id" in turn_columns

    assert "event_type" in event_columns
    assert "event_source" in event_columns
    assert "session_status" in event_columns
    assert "worker_status" in event_columns
    assert "provider_status" in event_columns
    assert "payload" in event_columns


def test_realtime_interview_schemas_accept_valid_payloads() -> None:
    publish_response = PublishInterviewResponse.model_validate(
        {
            "session_id": "session-1",
            "share_link": "http://localhost:3000/interviews/join/share-token-1",
            "room_name": "interview-room-1",
            "status": "published",
        }
    )
    join_response = CandidateJoinResponse.model_validate(
        {
            "session_id": "session-1",
            "room_name": "interview-room-1",
            "participant_token": "candidate-token-1",
            "candidate_identity": "candidate-session-1",
        }
    )
    event_request = InterviewRuntimeEventRequest.model_validate(
        {
            "event_type": "worker.connected",
            "event_source": "worker",
            "session_status": "connecting",
            "worker_status": "room_connected",
            "provider_status": "livekit_connected",
            "payload": {"room_name": "interview-room-1"},
        }
    )
    transcript_turn = TranscriptTurnRequest.model_validate(
        {
            "speaker": "agent",
            "sequence_number": 1,
            "transcript_text": "Xin chào, tôi là AI phỏng vấn viên.",
            "provider_event_id": "evt-1",
            "event_payload": {},
        }
    )
    generated_response = GenerateInterviewQuestionsResponse.model_validate(
        {
            "screening_id": "screening-1",
            "manual_questions": ["Bạn đã làm dự án nào gần đây?"],
            "question_guidance": "Tập trung vào backend",
            "generated_questions": [
                {
                    "question_text": "Giới thiệu ngắn về bản thân bạn.",
                    "source": "manual",
                    "rationale": "Provided directly by HR.",
                }
            ],
        }
    )
    update_schedule_request = UpdateInterviewScheduleRequest.model_validate(
        {
            "scheduled_start_at": "2026-04-18T09:00:00+00:00",
            "schedule_timezone": "Asia/Ho_Chi_Minh",
            "schedule_note": "Candidate selected this slot.",
        }
    )
    propose_schedule_request = ProposeInterviewScheduleRequest.model_validate(
        {
            "proposed_start_at": "2026-04-18T13:30:00+00:00",
            "note": "After work hours works better.",
            "timezone": "Asia/Ho_Chi_Minh",
        }
    )
    detail_response = InterviewSessionDetailResponse.model_validate(
        {
            "session_id": "session-1",
            "status": "in_progress",
            "worker_status": "responding",
            "provider_status": "gemini_streaming",
            "livekit_room_name": "interview-room-1",
            "opening_question": "Giới thiệu ngắn về bản thân bạn.",
            "approved_questions": ["Giới thiệu ngắn về bản thân bạn."],
            "manual_questions": ["Giới thiệu ngắn về bản thân bạn."],
            "question_guidance": "Tập trung vào backend",
            "plan": {
                "session_goal": {
                    "vi": "Đánh giá mức độ phù hợp của ứng viên với JD backend.",
                    "en": "Assess the candidate's fit for the backend JD.",
                },
                "opening_script": {
                    "vi": "Cảm ơn bạn đã tham gia.",
                    "en": "Thanks for joining.",
                },
                "questions": [
                    {
                        "question_index": 0,
                        "dimension_name": {"vi": "Backend", "en": "Backend"},
                        "prompt": {
                            "vi": "Giới thiệu ngắn về bản thân bạn.",
                            "en": "Introduce yourself briefly.",
                        },
                        "purpose": {
                            "vi": "Xác minh tín hiệu backend.",
                            "en": "Validate backend signals.",
                        },
                    }
                ],
            },
            "current_question_index": 0,
            "total_questions": 1,
            "recommendation": "Nên tiếp tục vào vòng sau.",
            "schedule": InterviewSchedulePayload().model_dump(),
            "last_error_code": None,
            "last_error_message": None,
            "transcript_turns": [],
            "runtime_events": [],
        }
    )
    review_response = InterviewSessionReviewResponse.model_validate(
        {
            "session_id": "session-1",
            "status": "completed",
            "summary_payload": {"final_summary": "done"},
            "transcript_turns": [],
        }
    )

    assert generated_response.question_guidance == "Tập trung vào backend"
    assert update_schedule_request.schedule_timezone == "Asia/Ho_Chi_Minh"
    assert propose_schedule_request.note == "After work hours works better."
    assert generated_response.generated_questions[0].source == "manual"
    assert publish_response.status == "published"
    assert join_response.candidate_identity == "candidate-session-1"
    assert event_request.provider_status == "livekit_connected"
    assert transcript_turn.provider_event_id == "evt-1"
    assert detail_response.provider_status == "gemini_streaming"
    assert detail_response.approved_questions[0] == "Giới thiệu ngắn về bản thân bạn."
    assert detail_response.plan is not None
    assert detail_response.plan.session_goal.en == "Assess the candidate's fit for the backend JD."
    assert detail_response.recommendation == "Nên tiếp tục vào vòng sau."
    assert review_response.summary_payload["final_summary"] == "done"
