import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, expect, test, vi } from "vitest"

import { InterviewSessionDetail } from "@/components/interview/interview-session-detail"

vi.stubGlobal("fetch", vi.fn())

beforeEach(() => {
  window.sessionStorage.clear()
})

test("renders rich planning metadata in session detail", async () => {
  render(
    <InterviewSessionDetail
      accessToken="token"
      backendBaseUrl="http://localhost:8000"
      initialSession={{
        session_id: "session-1",
        status: "in_progress",
        worker_status: "responding",
        provider_status: "gemini_live",
        livekit_room_name: "interview-room-1",
        opening_question: "Intro",
        approved_questions: ["Intro"],
        manual_questions: ["Intro"],
        question_guidance: "Focus on backend depth",
        plan: {
          session_goal: {
            vi: "Đánh giá mức độ phù hợp với JD backend.",
            en: "Assess fit for the backend JD.",
          },
          opening_script: {
            vi: "Cảm ơn bạn đã tham gia.",
            en: "Thanks for joining.",
          },
          overall_strategy: {
            vi: "Bắt đầu với backend fundamentals rồi mở rộng theo evidence gap.",
            en: "Start with backend fundamentals, then expand based on evidence gaps.",
          },
          current_phase: "competency_validation",
          current_competency_index: 0,
          next_intended_step: {
            vi: "Làm rõ thêm ví dụ backend.",
            en: "Clarify the backend example further.",
          },
          interview_decision_status: "adjust",
          question_selection_policy: {
            vi: "Ưu tiên competency có evidence gap lớn nhất.",
            en: "Prioritize the competency with the biggest evidence gap.",
          },
          transition_rules: [],
          completion_criteria: [],
          competencies: [
            {
              name: { vi: "Backend", en: "Backend" },
              priority: 1,
              target_question_count: 2,
              current_coverage: 0,
              status: "needs_recovery",
              evidence_collected_count: 0,
              evidence_needed: [{ vi: "Ví dụ production backend", en: "Production backend example" }],
              stop_condition: { vi: "Đủ bằng chứng", en: "Enough evidence" },
              last_updated_at: "2026-04-17T10:03:00+00:00",
            },
          ],
          plan_events: [
            {
              event_type: "plan.created",
              reason: { vi: "Khởi tạo plan", en: "Plan initialized" },
              chosen_action: "start_with_backend",
              affected_competency: { vi: "Backend", en: "Backend" },
              confidence: 0.8,
              question_index: 0,
              created_at: "2026-04-17T10:00:00+00:00",
            },
            {
              event_type: "plan.adjusted",
              reason: { vi: "Cần hỏi làm rõ", en: "Need a clarification question" },
              chosen_action: "ask_clarification",
              affected_competency: { vi: "Backend", en: "Backend" },
              confidence: 0.74,
              question_index: 0,
              evidence_excerpt: {
                vi: "Em có làm backend.",
                en: "Em có làm backend.",
              },
              decision_rule: "generic_answer_needs_clarification",
              next_question_type: "clarification",
              created_at: "2026-04-17T10:02:00+00:00",
            },
          ],
          questions: [
            {
              question_index: 0,
              dimension_name: { vi: "Backend", en: "Backend" },
              prompt: { vi: "Giới thiệu ngắn về bản thân bạn.", en: "Introduce yourself briefly." },
              purpose: { vi: "Xác minh tín hiệu backend.", en: "Validate backend signals." },
              source: "manual",
              question_type: "manual",
              rationale: "Provided directly by HR.",
              priority: 1,
              target_competency: { vi: "Backend", en: "Backend" },
              evidence_gap: { vi: "Cần thêm bằng chứng backend.", en: "Need more backend evidence." },
              selection_reason: {
                vi: "HR muốn xác minh backend trước.",
                en: "HR wants to validate backend first.",
              },
              transition_on_strong_answer: "advance_to_next_competency",
              transition_on_weak_answer: "ask_clarification",
            },
            {
              question_index: 1,
              dimension_name: { vi: "Backend", en: "Backend" },
              prompt: {
                vi: "Tôi muốn làm rõ lại timeline và vai trò của bạn.",
                en: "I want to clarify the timeline and your ownership.",
              },
              purpose: { vi: "Làm rõ ownership.", en: "Clarify ownership." },
              source: "adaptive",
              question_type: "recovery",
              rationale: "Need a recovery question.",
              priority: 2,
              target_competency: { vi: "Backend", en: "Backend" },
              evidence_gap: { vi: "Cần làm rõ claim.", en: "Need to clarify the claim." },
              selection_reason: {
                vi: "Cần hỏi recovery.",
                en: "Need a recovery question.",
              },
              transition_on_strong_answer: "advance_to_next_competency",
              transition_on_weak_answer: "ask_recovery",
            },
          ],
        },
        current_question_index: 0,
        total_questions: 1,
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
        transcript_turns: [],
        runtime_events: [],
      }}
    />,
  )

  expect(screen.getByText("Tổng quan kế hoạch")).toBeInTheDocument()
  expect(screen.getByText("Ưu tiên năng lực")).toBeInTheDocument()
  expect(screen.getByText("Kế hoạch câu hỏi")).toBeInTheDocument()
  expect(screen.getByText("Quyết định của agent")).toBeInTheDocument()
  expect(screen.getByText(/Quyết định: Điều chỉnh/)).toBeInTheDocument()
  expect(screen.getByText(/Bước tiếp theo: Làm rõ thêm ví dụ backend\./)).toBeInTheDocument()

  const competencySection = screen.getByText("Ưu tiên năng lực").closest("section")
  const questionSection = screen.getByText("Kế hoạch câu hỏi").closest("section")
  const agentSection = screen.getByText("Quyết định của agent").closest("section")

  if (!competencySection || !questionSection || !agentSection) {
    throw new Error("Expected collapsible sections to be rendered")
  }

  const user = userEvent.setup()
  await user.click(within(competencySection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(questionSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(agentSection).getByRole("button", { name: "Mở rộng" }))

  expect(screen.getByText(/Trạng thái: Needs Recovery/)).toBeInTheDocument()
  expect(screen.getByText(/Số bằng chứng đã thu: 0/)).toBeInTheDocument()
  expect(screen.getByText(/Độ tin cậy: 74%/)).toBeInTheDocument()
  expect(screen.getByText(/Luật: Generic Answer Needs Clarification/)).toBeInTheDocument()
  expect(screen.getByText(/Loại câu hỏi tiếp theo: Làm rõ/)).toBeInTheDocument()
  expect(screen.getByText(/Bằng chứng: Em có làm backend\./)).toBeInTheDocument()
  expect(screen.getAllByText(/Lý do hỏi lúc này:/)).toHaveLength(2)
  expect(screen.getByText(/HR muốn xác minh backend trước\./)).toBeInTheDocument()
  expect(screen.getByText("Khoảng trống bằng chứng: Cần thêm bằng chứng backend.")).toBeInTheDocument()
  expect(screen.getByText("Khôi phục")).toBeInTheDocument()
})

test("restores expanded planning sections after reload", async () => {
  const user = userEvent.setup()

  const props = {
    accessToken: "token",
    backendBaseUrl: "http://localhost:8000",
    initialSession: {
      session_id: "session-1",
      status: "in_progress",
      worker_status: "responding",
      provider_status: "gemini_live",
      livekit_room_name: "interview-room-1",
      opening_question: "Intro",
      approved_questions: ["Intro"],
      manual_questions: ["Intro"],
      question_guidance: "Focus on backend depth",
      plan: {
        session_goal: {
          vi: "Đánh giá mức độ phù hợp với JD backend.",
          en: "Assess fit for the backend JD.",
        },
        opening_script: {
          vi: "Cảm ơn bạn đã tham gia.",
          en: "Thanks for joining.",
        },
        overall_strategy: {
          vi: "Bắt đầu với backend fundamentals rồi mở rộng theo evidence gap.",
          en: "Start with backend fundamentals, then expand based on evidence gaps.",
        },
        current_phase: "competency_validation",
        current_competency_index: 0,
        next_intended_step: {
          vi: "Làm rõ thêm ví dụ backend.",
          en: "Clarify the backend example further.",
        },
        interview_decision_status: "adjust",
        question_selection_policy: {
          vi: "Ưu tiên competency có evidence gap lớn nhất.",
          en: "Prioritize the competency with the biggest evidence gap.",
        },
        transition_rules: [],
        completion_criteria: [],
        competencies: [
          {
            name: { vi: "Backend", en: "Backend" },
            priority: 1,
            target_question_count: 2,
            current_coverage: 0,
            status: "needs_recovery",
            evidence_collected_count: 0,
            evidence_needed: [{ vi: "Ví dụ production backend", en: "Production backend example" }],
            stop_condition: { vi: "Đủ bằng chứng", en: "Enough evidence" },
            last_updated_at: "2026-04-17T10:03:00+00:00",
          },
        ],
        plan_events: [
          {
            event_type: "plan.created",
            reason: { vi: "Khởi tạo plan", en: "Plan initialized" },
            chosen_action: "start_with_backend",
            affected_competency: { vi: "Backend", en: "Backend" },
            confidence: 0.8,
            question_index: 0,
            created_at: "2026-04-17T10:00:00+00:00",
          },
        ],
        questions: [
          {
            question_index: 0,
            dimension_name: { vi: "Backend", en: "Backend" },
            prompt: { vi: "Giới thiệu ngắn về bản thân bạn.", en: "Introduce yourself briefly." },
            purpose: { vi: "Xác minh tín hiệu backend.", en: "Validate backend signals." },
            source: "manual",
            question_type: "manual",
            rationale: "Provided directly by HR.",
            priority: 1,
            target_competency: { vi: "Backend", en: "Backend" },
            evidence_gap: { vi: "Cần thêm bằng chứng backend.", en: "Need more backend evidence." },
            selection_reason: {
              vi: "HR muốn xác minh backend trước.",
              en: "HR wants to validate backend first.",
            },
            transition_on_strong_answer: "advance_to_next_competency",
            transition_on_weak_answer: "ask_clarification",
          },
        ],
      },
      current_question_index: 0,
      total_questions: 1,
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
      transcript_turns: [],
      runtime_events: [],
    },
  } satisfies Parameters<typeof InterviewSessionDetail>[0]

  const { unmount } = render(<InterviewSessionDetail {...props} />)

  const competencySection = screen.getByText("Ưu tiên năng lực").closest("section")
  if (!competencySection) {
    throw new Error("Expected competency section to be rendered")
  }

  await user.click(within(competencySection).getByRole("button", { name: "Mở rộng" }))
  expect(screen.getByText(/Trạng thái: Needs Recovery/)).toBeInTheDocument()

  unmount()

  render(<InterviewSessionDetail {...props} />)

  expect(screen.getByText(/Trạng thái: Needs Recovery/)).toBeInTheDocument()
})
