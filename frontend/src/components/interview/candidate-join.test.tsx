import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, beforeEach, expect, test, vi } from "vitest"

import { CandidateJoin } from "@/components/interview/candidate-join"

beforeEach(() => {
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
  vi.restoreAllMocks()
})

test("shows join error message when backend join fails", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }))

  render(<CandidateJoin token="share-token-1" backendBaseUrl="http://localhost:8000" />)

  await userEvent.setup().type(screen.getByLabelText("Tên của bạn"), "Nguyen Van A")
  await userEvent.setup().click(screen.getByRole("button", { name: "Tham gia phỏng vấn" }))

  expect(await screen.findByText("Không thể tham gia buổi phỏng vấn này.")).toBeInTheDocument()
})
