import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { JDAnalysisContent, JDUploadPanel } from "@/components/jd/jd-upload-panel"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

const registerJob = vi.fn()

vi.mock("@/components/dashboard/job-tracker", () => ({
  useJobTracker: () => ({ registerJob }),
}))

afterEach(() => {
  vi.restoreAllMocks()
  registerJob.mockReset()
})

function buildAnalysisResult(): JDAnalysisResponse {
  return {
    jd_id: "c4566375-d73b-4bd3-895a-e0ce464b9586",
    file_name: "backend-lead.pdf",
    status: "completed",
    created_at: "2026-04-18T12:00:00.000Z",
    analysis: {
      job_overview: {
        job_title: { vi: "Truong nhom Backend", en: "Backend Lead" },
        department: { vi: "Ky thuat", en: "Engineering" },
        seniority_level: "Senior",
        location: { vi: "TP HCM", en: "Ho Chi Minh City" },
        work_mode: "Hybrid",
        role_summary: { vi: "Dan dat doi ngu backend", en: "Lead the backend team" },
        company_benefits: [],
      },
      requirements: {
        required_skills: ["Node.js"],
        preferred_skills: [],
        tools_and_technologies: [],
        experience_requirements: {
          minimum_years: 5,
          relevant_roles: [],
          preferred_domains: [],
        },
        education_and_certifications: [],
        language_requirements: [],
        key_responsibilities: [],
        screening_knockout_criteria: [],
      },
      rubric_seed: {
        evaluation_dimensions: [],
        screening_rules: {
          minimum_requirements: [],
          scoring_principle: "Cham dua tren bang chung",
        },
        ambiguities_for_human_review: [],
      },
    },
  }
}

test("uploads a JD file and registers the background job", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      job_id: "job-123",
      jd_id: "jd-123",
      file_name: "backend-lead.pdf",
      status: "processing",
    }),
  })
  vi.stubGlobal("fetch", fetchMock)

  render(<JDUploadPanel accessToken="token-123" backendBaseUrl="http://localhost:8000" />)

  const user = userEvent.setup()
  const input = screen.getByLabelText("Tệp mô tả công việc")
  const file = new File(["jd"], "backend-lead.pdf", { type: "application/pdf" })

  await user.upload(input, file)
  await user.click(screen.getByRole("button", { name: "Tải lên và phân tích" }))

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/jd/analyze",
    expect.objectContaining({
      method: "POST",
      headers: expect.objectContaining({
        Authorization: "Bearer token-123",
      }),
      body: expect.any(FormData),
    }),
  )

  await waitFor(() =>
    expect(registerJob).toHaveBeenCalledWith({
      jobId: "job-123",
      resourceId: "jd-123",
      resourceType: "jd",
      title: "backend-lead.pdf",
      accessToken: "token-123",
      backendBaseUrl: "http://localhost:8000",
    }),
  )
})

test("shows a quick jump action to the JD's CV screening section", () => {
  render(<JDAnalysisContent result={buildAnalysisResult()} />)

  const screeningLink = screen.getByRole("link", { name: "Xem nhanh phần sàng lọc CV" })

  expect(screeningLink).toHaveAttribute("href", "#cv-screening-panel")
  expect(screen.getByText("Trạng thái: Hoàn tất")).toBeInTheDocument()
})
