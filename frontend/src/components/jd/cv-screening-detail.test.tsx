import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach } from "vitest"
import { expect, test, vi } from "vitest"

import { CVScreeningDetail } from "@/components/jd/cv-screening-detail"

vi.mock("@/components/jd/cv-screening-history", () => ({
  CVScreeningHistory: ({ title }: { title: string }) => <div>{title}</div>,
}))

vi.mock("@/components/jd/cv-screening-summary", () => ({
  CVScreeningSummary: () => <div>Summary section</div>,
}))

vi.mock("@/components/jd/cv-candidate-profile", () => ({
  CVCandidateProfile: () => <div>Candidate profile section</div>,
}))

vi.mock("@/components/jd/cv-screening-assessments", () => ({
  CVScreeningAssessments: () => <div>Assessments section</div>,
}))

vi.mock("@/components/jd/cv-screening-dimensions", () => ({
  CVScreeningDimensions: () => <div>Dimensions section</div>,
}))

vi.mock("@/components/jd/cv-screening-insights", () => ({
  CVScreeningInsights: () => <div>Insights section</div>,
}))

vi.mock("@/components/jd/cv-screening-followups", () => ({
  CVScreeningFollowups: () => <div>Follow-up section</div>,
}))

vi.mock("@/components/jd/cv-screening-risks", () => ({
  CVScreeningRisks: () => <div>Risks section</div>,
}))

vi.mock("@/components/jd/cv-screening-audit", () => ({
  CVScreeningAudit: () => <div>Audit section</div>,
}))

vi.mock("@/components/interview/interview-launch-panel", () => ({
  InterviewLaunchPanel: ({ defaultCollapsed }: { defaultCollapsed?: boolean }) => (
    <div>
      <span>Launch panel</span>
      {defaultCollapsed ? <span>collapsed</span> : null}
    </div>
  ),
}))

vi.mock("@/components/interview/session-status-card", () => ({
  SessionStatusCard: () => <div>Session status</div>,
}))

vi.mock("@/components/interview/transcript-review", () => ({
  TranscriptReview: () => <div>Transcript review</div>,
}))

vi.mock("@/components/interview/interview-feedback-form", () => ({
  InterviewFeedbackForm: () => <div>Feedback form</div>,
}))

vi.mock("@/components/interview/interview-feedback-analytics", () => ({
  InterviewFeedbackAnalytics: () => <div>Feedback analytics</div>,
}))

vi.mock("@/components/interview/interview-feedback-policy-panel", () => ({
  InterviewFeedbackPolicyPanel: () => <div>Feedback policy</div>,
}))

beforeEach(() => {
  window.sessionStorage.clear()
  vi.stubGlobal("scrollTo", vi.fn())
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callback(0)
    return 0
  })
})

test("switches between screening phases without unmounting the shell", async () => {
  render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-1",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={{
        session_id: "session-1",
        status: "completed",
        worker_status: "idle",
        provider_status: "gemini_live",
        livekit_room_name: "room-1",
        opening_question: "Intro",
        approved_questions: [],
        manual_questions: [],
        question_guidance: null,
        plan: null,
        current_question_index: 0,
        total_questions: 1,
        recommendation: null,
        transcript_turns: [],
        runtime_events: [],
        last_error_code: null,
        last_error_message: null,
      }}
      interviewReview={{
        session_id: "session-1",
        status: "completed",
        transcript_turns: [],
        summary_payload: {},
        ai_competency_assessments: [],
      }}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={null}
      companyDocuments={[]}
    />,
  )

  expect(screen.getByText("Lịch sử sàng lọc của JD này")).toBeInTheDocument()
  expect(screen.getByText("Summary section")).toBeInTheDocument()
  expect(screen.getByText("Candidate profile section")).toBeInTheDocument()

  const user = userEvent.setup()
  await user.click(screen.getByRole("button", { name: "Giai đoạn 4 · Phỏng vấn" }))

  expect(screen.getByText("Launch panel")).toBeInTheDocument()
  expect(screen.getByText("collapsed")).toBeInTheDocument()
  expect(screen.getByText("Session status")).toBeInTheDocument()
  expect(screen.getByText("Transcript review")).toBeInTheDocument()

  await user.click(screen.getByRole("button", { name: "Giai đoạn 5 · Vòng phản hồi" }))

  expect(screen.getByText("Feedback form")).toBeInTheDocument()
  expect(screen.getByText("Feedback analytics")).toBeInTheDocument()
  expect(screen.getByText("Feedback policy")).toBeInTheDocument()
})

test("still shows feedback policy in phase five when interview review is not available yet", async () => {
  render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-policy",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={null}
      interviewReview={null}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={{
        jd_id: "jd-1",
        active_policy: null,
        latest_suggested_policy: null,
        memory_context: [],
        policy_audit_trail: [],
      }}
      companyDocuments={[]}
    />,
  )

  const user = userEvent.setup()
  await user.click(screen.getByRole("button", { name: "Giai đoạn 5 · Vòng phản hồi" }))

  expect(screen.getByText("Feedback policy")).toBeInTheDocument()
})

test("adds consistent spacing between cards in each screening phase", async () => {
  render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-spacing",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={{
        session_id: "session-1",
        status: "completed",
        worker_status: "idle",
        provider_status: "gemini_live",
        livekit_room_name: "room-1",
        opening_question: "Intro",
        approved_questions: [],
        manual_questions: [],
        question_guidance: null,
        plan: null,
        current_question_index: 0,
        total_questions: 1,
        recommendation: null,
        transcript_turns: [],
        runtime_events: [],
        last_error_code: null,
        last_error_message: null,
      }}
      interviewReview={{
        session_id: "session-1",
        status: "completed",
        transcript_turns: [],
        summary_payload: {},
        ai_competency_assessments: [],
      }}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={null}
      companyDocuments={[]}
    />,
  )

  const user = userEvent.setup()

  expect(screen.getByText("Lịch sử sàng lọc của JD này").parentElement).toHaveClass("space-y-6")

  await user.click(screen.getByRole("button", { name: "Giai đoạn 2 · Đánh giá" }))
  expect(screen.getByText("Assessments section").parentElement).toHaveClass("space-y-6")

  await user.click(screen.getByRole("button", { name: "Giai đoạn 3 · Hành động và rà soát" }))
  expect(screen.getByText("Follow-up section").parentElement).toHaveClass("space-y-6")

  await user.click(screen.getByRole("button", { name: "Giai đoạn 5 · Vòng phản hồi" }))
  expect(screen.getByText("Feedback form").parentElement).toHaveClass("space-y-6")
})

test("restores the last selected screening phase after reload", async () => {
  const user = userEvent.setup()

  const { unmount } = render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-restore",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={{
        session_id: "session-1",
        status: "completed",
        worker_status: "idle",
        provider_status: "gemini_live",
        livekit_room_name: "room-1",
        opening_question: "Intro",
        approved_questions: [],
        manual_questions: [],
        question_guidance: null,
        plan: null,
        current_question_index: 0,
        total_questions: 1,
        recommendation: null,
        transcript_turns: [],
        runtime_events: [],
        last_error_code: null,
        last_error_message: null,
      }}
      interviewReview={{
        session_id: "session-1",
        status: "completed",
        transcript_turns: [],
        summary_payload: {},
        ai_competency_assessments: [],
      }}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={null}
      companyDocuments={[]}
    />,
  )

  await user.click(screen.getByRole("button", { name: "Giai đoạn 4 · Phỏng vấn" }))
  expect(screen.getByText("Launch panel")).toBeInTheDocument()

  unmount()

  render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-restore",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={{
        session_id: "session-1",
        status: "completed",
        worker_status: "idle",
        provider_status: "gemini_live",
        livekit_room_name: "room-1",
        opening_question: "Intro",
        approved_questions: [],
        manual_questions: [],
        question_guidance: null,
        plan: null,
        current_question_index: 0,
        total_questions: 1,
        recommendation: null,
        transcript_turns: [],
        runtime_events: [],
        last_error_code: null,
        last_error_message: null,
      }}
      interviewReview={{
        session_id: "session-1",
        status: "completed",
        transcript_turns: [],
        summary_payload: {},
        ai_competency_assessments: [],
      }}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={null}
      companyDocuments={[]}
    />,
  )

  expect(screen.getByText("Launch panel")).toBeInTheDocument()
})

test("restores the previous scroll position for the screening detail page", () => {
  window.sessionStorage.setItem("interviewx:cv-screening-detail:screening-scroll:scroll-y", "240")
  const scrollTo = vi.fn()
  vi.stubGlobal("scrollTo", scrollTo)
  vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
    callback(0)
    return 0
  })

  render(
    <CVScreeningDetail
      screening={{
        screening_id: "screening-scroll",
        jd_id: "jd-1",
        candidate_id: "candidate-1",
        file_name: "candidate-a.pdf",
        created_at: "2026-04-18T00:00:00Z",
        error_message: null,
        status: "completed",
        interview_session_id: "session-1",
        candidate_profile: {
          candidate_summary: {
            full_name: "Nguyen Van A",
            current_title: "Backend Engineer",
            location: "Ho Chi Minh City",
            total_years_experience: 4,
            seniority_signal: "mid",
            professional_summary: {
              vi: "Ky su backend.",
              en: "Backend engineer.",
            },
          },
          work_experience: [],
          projects: [],
          skills_inventory: [],
          education: [],
          certifications: [],
          languages: [],
          profile_uncertainties: [],
        },
        interview_draft: null,
        result: {
          match_score: 0.82,
          recommendation: "advance",
          decision_reason: { vi: "Phu hop.", en: "Strong fit." },
          screening_summary: { vi: "Tom tat.", en: "Summary." },
          knockout_assessments: [],
          minimum_requirement_checks: [],
          dimension_scores: [],
          strengths: [],
          gaps: [],
          uncertainties: [],
          follow_up_questions: [],
          risk_flags: [],
        },
        audit: {
          extraction_model: "model-a",
          screening_model: "model-b",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [],
          consistency_flags: [],
        },
      }}
      historyItems={[]}
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      interviewDetail={null}
      interviewReview={null}
      interviewFeedback={null}
      feedbackSummary={null}
      feedbackPolicy={null}
      companyDocuments={[]}
    />,
  )

  expect(scrollTo).toHaveBeenCalledWith({ top: 240, behavior: "auto" })
})
