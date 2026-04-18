import { render } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { FeedbackLoopSummary } from "@/components/jd/cv-screening-detail/feedback-loop-summary"

afterEach(() => {
  vi.restoreAllMocks()
})

test("feedback loop summary renders duplicate policy strings without duplicate-key warnings", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

  render(
    <FeedbackLoopSummary
      interviewDetail={{
        session_id: "session-1",
        status: "completed",
        worker_status: "completed",
        provider_status: "completed",
        livekit_room_name: "room-1",
        opening_question: "Intro",
        approved_questions: [],
        manual_questions: [],
        question_guidance: null,
        current_question_index: 0,
        total_questions: 1,
        recommendation: "review",
        transcript_turns: [],
        runtime_events: [],
        last_error_code: null,
        last_error_message: null,
        plan: {
          session_goal: { vi: "Mục tiêu", en: "Goal" },
          opening_script: { vi: "Mở đầu", en: "Opening" },
          questions: [],
          policy_version: 2,
          interview_decision_status: "adjust",
          policy_summary: {
            source_feedback_count: 2,
            top_overrated_competencies: [],
            top_underrated_competencies: [],
            top_failure_reasons: [],
            expected_effects: [
              "Tăng trọng số cho tín hiệu đo lường.",
              "Tăng trọng số cho tín hiệu đo lường.",
            ],
          },
          active_policy: {
            global_thresholds: {
              generic_answer_min_length: 10,
              generic_answer_evidence_threshold: 0.4,
              strong_evidence_threshold: 0.8,
              wrap_up_confidence_threshold: 0.8,
              escalate_after_consecutive_adjustments: 2,
              max_clarification_turns_per_competency: 2,
              measurable_signal_bonus: 0.1,
              example_signal_bonus: 0.1,
              semantic_default_confidence_threshold: 0.5,
              semantic_move_on_confidence_threshold: 0.7,
              semantic_recovery_confidence_threshold: 0.4,
            },
            competency_overrides: [],
            questioning_rules: {},
            application_scope: {},
          },
          competencies: [
            {
              name: { vi: "Phân tích nghiệp vụ", en: "Business analysis" },
              priority: 1,
              target_question_count: 2,
              current_coverage: 0,
              evidence_needed: [
                {
                  vi: "Tín hiệu này previously showed AI-HR disagreement",
                  en: "This signal previously showed AI-HR disagreement",
                },
                {
                  vi: "Tín hiệu này previously showed AI-HR disagreement",
                  en: "This signal previously showed AI-HR disagreement",
                },
              ],
            },
          ],
        },
      }}
      interviewFeedback={{
        session_id: "session-1",
        jd_id: "jd-1",
        overall_agreement_score: 0.5,
        ai_recommendation: "review",
        hr_recommendation: "review",
        recommendation_agreement: true,
        competencies: [],
        overall_notes: null,
        missing_evidence_notes: null,
        false_positive_notes: null,
        false_negative_notes: null,
        created_at: "2026-04-18T00:00:00Z",
        updated_at: "2026-04-18T00:00:00Z",
      }}
      feedbackSummary={{
        jd_id: "jd-1",
        feedback_count: 2,
        agreement_rate: 0.5,
        recommendation_agreement_rate: 0.5,
        average_score_delta: 0.2,
        competency_deltas: [],
        judgement_breakdown: [],
        failure_reasons: [],
        disagreement_sessions: [],
        policy_audit_trail: [],
      }}
      feedbackPolicy={null}
    />,
  )

  const duplicateKeyWarnings = consoleError.mock.calls.filter((call) =>
    call.some(
      (value) =>
        typeof value === "string" && value.includes("Encountered two children with the same key"),
    ),
  )

  expect(duplicateKeyWarnings).toHaveLength(0)
})
