import { render, screen } from "@testing-library/react"
import { afterEach, expect, test, vi } from "vitest"

import { CVScreeningAudit } from "@/components/jd/cv-screening-audit"
import { CVScreeningFollowups } from "@/components/jd/cv-screening-followups"
import { CVScreeningRisks } from "@/components/jd/cv-screening-risks"

afterEach(() => {
  vi.restoreAllMocks()
})

test("phase 3 lists render duplicate backend items without duplicate-key warnings", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => {})

  render(
    <>
      <CVScreeningAudit
        audit={{
          extraction_model: "extract-model",
          screening_model: "screen-model",
          profile_schema_version: "1",
          screening_schema_version: "1",
          generated_at: "2026-04-18T00:00:00Z",
          reconciliation_notes: [
            "Recomputed weighted match score from dimension scores.",
            "Recomputed weighted match score from dimension scores.",
          ],
          consistency_flags: [
            "Must-have dimension lacks supporting evidence.",
            "Must-have dimension lacks supporting evidence.",
          ],
        }}
      />
      <CVScreeningFollowups
        items={[
          {
            question: {
              vi: "Bạn có thể chia sẻ ví dụ rõ hơn không?",
              en: "Can you share a clearer example?",
            },
            purpose: {
              vi: "Làm rõ bằng chứng cho năng lực chính.",
              en: "Clarify evidence for the key dimension.",
            },
            linked_dimension: {
              vi: "Phân tích nghiệp vụ",
              en: "Business analysis",
            },
          },
          {
            question: {
              vi: "Bạn có thể chia sẻ ví dụ rõ hơn không?",
              en: "Can you share a clearer example?",
            },
            purpose: {
              vi: "Làm rõ bằng chứng cho năng lực chính.",
              en: "Clarify evidence for the key dimension.",
            },
            linked_dimension: {
              vi: "Phân tích nghiệp vụ",
              en: "Business analysis",
            },
          },
        ]}
      />
      <CVScreeningRisks
        items={[
          {
            title: {
              vi: "Thiếu bằng chứng về chiều sâu chuyên môn",
              en: "Lacks evidence for technical depth",
            },
            reason: {
              vi: "CV không nêu rõ kết quả định lượng.",
              en: "The CV does not provide quantified outcomes.",
            },
            severity: "high",
          },
          {
            title: {
              vi: "Thiếu bằng chứng về chiều sâu chuyên môn",
              en: "Lacks evidence for technical depth",
            },
            reason: {
              vi: "CV không nêu rõ kết quả định lượng.",
              en: "The CV does not provide quantified outcomes.",
            },
            severity: "high",
          },
        ]}
      />
    </>,
  )

  expect(
    screen.getAllByText("Must-have dimension lacks supporting evidence."),
  ).toHaveLength(2)
  expect(screen.getAllByText("Can you share a clearer example?")).toHaveLength(2)
  expect(screen.getAllByText("Lacks evidence for technical depth")).toHaveLength(2)

  const duplicateKeyWarnings = consoleError.mock.calls.filter((call) =>
    call.some(
      (value) =>
        typeof value === "string" && value.includes("Encountered two children with the same key"),
    ),
  )

  expect(duplicateKeyWarnings).toHaveLength(0)
})
