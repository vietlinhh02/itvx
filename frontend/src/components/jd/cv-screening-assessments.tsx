import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import {
  BilingualBlock,
  EmptyValue,
  EvidenceList,
  ReviewSection,
  StatusBadge,
} from "@/components/jd/cv-screening-ui"

export function CVScreeningAssessments({
  knockoutAssessments,
  minimumRequirements,
}: {
  knockoutAssessments: ScreeningResult["knockout_assessments"]
  minimumRequirements: ScreeningResult["minimum_requirement_checks"]
}) {
  return (
    <ReviewSection
      title="Đánh giá yêu cầu"
      description="Các kiểm tra loại trực tiếp và yêu cầu tối thiểu được dùng cho khuyến nghị cuối."
    >
      <div className="grid gap-6 xl:grid-cols-2">
        <AssessmentGroup
          title="Đánh giá loại trực tiếp"
          items={knockoutAssessments}
          emptyText="Không có quy tắc loại trực tiếp"
        />
        <AssessmentGroup
          title="Yêu cầu tối thiểu"
          items={minimumRequirements}
          emptyText="Không có yêu cầu tối thiểu"
        />
      </div>
    </ReviewSection>
  )
}

function AssessmentGroup({
  title,
  items,
  emptyText,
}: {
  title: string
  items: ScreeningResult["knockout_assessments"]
  emptyText: string
}) {
  return (
    <section>
      <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{title}</p>
      <div className="mt-3 space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.criterion.en}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <BilingualBlock value={item.criterion} />
                <StatusBadge status={item.status} />
              </div>
              <div className="mt-3">
                <p className="text-sm text-[var(--color-brand-text-body)]">{item.reason.en}</p>
                <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.reason.vi}</p>
              </div>
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
