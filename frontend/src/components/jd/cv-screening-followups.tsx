import type { CVScreeningResponse } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningFollowups({
  items,
}: {
  items: CVScreeningResponse["result"]["follow_up_questions"]
}) {
  return (
    <ReviewSection
      title="Follow-up Questions"
      description="Suggested interviewer prompts grounded in the screening output."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item) => (
            <article className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4" key={item.question.en}>
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.question.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.question.vi}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.purpose.en}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.purpose.vi}</p>
              {item.linked_dimension ? (
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Linked dimension: {item.linked_dimension.en}
                </p>
              ) : null}
            </article>
          ))
        ) : (
          <EmptyValue text="No follow-up questions" />
        )}
      </div>
    </ReviewSection>
  )
}
