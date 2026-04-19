import { act, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

import { CandidateJoin } from "@/components/interview/candidate-join"
import { formatVietnamDateTime } from "@/lib/datetime"

vi.mock("@/components/interview/live-room", () => ({
  LiveRoom: () => <div data-testid="live-room" />,
}))

beforeEach(() => {
  window.sessionStorage.clear()
  vi.stubGlobal("navigator", {
    mediaDevices: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [],
        getAudioTracks: () => [],
        getVideoTracks: () => [],
      }),
    },
  })
})

afterEach(() => {
  window.sessionStorage.clear()
  vi.useRealTimers()
  vi.restoreAllMocks()
})

test("shows join error message when backend join fails", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          session_id: "session-1",
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
      .mockResolvedValueOnce({ ok: false, status: 500 }),
  )

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  await userEvent.setup().type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await userEvent.setup().click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))

  expect(await screen.findByText("Không thể tham gia buổi phỏng vấn này.")).toBeInTheDocument()
})

test("shows an interview-ended popup when the share link is already dead on first load", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce({ ok: false, status: 404 }))

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  const dialog = await screen.findByRole("dialog", { name: "Buổi phỏng vấn đã kết thúc" })

  expect(within(dialog).getByText("Cảm ơn bạn đã dành thời gian tham gia buổi phỏng vấn.")).toBeInTheDocument()
  expect(
    within(dialog).getByText("Link phỏng vấn này đã hết hiệu lực và không thể dùng để vào lại phòng."),
  ).toBeInTheDocument()
  expect(screen.queryByLabelText("Tên của bạn")).not.toBeInTheDocument()
})

test("shows an interview-ended popup when join returns a dead-link response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          session_id: "session-1",
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
      .mockResolvedValueOnce({ ok: false, status: 404 }),
  )

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await user.click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))

  const dialog = await screen.findByRole("dialog", { name: "Buổi phỏng vấn đã kết thúc" })

  expect(within(dialog).getByText("Cảm ơn bạn đã dành thời gian tham gia buổi phỏng vấn.")).toBeInTheDocument()
  expect(screen.queryByLabelText("Tên của bạn")).not.toBeInTheDocument()
})

test("shows the interview-ended popup instead of allowing re-entry when the joined session finishes", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          session_id: "session-1",
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
          session_id: "session-1",
          room_name: "interview-room-1",
          participant_token: "participant-token-1",
          candidate_identity: "candidate-session-1-nguyen-van-a",
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
          session_id: "session-1",
          status: "completed",
          worker_status: "completed",
          provider_status: "completed",
          livekit_room_name: "interview-room-1",
          opening_question: "Giới thiệu ngắn về bản thân bạn.",
          approved_questions: [],
          manual_questions: [],
          question_guidance: null,
          plan: null,
          current_question_index: 0,
          total_questions: 0,
          recommendation: null,
          schedule: {
            scheduled_start_at: null,
            schedule_timezone: "Asia/Ho_Chi_Minh",
            schedule_status: "unscheduled",
            schedule_note: null,
            candidate_proposed_start_at: null,
            candidate_proposed_note: null,
          },
          disconnect_deadline_at: null,
          last_disconnect_reason: null,
          last_error_code: null,
          last_error_message: null,
          transcript_turns: [],
          runtime_events: [],
        }),
      }),
  )

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await user.click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))

  const dialog = await screen.findByRole("dialog", { name: "Buổi phỏng vấn đã kết thúc" })

  expect(dialog).toBeInTheDocument()
  expect(screen.queryByTestId("live-room")).not.toBeInTheDocument()
  expect(screen.queryByRole("button", { name: "Tham gia phỏng vấn" })).not.toBeInTheDocument()
})

test("submits a candidate schedule proposal to the backend", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: "session-1",
        status: "published",
        schedule: {
          scheduled_start_at: "2026-04-20T09:00:00+07:00",
          schedule_timezone: "Asia/Ho_Chi_Minh",
          schedule_status: "scheduled",
          schedule_note: "Phong van dung gio.",
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
        schedule_note: "Phong van dung gio.",
        candidate_proposed_start_at: "2026-04-20T09:00:00+07:00",
        candidate_proposed_note: "Toi ranh buoi sang",
      }),
    })
  vi.stubGlobal("fetch", fetchMock)

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  const user = userEvent.setup()
  const scheduleSection = screen.getByText("Đề xuất thời gian khác").closest("section")
  if (!scheduleSection) {
    throw new Error("Could not locate candidate schedule section")
  }

  await user.click(within(scheduleSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(scheduleSection).getByRole("button", { name: "09:00" }))
  await user.type(screen.getByLabelText("Lời nhắn cho HR"), "Toi ranh buoi sang")
  await user.click(screen.getByRole("button", { name: "Gửi đề xuất thời gian khác" }))

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/interviews/join/share-token-1/schedule",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        "Content-Type": "application/json",
      }),
      cache: "no-store",
    }),
  )

  const scheduleRequest = fetchMock.mock.calls[1]?.[1]
  expect(scheduleRequest?.body).toEqual(
    expect.stringMatching(
      /^\{"proposed_start_at":"\d{4}-\d{2}-\d{2}T09:00:00\+07:00","note":"Toi ranh buoi sang","timezone":"Asia\/Ho_Chi_Minh"\}$/,
    ),
  )
})

test("loads and shows the scheduled interview time before the candidate joins", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      session_id: "session-1",
      status: "published",
      schedule: {
        scheduled_start_at: "2026-04-20T09:00:00+07:00",
        schedule_timezone: "Asia/Ho_Chi_Minh",
        schedule_status: "scheduled",
        schedule_note: "Phong van dung gio.",
        candidate_proposed_start_at: null,
        candidate_proposed_note: null,
      },
    }),
  })
  vi.stubGlobal("fetch", fetchMock)

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  expect(
    await screen.findByText(
      `Thời gian đã hẹn: ${formatVietnamDateTime("2026-04-20T09:00:00+07:00")} (ICT)`,
    ),
  ).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/interviews/join/share-token-1",
    expect.objectContaining({ cache: "no-store" }),
  )
})

test("restores only the candidate name from session storage", async () => {
  const fetchMock = vi.fn().mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      session_id: "session-1",
      status: "published",
      schedule: {
        scheduled_start_at: "2026-04-20T09:00:00+07:00",
        schedule_timezone: "Asia/Ho_Chi_Minh",
        schedule_status: "scheduled",
        schedule_note: "Phong van dung gio.",
        candidate_proposed_start_at: null,
        candidate_proposed_note: null,
      },
    }),
  })
  vi.stubGlobal("fetch", fetchMock)
  window.sessionStorage.setItem(
    "interviewx:candidate-join:share-token-1",
    JSON.stringify({
      candidateName: "Nguyen Van A",
      joinPayload: {
        session_id: "session-1",
        room_name: "interview-room-1",
        participant_token: "participant-token-1",
        candidate_identity: "candidate-session-1-nguyen-van-a",
      },
    }),
  )

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  expect(screen.getByLabelText("Tên của bạn")).toHaveValue("Nguyen Van A")
  expect(screen.queryByTestId("live-room")).not.toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/interviews/join/share-token-1",
    expect.objectContaining({ cache: "no-store" }),
  )
})

test("does not persist join payload or log sensitive join data", async () => {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: "session-1",
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
        session_id: "session-1",
        room_name: "interview-room-1",
        participant_token: "participant-token-1",
        candidate_identity: "candidate-session-1-nguyen-van-a",
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
    .mockResolvedValue({
      ok: true,
      json: async () => ({
        session_id: "session-1",
        status: "connecting",
        worker_status: "room_connected",
        provider_status: "livekit_connected",
        livekit_room_name: "interview-room-1",
        opening_question: "Giới thiệu ngắn về bản thân bạn.",
        approved_questions: [],
        manual_questions: [],
        question_guidance: "Tập trung vào backend",
        plan: {
          session_goal: { vi: "Mục tiêu", en: "Goal" },
          opening_script: { vi: "Xin chào", en: "Hello" },
          overall_strategy: { vi: "Chiến lược", en: "Strategy" },
          current_phase: "competency_validation",
          question_selection_policy: { vi: "Chính sách", en: "Policy" },
          transition_rules: [],
          completion_criteria: [],
          competencies: [],
          plan_events: [],
          questions: [],
        },
        current_question_index: 0,
        total_questions: 0,
        recommendation: null,
        schedule: {
          scheduled_start_at: null,
          schedule_timezone: "Asia/Ho_Chi_Minh",
          schedule_status: "unscheduled",
          schedule_note: null,
          candidate_proposed_start_at: null,
          candidate_proposed_note: null,
        },
        disconnect_deadline_at: null,
        last_disconnect_reason: null,
        last_error_code: null,
        last_error_message: null,
        transcript_turns: [],
        runtime_events: [],
      }),
    })
  const consoleInfoSpy = vi.spyOn(console, "info").mockImplementation(() => {})
  const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
  const consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {})
  vi.stubGlobal("fetch", fetchMock)

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await user.click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))

  expect(await screen.findByTestId("live-room")).toBeInTheDocument()

  const stored = window.sessionStorage.getItem("interviewx:candidate-join:share-token-1")
  expect(stored).toBe(JSON.stringify({ candidateName: "Nguyen Van A" }))
  expect(stored).not.toContain("participant-token-1")
  expect(stored).not.toContain("interview-room-1")
  expect(consoleInfoSpy).not.toHaveBeenCalled()
  expect(consoleWarnSpy).not.toHaveBeenCalled()
  expect(consoleErrorSpy).not.toHaveBeenCalled()
})

test("does not log polling failures after the candidate joins", async () => {
  const consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {})
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        session_id: "session-1",
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
        session_id: "session-1",
        room_name: "interview-room-1",
        participant_token: "participant-token-1",
        candidate_identity: "candidate-session-1-nguyen-van-a",
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
    .mockRejectedValueOnce(new TypeError("Failed to fetch"))
  vi.stubGlobal("fetch", fetchMock)

  const view = render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)
  const user = userEvent.setup()
  await user.type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await user.click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))
  await act(async () => {
    await Promise.resolve()
  })

  expect(screen.getByTestId("live-room")).toBeInTheDocument()
  expect(fetchMock).toHaveBeenCalledTimes(3)
  expect(consoleWarnSpy).not.toHaveBeenCalled()
  view.unmount()
})
