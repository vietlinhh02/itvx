from contextlib import asynccontextmanager
from importlib import import_module

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from src.database import get_db
from src.main import app
from src.models.user import User
from src.schemas.interview import (
    CandidateJoinPreviewResponse,
    CandidateJoinRequest,
    CandidateJoinResponse,
    CompleteInterviewRequest,
    GenerateInterviewQuestionsResponse,
    InterviewFeedbackPolicyCollectionResponse,
    InterviewFeedbackPolicyResponse,
    InterviewFeedbackResponse,
    InterviewFeedbackSummaryResponse,
    InterviewPolicySummaryPayload,
    InterviewPolicyThresholds,
    InterviewSchedulePayload,
    InterviewSessionDetailResponse,
    InterviewSessionReviewResponse,
    InterviewSessionRuntimeStateResponse,
    PublishInterviewResponse,
    SuggestInterviewFeedbackPolicyResponse,
    TranscriptTurnRequest,
)
from src.schemas.jd import BilingualText, JDCompanyKnowledgeQueryResponse


class FakeInterviewSessionService:
    last_payload = None

    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def generate_questions(self, payload):
        type(self).last_payload = payload
        return GenerateInterviewQuestionsResponse(
            screening_id=payload.screening_id,
            manual_questions=payload.manual_questions,
            question_guidance=payload.question_guidance,
            generated_questions=[
                {
                    "question_text": "Giới thiệu ngắn về bản thân bạn.",
                    "source": "manual",
                    "rationale": "Provided directly by HR.",
                    "question_type": "manual",
                    "selection_reason": {
                        "vi": "Câu hỏi do HR cung cấp trực tiếp.",
                        "en": "Question provided directly by HR.",
                    },
                    "priority": 1,
                    "target_competency": {
                        "vi": "Backend",
                        "en": "Backend",
                    },
                    "evidence_gap": {
                        "vi": "Cần thêm bằng chứng backend.",
                        "en": "Need more backend evidence.",
                    },
                }
            ],
        )

    async def publish_interview(self, payload):
        type(self).last_payload = payload
        return PublishInterviewResponse(
            session_id="session-1",
            share_link="http://localhost:3000/interviews/join/share-token-1",
            room_name="interview-room-1",
            status="published",
            schedule=InterviewSchedulePayload(),
        )

    async def resolve_join(self, share_token: str, payload):
        _ = (share_token, payload)
        return CandidateJoinResponse(
            session_id="session-1",
            room_name="interview-room-1",
            participant_token="token-1",
            candidate_identity="candidate-session-1",
            schedule=InterviewSchedulePayload(),
        )

    async def get_join_preview(self, share_token: str):
        _ = share_token
        return CandidateJoinPreviewResponse(
            session_id="session-1",
            status="published",
            schedule=InterviewSchedulePayload(
                scheduled_start_at="2026-04-20T09:00:00+07:00",
                schedule_timezone="Asia/Ho_Chi_Minh",
                schedule_status="scheduled",
                schedule_note="Phong van dung gio.",
                candidate_proposed_start_at=None,
                candidate_proposed_note=None,
            ),
        )

    async def append_turn(self, session_id, payload):
        _ = (session_id, payload)

    async def get_session_detail(self, session_id: str):
        _ = session_id
        return InterviewSessionDetailResponse(
            session_id="session-1",
            status="connecting",
            worker_status="room_connected",
            provider_status="livekit_connected",
            livekit_room_name="interview-room-1",
            opening_question="Giới thiệu ngắn về bản thân bạn.",
            approved_questions=["Giới thiệu ngắn về bản thân bạn."],
            manual_questions=["Giới thiệu ngắn về bản thân bạn."],
            question_guidance="Tập trung vào backend",
            plan={
                "session_goal": BilingualText(
                    vi="Đánh giá mức độ phù hợp của ứng viên với JD backend.",
                    en="Assess the candidate's fit for the backend JD.",
                ),
                "opening_script": BilingualText(
                    vi="Cảm ơn bạn đã tham gia.",
                    en="Thanks for joining.",
                ),
                "overall_strategy": BilingualText(
                    vi="Bắt đầu với backend fundamentals rồi mở rộng theo evidence gap.",
                    en="Start with backend fundamentals, then expand based on evidence gaps.",
                ),
                "current_phase": "competency_validation",
                "question_selection_policy": BilingualText(
                    vi="Ưu tiên competency có evidence gap lớn nhất.",
                    en="Prioritize the competency with the biggest evidence gap.",
                ),
                "transition_rules": [
                    BilingualText(
                        vi="Nếu câu trả lời chung chung, hỏi làm rõ.",
                        en="If the answer is generic, ask for clarification.",
                    )
                ],
                "completion_criteria": [
                    BilingualText(
                        vi="Đủ bằng chứng cho competency trọng tâm.",
                        en="Enough evidence for the core competency.",
                    )
                ],
                "competencies": [
                    {
                        "name": {"vi": "Backend", "en": "Backend"},
                        "priority": 1,
                        "target_question_count": 2,
                        "current_coverage": 0.0,
                        "evidence_needed": [
                            {
                                "vi": "Ví dụ production backend cụ thể.",
                                "en": "A concrete production backend example.",
                            }
                        ],
                        "stop_condition": {
                            "vi": "Có đủ ví dụ và trade-off.",
                            "en": "Has enough examples and trade-offs.",
                        },
                    }
                ],
                "plan_events": [
                    {
                        "event_type": "plan.created",
                        "reason": {
                            "vi": "Khởi tạo plan từ screening.",
                            "en": "Plan initialized from screening.",
                        },
                        "chosen_action": "start_with_backend",
                        "affected_competency": {"vi": "Backend", "en": "Backend"},
                        "confidence": 0.8,
                        "question_index": 0,
                        "created_at": "2026-04-17T10:00:00+00:00",
                    }
                ],
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
                        "source": "manual",
                        "question_type": "manual",
                        "rationale": "Provided directly by HR.",
                        "priority": 1,
                        "target_competency": {"vi": "Backend", "en": "Backend"},
                        "evidence_gap": {
                            "vi": "Cần thêm bằng chứng backend.",
                            "en": "Need more backend evidence.",
                        },
                        "selection_reason": {
                            "vi": "HR muốn xác minh competency backend trước.",
                            "en": "HR wants to validate backend competency first.",
                        },
                        "transition_on_strong_answer": "advance_to_next_competency",
                        "transition_on_weak_answer": "ask_clarification",
                    }
                ],
            },
            current_question_index=0,
            total_questions=1,
            recommendation=None,
            schedule=InterviewSchedulePayload(),
            disconnect_deadline_at=None,
            last_disconnect_reason=None,
            last_error_code=None,
            last_error_message=None,
            transcript_turns=[],
            runtime_events=[],
        )

    async def get_runtime_state(self, session_id: str):
        _ = session_id
        return InterviewSessionRuntimeStateResponse(
            session_id="session-1",
            status="in_progress",
            worker_status="responding",
            provider_status="gemini_live",
            current_question_index=0,
            current_question={
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
                "source": "manual",
                "question_type": "manual",
            },
            next_intended_step=BilingualText(
                vi="Yêu cầu ứng viên bổ sung bối cảnh.",
                en="Ask the candidate for more context.",
            ),
            interview_decision_status="adjust",
            current_phase="competency_validation",
            last_plan_event={
                "event_type": "plan.adjusted",
                "reason": {
                    "vi": "Cần hỏi làm rõ",
                    "en": "Need a clarification question",
                },
                "chosen_action": "ask_clarification",
                "affected_competency": {"vi": "Backend", "en": "Backend"},
                "confidence": 0.74,
                "question_index": 0,
                "evidence_excerpt": {
                    "vi": "Em có làm backend.",
                    "en": "Em có làm backend.",
                },
                "decision_rule": "generic_answer_needs_clarification",
                "next_question_type": "clarification",
                "created_at": "2026-04-17T10:02:00+00:00",
            },
        )

    async def get_session_review(self, session_id: str):
        _ = session_id
        return InterviewSessionReviewResponse(
            session_id="session-1",
            status="completed",
            summary_payload={"final_summary": "done"},
            transcript_turns=[],
        )

    async def complete_session(self, session_id: str, payload):
        _ = (session_id, payload)

    async def expire_reconnect_grace_period(self, session_id: str):
        _ = session_id

    async def update_schedule(self, session_id: str, payload):
        _ = session_id
        type(self).last_payload = payload
        return InterviewSchedulePayload(
            scheduled_start_at="2026-04-18T09:00:00+00:00",
            schedule_timezone="Asia/Ho_Chi_Minh",
            schedule_status="confirmed",
            schedule_note="Candidate selected this slot.",
            candidate_proposed_start_at=None,
            candidate_proposed_note=None,
        )

    async def propose_schedule(self, share_token: str, payload):
        _ = share_token
        type(self).last_payload = payload
        return InterviewSchedulePayload(
            scheduled_start_at=None,
            schedule_timezone="Asia/Ho_Chi_Minh",
            schedule_status="proposed",
            schedule_note=None,
            candidate_proposed_start_at="2026-04-18T13:30:00+00:00",
            candidate_proposed_note="After work hours works better.",
        )

    async def get_jd_id_for_session(self, session_id: str):
        _ = session_id
        return "jd-1"

class FakeInterviewRuntimeService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def record_event(self, session_id: str, payload):
        _ = (session_id, payload)


class FakeInterviewFeedbackService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def submit_feedback(self, session_id: str, payload, current_user: User):
        _ = (payload, current_user)
        return InterviewFeedbackResponse(
            session_id=session_id,
            jd_id="jd-1",
            submitted_by_user_id="user-1",
            submitted_by_email="hr@example.com",
            overall_agreement_score=0.8,
            ai_recommendation="review",
            hr_recommendation="advance",
            recommendation_agreement=False,
            overall_notes="HR thinks the AI was too conservative.",
            missing_evidence_notes="Need more system design evidence.",
            false_positive_notes=None,
            false_negative_notes="Missed strong leadership signal.",
            competencies=[
                {
                    "competency_name": {"vi": "Backend", "en": "Backend"},
                    "ai_score": 0.55,
                    "hr_score": 0.8,
                    "delta": -0.25,
                    "judgement": "underrated",
                    "missing_evidence": "Need clearer system design evidence.",
                    "notes": "HR weighted backend depth higher.",
                }
            ],
            created_at="2026-04-17T17:00:00+07:00",
            updated_at="2026-04-17T17:00:00+07:00",
        )

    async def get_feedback(self, session_id: str):
        return await self.submit_feedback(session_id, None, User(id="user-1", email="hr@example.com", role="hr", is_active=True))

    async def get_feedback_summary(self, jd_id: str):
        return InterviewFeedbackSummaryResponse(
            jd_id=jd_id,
            feedback_count=3,
            agreement_rate=0.67,
            recommendation_agreement_rate=0.33,
            average_score_delta=0.22,
            competency_deltas=[{"label": "Backend", "value": 0.22}],
            judgement_breakdown=[{"label": "underrated", "value": 2.0}],
            failure_reasons=[{"reason": "Need clearer system design evidence.", "count": 2}],
            disagreement_sessions=[
                {
                    "session_id": "session-1",
                    "candidate_name": "candidate-session-1",
                    "overall_agreement_score": 0.8,
                    "recommendation_agreement": False,
                    "delta_magnitude": 0.25,
                    "created_at": "2026-04-17T17:00:00+07:00",
                }
            ],
            active_policy=None,
            latest_suggested_policy=None,
            policy_audit_trail=[],
        )

    async def get_policy_collection(self, jd_id: str):
        _ = jd_id
        return InterviewFeedbackPolicyCollectionResponse(
            jd_id="jd-1",
            active_policy=None,
            latest_suggested_policy=None,
            policy_audit_trail=[],
        )

    async def suggest_policy(self, jd_id: str, current_user: User):
        _ = (jd_id, current_user)
        policy = InterviewFeedbackPolicyResponse(
            policy_id="policy-1",
            jd_id="jd-1",
            status="suggested",
            version=1,
            source_feedback_count=3,
            policy_payload={
                "global_thresholds": InterviewPolicyThresholds().model_dump(mode="json"),
                "competency_overrides": [],
                "questioning_rules": {"require_measurable_outcome_before_advance": True},
                "application_scope": {"jd_id": "jd-1", "effective_from": "2026-04-17T10:00:00+00:00"},
            },
            summary_payload=InterviewPolicySummaryPayload(
                source_feedback_count=3,
                top_overrated_competencies=["Backend"],
                top_underrated_competencies=[],
                top_failure_reasons=["Need clearer system design evidence."],
                expected_effects=["Ask for more measurable examples before advancing."],
                recommendation_agreement_rate=0.33,
            ),
            approved_by_user_id=None,
            approved_by_email=None,
            approved_at=None,
            created_at="2026-04-17T17:05:00+07:00",
            updated_at="2026-04-17T17:05:00+07:00",
        )
        return SuggestInterviewFeedbackPolicyResponse(
            policy=policy,
            audit_event={
                "event_type": "policy.suggested",
                "payload": {"version": 1},
                "created_at": "2026-04-17T17:05:00+07:00",
            },
        )

    async def apply_policy(self, jd_id: str, policy_id: str, current_user: User):
        _ = (jd_id, policy_id, current_user)
        return (await self.suggest_policy("jd-1", current_user)).policy.model_copy(update={"status": "active"})

    async def reject_policy(self, jd_id: str, policy_id: str, current_user: User):
        _ = (jd_id, policy_id, current_user)
        return (await self.suggest_policy("jd-1", current_user)).policy.model_copy(update={"status": "superseded"})


class FakeCompanyKnowledgeService:
    def __init__(self, db_session) -> None:
        self._db_session = db_session

    async def query_knowledge(self, jd_id: str, query: str):
        _ = jd_id
        return JDCompanyKnowledgeQueryResponse(
            query=query,
            citations=[
                {
                    "chunk_id": "chunk-1",
                    "document_id": "doc-1",
                    "file_name": "company-handbook.pdf",
                    "section_title": "Benefits",
                    "page_number": None,
                    "excerpt": "Annual leave is 15 days.",
                }
            ],
        )


SENSITIVE_READ_ENDPOINTS = [
    "/api/v1/interviews/sessions/session-1/review",
    "/api/v1/interviews/sessions/session-1/feedback",
    "/api/v1/interviews/jd/jd-1/feedback-summary",
    "/api/v1/interviews/jd/jd-1/feedback-policy",
]


def build_client(
    monkeypatch: MonkeyPatch,
    *,
    current_user: User | None = None,
    auth_error: HTTPException | None = None,
) -> TestClient:
    @asynccontextmanager
    async def fake_lifespan(_: FastAPI):
        yield

    async def fake_db_session():
        yield object()

    async def fake_current_user():
        if auth_error is not None:
            raise auth_error
        return current_user or User(id="user-1", email="hr@example.com", role="hr", is_active=True)

    monkeypatch.setattr(app.router, "lifespan_context", fake_lifespan)
    app.dependency_overrides.clear()
    monkeypatch.setitem(app.dependency_overrides, get_db, fake_db_session)

    module = import_module("src.api.v1.interviews")
    monkeypatch.setattr(module, "InterviewSessionService", FakeInterviewSessionService)
    monkeypatch.setattr(module, "InterviewRuntimeService", FakeInterviewRuntimeService)
    monkeypatch.setattr(module, "InterviewFeedbackService", FakeInterviewFeedbackService)
    monkeypatch.setattr(module, "CompanyKnowledgeService", FakeCompanyKnowledgeService)
    monkeypatch.setitem(app.dependency_overrides, module.get_current_active_user, fake_current_user)
    monkeypatch.setattr(module, "settings", type("Settings", (), {"worker_callback_secret": "change-me"})())
    return TestClient(app)



def test_generate_interview_questions_returns_candidates(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/generate-questions",
        json={
            "screening_id": "screening-1",
            "manual_questions": ["Bạn có thể giới thiệu ngắn về bản thân không?"],
            "question_guidance": "Tập trung vào backend",
        },
    )

    assert response.status_code == 200
    assert response.json()["manual_questions"] == ["Bạn có thể giới thiệu ngắn về bản thân không?"]
    assert response.json()["question_guidance"] == "Tập trung vào backend"
    assert response.json()["generated_questions"][0]["source"] == "manual"


def test_publish_interview_returns_share_link(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/publish",
        json={
            "screening_id": "screening-1",
            "approved_questions": ["Bạn có thể giới thiệu ngắn về bản thân không?"],
            "manual_questions": ["Bạn có thể giới thiệu ngắn về bản thân không?"],
            "question_guidance": "Tập trung vào backend",
        },
    )

    assert response.status_code == 201
    assert "/interviews/join/" in response.json()["share_link"]
    assert response.json()["status"] == "published"



def test_join_interview_returns_room_and_token(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/join/share-token-1",
        json=CandidateJoinRequest(candidate_name="Nguyen Van A").model_dump(),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["room_name"] == "interview-room-1"
    assert payload["participant_token"] == "token-1"


def test_get_join_preview_returns_public_schedule(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/join/share-token-1")

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-1"
    assert response.json()["schedule"]["scheduled_start_at"] == "2026-04-20T09:00:00+07:00"
    assert response.json()["schedule"]["schedule_status"] == "scheduled"


def test_get_session_detail_returns_runtime_state(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/sessions/session-1")

    assert response.status_code == 200
    assert response.json()["provider_status"] == "livekit_connected"
    assert response.json()["plan"]["session_goal"]["en"] == "Assess the candidate's fit for the backend JD."
    assert response.json()["plan"]["current_phase"] == "competency_validation"
    assert response.json()["plan"]["questions"][0]["source"] == "manual"
    assert response.json()["plan"]["plan_events"][0]["event_type"] == "plan.created"
    assert response.json()["total_questions"] == 1


def test_get_session_detail_is_public_for_candidate_polling(monkeypatch: MonkeyPatch) -> None:
    client = build_client(
        monkeypatch,
        auth_error=HTTPException(status_code=401, detail="Invalid authentication credentials"),
    )
    response = client.get("/api/v1/interviews/sessions/session-1")

    assert response.status_code == 200
    assert response.json()["session_id"] == "session-1"


def test_sensitive_read_endpoints_require_authenticated_user(monkeypatch: MonkeyPatch) -> None:
    client = build_client(
        monkeypatch,
        auth_error=HTTPException(status_code=401, detail="Invalid authentication credentials"),
    )

    for endpoint in SENSITIVE_READ_ENDPOINTS:
        response = client.get(endpoint)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid authentication credentials"}


def test_sensitive_read_endpoints_forbid_non_hr_roles(monkeypatch: MonkeyPatch) -> None:
    client = build_client(
        monkeypatch,
        current_user=User(id="user-2", email="candidate@example.com", role="candidate", is_active=True),
    )

    for endpoint in SENSITIVE_READ_ENDPOINTS:
        response = client.get(endpoint)
        assert response.status_code == 403
        assert response.json() == {"detail": "HR or admin access required"}


def test_get_session_runtime_state_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/sessions/session-1/runtime-state")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_get_session_runtime_state_returns_current_question(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get(
        "/api/v1/interviews/sessions/session-1/runtime-state",
        headers={"X-Worker-Callback-Secret": "change-me"},
    )

    assert response.status_code == 200
    assert response.json()["interview_decision_status"] == "adjust"
    assert response.json()["current_question"]["question_type"] == "manual"
    assert response.json()["last_plan_event"]["decision_rule"] == "generic_answer_needs_clarification"


def test_append_turn_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/turns",
        json=TranscriptTurnRequest(
            speaker="assistant",
            transcript_text="Xin chao, chung ta bat dau nhe.",
            sequence_number=0,
            provider_event_id="evt-1",
        ).model_dump(),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_append_turn_accepts_worker_callback_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/turns",
        headers={"X-Worker-Callback-Secret": "change-me"},
        json=TranscriptTurnRequest(
            speaker="assistant",
            transcript_text="Xin chao, chung ta bat dau nhe.",
            sequence_number=0,
            provider_event_id="evt-1",
        ).model_dump(),
    )

    assert response.status_code == 204


def test_post_runtime_event_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/runtime-events",
        json={
            "event_type": "worker.connected",
            "event_source": "worker",
            "session_status": "connecting",
            "worker_status": "room_connected",
            "provider_status": "livekit_connected",
            "payload": {},
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_post_runtime_event_accepts_worker_callback_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/runtime-events",
        headers={"X-Worker-Callback-Secret": "change-me"},
        json={
            "event_type": "worker.connected",
            "event_source": "worker",
            "session_status": "connecting",
            "worker_status": "room_connected",
            "provider_status": "livekit_connected",
            "payload": {},
        },
    )

    assert response.status_code == 204


def test_get_session_review_returns_summary(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/sessions/session-1/review")

    assert response.status_code == 200
    assert response.json()["summary_payload"]["final_summary"] == "done"


def test_submit_session_feedback_returns_structured_record(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/feedback",
        json={
            "overall_agreement_score": 0.8,
            "hr_recommendation": "advance",
            "overall_notes": "HR thinks the AI was too conservative.",
            "missing_evidence_notes": "Need more system design evidence.",
            "false_positive_notes": None,
            "false_negative_notes": "Missed strong leadership signal.",
            "competencies": [
                {
                    "competency_name": {"vi": "Backend", "en": "Backend"},
                    "hr_score": 0.8,
                    "judgement": "underrated",
                    "missing_evidence": "Need clearer system design evidence.",
                    "notes": "HR weighted backend depth higher.",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["recommendation_agreement"] is False
    assert response.json()["competencies"][0]["judgement"] == "underrated"


def test_get_feedback_summary_returns_jd_analytics(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.get("/api/v1/interviews/jd/jd-1/feedback-summary")

    assert response.status_code == 200
    assert response.json()["feedback_count"] == 3
    assert response.json()["competency_deltas"][0]["label"] == "Backend"


def test_suggest_policy_returns_suggested_policy(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews/jd/jd-1/feedback-policy/suggest")

    assert response.status_code == 200
    assert response.json()["policy"]["status"] == "suggested"
    assert response.json()["audit_event"]["event_type"] == "policy.suggested"


def test_apply_policy_returns_active_policy(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews/jd/jd-1/feedback-policy/policy-1/apply")

    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_complete_session_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/complete",
        json=CompleteInterviewRequest(reason="candidate_left").model_dump(),
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_complete_session_accepts_worker_callback_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/complete",
        headers={"X-Worker-Callback-Secret": "change-me"},
        json=CompleteInterviewRequest(reason="candidate_left").model_dump(),
    )

    assert response.status_code == 204


def test_expire_reconnect_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post("/api/v1/interviews/sessions/session-1/expire-reconnect")

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_expire_reconnect_accepts_worker_callback_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/expire-reconnect",
        headers={"X-Worker-Callback-Secret": "change-me"},
    )

    assert response.status_code == 204


def test_update_schedule_returns_schedule_payload(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/schedule",
        json={
            "scheduled_start_at": "2026-04-18T09:00:00+00:00",
            "schedule_timezone": "Asia/Ho_Chi_Minh",
            "schedule_note": "Candidate selected this slot.",
        },
    )

    assert response.status_code == 200
    assert response.json()["schedule_status"] == "confirmed"


def test_candidate_can_propose_schedule(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/join/share-token-1/schedule",
        json={
            "proposed_start_at": "2026-04-18T13:30:00+00:00",
            "note": "After work hours works better.",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )

    assert response.status_code == 200
    assert response.json()["schedule_status"] == "proposed"


def test_worker_can_query_company_knowledge_for_session(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/knowledge-query",
        headers={"X-Worker-Callback-Secret": "change-me"},
        json={"query": "benefits"},
    )

    assert response.status_code == 200
    assert response.json()["citations"][0]["file_name"] == "company-handbook.pdf"


def test_company_knowledge_query_requires_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/knowledge-query",
        json={"query": "benefits"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}


def test_company_knowledge_query_rejects_wrong_worker_secret(monkeypatch: MonkeyPatch) -> None:
    client = build_client(monkeypatch)
    response = client.post(
        "/api/v1/interviews/sessions/session-1/knowledge-query",
        headers={"X-Worker-Callback-Secret": "wrong"},
        json={"query": "benefits"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid worker callback secret"}
