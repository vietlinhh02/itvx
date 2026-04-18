import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test } from "vitest"

import { ConversationPanel } from "@/components/interview/live-room/live-room-conversation-panel"
import type { InterviewSessionDetailResponse } from "@/components/interview/interview-types"

function buildSessionDetail(): InterviewSessionDetailResponse {
  return {
    session_id: "session-1",
    status: "in_progress",
    worker_status: "responding",
    provider_status: "gemini_live",
    livekit_room_name: "interview-room-1",
    opening_question: "Intro",
    approved_questions: ["Intro"],
    manual_questions: ["Intro"],
    question_guidance: null,
    plan: {
      session_goal: {
        vi: "Đánh giá mức độ phù hợp của ứng viên với JD backend.",
        en: "Assess the candidate's fit for the backend JD.",
      },
      opening_script: {
        vi: "Cảm ơn bạn đã tham gia.",
        en: "Thanks for joining.",
      },
      overall_strategy: {
        vi: "Đi lần lượt theo từng competency.",
        en: "Walk through each competency in sequence.",
      },
      current_phase: "competency_validation",
      current_competency_index: 1,
      next_intended_step: {
        vi: "Tiếp tục khai thác competency đang active.",
        en: "Continue probing the active competency.",
      },
      interview_decision_status: "adjust",
      question_selection_policy: null,
      transition_rules: [],
      completion_criteria: [],
      competencies: [
        {
          name: { vi: "Nền tảng học thuật", en: "Academic foundation" },
          priority: 1,
          target_question_count: 2,
          current_coverage: 1,
          status: "covered",
          evidence_collected_count: 2,
          evidence_needed: [],
          stop_condition: null,
          last_updated_at: "2026-04-17T10:00:00+00:00",
        },
        {
          name: { vi: "Kiến thức nghiệp vụ BA", en: "BA domain knowledge" },
          priority: 2,
          target_question_count: 3,
          current_coverage: 0.4,
          status: "in_progress",
          evidence_collected_count: 1,
          evidence_needed: [{ vi: "Ví dụ quy trình BA", en: "BA process example" }],
          stop_condition: null,
          last_updated_at: "2026-04-17T10:03:00+00:00",
        },
        {
          name: { vi: "Kỹ năng bổ trợ (UI/UX & Mockup)", en: "UI/UX and mockup support skills" },
          priority: 3,
          target_question_count: 2,
          current_coverage: 0,
          status: "not_started",
          evidence_collected_count: 0,
          evidence_needed: [{ vi: "Case thiết kế mockup", en: "Mockup design case" }],
          stop_condition: null,
          last_updated_at: null,
        },
        {
          name: { vi: "Giao tiếp", en: "Communication" },
          priority: 4,
          target_question_count: 1,
          current_coverage: 0,
          status: "not_started",
          evidence_collected_count: 0,
          evidence_needed: [{ vi: "Ví dụ phối hợp team", en: "Cross-team collaboration example" }],
          stop_condition: null,
          last_updated_at: null,
        },
      ],
      plan_events: [],
      questions: [
        {
          question_index: 0,
          dimension_name: { vi: "Kiến thức nghiệp vụ BA", en: "BA domain knowledge" },
          prompt: { vi: "Bạn mô tả một flow BA gần đây nhé.", en: "Describe a recent BA flow." },
          purpose: { vi: "Kiểm tra tư duy BA.", en: "Validate BA thinking." },
          source: "manual",
          question_type: "manual",
        },
      ],
    },
    current_question_index: 0,
    total_questions: 4,
    recommendation: null,
    schedule: {
      scheduled_start_at: null,
      schedule_timezone: null,
      schedule_status: "unscheduled",
      schedule_note: null,
      candidate_proposed_start_at: null,
      candidate_proposed_note: null,
    },
    disconnect_deadline_at: null,
    last_disconnect_reason: null,
    last_error_code: null,
    last_error_message: null,
    transcript_turns: [
      {
        speaker: "candidate",
        sequence_number: 1,
        transcript_text: "Em đã làm BA cho sản phẩm nội bộ.\nSau đó em phối hợp với design để ra mockup.",
        provider_event_id: "evt-1",
        event_payload: {},
      },
      {
        speaker: "agent",
        sequence_number: 2,
        transcript_text: "Mình đi sâu hơn vào cách em xử lý user flow nhé.",
        provider_event_id: "evt-2",
        event_payload: {},
      },
    ],
    runtime_events: [],
  }
}

test("renders the full competency queue with clear active and queued states", async () => {
  render(<ConversationPanel sessionDetail={buildSessionDetail()} />)

  const section = screen.getByText("Tiến độ bao phủ").closest("section")
  if (!section) {
    throw new Error("Expected coverage section to be rendered")
  }

  await userEvent.setup().click(within(section).getByRole("button", { name: "Mở rộng" }))

  expect(within(section).getByText("Nền tảng học thuật")).toBeInTheDocument()
  expect(within(section).getAllByText("Kiến thức nghiệp vụ BA").length).toBeGreaterThan(0)
  expect(within(section).getByText("Kỹ năng bổ trợ (UI/UX & Mockup)")).toBeInTheDocument()
  expect(within(section).getByText("Giao tiếp")).toBeInTheDocument()
  expect(screen.getByText("Đang theo dõi")).toBeInTheDocument()
  expect(screen.getAllByText("Chờ đến lượt")).toHaveLength(2)
  expect(screen.getByText("Hoàn tất")).toBeInTheDocument()
})

test("uses the current question target when the competency index is stale", async () => {
  const sessionDetail = buildSessionDetail()
  if (!sessionDetail.plan) {
    throw new Error("Expected plan")
  }

  sessionDetail.plan.current_competency_index = 0

  render(<ConversationPanel sessionDetail={sessionDetail} />)

  const section = screen.getByText("Tiến độ bao phủ").closest("section")
  if (!section) {
    throw new Error("Expected coverage section to be rendered")
  }

  await userEvent.setup().click(within(section).getByRole("button", { name: "Mở rộng" }))

  const communicationCard = within(section).getAllByText("Kiến thức nghiệp vụ BA")[0]?.closest("article")
  const academicCard = within(section).getByText("Nền tảng học thuật").closest("article")

  expect(communicationCard?.textContent).toContain("Đang theo dõi")
  expect(academicCard?.textContent).toContain("Hoàn tất")
})

test("shows balanced empty states for agent and system event columns", async () => {
  render(<ConversationPanel sessionDetail={buildSessionDetail()} />)

  const section = screen.getByText("Sự kiện từ agent và hệ thống").closest("section")
  if (!section) {
    throw new Error("Expected events section to be rendered")
  }

  await userEvent.setup().click(within(section).getByRole("button", { name: "Mở rộng" }))

  expect(screen.getByText("Chưa có quyết định mới từ agent.")).toBeInTheDocument()
  expect(screen.getByText("Chưa có sự kiện hệ thống mới.")).toBeInTheDocument()
})

test("separates transcript turns into speaker lanes and preserves line breaks", async () => {
  render(<ConversationPanel sessionDetail={buildSessionDetail()} />)

  const section = screen.getByText("Bản ghi hội thoại").closest("section")
  if (!section) {
    throw new Error("Expected transcript section to be rendered")
  }

  await userEvent.setup().click(within(section).getByRole("button", { name: "Mở rộng" }))

  const candidateMessage = screen.getByText(/Em đã làm BA cho sản phẩm nội bộ\./)
  const candidateBubble = candidateMessage.closest("article")

  expect(candidateBubble?.className).toContain("ml-auto")
  expect(candidateMessage.className).toContain("whitespace-pre-wrap")
})
