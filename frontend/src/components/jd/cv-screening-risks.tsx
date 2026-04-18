import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection, RiskBadge } from "@/components/jd/cv-screening-ui"

export function CVScreeningRisks({
  items,
}: {
  items: ScreeningResult["risk_flags"]
}) {
  return (
    <ReviewSection
      title="Cờ rủi ro"
      description="Các cảnh báo rõ ràng trong bước sàng lọc mà HR nên xem kỹ."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item, index) => (
            <article
              className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
              key={`${item.title.en}-${index}`}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.vi}</p>
                  <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.en}</p>
                </div>
                <RiskBadge severity={item.severity} />
              </div>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.en}</p>
            </article>
          ))
        ) : (
          <EmptyValue text="Không có cờ rủi ro" />
        )}
      </div>
    </ReviewSection>
  )
}
