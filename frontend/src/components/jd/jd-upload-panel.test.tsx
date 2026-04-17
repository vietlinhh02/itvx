import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, expect, test, vi } from "vitest"

import { JDUploadPanel } from "@/components/jd/jd-upload-panel"

const registerJob = vi.fn()

vi.mock("@/components/dashboard/job-tracker", () => ({
  useJobTracker: () => ({ registerJob }),
}))

afterEach(() => {
  vi.restoreAllMocks()
  registerJob.mockReset()
})

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
    "http://localhost:8000/api/v1/jd/analyze",
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
