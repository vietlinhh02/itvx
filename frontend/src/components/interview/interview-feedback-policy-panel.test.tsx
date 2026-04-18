import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { InterviewFeedbackPolicyPanel } from "@/components/interview/interview-feedback-policy-panel"

afterEach(() => {
  vi.restoreAllMocks()
})

test("renders repeated policy summary items without duplicate key warnings", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

  render(
    <InterviewFeedbackPolicyPanel
      jdId="jd-1"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      initialData={{
        jd_id: "jd-1",
        active_policy: {
          policy_id: "policy-1",
          jd_id: "jd-1",
          status: "active",
          version: 1,
          source_feedback_count: 2,
          policy_payload: {
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
          summary_payload: {
            source_feedback_count: 2,
            top_overrated_competencies: ["Communication gap", "Communication gap"],
            top_underrated_competencies: [],
            top_failure_reasons: [],
            expected_effects: [
              "Must-have dimension lacks supporting evidence.",
              "Must-have dimension lacks supporting evidence.",
            ],
            recommendation_agreement_rate: 0.5,
          },
          approved_by_user_id: null,
          approved_by_email: null,
          approved_at: null,
          created_at: "2026-04-20T09:00:00+07:00",
          updated_at: "2026-04-20T09:00:00+07:00",
        },
        latest_suggested_policy: null,
        memory_context: [],
        policy_audit_trail: [],
      }}
      interviewDetail={null}
    />,
  )

  expect(screen.getAllByText("Communication gap")).toHaveLength(2)
  expect(screen.getAllByText("Must-have dimension lacks supporting evidence.")).toHaveLength(2)

  const duplicateKeyWarnings = consoleError.mock.calls.filter((call) =>
    call
      .map((arg) => String(arg))
      .join(" ")
      .includes("Encountered two children with the same key"),
  )

  expect(duplicateKeyWarnings).toHaveLength(0)
})

test("explains why memory context is empty before HR feedback creates memories", () => {
  render(
    <InterviewFeedbackPolicyPanel
      jdId="jd-1"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      initialData={{
        jd_id: "jd-1",
        active_policy: null,
        latest_suggested_policy: null,
        memory_context: [],
        policy_audit_trail: [],
      }}
      interviewDetail={null}
    />,
  )

  expect(
    screen.getByText("Memory context sẽ xuất hiện sau khi HR gửi feedback cho ít nhất một buổi phỏng vấn đã hoàn tất."),
  ).toBeInTheDocument()
})

test("suggests interview feedback policy through the same-origin api route", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        policy: {
          policy_id: "policy-1",
          jd_id: "jd-1",
          status: "suggested",
          version: 1,
          source_feedback_count: 1,
          policy_payload: {
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
          summary_payload: {
            source_feedback_count: 1,
            top_overrated_competencies: [],
            top_underrated_competencies: [],
            top_failure_reasons: [],
            expected_effects: [],
            recommendation_agreement_rate: 0.5,
          },
          approved_by_user_id: null,
          approved_by_email: null,
          approved_at: null,
          created_at: "2026-04-20T09:00:00+07:00",
          updated_at: "2026-04-20T09:00:00+07:00",
        },
        audit_event: {
          event_type: "policy.suggested",
          payload: {},
          created_at: "2026-04-20T09:00:00+07:00",
        },
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        jd_id: "jd-1",
        active_policy: null,
        latest_suggested_policy: null,
        memory_context: [],
        policy_audit_trail: [],
      }),
    })
  vi.stubGlobal("fetch", fetchMock)

  render(
    <InterviewFeedbackPolicyPanel
      jdId="jd-1"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      initialData={{
        jd_id: "jd-1",
        active_policy: null,
        latest_suggested_policy: null,
        memory_context: [],
        policy_audit_trail: [],
      }}
      interviewDetail={null}
    />,
  )

  await userEvent.setup().click(screen.getByRole("button", { name: "Tạo gợi ý chính sách bằng AI" }))

  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/interviews/jd/jd-1/feedback-policy/suggest",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
    }),
  )
  await waitFor(() =>
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/interviews/jd/jd-1/feedback-policy",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
        cache: "no-store",
      }),
    ),
  )
})
