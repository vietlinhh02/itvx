import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import {
  BilingualBlock,
  EmptyValue,
  EvidenceList,
  PriorityBadge,
  ReviewSection,
} from "@/components/jd/cv-screening-ui"

export function CVScreeningDimensions({
  dimensions,
}: {
  dimensions: ScreeningResult["dimension_scores"]
}) {
  return (
    <ReviewSection
      title="Điểm theo từng năng lực"
      description="Đánh giá theo từng năng lực có trọng số từ engine sàng lọc của backend."
    >
      <div className="space-y-4">
        {dimensions.length ? (
          dimensions.map((dimension) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={dimension.dimension_name.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <BilingualBlock value={dimension.dimension_name} />
                <PriorityBadge priority={dimension.priority} />
              </div>
              <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <Metric label="Trọng số" value={String(dimension.weight)} />
                <Metric label="Điểm" value={`${Math.round(dimension.score * 100)}%`} />
                <Metric label="Mức ưu tiên" value={dimension.priority.replaceAll("_", " ")} />
              </div>
              <div className="mt-4">
                <p className="text-sm text-[var(--color-brand-text-body)]">{dimension.reason.vi}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{dimension.reason.en}</p>
              </div>
              {dimension.confidence_note ? (
                <div className="mt-4 rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2">
                  <p className="text-sm font-medium text-[var(--color-brand-text-primary)]">
                    {dimension.confidence_note.vi}
                  </p>
                  <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">
                    {dimension.confidence_note.en}
                  </p>
                </div>
              ) : null}
              <EvidenceList items={dimension.evidence} />
            </article>
          ))
        ) : (
          <EmptyValue text="Không có điểm theo năng lực" />
        )}
      </div>
    </ReviewSection>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] bg-[var(--color-primary-50)] px-3 py-2">
      <p className="text-xs text-[var(--color-brand-text-muted)]">{label}</p>
      <p className="mt-2 text-sm font-medium capitalize text-[var(--color-brand-text-primary)]">{value}</p>
    </div>
  )
}
