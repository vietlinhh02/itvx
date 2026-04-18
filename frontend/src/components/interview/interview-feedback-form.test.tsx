import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { InterviewFeedbackForm } from "@/components/interview/interview-feedback-form"

afterEach(() => {
  vi.restoreAllMocks()
})

test("submits HR feedback through the same-origin api route", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      session_id: "session-1",
      jd_id: "jd-1",
      submitted_by_user_id: "user-1",
      submitted_by_email: "hr@example.com",
      overall_agreement_score: 0.75,
      ai_recommendation: "review",
      hr_recommendation: "advance",
      recommendation_agreement: false,
      overall_notes: null,
      missing_evidence_notes: null,
      false_positive_notes: null,
      false_negative_notes: null,
      competencies: [],
      created_at: "2026-04-20T09:00:00+07:00",
      updated_at: "2026-04-20T09:00:00+07:00",
    }),
  })
  const onSaved = vi.fn()
  vi.stubGlobal("fetch", fetchMock)

  render(
    <InterviewFeedbackForm
      sessionId="session-1"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      assessments={[]}
      initialFeedback={null}
      onSaved={onSaved}
    />,
  )

  await userEvent.setup().click(screen.getByRole("button", { name: "Lưu phản hồi của HR" }))

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/interviews/sessions/session-1/feedback",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
        "Content-Type": "application/json",
      }),
    }),
  )
  await waitFor(() => expect(onSaved).toHaveBeenCalledTimes(1))
})
