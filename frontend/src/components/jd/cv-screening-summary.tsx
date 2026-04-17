import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import { ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningSummary({ result }: { result: ScreeningResult }) {
  const scorePercentage = `${Math.round(result.match_score * 100)}%`
  const recommendationLabel =
    result.recommendation === "advance"
      ? "Nên mời vào vòng tiếp theo"
      : result.recommendation === "review"
        ? "Cần xem xét thêm"
        : "Không phù hợp để đi tiếp"

  return (
    <ReviewSection
      title="Tóm tắt kết quả sàng lọc"
      description="Kết luận đề xuất, mức độ phù hợp và phần tóm tắt để HR xem nhanh trước khi ra quyết định."
    >
      <div className="space-y-4">
        <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
          <p className="text-sm font-semibold text-[var(--color-brand-primary)]">
            Đề xuất xử lý
          </p>
          <p className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
            {recommendationLabel}
          </p>
          <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
            Mức độ phù hợp với JD: {scorePercentage}
          </p>
        </div>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Tóm tắt kết quả</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.screening_summary.vi}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.screening_summary.en}</p>
        </article>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Lý do đưa ra quyết định</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.decision_reason.vi}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.decision_reason.en}</p>
        </article>
      </div>
    </ReviewSection>
  )
}
