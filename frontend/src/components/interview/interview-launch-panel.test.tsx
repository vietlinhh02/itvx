import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { InterviewLaunchPanel } from "@/components/interview/interview-launch-panel"

const push = vi.fn()
const refresh = vi.fn()

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}))

afterEach(() => {
  vi.restoreAllMocks()
  push.mockReset()
  refresh.mockReset()
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
  expect(refresh).toHaveBeenCalledTimes(1)
})

test("publishes interview and persists the selected schedule", async () => {
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
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scheduled_start_at: "2026-04-20T09:00:00+07:00",
        schedule_timezone: "Asia/Ho_Chi_Minh",
        schedule_status: "scheduled",
        schedule_note: "Xin vao hop dung gio",
        candidate_proposed_start_at: null,
        candidate_proposed_note: null,
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
  const scheduleSection = screen.getByText("Thời gian buổi họp").closest("section")
  if (!scheduleSection) {
    throw new Error("Could not locate schedule section")
  }

  await user.click(within(scheduleSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(scheduleSection).getByRole("button", { name: "09:00" }))
  await user.type(screen.getByLabelText("Ghi chú lịch hẹn"), "Xin vao hop dung gio")
  await user.click(screen.getByRole("button", { name: "Tạo câu hỏi" }))
  await user.click(screen.getByRole("button", { name: "Bắt đầu buổi phỏng vấn" }))

  expect(fetchMock).toHaveBeenNthCalledWith(
    3,
    "/api/v1/interviews/sessions/session-123/schedule",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
    }),
  )

  const scheduleRequest = fetchMock.mock.calls[2]?.[1]
  expect(scheduleRequest?.body).toEqual(
    expect.stringMatching(
      /^\{"scheduled_start_at":"\d{4}-\d{2}-\d{2}T09:00:00\+07:00","schedule_timezone":"Asia\/Ho_Chi_Minh","schedule_note":"Xin vao hop dung gio"\}$/,
    ),
  )
  expect(refresh).toHaveBeenCalledTimes(1)
})

test("keeps the published interview link visible when schedule persistence fails", async () => {
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
    .mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        detail: "Không thể cập nhật lịch họp.",
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
  const scheduleSection = screen.getByText("Thời gian buổi họp").closest("section")
  if (!scheduleSection) {
    throw new Error("Could not locate schedule section")
  }

  await user.click(within(scheduleSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(scheduleSection).getByRole("button", { name: "09:00" }))
  await user.type(screen.getByLabelText("Ghi chú lịch hẹn"), "Xin vao hop dung gio")
  await user.click(screen.getByRole("button", { name: "Tạo câu hỏi" }))
  await user.click(screen.getByRole("button", { name: "Bắt đầu buổi phỏng vấn" }))

  expect(await screen.findByText("Liên kết tham gia")).toBeInTheDocument()
  expect(screen.getByText("http://localhost:3000/interviews/join/share-token-123")).toBeInTheDocument()
  expect(screen.getByText("Session ID: session-123")).toBeInTheDocument()
  expect(screen.getByText("Room name: interview-room-123")).toBeInTheDocument()
  expect(screen.getByText("Không thể cập nhật lịch họp.")).toBeInTheDocument()
  expect(refresh).not.toHaveBeenCalled()
})

test("updates the schedule for an existing published interview session", async () => {
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
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        scheduled_start_at: "2026-04-20T10:00:00+07:00",
        schedule_timezone: "Asia/Ho_Chi_Minh",
        schedule_status: "scheduled",
        schedule_note: "Cap nhat lich hop",
        candidate_proposed_start_at: null,
        candidate_proposed_note: null,
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

  const scheduleSection = screen.getByText("Thời gian buổi họp").closest("section")
  if (!scheduleSection) {
    throw new Error("Could not locate schedule section")
  }

  await user.click(within(scheduleSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(scheduleSection).getByRole("button", { name: "10:00" }))
  await user.type(screen.getByLabelText("Ghi chú lịch hẹn"), "Cap nhat lich hop")
  await user.click(screen.getByRole("button", { name: "Cập nhật lịch phỏng vấn" }))

  expect(fetchMock).toHaveBeenNthCalledWith(
    3,
    "/api/v1/interviews/sessions/session-123/schedule",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
    }),
  )

  const scheduleRequest = fetchMock.mock.calls[2]?.[1]
  expect(scheduleRequest?.body).toEqual(
    expect.stringMatching(
      /^\{"scheduled_start_at":"\d{4}-\d{2}-\d{2}T10:00:00\+07:00","schedule_timezone":"Asia\/Ho_Chi_Minh","schedule_note":"Cap nhat lich hop"\}$/,
    ),
  )
  expect(refresh).toHaveBeenCalledTimes(2)
})

test("uploads company document through same-origin api route", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        job_id: "job-company-123",
        document: {
          document_id: "doc-123",
          jd_id: "jd-123",
          file_name: "company.pdf",
          status: "queued",
          chunk_count: 0,
          error_message: null,
          created_at: "2026-04-18T00:00:00Z",
        },
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        items: [
          {
            document_id: "doc-123",
            jd_id: "jd-123",
            file_name: "company.pdf",
            status: "queued",
            chunk_count: 0,
            error_message: null,
            created_at: "2026-04-18T00:00:00Z",
          },
        ],
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
  const input = screen.getByLabelText("Tải tài liệu lên")
  const file = new File(["%PDF-1.7\ncompany"], "company.pdf", { type: "application/pdf" })

  await user.upload(input, file)

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/jd/jd-123/company-documents",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
      body: expect.any(FormData),
    }),
  )
})

test("starts collapsed when the interview is already completed and expands on demand", async () => {
  render(
    <InterviewLaunchPanel
      screeningId="screening-123"
      jdId="jd-123"
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      defaultCollapsed
    />,
  )

  const toggle = screen.getByRole("button", {
    name: /Chuẩn bị câu hỏi trước khi bắt đầu buổi phỏng vấn/i,
  })

  expect(toggle).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByLabelText("Câu hỏi thủ công")).not.toBeInTheDocument()

  const user = userEvent.setup()
  await user.click(toggle)

  await waitFor(() => {
    expect(toggle).toHaveAttribute("aria-expanded", "true")
  })
  expect(await screen.findByLabelText("Câu hỏi thủ công")).toBeInTheDocument()
})
