import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test, vi } from "vitest"

import { CVScreeningHistory } from "@/components/jd/cv-screening-history"
import type { CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"

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

function buildHistoryItems(): CVScreeningHistoryItem[] {
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

test("renders the screening history toggle collapsed by default", () => {
  render(<CVScreeningHistory title="Lịch sử sàng lọc của JD này" items={buildHistoryItems()} currentScreeningId="screening-1" />)

  expect(screen.getByRole("button", { name: /Lịch sử sàng lọc của JD này/i })).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByRole("link", { name: /candidate-a\.pdf/i })).not.toBeInTheDocument()
})

test("toggles the screening history section open and closed", async () => {
  render(<CVScreeningHistory title="Lịch sử sàng lọc của JD này" items={buildHistoryItems()} currentScreeningId="screening-1" />)

  const user = userEvent.setup()
  const toggleButton = screen.getByRole("button", { name: /Lịch sử sàng lọc của JD này/i })

  await user.click(toggleButton)

  expect(toggleButton).toHaveAttribute("aria-expanded", "true")
  expect(screen.getByRole("link", { name: /candidate-a\.pdf/i })).toHaveAttribute(
    "href",
    "/dashboard/cv-screenings/screening-1",
  )

  await user.click(toggleButton)

  expect(toggleButton).toHaveAttribute("aria-expanded", "false")
  expect(screen.queryByRole("link", { name: /candidate-a\.pdf/i })).not.toBeInTheDocument()
})
