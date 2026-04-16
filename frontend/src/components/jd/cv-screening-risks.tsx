import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection, RiskBadge } from "@/components/jd/cv-screening-ui"

export function CVScreeningRisks({
  items,
}: {
  items: CVScreeningResponse["result"]["risk_flags"]
}) {
  return (
    <ReviewSection
      title="Risk Flags"
      description="Explicit screening warnings that HR should review carefully."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.en}</p>
                  <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.vi}</p>
                </div>
                <RiskBadge severity={item.severity} />
              </div>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
            </article>
          ))
        ) : (
          <EmptyValue text="No risk flags" />
        )}
      </div>
    </ReviewSection>
  )
}
