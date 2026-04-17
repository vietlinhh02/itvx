export type InterviewQuestion = {
  question_index: number
  dimension_name: { vi: string; en: string }
  prompt: { vi: string; en: string }
  purpose: { vi: string; en: string }
  source?: string | null
  question_type?: string | null
  rationale?: string | null
  priority?: number
  target_competency?: { vi: string; en: string } | null
  evidence_gap?: { vi: string; en: string } | null
  selection_reason?: { vi: string; en: string } | null
  transition_on_strong_answer?: string | null
  transition_on_weak_answer?: string | null
}

export type InterviewQuestionCandidate = {
  question_text: string
  source: string
  rationale: string | null
  question_type?: string | null
  target_competency?: { vi: string; en: string } | null
  selection_reason?: { vi: string; en: string } | null
  priority?: number
  evidence_gap?: { vi: string; en: string } | null
}

export type GenerateInterviewQuestionsRequest = {
  screening_id: string
  manual_questions: string[]
  question_guidance: string | null
}

export type GenerateInterviewQuestionsResponse = {
  screening_id: string
  manual_questions: string[]
  question_guidance: string | null
  generated_questions: InterviewQuestionCandidate[]
}

export type PublishInterviewRequest = {
  screening_id: string
  approved_questions: string[]
  manual_questions: string[]
  question_guidance: string | null
}

export type InterviewSchedule = {
  scheduled_start_at: string | null
  schedule_timezone: string | null
  schedule_status: string
  schedule_note: string | null
  candidate_proposed_start_at: string | null
  candidate_proposed_note: string | null
}

export type PublishInterviewResponse = {
  session_id: string
  share_link: string
  room_name: string
  status: string
  schedule: InterviewSchedule
}

export type InterviewSessionCreateResponse = {
  session_id: string
  share_link?: string
  room_name?: string
  status: string
}

export type CandidateJoinResponse = {
  session_id: string
  room_name: string
  participant_token: string
  candidate_identity: string
  schedule?: InterviewSchedule
}

export type CandidateJoinRequest = {
  candidate_name: string
}

export type InterviewRuntimeEvent = {
  event_type: string
  event_source: string
  session_status: string | null
  worker_status: string | null
  provider_status: string | null
  payload: Record<string, unknown>
}

export type TranscriptTurn = {
  speaker: string
  sequence_number: number
  transcript_text: string
  provider_event_id: string | null
  event_payload: Record<string, unknown>
}

export type InterviewCompetencyPlan = {
  name: { vi: string; en: string }
  priority: number
  target_question_count: number
  current_coverage: number
  status?: "not_started" | "in_progress" | "covered" | "needs_recovery" | null
  evidence_collected_count?: number
  evidence_needed: Array<{ vi: string; en: string }>
  stop_condition?: { vi: string; en: string } | null
  last_updated_at?: string | null
}

export type InterviewPlanEvent = {
  event_type: string
  reason: { vi: string; en: string }
  chosen_action: string
  affected_competency?: { vi: string; en: string } | null
  confidence?: number | null
  question_index?: number | null
  evidence_excerpt?: { vi: string; en: string } | null
  decision_rule?: string | null
  next_question_type?: string | null
  created_at: string
}

export type InterviewPolicyThresholds = {
  generic_answer_min_length: number
  generic_answer_evidence_threshold: number
  strong_evidence_threshold: number
  wrap_up_confidence_threshold: number
  escalate_after_consecutive_adjustments: number
  measurable_signal_bonus: number
  example_signal_bonus: number
}

export type InterviewCompetencyPolicyOverride = {
  competency_name: { vi: string; en: string }
  coverage_target_multiplier: number
  clarification_bias: number
  escalation_bias: number
  priority_boost: number
  preferred_question_types: string[]
  require_measurable_outcome: boolean
  adjustment_reason?: string | null
}

export type InterviewPolicySummaryPayload = {
  source_feedback_count: number
  top_overrated_competencies: string[]
  top_underrated_competencies: string[]
  top_failure_reasons: string[]
  expected_effects: string[]
  recommendation_agreement_rate?: number | null
}

export type InterviewFeedbackPolicyPayload = {
  global_thresholds: InterviewPolicyThresholds
  competency_overrides: InterviewCompetencyPolicyOverride[]
  questioning_rules: Record<string, boolean>
  application_scope: Record<string, string>
}

export type InterviewPlan = {
  session_goal: { vi: string; en: string }
  opening_script: { vi: string; en: string }
  overall_strategy?: { vi: string; en: string } | null
  current_phase?: string | null
  current_competency_index?: number
  next_intended_step?: { vi: string; en: string } | null
  interview_decision_status?: "continue" | "adjust" | "ready_to_wrap" | "escalate_hr" | null
  question_selection_policy?: { vi: string; en: string } | null
  transition_rules?: Array<{ vi: string; en: string }>
  completion_criteria?: Array<{ vi: string; en: string }>
  competencies?: InterviewCompetencyPlan[]
  plan_events?: InterviewPlanEvent[]
  policy_version?: number | null
  policy_summary?: InterviewPolicySummaryPayload | null
  active_policy?: InterviewFeedbackPolicyPayload | null
  questions: InterviewQuestion[]
}

export type InterviewSessionDetailResponse = {
  session_id: string
  status: string
  worker_status: string
  provider_status: string
  livekit_room_name: string
  opening_question: string
  approved_questions: string[]
  manual_questions: string[]
  question_guidance: string | null
  plan: InterviewPlan | null
  current_question_index: number
  total_questions: number
  recommendation: string | null
  schedule?: InterviewSchedule
  disconnect_deadline_at?: string | null
  last_disconnect_reason?: string | null
  last_error_code: string | null
  last_error_message: string | null
  transcript_turns: TranscriptTurn[]
  runtime_events: InterviewRuntimeEvent[]
}

export type UpdateInterviewScheduleRequest = {
  scheduled_start_at: string | null
  schedule_timezone: string | null
  schedule_note: string | null
  confirm_candidate_proposal?: boolean
}

export type ProposeInterviewScheduleRequest = {
  proposed_start_at: string
  note: string | null
  timezone: string | null
}

export type InterviewSessionCompetencyAssessment = {
  competency_name: { vi: string; en: string }
  ai_score?: number | null
  evidence_strength?: number | null
  needs_hr_review: boolean
  notes?: string | null
}

export type InterviewFeedbackCompetencyInput = {
  competency_name: { vi: string; en: string }
  hr_score?: number | null
  judgement: string
  missing_evidence?: string | null
  notes?: string | null
}

export type InterviewFeedbackRequest = {
  overall_agreement_score: number
  hr_recommendation?: string | null
  overall_notes?: string | null
  missing_evidence_notes?: string | null
  false_positive_notes?: string | null
  false_negative_notes?: string | null
  competencies: InterviewFeedbackCompetencyInput[]
}

export type InterviewFeedbackCompetencyResponse = {
  competency_name: { vi: string; en: string }
  ai_score?: number | null
  hr_score?: number | null
  delta?: number | null
  judgement: string
  missing_evidence?: string | null
  notes?: string | null
}

export type InterviewFeedbackResponse = {
  session_id: string
  jd_id: string
  submitted_by_user_id?: string | null
  submitted_by_email?: string | null
  overall_agreement_score: number
  ai_recommendation?: string | null
  hr_recommendation?: string | null
  recommendation_agreement: boolean
  overall_notes?: string | null
  missing_evidence_notes?: string | null
  false_positive_notes?: string | null
  false_negative_notes?: string | null
  competencies: InterviewFeedbackCompetencyResponse[]
  created_at: string
  updated_at: string
}

export type InterviewFeedbackMetricItem = {
  label: string
  value: number
}

export type InterviewFeedbackFailureReason = {
  reason: string
  count: number
}

export type InterviewFeedbackSessionDisagreementItem = {
  session_id: string
  candidate_name?: string | null
  overall_agreement_score: number
  recommendation_agreement: boolean
  delta_magnitude: number
  created_at: string
}

export type InterviewFeedbackMemoryResponse = {
  memory_id: string
  jd_id: string
  session_id?: string | null
  feedback_record_id?: string | null
  memory_type: string
  title: string
  memory_text: string
  importance_score: number
  source_event_at?: string | null
  payload: Record<string, unknown>
  created_at: string
}

export type InterviewFeedbackPolicyAuditResponse = {
  event_type: string
  payload: Record<string, unknown>
  created_at: string
}

export type InterviewFeedbackPolicyResponse = {
  policy_id: string
  jd_id: string
  status: string
  version: number
  source_feedback_count: number
  policy_payload: InterviewFeedbackPolicyPayload
  summary_payload: InterviewPolicySummaryPayload
  approved_by_user_id?: string | null
  approved_by_email?: string | null
  approved_at?: string | null
  created_at: string
  updated_at: string
}

export type SuggestInterviewFeedbackPolicyResponse = {
  policy: InterviewFeedbackPolicyResponse
  audit_event: InterviewFeedbackPolicyAuditResponse
}

export type InterviewFeedbackPolicyCollectionResponse = {
  jd_id: string
  active_policy?: InterviewFeedbackPolicyResponse | null
  latest_suggested_policy?: InterviewFeedbackPolicyResponse | null
  memory_context: InterviewFeedbackMemoryResponse[]
  policy_audit_trail: InterviewFeedbackPolicyAuditResponse[]
}

export type InterviewFeedbackSummaryResponse = {
  jd_id: string
  feedback_count: number
  agreement_rate: number
  recommendation_agreement_rate: number
  average_score_delta: number
  competency_deltas: InterviewFeedbackMetricItem[]
  judgement_breakdown: InterviewFeedbackMetricItem[]
  failure_reasons: InterviewFeedbackFailureReason[]
  disagreement_sessions: InterviewFeedbackSessionDisagreementItem[]
  active_policy?: InterviewFeedbackPolicyResponse | null
  latest_suggested_policy?: InterviewFeedbackPolicyResponse | null
  policy_audit_trail: InterviewFeedbackPolicyAuditResponse[]
}

export type InterviewSessionReviewResponse = {
  session_id: string
  status: string
  summary_payload: Record<string, unknown>
  transcript_turns: TranscriptTurn[]
  ai_competency_assessments: InterviewSessionCompetencyAssessment[]
}

export type CompanyKnowledgeDocument = {
  document_id: string
  jd_id: string
  file_name: string
  status: string
  chunk_count: number
  error_message: string | null
  created_at: string
}

export type CompanyKnowledgeDocumentListResponse = {
  items: CompanyKnowledgeDocument[]
}

export type CompanyKnowledgeDocumentUploadResponse = {
  job_id: string
  document: CompanyKnowledgeDocument
}
