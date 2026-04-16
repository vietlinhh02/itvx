import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
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
  knockoutAssessments: CVScreeningResponse["result"]["knockout_assessments"]
  minimumRequirements: CVScreeningResponse["result"]["minimum_requirement_checks"]
}) {
  return (
    <ReviewSection
      title="Requirement Assessments"
      description="Knockout and minimum requirement checks used for the final recommendation."
    >
      <div className="grid gap-6 xl:grid-cols-2">
        <AssessmentGroup
          title="Knockout assessments"
          items={knockoutAssessments}
          emptyText="No knockout rules"
        />
        <AssessmentGroup
          title="Minimum requirements"
          items={minimumRequirements}
          emptyText="No minimum requirements"
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
  items: CVScreeningResponse["result"]["knockout_assessments"]
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
