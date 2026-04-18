import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, expect, test, vi } from "vitest"

import { LiveRoom } from "@/components/interview/live-room"

let capturedLiveKitRoomProps: Record<string, unknown> | null = null

vi.mock("@livekit/components-react", () => ({
  LiveKitRoom: ({ children, ...props }: { children: React.ReactNode } & Record<string, unknown>) => {
    capturedLiveKitRoomProps = props
    return <div data-testid="livekit-room">{children}</div>
  },
  RoomAudioRenderer: () => <div data-testid="room-audio-renderer" />,
  StartAudio: ({ label }: { label: string }) => <button type="button">{label}</button>,
  TrackToggle: ({ children }: { children: React.ReactNode }) => <button type="button">{children}</button>,
  DisconnectButton: ({ children }: { children: React.ReactNode }) => <button type="button">{children}</button>,
  useLocalParticipant: () => ({
    microphoneTrack: null,
    localParticipant: null,
    isMicrophoneEnabled: true,
  }),
  useAudioWaveform: () => ({ bars: [1, 2, 3, 4, 5, 6, 7] }),
  useMediaDevices: () => ([
    { deviceId: "mic-default", label: "Default microphone", kind: "audioinput", groupId: "group-1", toJSON: () => ({}) },
    { deviceId: "usb-mic", label: "USB Headset Mic", kind: "audioinput", groupId: "group-2", toJSON: () => ({}) },
  ]),
}))

beforeEach(() => {
  Object.defineProperty(window.navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue({
        getTracks: () => [{ stop: vi.fn() }],
      }),
    },
  })
})

test("shows and updates the selected microphone before connecting", async () => {
  render(
    <LiveRoom
      participantName="Nguyen Van A"
      roomName="interview-room-1"
      participantToken="token-123"
    />,
  )

  const user = userEvent.setup()
  await user.click(screen.getByRole("button", { name: /select microphone|default microphone/i }))

  const microphoneList = screen.getByRole("listbox", { name: "Danh sách micro" })
  expect(within(microphoneList).getByText("USB Headset Mic")).toBeInTheDocument()

  await user.click(within(microphoneList).getByRole("option", { name: /USB Headset Mic/i }))

  expect(screen.getByRole("button", { name: /USB Headset Mic/i })).toBeInTheDocument()
})

test("enables browser echo and noise cancellation when connecting to the live room", async () => {
  capturedLiveKitRoomProps = null

  render(
    <LiveRoom
      participantName="Nguyen Van A"
      roomName="interview-room-1"
      participantToken="token-123"
    />,
  )

  await userEvent.setup().click(screen.getByRole("button", { name: "Kết nối vào buổi phỏng vấn" }))

  expect(capturedLiveKitRoomProps).not.toBeNull()
  expect(((capturedLiveKitRoomProps as unknown) as { audio?: Record<string, unknown> }).audio).toMatchObject({
    autoGainControl: true,
    echoCancellation: true,
    noiseSuppression: true,
  })
})

test("hard-disables camera in the prejoin flow and live room connection", async () => {
  capturedLiveKitRoomProps = null

  render(
    <LiveRoom
      participantName="Nguyen Van A"
      roomName="interview-room-1"
      participantToken="token-123"
    />,
  )

  expect(screen.queryByText("Camera")).not.toBeInTheDocument()

  await userEvent.setup().click(screen.getByRole("button", { name: "Kết nối vào buổi phỏng vấn" }))

  expect(capturedLiveKitRoomProps).not.toBeNull()
  expect(((capturedLiveKitRoomProps as unknown) as { video?: unknown }).video).toBe(false)
})

test("prompts the candidate to speak first when no transcript has started yet", async () => {
  render(
    <LiveRoom
      participantName="Nguyen Van A"
      roomName="interview-room-1"
      participantToken="token-123"
      sessionDetail={{
        session_id: "session-1",
        status: "waiting",
        worker_status: "responding",
        provider_status: "gemini_live",
        livekit_room_name: "interview-room-1",
        opening_question: "Intro",
        approved_questions: ["Intro"],
        manual_questions: ["Intro"],
        question_guidance: null,
        plan: null,
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
        last_error_code: null,
        last_error_message: null,
        transcript_turns: [],
        runtime_events: [],
      }}
    />,
  )

  await userEvent.setup().click(screen.getByRole("button", { name: "Kết nối vào buổi phỏng vấn" }))

  expect(
    screen.getByText("Hãy nói một câu ngắn để bắt đầu cuộc phỏng vấn. AI sẽ phản hồi ngay sau khi nghe thấy bạn."),
  ).toBeInTheDocument()
})

test("renders full-screen meeting layout with candidate and ai avatar tiles after connecting", async () => {
  render(
    <LiveRoom
      participantName="Nguyen Van A"
      roomName="interview-room-1"
      participantToken="token-123"
      sessionDetail={{
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
            vi: "Bắt đầu với backend fundamentals rồi mở rộng theo evidence gap.",
            en: "Start with backend fundamentals, then expand based on evidence gaps.",
          },
          current_phase: "competency_validation",
          current_competency_index: 0,
          next_intended_step: {
            vi: "Yêu cầu ứng viên bổ sung bối cảnh, hành động và kết quả.",
            en: "Ask the candidate to add context, actions, and measurable outcomes.",
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
              current_coverage: 0.5,
              status: "in_progress",
              evidence_collected_count: 1,
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
              evidence_excerpt: {
                vi: "CV screening cho thấy evidence backend còn thiếu.",
                en: "CV screening showed missing backend evidence.",
              },
              decision_rule: "start_with_priority_competency",
              next_question_type: "manual",
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
        last_error_code: null,
        last_error_message: null,
        transcript_turns: [
          {
            speaker: "agent",
            sequence_number: 0,
            transcript_text: "Xin chào, chúng ta bắt đầu nhé.",
            provider_event_id: "evt-1",
            event_payload: { role: "assistant" },
          },
        ],
        runtime_events: [
          {
            event_type: "planning.published",
            event_source: "backend",
            session_status: "in_progress",
            worker_status: "responding",
            provider_status: "gemini_live",
            payload: { current_phase: "competency_validation" },
          },
        ],
      }}
    />,
  )

  await userEvent.setup().click(screen.getByRole("button", { name: "Kết nối vào buổi phỏng vấn" }))

  expect(screen.getByTestId("meeting-shell")).toBeInTheDocument()
  expect(screen.getByText("Nguyen Van A")).toBeInTheDocument()
  expect(screen.getByText("InterviewX AI")).toBeInTheDocument()
  expect(screen.getByTestId("candidate-avatar-tile")).toBeInTheDocument()
  expect(screen.getByTestId("ai-avatar-tile")).toBeInTheDocument()
  expect(screen.getByTestId("meeting-controls")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Bật âm thanh" })).toBeInTheDocument()
  expect(screen.getByText("Bản ghi")).toBeInTheDocument()
  expect(screen.getByText("Tóm tắt buổi phỏng vấn")).toBeInTheDocument()
  expect(screen.getByText("Vì sao chọn câu này?")).toBeInTheDocument()
  expect(screen.getByText("Tiến độ bao phủ")).toBeInTheDocument()
  expect(screen.getByText("Kế hoạch tiếp theo")).toBeInTheDocument()
  expect(screen.getByText("Sự kiện từ agent và hệ thống")).toBeInTheDocument()

  const summarySection = screen.getByText("Tóm tắt buổi phỏng vấn").closest("section")
  const whySection = screen.getByText("Vì sao chọn câu này?").closest("section")
  const coverageSection = screen.getByText("Tiến độ bao phủ").closest("section")
  const upcomingSection = screen.getByText("Kế hoạch tiếp theo").closest("section")
  const eventsSection = screen.getByText("Sự kiện từ agent và hệ thống").closest("section")

  if (!summarySection || !whySection || !coverageSection || !upcomingSection || !eventsSection) {
    throw new Error("Expected collapsible sections to be rendered")
  }

  const user = userEvent.setup()
  await user.click(within(summarySection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(whySection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(coverageSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(upcomingSection).getByRole("button", { name: "Mở rộng" }))
  await user.click(within(eventsSection).getByRole("button", { name: "Mở rộng" }))

  expect(screen.getByText("Đánh giá mức độ phù hợp của ứng viên với JD backend.")).toBeInTheDocument()
  expect(screen.getByText("Quyết định")).toBeInTheDocument()
  expect(screen.getByText("Điều chỉnh")).toBeInTheDocument()
  expect(screen.getByText("Bước tiếp theo: Yêu cầu ứng viên bổ sung bối cảnh, hành động và kết quả.")).toBeInTheDocument()
  expect(screen.getByText("HR muốn xác minh backend trước.")).toBeInTheDocument()
  expect(screen.getByText("Đã bao phủ 50%")).toBeInTheDocument()
  expect(screen.getByText(/Hành động: Start With Backend · Độ tin cậy 80%/)).toBeInTheDocument()
  expect(screen.getByText(/Luật: Start With Priority Competency/)).toBeInTheDocument()
  expect(screen.getByText(/Loại câu hỏi tiếp theo: Thủ công/)).toBeInTheDocument()
  expect(screen.getByText(/Bằng chứng: CV screening cho thấy evidence backend còn thiếu\./)).toBeInTheDocument()
  expect(screen.getByText("Xin chào, chúng ta bắt đầu nhé.")).toBeInTheDocument()
})
