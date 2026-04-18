import { render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { FeedbackLoopSummary } from "@/components/jd/cv-screening-detail/feedback-loop-summary"
import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"

afterEach(() => {
  vi.restoreAllMocks()
})

function buildInterviewDetail(): InterviewSessionDetailResponse {
  return {
    session_id: "session-1",
    status: "completed",
    worker_status: "idle",
    provider_status: "gemini_live",
    livekit_room_name: "room-1",
    opening_question: "Intro",
    approved_questions: [],
    manual_questions: [],
    question_guidance: null,
    plan: {
      session_goal: { vi: "Danh gia", en: "Evaluate" },
      opening_script: { vi: "Xin chao", en: "Hello" },
      policy_version: 3,
      interview_decision_status: "adjust",
      policy_summary: {
        source_feedback_count: 2,
        top_overrated_competencies: [],
        top_underrated_competencies: [],
        top_failure_reasons: [],
        expected_effects: [
          "Must-have dimension lacks supporting evidence.",
          "Must-have dimension lacks supporting evidence.",
        ],
        recommendation_agreement_rate: 0.5,
      },
      active_policy: {
        global_thresholds: {
          generic_answer_min_length: 20,
          generic_answer_evidence_threshold: 0.45,
          strong_evidence_threshold: 0.55,
          wrap_up_confidence_threshold: 0.91,
          escalate_after_consecutive_adjustments: 2,
          max_clarification_turns_per_competency: 2,
          measurable_signal_bonus: 0.05,
          example_signal_bonus: 0.05,
          semantic_default_confidence_threshold: 0.6,
          semantic_move_on_confidence_threshold: 0.72,
          semantic_recovery_confidence_threshold: 0.68,
        },
        competency_overrides: [],
        questioning_rules: {},
        application_scope: {},
      },
      competencies: [],
      questions: [],
    },
    current_question_index: 0,
    total_questions: 1,
    recommendation: "advance",
    transcript_turns: [],
    runtime_events: [],
    last_error_code: null,
    last_error_message: null,
  }
}

test("does not emit duplicate key warnings when expected effects repeat", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

  render(
    <FeedbackLoopSummary
      interviewDetail={buildInterviewDetail()}
      interviewFeedback={null}
      feedbackSummary={{
        jd_id: "jd-1",
        feedback_count: 2,
        agreement_rate: 0.5,
        recommendation_agreement_rate: 0.5,
        average_score_delta: 0.1,
        competency_deltas: [],
        judgement_breakdown: [],
        failure_reasons: [],
        disagreement_sessions: [],
        policy_audit_trail: [],
      }}
      feedbackPolicy={null}
    />,
  )

  expect(screen.getAllByText("Must-have dimension lacks supporting evidence.")).toHaveLength(2)

  const duplicateKeyWarnings = consoleError.mock.calls.filter((call) =>
    call
      .map((arg) => String(arg))
      .join(" ")
      .includes("Encountered two children with the same key"),
  )

  expect(duplicateKeyWarnings).toHaveLength(0)
})
