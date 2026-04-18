import type { ScreeningResult } from "@/components/jd/cv-screening-types"
import { EmptyValue, ReviewSection } from "@/components/jd/cv-screening-ui"

export function CVScreeningFollowups({
  items,
}: {
  items: ScreeningResult["follow_up_questions"]
}) {
  return (
    <ReviewSection
      title="Câu hỏi follow-up"
      description="Các câu hỏi gợi ý cho người phỏng vấn dựa trên kết quả sàng lọc."
    >
      <div className="space-y-3">
        {items.length ? (
          items.map((item, index) => (
            <article
              className="rounded-[16px] border border-[var(--color-brand-input-border)] p-4"
              key={`${item.question.en}-${index}`}
            >
              <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">{item.question.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.question.en}</p>
              <p className="mt-3 text-sm text-[var(--color-brand-text-body)]">{item.purpose.vi}</p>
              <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.purpose.en}</p>
              {item.linked_dimension ? (
                <p className="mt-3 text-sm font-medium text-[var(--color-brand-text-primary)]">
                  Năng lực liên quan: {item.linked_dimension.vi}
                </p>
              ) : null}
            </article>
          ))
        ) : (
          <EmptyValue text="Không có câu hỏi follow-up" />
        )}
      </div>
    </ReviewSection>
  )
}
