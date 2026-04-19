import asyncio
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pytest import MonkeyPatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.background_job import BackgroundJob
from src.models.cv import CandidateDocument, CandidateProfile, CandidateScreening
from src.models.interview import InterviewSession
from src.models.jd import JDAnalysis, JDCompanyDocument, JDDocument
from src.schemas.interview import (
    CandidateJoinRequest,
    CompleteInterviewRequest,
    GenerateInterviewQuestionsRequest,
    InterviewRuntimeEventRequest,
    InterviewSemanticAnswerEvaluation,
    InterviewScopeConfig,
    ProposeInterviewScheduleRequest,
    PublishInterviewRequest,
    TranscriptTurnRequest,
    UpdateInterviewScheduleRequest,
)
from src.schemas.jd import BilingualText
from src.services.cv_screening_service import CVScreeningService
from src.services.interview_runtime_service import InterviewRuntimeService
from src.services.interview_session_service import InterviewSessionService
from src.services.interview_summary_service import InterviewSummaryService
from src.services.interview_worker_launcher import InterviewWorkerLauncher


class FakeDispatchResponse:
    accepted: bool = True
    status: str = "queued"


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
        _ = jd_id
        self.called_with = {
            "session_id": session_id,
            "room_name": room_name,
            "opening_question": opening_question,
            "worker_token": worker_token,
        }
        return FakeDispatchResponse()


class FakeSemanticAnswerEvaluator:
    def __init__(
        self,
        *,
        responses: list[InterviewSemanticAnswerEvaluation] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses: list[InterviewSemanticAnswerEvaluation] = list(responses or [])
        self._error: Exception | None = error
        self.calls: list[dict[str, object]] = []

    async def evaluate(
        self,
        *,
        plan_payload: Mapping[str, object],
        current_question: Mapping[str, object],
        current_competency: Mapping[str, object] | None,
        answer_text: str,
        recent_plan_events: Sequence[Mapping[str, object]],
        transcript_context: Sequence[Mapping[str, object]],
    ) -> InterviewSemanticAnswerEvaluation:
        self.calls.append(
            {
                "plan_payload": plan_payload,
                "current_question": current_question,
                "current_competency": current_competency,
                "answer_text": answer_text,
                "recent_plan_events": recent_plan_events,
                "transcript_context": transcript_context,
            }
        )
        if self._error is not None:
            raise self._error
        if not self._responses:
            raise AssertionError("No semantic evaluator response was configured")
        return self._responses.pop(0)


def require_object_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def require_object_list(value: object) -> list[object]:
    assert isinstance(value, list)
    return cast(list[object], value)


def build_service(
    db_session: AsyncSession,
    *,
    semantic_evaluator: FakeSemanticAnswerEvaluator | None = None,
) -> tuple[InterviewSessionService, FakeWorkerLauncher]:
    launcher = FakeWorkerLauncher()
    evaluator = semantic_evaluator or FakeSemanticAnswerEvaluator(error=RuntimeError("semantic disabled in test"))
    return (
        InterviewSessionService(
            db_session,
            worker_launcher=cast(InterviewWorkerLauncher, cast(object, launcher)),
            semantic_evaluator=evaluator,
        ),
        launcher,
    )


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
    assert len(published.share_link.rsplit("/", 1)[-1]) == 8
    assert "/interviews/join/" in published.share_link
    detail = await service.get_session_detail(published.session_id)
    assert detail.approved_questions == ["Bạn có thể giới thiệu ngắn về bản thân không?"]
    assert detail.plan is not None
    assert detail.plan.current_phase == "competency_validation"
    assert detail.plan.questions[0].source is not None
    assert detail.plan.plan_events[-1].event_type == "plan.started"
    assert any(event.event_type == "planning.published" for event in detail.runtime_events)


@pytest.mark.asyncio
async def test_publish_session_respects_hr_selected_scope(
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
            interview_scope=InterviewScopeConfig(
                preset="basic",
                enabled_competencies=["Communication"],
            ),
        )
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.interview_scope is not None
    assert detail.plan.interview_scope.enabled_competencies == ["Communication"]
    assert [item.name.en for item in detail.plan.competencies] == ["Communication"]


@pytest.mark.asyncio
async def test_publish_session_rebinds_generated_question_target_to_selected_scope(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    screening = await db_session.get(CandidateScreening, screening_id)
    assert screening is not None
    screening_payload = dict(screening.screening_payload)
    screening_payload["interview_draft"] = {
        "generated_questions": [
            {
                "question_text": "Bạn đã dùng Figma trong công việc như thế nào?",
                "source": "llm",
                "rationale": "Probe design tooling.",
                "target_competency": {"vi": "Figma", "en": "Figma"},
            }
        ]
    }
    screening.screening_payload = screening_payload
    await db_session.commit()

    service, _ = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn đã dùng Figma trong công việc như thế nào?"],
            interview_scope=InterviewScopeConfig(
                preset="basic",
                enabled_competencies=["Communication"],
            ),
        )
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert len(detail.plan.questions) == 1
    assert detail.plan.questions[0].target_competency is not None
    assert detail.plan.questions[0].target_competency.en == "Communication"
    assert detail.plan.questions[0].selection_reason is not None
    assert "scope" in detail.plan.questions[0].selection_reason.en.lower()


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
async def test_publish_session_creates_new_session_after_previous_session_starts_finishing(
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

    await service.complete_session(
        first.session_id,
        CompleteInterviewRequest(reason="agent_wrap_up"),
    )

    second = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Hãy chia sẻ về dự án gần nhất của bạn."],
        )
    )

    assert second.session_id != first.session_id
    assert second.share_link != first.share_link
    assert second.room_name != first.room_name


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
        _ = await service.update_schedule(
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
    interview_draft = require_object_dict(screening.screening_payload["interview_draft"])
    generated_questions = require_object_list(interview_draft["generated_questions"])
    first_generated_question = require_object_dict(generated_questions[0])
    assert interview_draft["manual_questions"] == ["Bạn đang tự hào nhất về dự án nào gần đây?"]
    assert interview_draft["question_guidance"] == "Tập trung vào backend và ownership"
    assert interview_draft["approved_questions"]
    assert generated_questions
    assert first_generated_question["source"] == "manual"

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
        _ = await service.publish_interview(
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
        _ = await service.resolve_join(
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
async def test_candidate_generic_answer_creates_contextual_clarification_question(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    approved_question = "Kể về lần gần nhất bạn tối ưu performance cho service backend."
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=[approved_question, "Bạn xử lý trade-off với team như thế nào?"],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em có làm backend.",
            provider_event_id="evt-contextual-clarification-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    clarification_question = next(
        question for question in detail.plan.questions if question.question_type == "clarification"
    )
    assert clarification_question.prompt.vi != (
        "Bạn có thể chia sẻ một ví dụ cụ thể hơn, bao gồm bối cảnh, hành động và kết quả không?"
    )
    assert approved_question in clarification_question.prompt.vi
    assert clarification_question.prompt.vi.startswith("Quay lại câu hỏi")


@pytest.mark.asyncio
async def test_candidate_answer_uses_current_question_competency_when_plan_index_is_stale(
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
            approved_questions=[
                "Bạn có thể chia sẻ ví dụ backend gần đây nhất không?",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    questions_payload = require_object_list(plan_payload.get("questions", []))
    competencies_payload = require_object_list(plan_payload.get("competencies", []))
    assert len(questions_payload) >= 2
    assert len(competencies_payload) >= 2

    first_question = dict(require_object_dict(questions_payload[0]))
    first_question["dimension_name"] = {"vi": "Kỹ thuật", "en": "Technical"}
    first_question["target_competency"] = {"vi": "Kỹ thuật", "en": "Technical"}
    questions_payload[0] = first_question

    second_question = dict(require_object_dict(questions_payload[1]))
    second_question["dimension_name"] = {"vi": "Giao tiếp", "en": "Communication"}
    second_question["target_competency"] = {"vi": "Giao tiếp", "en": "Communication"}
    questions_payload[1] = second_question

    plan_payload["questions"] = questions_payload
    plan_payload["current_competency_index"] = 0
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text=(
                "Khi có trade-off em trình bày bối cảnh, phương án, rủi ro và lý do chọn giải pháp. "
                "Ví dụ gần đây em phải giải thích vì sao ưu tiên độ ổn định thay vì thêm tính năng mới."
            ),
            provider_event_id="evt-communication-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 2
    assert detail.plan.plan_events[-1].affected_competency is not None
    assert detail.plan.plan_events[-1].affected_competency.en == "Communication"
    assert detail.plan.competencies[1].status == "covered"
    assert detail.plan.competencies[1].current_coverage > 0
    assert detail.plan.competencies[0].current_coverage == 0.0


@pytest.mark.asyncio
async def test_candidate_capability_gap_moves_on_to_next_competency_without_looping_clarification(
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
            approved_questions=[
                "Bạn đã dùng Figma trong công việc như thế nào?",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    plan_payload["current_competency_index"] = 0
    plan_payload["competencies"] = [
        {
            "name": {"vi": "Figma", "en": "Figma"},
            "priority": 1,
            "target_question_count": 1,
            "current_coverage": 0.0,
            "status": "in_progress",
            "evidence_collected_count": 0,
            "evidence_needed": [{"vi": "Cần ví dụ dùng Figma.", "en": "Need a Figma example."}],
            "stop_condition": {
                "vi": "Có ví dụ thực tế về cách dùng Figma.",
                "en": "Has a real example of using Figma.",
            },
        },
        {
            "name": {"vi": "Giao tiếp", "en": "Communication"},
            "priority": 2,
            "target_question_count": 1,
            "current_coverage": 0.0,
            "status": "not_started",
            "evidence_collected_count": 0,
            "evidence_needed": [{"vi": "Cần ví dụ giao tiếp.", "en": "Need a communication example."}],
            "stop_condition": {
                "vi": "Có ví dụ phối hợp với team.",
                "en": "Has a collaboration example.",
            },
        },
    ]
    plan_payload["questions"] = [
        {
            "question_index": 0,
            "dimension_name": {"vi": "Figma", "en": "Figma"},
            "prompt": {
                "vi": "Bạn đã dùng Figma trong công việc như thế nào?",
                "en": "How have you used Figma in your work?",
            },
            "purpose": {
                "vi": "Xác minh mức độ quen thuộc với Figma.",
                "en": "Validate familiarity with Figma.",
            },
            "source": "manual",
            "question_type": "manual",
            "rationale": "Check tool familiarity.",
            "priority": 1,
            "target_competency": {"vi": "Figma", "en": "Figma"},
            "evidence_gap": {
                "vi": "Chưa có bằng chứng về Figma.",
                "en": "No evidence about Figma yet.",
            },
            "selection_reason": {
                "vi": "HR muốn xác minh Figma trước.",
                "en": "HR wants to validate Figma first.",
            },
            "transition_on_strong_answer": "advance_to_next_competency",
            "transition_on_weak_answer": "ask_clarification",
        },
        {
            "question_index": 1,
            "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
            "prompt": {
                "vi": "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
                "en": "How do you communicate technical trade-offs when working with the team?",
            },
            "purpose": {
                "vi": "Xác minh năng lực giao tiếp.",
                "en": "Validate communication competency.",
            },
            "source": "manual",
            "question_type": "manual",
            "rationale": "Check communication competency.",
            "priority": 2,
            "target_competency": {"vi": "Giao tiếp", "en": "Communication"},
            "evidence_gap": {
                "vi": "Chưa có bằng chứng giao tiếp.",
                "en": "No communication evidence yet.",
            },
            "selection_reason": {
                "vi": "Chuyển sang competency tiếp theo nếu Figma không phù hợp.",
                "en": "Move to the next competency if Figma is not applicable.",
            },
            "transition_on_strong_answer": "advance_to_next_competency",
            "transition_on_weak_answer": "ask_clarification",
        },
    ]
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em chưa dùng Figma bao giờ nên không có ví dụ thực tế về công cụ này.",
            provider_event_id="evt-capability-gap",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 1
    assert detail.plan.competencies[0].status == "needs_recovery"
    assert detail.plan.competencies[1].status == "in_progress"
    assert len(detail.plan.questions) == 2
    adjusted_event = detail.plan.plan_events[-1]
    assert adjusted_event.chosen_action == "move_on_from_unresolved_competency"
    assert adjusted_event.decision_rule == "explicit_capability_gap_move_on"
    assert detail.plan.interview_decision_status == "adjust"
    assert detail.plan.next_intended_step is not None
    assert detail.plan.next_intended_step.en == "Move on to validate the next competency: Communication."


@pytest.mark.asyncio
async def test_repeated_low_signal_answers_move_on_after_clarification_is_exhausted(
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
            approved_questions=[
                "Bạn kể về một case backend gần đây nhất đi.",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    plan_payload["current_competency_index"] = 0
    plan_payload["competencies"] = [
        {
            "name": {"vi": "Backend", "en": "Backend"},
            "priority": 1,
            "target_question_count": 1,
            "current_coverage": 0.0,
            "status": "in_progress",
            "evidence_collected_count": 0,
            "evidence_needed": [{"vi": "Cần ví dụ backend.", "en": "Need a backend example."}],
            "stop_condition": {
                "vi": "Có ví dụ backend rõ ràng.",
                "en": "Has a clear backend example.",
            },
        },
        {
            "name": {"vi": "Giao tiếp", "en": "Communication"},
            "priority": 2,
            "target_question_count": 1,
            "current_coverage": 0.0,
            "status": "not_started",
            "evidence_collected_count": 0,
            "evidence_needed": [{"vi": "Cần ví dụ giao tiếp.", "en": "Need a communication example."}],
            "stop_condition": {
                "vi": "Có ví dụ phối hợp với team.",
                "en": "Has a collaboration example.",
            },
        },
    ]
    plan_payload["questions"] = [
        {
            "question_index": 0,
            "dimension_name": {"vi": "Backend", "en": "Backend"},
            "prompt": {
                "vi": "Bạn kể về một case backend gần đây nhất đi.",
                "en": "Tell me about a recent backend case.",
            },
            "purpose": {
                "vi": "Xác minh năng lực backend.",
                "en": "Validate backend competency.",
            },
            "source": "manual",
            "question_type": "manual",
            "rationale": "Check backend competency.",
            "priority": 1,
            "target_competency": {"vi": "Backend", "en": "Backend"},
            "evidence_gap": {
                "vi": "Chưa có bằng chứng backend.",
                "en": "No backend evidence yet.",
            },
            "selection_reason": {
                "vi": "Ưu tiên xác minh backend trước.",
                "en": "Validate backend first.",
            },
            "transition_on_strong_answer": "advance_to_next_competency",
            "transition_on_weak_answer": "ask_clarification",
        },
        {
            "question_index": 1,
            "dimension_name": {"vi": "Giao tiếp", "en": "Communication"},
            "prompt": {
                "vi": "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
                "en": "How do you communicate technical trade-offs when working with the team?",
            },
            "purpose": {
                "vi": "Xác minh năng lực giao tiếp.",
                "en": "Validate communication competency.",
            },
            "source": "manual",
            "question_type": "manual",
            "rationale": "Check communication competency.",
            "priority": 2,
            "target_competency": {"vi": "Giao tiếp", "en": "Communication"},
            "evidence_gap": {
                "vi": "Chưa có bằng chứng giao tiếp.",
                "en": "No communication evidence yet.",
            },
            "selection_reason": {
                "vi": "Chuyển sang competency tiếp theo nếu backend chưa đủ rõ.",
                "en": "Move to the next competency if backend stays unresolved.",
            },
            "transition_on_strong_answer": "advance_to_next_competency",
            "transition_on_weak_answer": "ask_clarification",
        },
    ]
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em cũng làm nhiều thứ backend thôi, chủ yếu support team.",
            provider_event_id="evt-low-signal-1",
            event_payload={},
        ),
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text="Nói chung em hỗ trợ mọi người và xử lý các việc phát sinh, cũng không nhớ rõ lắm.",
            provider_event_id="evt-low-signal-2",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 1
    assert detail.plan.competencies[0].status == "needs_recovery"
    assert detail.plan.competencies[1].status == "in_progress"
    move_on_event = detail.plan.plan_events[-1]
    assert move_on_event.chosen_action == "move_on_from_unresolved_competency"
    assert move_on_event.decision_rule == "low_signal_answer_after_clarification_move_on"
    assert len([event for event in detail.plan.plan_events if event.chosen_action == "ask_clarification"]) == 1


@pytest.mark.asyncio
async def test_policy_can_allow_an_extra_clarification_before_moving_on(
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
            approved_questions=[
                "Bạn kể về một case backend gần đây nhất đi.",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    plan_payload["active_policy"] = {
        "global_thresholds": {
            "generic_answer_min_length": 60,
            "generic_answer_evidence_threshold": 0.45,
            "strong_evidence_threshold": 0.55,
            "wrap_up_confidence_threshold": 0.91,
            "escalate_after_consecutive_adjustments": 3,
            "max_clarification_turns_per_competency": 2,
            "measurable_signal_bonus": 0.15,
            "example_signal_bonus": 0.12,
        },
        "competency_overrides": [],
        "questioning_rules": {},
        "application_scope": {"jd_id": "jd-1"},
    }
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em cũng làm nhiều thứ backend thôi, chủ yếu support team.",
            provider_event_id="evt-low-signal-policy-1",
            event_payload={},
        ),
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text="Nói chung em hỗ trợ mọi người và xử lý các việc phát sinh, cũng không nhớ rõ lắm.",
            provider_event_id="evt-low-signal-policy-2",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 0
    assert detail.plan.competencies[0].status == "in_progress"
    assert detail.plan.plan_events[-1].chosen_action == "ask_clarification"
    assert (
        len([event for event in detail.plan.plan_events if event.chosen_action == "ask_clarification"])
        == 2
    )


@pytest.mark.asyncio
async def test_semantic_evaluator_advances_on_concrete_answer_without_keyword_markers(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    semantic_evaluator = FakeSemanticAnswerEvaluator(
        responses=[
            InterviewSemanticAnswerEvaluation(
                answer_quality="strong",
                evidence_progress="improved",
                recommended_action="move_on",
                reason=BilingualText(
                    vi="Câu trả lời có ví dụ triển khai đủ rõ dù không dùng từ khóa đo lường.",
                    en="The answer gives a concrete implementation example even without measurable keywords.",
                ),
                confidence=0.88,
                needs_hr_review=False,
            )
        ]
    )
    service, _ = build_service(db_session, semantic_evaluator=semantic_evaluator)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=[
                "Bạn kể về một case backend gần đây nhất đi.",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text=(
                "Ở dự án checkout, em tách phần xử lý đơn hàng khỏi API chính, chuyển việc gửi email "
                "sang queue và theo dõi lỗi theo từng bước triển khai."
            ),
            provider_event_id="evt-semantic-strong-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 1
    assert detail.plan.competencies[0].status == "covered"
    assert detail.plan.plan_events[-1].chosen_action == "advance_to_next_competency"
    assert detail.plan.plan_events[-1].decision_rule == "semantic_answer_move_on"
    assert semantic_evaluator.calls


@pytest.mark.asyncio
async def test_semantic_evaluator_respects_move_on_confidence_threshold(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    semantic_evaluator = FakeSemanticAnswerEvaluator(
        responses=[
            InterviewSemanticAnswerEvaluation(
                answer_quality="off_topic",
                evidence_progress="unchanged",
                recommended_action="move_on",
                reason=BilingualText(
                    vi="Câu trả lời đang lệch khỏi competency hiện tại nhưng độ tin cậy chưa đủ cao để bỏ hẳn.",
                    en="The answer drifts away from the current competency but confidence is not high enough to abandon it.",
                ),
                confidence=0.58,
                needs_hr_review=False,
            )
        ]
    )
    service, _ = build_service(db_session, semantic_evaluator=semantic_evaluator)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn kể về một case backend gần đây nhất đi."],
        )
    )

    session = await db_session.get(InterviewSession, published.session_id)
    assert session is not None
    plan_payload = dict(session.plan_payload)
    plan_payload["active_policy"] = {
        "global_thresholds": {
            "generic_answer_min_length": 60,
            "generic_answer_evidence_threshold": 0.45,
            "strong_evidence_threshold": 0.55,
            "wrap_up_confidence_threshold": 0.91,
            "escalate_after_consecutive_adjustments": 2,
            "max_clarification_turns_per_competency": 1,
            "measurable_signal_bonus": 0.15,
            "example_signal_bonus": 0.12,
            "semantic_move_on_confidence_threshold": 0.72,
            "semantic_recovery_confidence_threshold": 0.68,
            "semantic_default_confidence_threshold": 0.6,
        },
        "competency_overrides": [],
        "questioning_rules": {},
        "application_scope": {"jd_id": "jd-1"},
    }
    session.plan_payload = plan_payload
    await db_session.commit()

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em cũng làm nhiều thứ backend thôi, chủ yếu support team.",
            provider_event_id="evt-semantic-low-confidence-move-on",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 0
    assert detail.plan.plan_events[-1].chosen_action == "ask_clarification"
    assert detail.plan.plan_events[-1].decision_rule == "generic_answer_needs_clarification"


@pytest.mark.asyncio
async def test_semantic_evaluator_detects_indirect_capability_gap_and_moves_on(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    semantic_evaluator = FakeSemanticAnswerEvaluator(
        responses=[
            InterviewSemanticAnswerEvaluation(
                answer_quality="explicit_gap",
                evidence_progress="unchanged",
                recommended_action="move_on",
                reason=BilingualText(
                    vi="Ứng viên mô tả đây là phần việc của designer nên chưa có bằng chứng trực tiếp cho competency này.",
                    en="The candidate describes this as the designer's area, so there is no direct evidence for this competency.",
                ),
                confidence=0.84,
                needs_hr_review=False,
            )
        ]
    )
    service, _ = build_service(db_session, semantic_evaluator=semantic_evaluator)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=[
                "Bạn đã dùng Figma trong công việc như thế nào?",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text=(
                "Phần đó bên designer đảm nhiệm, còn em chủ yếu nhận handoff và trao đổi requirement với team."
            ),
            provider_event_id="evt-semantic-indirect-gap",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 1
    assert detail.plan.competencies[0].status == "needs_recovery"
    assert detail.plan.plan_events[-1].chosen_action == "move_on_from_unresolved_competency"
    assert detail.plan.plan_events[-1].decision_rule == "semantic_answer_move_on"


@pytest.mark.asyncio
async def test_semantic_wrap_up_does_not_close_when_remaining_competencies_are_untouched(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    semantic_evaluator = FakeSemanticAnswerEvaluator(
        responses=[
            InterviewSemanticAnswerEvaluation(
                answer_quality="strong",
                evidence_progress="improved",
                recommended_action="wrap_up",
                reason=BilingualText(
                    vi="Câu trả lời hiện tại khá tốt.",
                    en="The current answer is strong.",
                ),
                confidence=0.96,
                needs_hr_review=False,
            )
        ]
    )
    service, _ = build_service(db_session, semantic_evaluator=semantic_evaluator)
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
                "Em trực tiếp triển khai rollout cho một service production và theo dõi kết quả sau release."
            ),
            provider_event_id="evt-semantic-wrap-up-too-early",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.interview_decision_status != "ready_to_wrap"
    assert detail.plan.current_competency_index == 1
    assert detail.plan.plan_events[-1].chosen_action == "advance_to_next_competency"
    assert detail.plan.plan_events[-1].decision_rule == "semantic_wrap_up_blocked_remaining_coverage"


@pytest.mark.asyncio
async def test_semantic_evaluator_falls_back_to_heuristics_when_model_errors(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    semantic_evaluator = FakeSemanticAnswerEvaluator(error=RuntimeError("Gemini timeout"))
    service, _ = build_service(db_session, semantic_evaluator=semantic_evaluator)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=[
                "Bạn đã dùng Figma trong công việc như thế nào?",
                "Khi phối hợp với team, bạn truyền đạt trade-off kỹ thuật như thế nào?",
            ],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Em chưa dùng Figma bao giờ nên không có ví dụ thực tế về công cụ này.",
            provider_event_id="evt-semantic-fallback",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.current_competency_index == 1
    assert detail.plan.plan_events[-1].chosen_action == "move_on_from_unresolved_competency"
    assert detail.plan.plan_events[-1].decision_rule == "explicit_capability_gap_move_on"


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
async def test_record_runtime_event_recovers_provider_disconnect_and_redispatches_worker(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, launcher = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )

    runtime_service = InterviewRuntimeService(
        db_session,
        worker_launcher=cast(InterviewWorkerLauncher, cast(object, launcher)),
    )
    await runtime_service.record_event(
        published.session_id,
        InterviewRuntimeEventRequest(
            event_type="worker.failed",
            event_source="worker",
            session_status="failed",
            worker_status="failed",
            provider_status="failed",
            payload={
                "message": "Gemini server indicates disconnection soon. Time left: 50s (go_away)",
            },
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "reconnecting"
    assert detail.worker_status == "queued"
    assert detail.provider_status == "provider_reconnecting"
    assert detail.last_disconnect_reason == "provider_disconnect"
    assert detail.disconnect_deadline_at is not None
    assert detail.last_error_code == "worker.failed"
    assert launcher.called_with is not None
    assert launcher.called_with["session_id"] == published.session_id
    assert any(event.event_type == "worker.redispatch_requested" for event in detail.runtime_events)


@pytest.mark.asyncio
async def test_record_runtime_event_keeps_nonrecoverable_worker_failure_failed(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, launcher = build_service(db_session)
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=["Bạn hãy giới thiệu ngắn về bản thân."],
        )
    )
    launcher.called_with = None

    runtime_service = InterviewRuntimeService(
        db_session,
        worker_launcher=cast(InterviewWorkerLauncher, cast(object, launcher)),
    )
    await runtime_service.record_event(
        published.session_id,
        InterviewRuntimeEventRequest(
            event_type="worker.failed",
            event_source="worker",
            session_status="failed",
            worker_status="failed",
            provider_status="failed",
            payload={"message": "worker crashed because configuration is invalid"},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "failed"
    assert detail.worker_status == "failed"
    assert detail.provider_status == "failed"
    assert launcher.called_with is None


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
    assert detail.plan.competencies[0].current_coverage == 1.0


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
    assert detail.plan.interview_decision_status == "adjust"
    assert detail.plan.competencies[0].status == "needs_recovery"
    recovery_event = next(event for event in detail.plan.plan_events if event.chosen_action == "ask_recovery")
    assert recovery_event.decision_rule == "recovery_signal_detected"
    assert recovery_event.next_question_type == "recovery"
    assert recovery_event.evidence_excerpt is not None


@pytest.mark.asyncio
async def test_candidate_inconsistent_answer_creates_contextual_recovery_question(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, _ = build_service(db_session)
    approved_question = "Hãy kể về lần bạn trực tiếp ownership một incident production phức tạp."
    published = await service.publish_interview(
        PublishInterviewRequest(
            screening_id=screening_id,
            approved_questions=[approved_question],
        )
    )

    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=1,
            transcript_text="Thực ra timeline dự án hơi mâu thuẫn vì em nói lead toàn bộ nhưng phần lớn chỉ review.",
            provider_event_id="evt-contextual-recovery-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    recovery_question = next(question for question in detail.plan.questions if question.question_type == "recovery")
    assert recovery_question.prompt.vi != (
        "Tôi muốn làm rõ lại timeline và vai trò của bạn trong ví dụ vừa nêu. Bạn có thể mô tả theo thứ tự thời gian và phần việc trực tiếp bạn chịu trách nhiệm không?"
    )
    assert approved_question in recovery_question.prompt.vi
    assert recovery_question.prompt.vi.startswith("Quay lại câu hỏi")


@pytest.mark.asyncio
async def test_recovery_follow_up_can_escalate_after_recovery_answer(
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
            provider_event_id="evt-recovery-answer-1",
            event_payload={},
        ),
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text=(
                "Timeline cũng chưa rõ lắm, có lúc em nói là tự làm chính nhưng thực tế chủ yếu là hỗ trợ và review."
            ),
            provider_event_id="evt-recovery-answer-2",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.interview_decision_status == "continue_with_hr_flag"


@pytest.mark.asyncio
async def test_runtime_state_hides_current_question_when_ready_to_wrap(
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
    competencies = require_object_list(plan_payload.get("competencies", []))
    for index, item in enumerate(competencies):
        if not isinstance(item, dict):
            continue
        updated = dict(require_object_dict(cast(object, item)))
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
            provider_event_id="evt-runtime-wrap-up-answer",
            event_payload={},
        ),
    )

    runtime_state = await service.get_runtime_state(published.session_id)
    assert runtime_state.interview_decision_status == "ready_to_wrap"
    assert runtime_state.current_question is None


@pytest.mark.asyncio
async def test_runtime_state_reports_company_knowledge_availability(
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

    runtime_state = await service.get_runtime_state(published.session_id)
    assert runtime_state.company_knowledge_available is False

    screening = await db_session.get(CandidateScreening, screening_id)
    assert screening is not None
    db_session.add(
        JDCompanyDocument(
            jd_document_id=screening.jd_document_id,
            file_name="company-handbook.pdf",
            mime_type="application/pdf",
            storage_path="/tmp/company-handbook.pdf",
            status="ready",
            chunk_count=3,
        )
    )
    await db_session.commit()

    runtime_state = await service.get_runtime_state(published.session_id)
    assert runtime_state.company_knowledge_available is True


@pytest.mark.asyncio
async def test_runtime_state_keeps_current_question_when_continuing_with_hr_flag(
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
            provider_event_id="evt-runtime-escalate-answer-1",
            event_payload={},
        ),
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text=(
                "Timeline cũng chưa rõ lắm, có lúc em nói là tự làm chính nhưng thực tế chủ yếu là hỗ trợ và review."
            ),
            provider_event_id="evt-runtime-escalate-answer-2",
            event_payload={},
        ),
    )

    runtime_state = await service.get_runtime_state(published.session_id)
    assert runtime_state.interview_decision_status == "continue_with_hr_flag"
    assert runtime_state.current_question is not None
    assert runtime_state.current_question.question_type == "recovery"


@pytest.mark.asyncio
async def test_summary_fallback_recommends_hr_review_for_continue_with_hr_flag(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
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
            provider_event_id="evt-summary-hr-flag-1",
            event_payload={},
        ),
    )
    await service.append_turn(
        session_id=published.session_id,
        payload=TranscriptTurnRequest(
            speaker="candidate",
            sequence_number=3,
            transcript_text=(
                "Timeline cũng chưa rõ lắm, có lúc em nói là tự làm chính nhưng thực tế chủ yếu là hỗ trợ và review."
            ),
            provider_event_id="evt-summary-hr-flag-2",
            event_payload={},
        ),
    )

    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="candidate_left"),
    )
    await service.run_summary_job(published.session_id)

    review = await service.get_session_review(published.session_id)
    assert review.summary_payload["decision_status"] == "continue_with_hr_flag"
    assert review.summary_payload["recommendation"] == "HR review is required before making the final decision."


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
    _ = await service.resolve_join(
        share_token,
        CandidateJoinRequest(candidate_name="Nguyen Van A"),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "waiting"
    assert detail.disconnect_deadline_at is None
    assert detail.last_disconnect_reason is None


@pytest.mark.asyncio
async def test_resolve_join_relaunches_worker_after_reconnect_state(
    db_session: AsyncSession,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key-1234567890")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret-1234567890-test-secret")
    screening_id = await seed_completed_screening(db_session)
    service, launcher = build_service(db_session)
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
    launcher.called_with = None

    share_token = published.share_link.rsplit("/", 1)[-1]
    _ = await service.resolve_join(
        share_token,
        CandidateJoinRequest(candidate_name="Nguyen Van A"),
    )

    assert launcher.called_with is not None
    assert launcher.called_with["session_id"] == published.session_id
    assert launcher.called_with["room_name"] == published.room_name


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
    competencies = require_object_list(plan_payload.get("competencies", []))
    for index, item in enumerate(competencies):
        if not isinstance(item, dict):
            continue
        updated = dict(require_object_dict(cast(object, item)))
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
async def test_last_unresolved_competency_does_not_wrap_up_with_low_coverage(
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
    competencies = require_object_list(plan_payload.get("competencies", []))
    for index, item in enumerate(competencies):
        if not isinstance(item, dict):
            continue
        updated = dict(require_object_dict(cast(object, item)))
        updated["status"] = "covered" if index < len(competencies) - 1 else "in_progress"
        updated["current_coverage"] = 1.0 if index < len(competencies) - 1 else 0.12
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
            transcript_text="Em chưa có kinh nghiệm thực tế ở phần này nên chưa thể đưa ví dụ cụ thể.",
            provider_event_id="evt-last-gap-answer",
            event_payload={},
        ),
    )

    detail = await service.get_session_detail(published.session_id)
    assert detail.plan is not None
    assert detail.plan.interview_decision_status == "adjust"
    assert detail.plan.current_phase == "deep_dive"
    assert detail.plan.next_intended_step is not None
    assert "Chưa đủ bằng chứng" in detail.plan.next_intended_step.vi
    assert detail.plan.plan_events[-1].chosen_action == "move_on_from_unresolved_competency"


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
            _ = plan_payload
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
        summary_generator=cast(InterviewSummaryService, cast(object, FakeSummaryGenerator())),
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
    service.livekit_service.delete_room = delete_room  # type: ignore[method-assign]

    await service.complete_session(
        published.session_id,
        CompleteInterviewRequest(reason="agent_wrap_up"),
    )
    await asyncio.sleep(0)

    detail = await service.get_session_detail(published.session_id)
    assert detail.status == "finishing"
    assert detail.worker_status == "summarizing"
    assert detail.provider_status == "closing"
    delete_room.assert_awaited_once_with(published.room_name)

    share_token = published.share_link.rsplit("/", 1)[-1]
    with pytest.raises(ValueError, match="Interview session not found"):
        _ = await service.resolve_join(
            share_token,
            CandidateJoinRequest(candidate_name="Nguyen Van A"),
        )


@pytest.mark.asyncio
async def test_complete_session_does_not_wait_for_room_deletion(
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
    deletion_started = asyncio.Event()
    allow_deletion_to_finish = asyncio.Event()

    async def delete_room(room_name: str) -> None:
        assert room_name == published.room_name
        deletion_started.set()
        _ = await allow_deletion_to_finish.wait()

    service.livekit_service.delete_room = delete_room  # type: ignore[method-assign]

    await asyncio.wait_for(
        service.complete_session(
            published.session_id,
            CompleteInterviewRequest(reason="agent_wrap_up"),
        ),
        timeout=0.05,
    )
    _ = await asyncio.wait_for(deletion_started.wait(), timeout=0.05)

    allow_deletion_to_finish.set()
    await asyncio.sleep(0)


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
        accepted: bool = True
        status: str = "queued"

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
    service = InterviewSessionService(
        db_session,
        worker_launcher=cast(InterviewWorkerLauncher, cast(object, launcher)),
    )

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
