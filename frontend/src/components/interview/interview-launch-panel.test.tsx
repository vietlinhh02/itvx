import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { InterviewLaunchPanel } from "@/components/interview/interview-launch-panel"

const push = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}))

afterEach(() => {
  vi.restoreAllMocks()
  push.mockReset()
})

test("publishes interview through same-origin api route", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        screening_id: "screening-123",
        manual_questions: ["Tell me about yourself."],
        question_guidance: null,
        generated_questions: [
          { question_text: "Tell me about yourself.", source: "llm", rationale: null },
        ],
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: "session-123",
        share_link: "http://localhost:3000/interviews/join/share-token-123",
        room_name: "interview-room-123",
        status: "published",
        schedule: {
          scheduled_start_at: null,
          schedule_timezone: "Asia/Ho_Chi_Minh",
          schedule_status: "unscheduled",
          schedule_note: null,
          candidate_proposed_start_at: null,
          candidate_proposed_note: null,
        },
      }),
    })
  vi.stubGlobal("fetch", fetchMock)

  render(
    <InterviewLaunchPanel
      screeningId="screening-123"
      jdId="jd-123"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
    />
  )

  const user = userEvent.setup()
  await user.click(screen.getByRole("button", { name: "Tạo câu hỏi" }))
  await user.click(screen.getByRole("button", { name: "Bắt đầu buổi phỏng vấn" }))

  expect(fetchMock).toHaveBeenNthCalledWith(
    1,
    "/api/v1/interviews/generate-questions",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
    }),
  )
  expect(fetchMock).toHaveBeenNthCalledWith(
    2,
    "/api/v1/interviews/publish",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
    }),
  )
  expect(push).not.toHaveBeenCalled()
})
