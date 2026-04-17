import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import { EmptyValue, EvidenceList, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningInsights({
  strengths,
  gaps,
  uncertainties,
}: {
  strengths: ScreeningResult["strengths"]
  gaps: ScreeningResult["gaps"]
  uncertainties: ScreeningResult["uncertainties"]
}) {
  return (
    <ReviewSection
      title="Nhận định nổi bật"
      description="Tóm tắt những điểm mạnh, điểm còn thiếu và các phần cần xác minh thêm từ kết quả sàng lọc."
    >
      <div className="grid gap-6 xl:grid-cols-3">
        <InsightGroup items={strengths} title="Điểm mạnh" emptyText="Không có điểm mạnh" />
        <InsightGroup items={gaps} title="Điểm còn thiếu" emptyText="Không có điểm còn thiếu đáng chú ý" />
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
  items: ScreeningResult["strengths"]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.en}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.en}</p>
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
  items: ScreeningResult["uncertainties"]
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">Điểm chưa chắc chắn</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.title.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.title.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.title.en}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.reason.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.en}</p>
              <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                Gợi ý follow-up: {item.follow_up_suggestion.vi}
              </p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                {item.follow_up_suggestion.en}
              </p>
            </article>
          ))
        ) : (
          <EmptyValue text="Không có điểm chưa chắc chắn" />
        )}
      </div>
    </section>
  )
}
