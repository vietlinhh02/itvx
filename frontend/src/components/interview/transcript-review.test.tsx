import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { expect, test } from "vitest"

import { TranscriptReview } from "@/components/interview/transcript-review"

test("renders AI competency assessments from the top-level review payload when the summary payload is empty", () => {
  render(
    <TranscriptReview
      summary={{}}
      turns={[]}
      aiCompetencyAssessments={[
        {
          competency_name: { vi: "Tư duy hệ thống", en: "Systems Thinking" },
          ai_score: 0.78,
          evidence_strength: 0.81,
          needs_hr_review: true,
          notes: "Có dẫn chứng rõ ràng từ phần trao đổi về kiến trúc.",
        },
      ]}
    />,
  )

  expect(screen.getByText("Tư duy hệ thống")).toBeInTheDocument()
  const hrReviewBadge = screen.getByText("Cần HR xem lại")

  expect(hrReviewBadge).toBeInTheDocument()
  expect(hrReviewBadge).toHaveClass("bg-sky-50")
  expect(hrReviewBadge).not.toHaveClass("bg-amber-50")
  expect(screen.getByText(/78%/i)).toBeInTheDocument()
})

test("parses nested JSON summaries, suppresses empty strengths, and renders only meaningful highlights", async () => {
  const user = userEvent.setup()

  render(
    <TranscriptReview
      summary={{
        final_summary: `\`\`\`json
${JSON.stringify({
  final_summary:
    "Ứng viên thể hiện thái độ tiêu cực và thiếu kỹ năng giao tiếp chuyên nghiệp.",
  strengths: "Không có.",
  concerns: [
    "Thiếu nền tảng tư duy và kiến thức chuyên môn.",
    "Khả năng giao tiếp kém, không phản hồi đúng trọng tâm câu hỏi.",
  ],
  recommendation: "Từ chối (Reject) - Cần HR xem xét kỹ lưỡng hồ sơ và lịch sử ứng tuyển.",
  completion_reason: "escalate_hr",
  turn_breakdown: [
    {
      sequence_number: 0,
      speaker: "agent",
      assessment: "Câu hỏi khởi đầu về học thuật.",
    },
    {
      sequence_number: 1,
      speaker: "candidate",
      assessment: "Phản hồi tiêu cực về cơ sở đào tạo, thiếu tư duy chuyên môn.",
    },
    {
      sequence_number: 2,
      speaker: "agent",
      transcript_text: "Cố gắng tìm kiếm bằng chứng thực tế.",
    },
  ],
  competency_assessments: [
    {
      competency_name: "Academic Background",
      ai_score: 0,
      evidence_strength: "none",
      needs_hr_review: true,
      notes: "Ứng viên không thể nêu kiến thức đã học.",
    },
  ],
})}
\`\`\``,
      }}
      turns={[]}
    />,
  )

  expect(
    screen.getByText("Ứng viên thể hiện thái độ tiêu cực và thiếu kỹ năng giao tiếp chuyên nghiệp."),
  ).toBeInTheDocument()
  expect(
    screen.getByText("Từ chối (Reject) - Cần HR xem xét kỹ lưỡng hồ sơ và lịch sử ứng tuyển."),
  ).toBeInTheDocument()
  expect(
    screen
      .getByText("Từ chối (Reject) - Cần HR xem xét kỹ lưỡng hồ sơ và lịch sử ứng tuyển.")
      .closest("article"),
  ).toHaveClass("bg-[var(--color-primary-50)]")
  expect(screen.getByText("Không có điểm mạnh")).toBeInTheDocument()
  expect(screen.getByText("Academic Background")).toBeInTheDocument()
  expect(screen.getByText(/Độ tin cậy của bằng chứng:\s*Không có/i)).toBeInTheDocument()
  expect(screen.queryAllByRole("listitem")).toHaveLength(0)
  expect(screen.queryByText(/"turn_breakdown"/i)).not.toBeInTheDocument()
  expect(screen.queryByText("Chưa có tóm tắt điểm nổi bật")).not.toBeInTheDocument()
  expect(screen.queryByText("Cố gắng tìm kiếm bằng chứng thực tế.")).not.toBeInTheDocument()

  const highlightsToggle = screen.getByRole("button", { name: /Điểm nổi bật của buổi phỏng vấn/i })

  expect(highlightsToggle).toHaveAttribute("aria-expanded", "false")

  await user.click(highlightsToggle)

  expect(highlightsToggle).toHaveAttribute("aria-expanded", "true")
  expect(screen.getByText("Câu hỏi khởi đầu về học thuật.")).toBeInTheDocument()
  expect(
    screen.getByText("Phản hồi tiêu cực về cơ sở đào tạo, thiếu tư duy chuyên môn."),
  ).toBeInTheDocument()
})
