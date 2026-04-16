import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, EvidenceList, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningInsights({
  strengths,
  gaps,
  uncertainties,
}: {
  strengths: CVScreeningResponse["result"]["strengths"]
  gaps: CVScreeningResponse["result"]["gaps"]
  uncertainties: CVScreeningResponse["result"]["uncertainties"]
}) {
  return (
    <ReviewSection
      title="Insights"
      description="Strengths, gaps, and unresolved uncertainties extracted from the screening output."
    >
      <div className="grid gap-6 xl:grid-cols-3">
        <InsightGroup items={strengths} title="Strengths" emptyText="No strengths" />
        <InsightGroup items={gaps} title="Gaps" emptyText="No gaps" />
        <UncertaintyGroup items={uncertainties} />
      </div>
    </ReviewSection>
  )
}

function InsightGroup({
  title,
  items,
  emptyText,
}: {
  title: string
  items: CVScreeningResponse["result"]["strengths"]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              <EvidenceList items={item.evidence} />
            </article>
          ))
        ) : (
          <EmptyValue text={emptyText} />
        )}
      </div>
    </section>
  )
}

function UncertaintyGroup({
  items,
}: {
  items: CVScreeningResponse["result"]["uncertainties"]
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Uncertainties</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                Follow-up: {item.follow_up_suggestion.en}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                {item.follow_up_suggestion.vi}
              </p>
            </article>
          ))
        ) : (
          <EmptyValue text="No uncertainties" />
        )}
      </div>
    </section>
  )
}
