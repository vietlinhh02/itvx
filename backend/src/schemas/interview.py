from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.jd import BilingualText


class InterviewQuestion(BaseModel):
    question_index: int = Field(ge=0)
    dimension_name: BilingualText
    prompt: BilingualText
    purpose: BilingualText
    source: str | None = None
    question_type: str | None = None
    rationale: str | None = None
    priority: int = Field(default=1, ge=1)
    target_competency: BilingualText | None = None
    evidence_gap: BilingualText | None = None
    selection_reason: BilingualText | None = None
    transition_on_strong_answer: str | None = None
    transition_on_weak_answer: str | None = None


class InterviewCompetencyPlan(BaseModel):
    name: BilingualText
    priority: int = Field(ge=1)
    target_question_count: int = Field(ge=1)
    current_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    status: str = Field(default="not_started", min_length=1)
    evidence_collected_count: int = Field(default=0, ge=0)
    evidence_needed: list[BilingualText] = Field(default_factory=list)
    stop_condition: BilingualText | None = None
    last_updated_at: str | None = None


class InterviewSemanticAnswerEvaluation(BaseModel):
    answer_quality: Literal[
        "strong",
        "partial",
        "low_signal",
        "off_topic",
        "explicit_gap",
        "inconsistent",
    ]
    evidence_progress: Literal["improved", "unchanged", "regressed"]
    recommended_action: Literal["continue", "clarify", "move_on", "recovery", "wrap_up"]
    reason: BilingualText
    confidence: float = Field(ge=0.0, le=1.0)
    needs_hr_review: bool = False


class InterviewPlanEvent(BaseModel):
    event_type: str = Field(min_length=1)
    reason: BilingualText
    chosen_action: str = Field(min_length=1)
    affected_competency: BilingualText | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    question_index: int | None = Field(default=None, ge=0)
    evidence_excerpt: BilingualText | None = None
    decision_rule: str | None = None
    next_question_type: str | None = None
    semantic_evaluation: InterviewSemanticAnswerEvaluation | None = None
    created_at: str


class InterviewPolicyThresholds(BaseModel):
    generic_answer_min_length: int = Field(default=60, ge=1)
    generic_answer_evidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    strong_evidence_threshold: float = Field(default=0.55, ge=0.0, le=1.0)
    wrap_up_confidence_threshold: float = Field(default=0.91, ge=0.0, le=1.0)
    escalate_after_consecutive_adjustments: int = Field(default=2, ge=1)
    max_clarification_turns_per_competency: int = Field(default=1, ge=0)
    measurable_signal_bonus: float = Field(default=0.15, ge=0.0, le=1.0)
    example_signal_bonus: float = Field(default=0.12, ge=0.0, le=1.0)
    semantic_default_confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    semantic_move_on_confidence_threshold: float = Field(default=0.72, ge=0.0, le=1.0)
    semantic_recovery_confidence_threshold: float = Field(default=0.68, ge=0.0, le=1.0)


class InterviewCompetencyPolicyOverride(BaseModel):
    competency_name: BilingualText
    coverage_target_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    clarification_bias: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_bias: float = Field(default=0.0, ge=0.0, le=1.0)
    priority_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    preferred_question_types: list[str] = Field(default_factory=list)
    require_measurable_outcome: bool = False
    adjustment_reason: str | None = None


class InterviewFeedbackPolicyPayload(BaseModel):
    global_thresholds: InterviewPolicyThresholds = Field(default_factory=InterviewPolicyThresholds)
    competency_overrides: list[InterviewCompetencyPolicyOverride] = Field(default_factory=list)
    questioning_rules: dict[str, bool] = Field(default_factory=dict)
    application_scope: dict[str, str] = Field(default_factory=dict)


class InterviewPolicySummaryPayload(BaseModel):
    source_feedback_count: int = Field(default=0, ge=0)
    top_overrated_competencies: list[str] = Field(default_factory=list)
    top_underrated_competencies: list[str] = Field(default_factory=list)
    top_failure_reasons: list[str] = Field(default_factory=list)
    expected_effects: list[str] = Field(default_factory=list)
    recommendation_agreement_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class InterviewPlanPayload(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    session_goal: BilingualText
    opening_script: BilingualText
    overall_strategy: BilingualText | None = None
    current_phase: str | None = None
    current_competency_index: int = Field(default=0, ge=0)
    next_intended_step: BilingualText | None = None
    interview_decision_status: str | None = None
    question_selection_policy: BilingualText | None = None
    transition_rules: list[BilingualText] = Field(default_factory=list)
    completion_criteria: list[BilingualText] = Field(default_factory=list)
    competencies: list[InterviewCompetencyPlan] = Field(default_factory=list)
    plan_events: list[InterviewPlanEvent] = Field(default_factory=list)
    policy_version: int | None = Field(default=None, ge=1)
    policy_summary: InterviewPolicySummaryPayload | None = None
    active_policy: InterviewFeedbackPolicyPayload | None = None
    questions: list[InterviewQuestion]


class InterviewQuestionCandidate(BaseModel):
    question_text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    rationale: str | None = None
    question_type: str | None = None
    target_competency: BilingualText | None = None
    selection_reason: BilingualText | None = None
    priority: int = Field(default=1, ge=1)
    evidence_gap: BilingualText | None = None


class GenerateInterviewQuestionsRequest(BaseModel):
    screening_id: str
    manual_questions: list[str] = Field(default_factory=list)
    question_guidance: str | None = None


class GenerateInterviewQuestionsResponse(BaseModel):
    screening_id: str
    manual_questions: list[str] = Field(default_factory=list)
    question_guidance: str | None = None
    generated_questions: list[InterviewQuestionCandidate]


class PublishInterviewRequest(BaseModel):
    screening_id: str
    approved_questions: list[str] = Field(min_length=1)
    manual_questions: list[str] = Field(default_factory=list)
    question_guidance: str | None = None


class InterviewSchedulePayload(BaseModel):
    scheduled_start_at: str | None = None
    schedule_timezone: str | None = None
    schedule_status: str = "unscheduled"
    schedule_note: str | None = None
    candidate_proposed_start_at: str | None = None
    candidate_proposed_note: str | None = None


class UpdateInterviewScheduleRequest(BaseModel):
    scheduled_start_at: str | None = None
    schedule_timezone: str | None = None
    schedule_note: str | None = None
    confirm_candidate_proposal: bool = False


class ProposeInterviewScheduleRequest(BaseModel):
    proposed_start_at: str
    note: str | None = None
    timezone: str | None = None


class PublishInterviewResponse(BaseModel):
    session_id: str
    share_link: str
    room_name: str
    status: str
    schedule: InterviewSchedulePayload = Field(default_factory=InterviewSchedulePayload)


class CandidateJoinPreviewResponse(BaseModel):
    session_id: str
    status: str
    schedule: InterviewSchedulePayload = Field(default_factory=InterviewSchedulePayload)


class CandidateJoinResponse(BaseModel):
    session_id: str
    room_name: str
    participant_token: str
    candidate_identity: str
    schedule: InterviewSchedulePayload = Field(default_factory=InterviewSchedulePayload)


class CandidateJoinRequest(BaseModel):
    candidate_name: str = Field(min_length=1, max_length=120)


class CompleteInterviewRequest(BaseModel):
    reason: str = Field(min_length=1)


class TranscriptTurnRequest(BaseModel):
    speaker: str
    sequence_number: int = Field(ge=0)
    transcript_text: str = Field(min_length=1)
    provider_event_id: str | None = None
    event_payload: dict[str, object] = Field(default_factory=dict)


class InterviewRuntimeEventRequest(BaseModel):
    event_type: str = Field(min_length=1)
    event_source: str = Field(min_length=1)
    session_status: str | None = None
    worker_status: str | None = None
    provider_status: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class InterviewRuntimeEventResponse(BaseModel):
    event_type: str
    event_source: str
    session_status: str | None
    worker_status: str | None
    provider_status: str | None
    payload: dict[str, object]


class TranscriptTurnResponse(BaseModel):
    speaker: str
    sequence_number: int
    transcript_text: str
    provider_event_id: str | None
    event_payload: dict[str, object]


class InterviewSessionDetailResponse(BaseModel):
    session_id: str
    status: str
    worker_status: str
    provider_status: str
    livekit_room_name: str
    opening_question: str
    approved_questions: list[str] = Field(default_factory=list)
    manual_questions: list[str] = Field(default_factory=list)
    question_guidance: str | None = None
    plan: InterviewPlanPayload | None = None
    current_question_index: int = Field(default=0, ge=0)
    total_questions: int = Field(default=0, ge=0)
    recommendation: str | None = None
    schedule: InterviewSchedulePayload = Field(default_factory=InterviewSchedulePayload)
    disconnect_deadline_at: str | None = None
    last_disconnect_reason: str | None = None
    last_error_code: str | None
    last_error_message: str | None
    transcript_turns: list[TranscriptTurnResponse]
    runtime_events: list[InterviewRuntimeEventResponse]


class InterviewSessionRuntimeStateResponse(BaseModel):
    session_id: str
    status: str
    worker_status: str
    provider_status: str
    current_question_index: int = Field(default=0, ge=0)
    current_question: InterviewQuestion | None = None
    next_intended_step: BilingualText | None = None
    interview_decision_status: str | None = None
    needs_hr_review: bool = False
    current_phase: str | None = None
    last_plan_event: InterviewPlanEvent | None = None


class InterviewSessionCompetencyAssessment(BaseModel):
    competency_name: BilingualText
    ai_score: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence_strength: float | None = Field(default=None, ge=0.0, le=1.0)
    needs_hr_review: bool = False
    notes: str | None = None


class InterviewFeedbackCompetencyRequest(BaseModel):
    competency_name: BilingualText
    hr_score: float | None = Field(default=None, ge=0.0, le=1.0)
    judgement: str = Field(min_length=1)
    missing_evidence: str | None = None
    notes: str | None = None


class InterviewFeedbackRequest(BaseModel):
    overall_agreement_score: float = Field(ge=0.0, le=1.0)
    hr_recommendation: str | None = None
    overall_notes: str | None = None
    missing_evidence_notes: str | None = None
    false_positive_notes: str | None = None
    false_negative_notes: str | None = None
    competencies: list[InterviewFeedbackCompetencyRequest] = Field(default_factory=list)


class InterviewFeedbackCompetencyResponse(BaseModel):
    competency_name: BilingualText
    ai_score: float | None = Field(default=None, ge=0.0, le=1.0)
    hr_score: float | None = Field(default=None, ge=0.0, le=1.0)
    delta: float | None = None
    judgement: str
    missing_evidence: str | None = None
    notes: str | None = None


class InterviewFeedbackResponse(BaseModel):
    session_id: str
    jd_id: str
    submitted_by_user_id: str | None = None
    submitted_by_email: str | None = None
    overall_agreement_score: float = Field(ge=0.0, le=1.0)
    ai_recommendation: str | None = None
    hr_recommendation: str | None = None
    recommendation_agreement: bool
    overall_notes: str | None = None
    missing_evidence_notes: str | None = None
    false_positive_notes: str | None = None
    false_negative_notes: str | None = None
    competencies: list[InterviewFeedbackCompetencyResponse] = Field(default_factory=list)
    created_at: str
    updated_at: str


class InterviewFeedbackMetricItem(BaseModel):
    label: str
    value: float


class InterviewFeedbackFailureReason(BaseModel):
    reason: str
    count: int = Field(ge=0)


class InterviewFeedbackSessionDisagreementItem(BaseModel):
    session_id: str
    candidate_name: str | None = None
    overall_agreement_score: float = Field(ge=0.0, le=1.0)
    recommendation_agreement: bool
    delta_magnitude: float = Field(ge=0.0)
    created_at: str


class InterviewFeedbackMemoryResponse(BaseModel):
    memory_id: str
    jd_id: str
    session_id: str | None = None
    feedback_record_id: str | None = None
    memory_type: str
    title: str
    memory_text: str
    importance_score: float = Field(ge=0.0)
    source_event_at: str | None = None
    payload: dict[str, object]
    created_at: str


class InterviewFeedbackPolicyAuditResponse(BaseModel):
    event_type: str
    payload: dict[str, object]
    created_at: str


class InterviewFeedbackPolicyResponse(BaseModel):
    policy_id: str
    jd_id: str
    status: str
    version: int = Field(ge=1)
    source_feedback_count: int = Field(ge=0)
    policy_payload: InterviewFeedbackPolicyPayload
    summary_payload: InterviewPolicySummaryPayload
    approved_by_user_id: str | None = None
    approved_by_email: str | None = None
    approved_at: str | None = None
    created_at: str
    updated_at: str


class SuggestInterviewFeedbackPolicyResponse(BaseModel):
    policy: InterviewFeedbackPolicyResponse
    audit_event: InterviewFeedbackPolicyAuditResponse


class InterviewFeedbackPolicyCollectionResponse(BaseModel):
    jd_id: str
    active_policy: InterviewFeedbackPolicyResponse | None = None
    latest_suggested_policy: InterviewFeedbackPolicyResponse | None = None
    memory_context: list[InterviewFeedbackMemoryResponse] = Field(default_factory=list)
    policy_audit_trail: list[InterviewFeedbackPolicyAuditResponse] = Field(default_factory=list)


class InterviewFeedbackSummaryResponse(BaseModel):
    jd_id: str
    feedback_count: int = Field(ge=0)
    agreement_rate: float = Field(ge=0.0, le=1.0)
    recommendation_agreement_rate: float = Field(ge=0.0, le=1.0)
    average_score_delta: float = Field(ge=0.0)
    competency_deltas: list[InterviewFeedbackMetricItem] = Field(default_factory=list)
    judgement_breakdown: list[InterviewFeedbackMetricItem] = Field(default_factory=list)
    failure_reasons: list[InterviewFeedbackFailureReason] = Field(default_factory=list)
    disagreement_sessions: list[InterviewFeedbackSessionDisagreementItem] = Field(default_factory=list)
    active_policy: InterviewFeedbackPolicyResponse | None = None
    latest_suggested_policy: InterviewFeedbackPolicyResponse | None = None
    policy_audit_trail: list[InterviewFeedbackPolicyAuditResponse] = Field(default_factory=list)


class InterviewSessionReviewResponse(BaseModel):
    session_id: str
    status: str
    summary_payload: dict[str, Any]
    transcript_turns: list[TranscriptTurnResponse]
    ai_competency_assessments: list[InterviewSessionCompetencyAssessment] = Field(default_factory=list)
