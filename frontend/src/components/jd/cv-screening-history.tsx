import { CaretDown } from "@phosphor-icons/react"
import type { Route } from "next"
import type { CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"
import { AppLink } from "@/components/navigation/app-link"
import { formatVietnamDateTime } from "@/lib/datetime"
import { useState } from "react"

type CVScreeningHistoryProps = {
  title: string
  items: CVScreeningHistoryItem[]
  currentScreeningId?: string
}

export function CVScreeningHistory({ title, items, currentScreeningId }: CVScreeningHistoryProps) {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <button
        aria-controls="cv-screening-history"
        aria-expanded={isOpen}
        className="flex w-full items-start justify-between gap-3 text-left"
        onClick={() => setIsOpen((current) => !current)}
        type="button"
      >
        <div className="flex flex-col gap-2">
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Lịch sử giai đoạn 2</p>
          <h2 className="text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
            {items.length} lượt
          </span>
          <CaretDown
            className={`mt-1 text-[var(--color-brand-text-muted)] transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
            size={18}
            weight="bold"
          />
        </div>
      </button>

      {isOpen ? (
        items.length ? (
          <div id="cv-screening-history" className="mt-6 space-y-3">
            {items.map((item) => {
              const isCurrent = item.screening_id === currentScreeningId
              return (
                <AppLink
                  key={item.screening_id}
                  className={[
                    "flex items-center justify-between rounded-[16px] border px-4 py-3",
                    isCurrent
                      ? "border-[var(--color-brand-primary)] bg-[var(--color-primary-50)]"
                      : "border-[var(--color-brand-input-border)]",
                  ].join(" ")}
                  href={buildScreeningRoute(item.screening_id)}
                >
                  <div>
                    <p className="text-sm font-semibold text-[var(--color-brand-text-primary)]">
                      {item.file_name}
                    </p>
                    <p className="text-sm text-[var(--color-brand-text-body)]">
                      {formatRecommendation(item.recommendation)} · Mức độ phù hợp {Math.round(item.match_score * 100)}%
                    </p>
                  </div>
                  <span className="text-xs text-[var(--color-brand-text-muted)]">
                    {isCurrent ? "Hiện tại" : formatVietnamDateTime(item.created_at)}
                  </span>
                </AppLink>
              )
            })}
          </div>
        ) : (
          <p
            id="cv-screening-history"
            className="mt-6 rounded-[16px] border border-dashed border-[var(--color-brand-input-border)] px-4 py-6 text-sm text-[var(--color-brand-text-muted)]"
          >
            Chưa có lượt sàng lọc nào.
          </p>
        )
      ) : null}
    </section>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}

function formatRecommendation(recommendation: CVScreeningHistoryItem["recommendation"]) {
  if (recommendation === "advance") {
    return "Nên mời vào vòng tiếp theo"
  }
  if (recommendation === "review") {
    return "Cần xem xét thêm"
  }
  return "Không phù hợp để đi tiếp"
}
