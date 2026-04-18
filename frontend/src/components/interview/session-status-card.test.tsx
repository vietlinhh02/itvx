import { render, screen } from "@testing-library/react"
import { expect, test } from "vitest"

import { SessionStatusCard } from "@/components/interview/session-status-card"

test("shows the latest worker error when the session is finishing but summary generation failed", () => {
  render(
    <SessionStatusCard
      status="finishing"
      workerStatus="failed"
      providerStatus="closing"
      lastErrorCode="review_generation_failed"
      lastErrorMessage="Không thể tạo bản tổng kết cuối vì worker đã dừng sớm."
    />,
  )

  expect(screen.getByText("finishing")).toBeInTheDocument()
  expect(screen.getByText("failed")).toBeInTheDocument()
  expect(screen.getByText("closing")).toBeInTheDocument()
  expect(screen.getByText("review_generation_failed")).toBeInTheDocument()
  expect(screen.getByText("Không thể tạo bản tổng kết cuối vì worker đã dừng sớm.")).toBeInTheDocument()
})
