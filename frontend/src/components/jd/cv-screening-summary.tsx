import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningSummary({ result }: { result: CVScreeningResponse["result"] }) {
  const scorePercentage = `${Math.round(result.match_score * 100)}%`

  return (
    <ReviewSection
      title="Screening Summary"
      description="Top-level recommendation, score, and summary for HR review."
    >
      <div className="space-y-4">
        <div className="rounded-[16px] bg-[var(--color-primary-50)] p-4">
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--color-brand-primary)]">
            Recommendation
          </p>
          <p className="mt-2 text-2xl font-semibold capitalize text-[var(--color-brand-text-primary)]">
            {result.recommendation}
          </p>
          <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
            Match score: {scorePercentage}
          </p>
        </div>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Screening summary</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.screening_summary.en}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.screening_summary.vi}</p>
        </article>
        <article>
          <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Decision reason</p>
          <p className="mt-2 text-sm text-[var(--color-brand-text-body)]">{result.decision_reason.en}</p>
          <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{result.decision_reason.vi}</p>
        </article>
      </div>
    </ReviewSection>
  )
}
