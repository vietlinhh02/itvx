import pytest
from pytest import MonkeyPatch
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.interview import InterviewSession
from src.models.jd import JDAnalysis, JDDocument
from src.schemas.interview import (
    CandidateJoinRequest,
    CompleteInterviewRequest,
    GenerateInterviewQuestionsRequest,
    InterviewRuntimeEventRequest,
    ProposeInterviewScheduleRequest,
    PublishInterviewRequest,
    TranscriptTurnRequest,
    UpdateInterviewScheduleRequest,
)
from src.services.cv_screening_service import CVScreeningService
from src.services.interview_runtime_service import InterviewRuntimeService
from src.services.interview_session_service import InterviewSessionService


class FakeDispatchResponse:
    accepted = True
    status = "queued"


class FakeWorkerLauncher:
    def __init__(self) -> None:
        self.called_with: dict[str, str] | None = None

    async def launch(
        self,
        *,
        session_id: str,
        room_name: str,
        opening_question: str,
        worker_token: str,
        jd_id: str,
    ) -> FakeDispatchResponse:
        self.called_with = {
            "session_id": session_id,
            "room_name": room_name,
            "opening_question": opening_question,
            "worker_token": worker_token,
        }
        return FakeDispatchResponse()


def build_service(db_session: AsyncSession) -> tuple[InterviewSessionService, FakeWorkerLauncher]:
    launcher = FakeWorkerLauncher()
    return InterviewSessionService(db_session, worker_launcher=launcher), launcher


async def seed_completed_screening(db_session: AsyncSession) -> str:
    jd_document = JDDocument(
        file_name="jd.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/jd.pdf",
        status="completed",
    )
    db_session.add(jd_document)
    await db_session.flush()

    db_session.add(
        JDAnalysis(
            jd_document_id=jd_document.id,
            model_name="gemini-2.5-pro",
            analysis_payload={
                "job_overview": {
                    "job_title": {"vi": "Ky su Backend", "en": "Backend Engineer"},
                    "department": {"vi": "Ky thuat", "en": "Engineering"},
                    "seniority_level": "mid",
                    "location": {"vi": "TP HCM", "en": "Ho Chi Minh City"},
                    "work_mode": "hybrid",
                    "role_summary": {"vi": "Tom tat", "en": "Summary"},
                    "company_benefits": [],
                },
                "requirements": {
                    "required_skills": ["Python"],
                    "preferred_skills": [],
                    "tools_and_technologies": ["FastAPI"],
                    "experience_requirements": {
                        "minimum_years": 3,
                        "relevant_roles": [{"vi": "Ky su Backend", "en": "Backend Engineer"}],
                        "preferred_domains": [],
                    },
                    "education_and_certifications": [],
                    "language_requirements": [],
                    "key_responsibilities": [],
                    "screening_knockout_criteria": [],
                },
                "rubric_seed": {
                    "evaluation_dimensions": [
                        {
                            "name": {"vi": "Kỹ thuật", "en": "Technical"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "must_have",
                            "weight": 0.4,
                            "evidence_signals": [{"vi": "API", "en": "API"}],
                        },
                        {
                            "name": {"vi": "Giao tiếp", "en": "Communication"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.2,
                            "evidence_signals": [{"vi": "Explain", "en": "Explain"}],
                        },
                        {
                            "name": {"vi": "SQL", "en": "SQL"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Query", "en": "Query"}],
                        },
                        {
                            "name": {"vi": "Docker", "en": "Docker"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "nice_to_have",
                            "weight": 0.15,
                            "evidence_signals": [{"vi": "Container", "en": "Container"}],
                        },
                        {
                            "name": {"vi": "Ownership", "en": "Ownership"},
                            "description": {"vi": "Mo ta", "en": "Description"},
                            "priority": "important",
                            "weight": 0.1,
                            "evidence_signals": [{"vi": "Lead", "en": "Lead"}],
                        },
                    ],
                    "screening_rules": {
                        "minimum_requirements": [],
                        "scoring_principle": {
                            "vi": "Khong bu tru must-have bang nice-to-have",
                            "en": "Nice-to-have cannot replace must-have",
                        },
                    },
                    "ambiguities_for_human_review": [],
                },
            },
        )
    )
    await db_session.flush()

    candidate_document = CandidateDocument(
        file_name="candidate.pdf",
        mime_type="application/pdf",
        storage_path="/tmp/candidate.pdf",
        status="completed",
    )
    db_session.add(candidate_document)
    await db_session.flush()

    candidate_profile = CandidateProfile(
        candidate_document_id=candidate_document.id,
        profile_payload={
            "candidate_summary": {
                "full_name": "Nguyen Van A",
                "current_title": "Backend Engineer",
                "location": "Ho Chi Minh City",
                "total_years_experience": 4,
                "seniority_signal": "mid",
                "professional_summary": {
                    "vi": "Kỹ sư backend tập trung vào Python.",
                    "en": "Backend engineer focused on Python.",
                },
            },
            "work_experience": [],
            "projects": [],
            "skills_inventory": [],
            "education": [],
            "certifications": [],
            "languages": [],
            "profile_uncertainties": [],
        },
    )
    db_session.add(candidate_profile)
    await db_session.flush()

    screening = CandidateScreening(
        jd_document_id=jd_document.id,
        candidate_profile_id=candidate_profile.id,
        model_name="gemini-2.5-pro",
        status="completed",
        screening_payload={
            "result": {
                "dimension_scores": [
                    {
                        "dimension_name": {"vi": "Kỹ thuật", "en": "Technical"},
                        "score": 0.82,
                    },
                    {
                        "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
                        "score": 0.68,
                    },
                    {
                        "dimension_name": {"vi": "SQL", "en": "SQL"},
                        "score": 0.61,
                    },
                ],
                "follow_up_questions": [
                    {
                        "question": {
                            "vi": "Hãy chia sẻ một ví dụ cụ thể về dự án backend gần đây nhất.",
                            "en": "Share a concrete example from your most recent backend project.",
                        },
                        "purpose": {
                            "vi": "Xác minh năng lực kỹ thuật cốt lõi.",
                            "en": "Validate the core technical competency.",
                        },
                        "linked_dimension": {"vi": "Kỹ thuật", "en": "Technical"},
                    }
                ],
            }
        },
    )
    db_session.add(screening)
    await db_session.commit()
    await db_session.refresh(screening)
    return screening.id


@pytest.mark.asyncio
async def test_publish_session_creates_room_and_share_token(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)

    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    assert published.status == "published"
    assert published.room_name.startswith("interview-")
    assert "/interviews/join/" in published.share_link
    detail = await service.get_session_detail(published.session_id)
    assert detail.approved_questions == ["Bạn có thể giới thiệu ngắn về bản thân không?"]
    assert detail.plan is not None
    assert detail.plan.current_phase == "competency_validation"
    assert detail.plan.questions[0].source is not None
    assert detail.plan.plan_events[-1].event_type == "plan.started"
    assert any(event.event_type == "planning.published" for event in detail.runtime_events)


@pytest.mark.asyncio
async def test_publish_session_returns_existing_session_for_same_screening(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)

    first = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )
    second = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Một câu hỏi khác nhưng cùng screening."],
        )
    )

    assert second.session_id == first.session_id
    assert second.share_link == first.share_link
    assert second.room_name == first.room_name


@pytest.mark.asyncio
async def test_update_schedule_sets_confirmed_time(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    schedule = await service.update_schedule(
        published.session_id,
        UpdateInterviewScheduleRequest(
            scheduled_start_at="2026-04-18T09:00:00+00:00",
            schedule_timezone="Asia/Ho_Chi_Minh",
            schedule_note="Candidate selected this slot.",
        ),
    )

    assert schedule.schedule_status == "confirmed"
    assert schedule.scheduled_start_at == "2026-04-18T16:00:00+07:00"
    assert schedule.schedule_note == "Candidate selected this slot."


@pytest.mark.asyncio
async def test_candidate_can_propose_schedule(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    share_token = published.share_link.rsplit("/", 1)[-1]
    schedule = await service.propose_schedule(
        share_token,
        ProposeInterviewScheduleRequest(
            proposed_start_at="2026-04-18T13:30:00+00:00",
            note="After work hours works better.",
            timezone="Asia/Ho_Chi_Minh",
        ),
    )

    assert schedule.schedule_status == "proposed"
    assert schedule.candidate_proposed_start_at == "2026-04-18T20:30:00+07:00"
    assert schedule.candidate_proposed_note == "After work hours works better."


@pytest.mark.asyncio
async def test_update_schedule_rejects_completed_session(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )
    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    session.status = "completed"
    await db_session.commit()

    with pytest.raises(ValueError, match="Completed interviews cannot be rescheduled"):
        await service.update_schedule(
            published.session_id,
            UpdateInterviewScheduleRequest(
                scheduled_start_at="2026-04-18T09:00:00+00:00",
                schedule_timezone="Asia/Ho_Chi_Minh",
            ),
        )


@pytest.mark.asyncio
async def test_generate_questions_combines_manual_and_screening_inputs(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)

    generated = await service.generate_questions(
        GenerateInterviewQuestionsRequest(
            screening_id=screening_id,
            manual_questions=["Bạn đang tự hào nhất về dự án nào gần đây?"],
            question_guidance="Tập trung vào backend và ownership",
        )
    )

    assert generated.screening_id == screening_id
    assert generated.manual_questions == ["Bạn đang tự hào nhất về dự án nào gần đây?"]
    assert generated.question_guidance == "Tập trung vào backend và ownership"
    assert generated.generated_questions[0].source == "manual"
    assert any(item.source in {"llm", "guidance", "screening"} for item in generated.generated_questions[1:])

    screening = await db_session.get(CandidateScreening, screening_id)
    assert screening is not None
    interview_draft = screening.screening_payload["interview_draft"]
    assert interview_draft["manual_questions"] == ["Bạn đang tự hào nhất về dự án nào gần đây?"]
    assert interview_draft["question_guidance"] == "Tập trung vào backend và ownership"
    assert interview_draft["approved_questions"]
    assert interview_draft["generated_questions"]
    assert interview_draft["generated_questions"][0]["source"] == "manual"

    from src.services.cv_screening_service import CVScreeningService

    screening_response = await CVScreeningService(db_session=db_session).get_screening(screening_id)
    assert screening_response is not None
    assert screening_response.interview_session_id is None
    assert screening_response.interview_draft is not None
    assert screening_response.interview_draft.manual_questions == ["Bạn đang tự hào nhất về dự án nào gần đây?"]
    assert screening_response.interview_draft.question_guidance == "Tập trung vào backend và ownership"
    assert screening_response.interview_draft.approved_questions


@pytest.mark.asyncio
async def test_get_screening_returns_linked_interview_session_id(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    interview_service, _ = build_service(db_session)

    published = await interview_service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    screening_response = await CVScreeningService(db_session=db_session).get_screening(screening_id)
    assert screening_response is not None
    assert screening_response.interview_session_id == published.session_id


@pytest.mark.asyncio
async def test_publish_session_requires_approved_questions(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)

    with pytest.raises(ValueError, match="Approved interview questions are required"):
        await service.publish_interview(
            PublishInterviewRequest(
                screening_id=screening_id,
                approved_questions=["   "],
            )
        )


@pytest.mark.asyncio
async def test_resolve_join_returns_token_and_room(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    share_token = published.share_link.rsplit("/", 1)[-1]
    join_payload = await service.resolve_join(
        share_token,
        CandidateJoinRequest(candidate_name="Nguyen Van A"),
    )

    assert join_payload.room_name == published.room_name
    assert join_payload.participant_token
    assert "nguyen-van-a" in join_payload.candidate_identity


@pytest.mark.asyncio
async def test_resolve_join_rejects_completed_session(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )
    await service.store_summary(
        published.session_id,
        {"final_summary": "Buổi phỏng vấn đã hoàn tất."},
    )

    share_token = published.share_link.rsplit("/", 1)[-1]
    with pytest.raises(ValueError, match="ended"):
        await service.resolve_join(
            share_token,
            CandidateJoinRequest(candidate_name="Nguyen Van A"),
        )


@pytest.mark.asyncio
async def test_append_turn_persists_transcript(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="agent",
            sequence_number=0,
            transcript_text="Xin chào, chúng ta bắt đầu nhé.",
            event_payload={},
        ),
    )

    turns = await service.list_turns(published.session_id)
    assert len(turns) == 1
    assert turns[0].speaker == "agent"


@pytest.mark.asyncio
async def test_candidate_generic_answer_creates_plan_adjusted_event(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em có làm backend.",
            provider_event_id="evt-generic-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert any(event.event_type == "plan.adjusted" for event in detail.runtime_events)
    assert detail.plan is not None
    assert any(event.event_type == "plan.adjusted" for event in detail.plan.plan_events)
    adjusted_event = next(event for event in detail.plan.plan_events if event.event_type == "plan.adjusted")
    assert adjusted_event.decision_rule == "generic_answer_needs_clarification"
    assert adjusted_event.next_question_type == "clarification"
    assert adjusted_event.evidence_excerpt is not None
    assert any(question.question_type == "clarification" for question in detail.plan.questions)
    assert detail.plan.interview_decision_status == "adjust"
    assert detail.plan.next_intended_step is not None
    assert detail.plan.competencies[0].status == "in_progress"
    assert detail.total_questions == len(detail.plan.questions)


@pytest.mark.asyncio
async def test_append_turn_ignores_duplicate_provider_event_id(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn có thể giới thiệu ngắn về bản thân không?"],
        )
    )

    payload = TranscriptTurnRequest(
        speaker="candidate",
        sequence_number=1,
        transcript_text="Em có bốn năm kinh nghiệm backend.",
        provider_event_id="evt-duplicate",
        event_payload={"role": "user"},
    )
    await service.append_turn(session_id=published.session_id, payload=payload)
    await service.append_turn(session_id=published.session_id, payload=payload)

    turns = await service.list_turns(published.session_id)
    assert len(turns) == 1
    assert turns[0].provider_event_id == "evt-duplicate"


@pytest.mark.asyncio
async def test_record_runtime_event_updates_session_reconciliation_state(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    runtime_service = InterviewRuntimeService(db_session)
    await runtime_service.record_event(
        published.session_id,
        InterviewRuntimeEventRequest(
            event_type="worker.connected",
            event_source="worker",
            session_status="connecting",
            worker_status="room_connected",
            provider_status="livekit_connected",
            payload={"attempt": 1},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.worker_status == "room_connected"
    assert detail.provider_status == "livekit_connected"
    assert detail.status == "connecting"

    await runtime_service.record_event(
        published.session_id,
        InterviewRuntimeEventRequest(
            event_type="agent.session_started",
            event_source="worker",
            session_status="in_progress",
            worker_status="responding",
            provider_status="gemini_live",
            payload={"room_name": published.room_name},
        ),
    )

    started_detail = await service.get_session_detail(published.session_id)
    assert started_detail.status == "in_progress"


@pytest.mark.asyncio
async def test_candidate_strong_answer_creates_phase_completed_event(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text=(
                "Ví dụ gần nhất là em phụ trách một service production có latency cao. "
                "Em phân tích bottleneck, tối ưu query và cache, rồi giảm 35% latency sau release."
            ),
            provider_event_id="evt-strong-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert any(event.event_type == "plan.phase_completed" for event in detail.runtime_events)
    assert detail.plan is not None
    assert any(event.event_type == "plan.phase_completed" for event in detail.plan.plan_events)
    completed_event = next(event for event in detail.plan.plan_events if event.event_type == "plan.phase_completed")
    assert completed_event.decision_rule in {
        "advance_after_sufficient_evidence",
        "all_competencies_covered_prepare_wrap_up",
    }
    assert completed_event.evidence_excerpt is not None
    assert detail.plan.current_phase in {"deep_dive", "wrap_up"}
    assert detail.plan.competencies[0].status == "covered"
    assert detail.plan.competencies[0].current_coverage == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_candidate_inconsistent_answer_creates_recovery_question(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Thực ra timeline dự án hơi mâu thuẫn vì em nói lead toàn bộ nhưng phần lớn chỉ review.",
            provider_event_id="evt-recovery-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert any(question.question_type == "recovery" for question in detail.plan.questions)
    assert detail.plan.interview_decision_status == "escalate_hr"
    assert detail.plan.competencies[0].status == "needs_recovery"
    recovery_event = next(event for event in detail.plan.plan_events if event.chosen_action == "ask_recovery")
    assert recovery_event.decision_rule == "recovery_signal_detected"
    assert recovery_event.next_question_type == "recovery"
    assert recovery_event.evidence_excerpt is not None


@pytest.mark.asyncio
async def test_start_reconnect_grace_period_marks_session_reconnecting(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.start_reconnect_grace_period(
        published.session_id,
        participant_identity="candidate-session-1",
        reason="candidate_left",
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "reconnecting"
    assert detail.worker_status == "waiting_for_candidate"
    assert detail.last_disconnect_reason == "candidate_left"
    assert detail.disconnect_deadline_at is not None

    timeout_job = await db_session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.resource_id == published.session_id,
            BackgroundJob.job_type == "interview_disconnect_timeout",
        )
    )
    assert timeout_job is not None
    assert timeout_job.status == "queued"


@pytest.mark.asyncio
async def test_resolve_join_clears_reconnect_deadline_after_rejoin(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.start_reconnect_grace_period(
        published.session_id,
        participant_identity="candidate-session-1",
        reason="candidate_left",
    )
    share_token = published.share_link.rsplit("/", 1)[-1]
    await service.resolve_join(
        share_token,
        CandidateJoinRequest(candidate_name="Nguyen Van A"),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "waiting"
    assert detail.disconnect_deadline_at is None
    assert detail.last_disconnect_reason is None


@pytest.mark.asyncio
async def test_expire_reconnect_grace_period_enqueues_summary_after_deadline(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.start_reconnect_grace_period(
        published.session_id,
        participant_identity="candidate-session-1",
        reason="candidate_left",
    )
    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    session.disconnect_deadline_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    expired = await service.expire_reconnect_grace_period(published.session_id)

    assert expired is True
    detail = await service.get_session_detail(published.session_id)
    assert detail.worker_status == "summarizing"
    summary_job = await db_session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.resource_id == published.session_id,
            BackgroundJob.job_type == "interview_summary",
        )
    )
    assert summary_job is not None
    assert summary_job.payload["completion_reason"] == "candidate_left"


@pytest.mark.asyncio
async def test_last_competency_strong_answer_moves_plan_to_wrap_up(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    competencies = list(plan_payload.get("competencies", []))
    for index, item in enumerate(competencies):
        if not isinstance(item, dict):
            continue
        updated = dict(item)
        updated["status"] = "covered" if index < len(competencies) - 1 else "in_progress"
        updated["current_coverage"] = 1.0 if index < len(competencies) - 1 else 0.4
        updated["evidence_collected_count"] = 1 if index < len(competencies) - 1 else 0
        competencies[index] = updated
    plan_payload["competencies"] = competencies
    plan_payload["current_competency_index"] = max(len(competencies) - 1, 0)
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Ví dụ cụ thể là em tối ưu service production, giảm 35% latency, trực tiếp triển khai và theo dõi KPI sau release.",
            provider_event_id="evt-wrap-up-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_phase == "wrap_up"
    assert detail.plan.interview_decision_status == "ready_to_wrap"
    assert detail.plan.next_intended_step is not None
    assert any(event.chosen_action == "prepare_wrap_up" for event in detail.plan.plan_events)


@pytest.mark.asyncio
async def test_get_review_returns_transcript_and_summary(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="agent",
            sequence_number=0,
            transcript_text="Xin chào, tôi là AI phỏng vấn viên.",
            provider_event_id="evt-opening",
            event_payload={},
        ),
    )
    await service.store_summary(
        published.session_id,
        {"final_summary": "Ứng viên trả lời rõ ràng ở lượt đầu."},
    )

    review = await service.get_session_review(published.session_id)
    assert review.summary_payload["final_summary"] == "Ứng viên trả lời rõ ràng ở lượt đầu."
    assert review.transcript_turns[0].provider_event_id == "evt-opening"


@pytest.mark.asyncio
async def test_complete_session_enqueues_summary_job_and_run_summary_job_stores_review(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeSummaryGenerator:
        async def generate(
            self,
            *,
            opening_question: str,
            turns: list[dict[str, object]],
            plan_payload: dict[str, object] | None = None,
        ) -> dict[str, object]:
            return {
                "final_summary": "Ứng viên trả lời mạch lạc và có chiều sâu.",
                "strengths": ["Giải thích rõ kinh nghiệm backend"],
                "concerns": ["Chưa nói rõ về scale hệ thống"],
                "recommendation": "Nên vào vòng kỹ thuật tiếp theo",
                "turn_breakdown": turns,
                "opening_question": opening_question,
            }

    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="agent",
            sequence_number=0,
            transcript_text="Xin chào, bạn hãy giới thiệu ngắn về bản thân.",
            provider_event_id="evt-agent-1",
            event_payload={},
        ),
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em có 4 năm làm backend với Python và FastAPI.",
            provider_event_id="evt-candidate-1",
            event_payload={},
        ),
    )

    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="candidate_left"),
    )

    job = await db_session.scalar(
        select(BackgroundJob).where(
            BackgroundJob.resource_id == published.session_id,
            BackgroundJob.job_type == "interview_summary",
        )
    )
    assert job is not None
    assert job.status == "queued"
    assert job.payload["completion_reason"] == "candidate_left"

    detail = await service.get_session_detail(published.session_id)
    review = await service.get_session_review(published.session_id)
    assert detail.worker_status == "summarizing"
    assert review.summary_payload == {}

    await service.run_summary_job(
        published.session_id,
        summary_generator=FakeSummaryGenerator(),
    )

    review = await service.get_session_review(published.session_id)
    detail = await service.get_session_detail(published.session_id)
    assert review.summary_payload["recommendation"] == "Nên vào vòng kỹ thuật tiếp theo"
    assert review.summary_payload["turn_breakdown"][1]["speaker"] == "candidate"
    assert review.summary_payload["completion_reason"] == "candidate_left"
    assert detail.status == "completed"
    assert detail.worker_status == "completed"
    assert detail.provider_status == "completed"


@pytest.mark.asyncio
async def test_complete_session_closes_room_and_blocks_rejoin_while_summarizing(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )
    delete_room = AsyncMock()
    service._livekit.delete_room = delete_room  # type: ignore[method-assign]

    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="agent_wrap_up"),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "finishing"
    assert detail.worker_status == "summarizing"
    assert detail.provider_status == "closing"
    delete_room.assert_awaited_once_with(published.room_name)

    share_token = published.share_link.rsplit("/", 1)[-1]
    with pytest.raises(ValueError, match="ended"):
        await service.resolve_join(
            share_token,
            CandidateJoinRequest(candidate_name="Nguyen Van A"),
        )


@pytest.mark.asyncio
async def test_complete_session_is_idempotent_while_summary_job_is_active(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="candidate_left"),
    )
    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="candidate_left"),
    )

    jobs = list(
        (
            await db_session.scalars(
                select(BackgroundJob).where(
                    BackgroundJob.resource_id == published.session_id,
                    BackgroundJob.job_type == "interview_summary",
                )
            )
        ).all()
    )
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_store_summary_ignores_completed_at_when_summary_is_missing(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    session = await db_session.scalar(
        select(InterviewSession).where(InterviewSession.id == published.session_id)
    )
    assert session is not None
    session.completed_at = session.created_at
    await db_session.commit()

    await service.store_summary(
        published.session_id,
        {"final_summary": "Ứng viên vẫn được tổng hợp sau khi room đã đóng."},
    )

    review = await service.get_session_review(published.session_id)
    assert review.summary_payload["final_summary"] == "Ứng viên vẫn được tổng hợp sau khi room đã đóng."


@pytest.mark.asyncio
async def test_publish_session_auto_spawns_worker_launch(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    class FakeDispatchResponse:
        accepted = True
        status = "queued"

    class FakeWorkerLauncher:
        def __init__(self) -> None:
            self.called_with: dict[str, str] | None = None

        async def launch(
            self,
            *,
            session_id: str,
            room_name: str,
            opening_question: str,
            worker_token: str,
            jd_id: str,
        ) -> FakeDispatchResponse:
            self.called_with = {
                "session_id": session_id,
                "room_name": room_name,
                "opening_question": opening_question,
                "worker_token": worker_token,
                "jd_id": jd_id,
            }
            return FakeDispatchResponse()

    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    launcher = FakeWorkerLauncher()
    service = InterviewSessionService(db_session, worker_launcher=launcher)

    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    assert launcher.called_with is not None
    assert launcher.called_with["session_id"] == published.session_id
    assert launcher.called_with["room_name"] == published.room_name
    assert launcher.called_with["opening_question"] == "Bạn hãy giới thiệu ngắn về bản thân."
    assert launcher.called_with["worker_token"]
    detail = await service.get_session_detail(published.session_id)
    assert detail.worker_status == "queued"
