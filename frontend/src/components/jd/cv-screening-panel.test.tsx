import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test, vi } from "vitest"

import { CVScreeningPanel } from "@/components/jd/cv-screening-panel"
import type { CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"
import type { JDAnalysisResponse } from "@/components/jd/jd-upload-panel"

const registerJob = vi.fn()

vi.mock("@/components/dashboard/job-tracker", () => ({
  useJobTracker: () => ({ registerJob }),
}))

vi.mock("@/components/navigation/app-link", () => ({
  AppLink: ({
    href,
    children,
    className,
  }: {
    href: string
    children: React.ReactNode
    className?: string
  }) => (
    <a className={className} href={href}>
      {children}
    </a>
  ),
}))

function buildJD(): JDAnalysisResponse {
  return {
    jd_id: "jd-123",
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
        required_skills: [],
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

function buildRecentScreenings(): CVScreeningHistoryItem[] {
  return [
    {
      screening_id: "screening-1",
      jd_id: "jd-123",
      candidate_id: "candidate-1",
      file_name: "candidate-a.pdf",
      created_at: "2026-04-18T12:15:00.000Z",
      recommendation: "review",
      match_score: 0.78,
    },
    {
      screening_id: "screening-2",
      jd_id: "jd-123",
      candidate_id: "candidate-2",
      file_name: "candidate-b.pdf",
      created_at: "2026-04-18T12:20:00.000Z",
      recommendation: "advance",
      match_score: 0.91,
    },
  ]
}

test("renders the recent CV screenings toggle in phase 2", () => {
  render(
    <CVScreeningPanel
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      jd={buildJD()}
      recentScreenings={buildRecentScreenings()}
    />,
  )

  expect(screen.getByText("CV đã tải gần đây")).toBeInTheDocument()
  expect(screen.getByRole("button", { name: /CV đã tải gần đây/i })).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByRole("link", { name: /candidate-a\.pdf/i })).not.toBeInTheDocument()
})

test("toggles the recent CV screenings section open and closed", async () => {
  render(
    <CVScreeningPanel
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      jd={buildJD()}
      recentScreenings={buildRecentScreenings()}
    />,
  )

  const user = userEvent.setup()
  const toggleButton = screen.getByRole("button", { name: /CV đã tải gần đây/i })

  expect(toggleButton).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByRole("link", { name: /candidate-a\.pdf/i })).not.toBeInTheDocument()

  await user.click(toggleButton)

  expect(toggleButton).toHaveAttribute("aria-expanded", "true")
  expect(screen.getByRole("link", { name: /candidate-a\.pdf/i })).toHaveAttribute(
    "href",
    "/dashboard/cv-screenings/screening-1",
  )
  expect(screen.getByRole("link", { name: /candidate-b\.pdf/i })).toHaveAttribute(
    "href",
    "/dashboard/cv-screenings/screening-2",
  )

  await user.click(toggleButton)

  expect(toggleButton).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByRole("link", { name: /candidate-a\.pdf/i })).not.toBeInTheDocument()
})

test("submits CV screening through the same-origin api route", async () => {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      screening_id: "screening-3",
      job_id: "job-3",
      file_name: "candidate-c.pdf",
      status: "processing",
      jd_id: "jd-123",
      candidate_id: "candidate-3",
    }),
  })
  vi.stubGlobal("fetch", fetchMock)

  render(
    <CVScreeningPanel
      accessToken="token-123"
      backendBaseUrl="http://localhost:8000"
      jd={buildJD()}
      recentScreenings={buildRecentScreenings()}
    />,
  )

  const user = userEvent.setup()
  const input = screen.getByLabelText("Tệp CV")
  const file = new File(["cv"], "candidate-c.pdf", { type: "application/pdf" })

  await user.upload(input, file)
  await user.click(screen.getByRole("button", { name: "Tải lên và sàng lọc CV" }))

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/cv/screen",
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
      jobId: "job-3",
      resourceId: "screening-3",
      resourceType: "screening",
      title: "candidate-c.pdf",
      accessToken: "token-123",
      backendBaseUrl: "http://localhost:8000",
    }),
  )
})
