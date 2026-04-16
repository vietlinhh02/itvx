import type { Route } from "next"
import Link from "next/link"

import type { CVScreeningHistoryItem } from "@/components/jd/cv-screening-types"

type CVScreeningHistoryProps = {
  title: string
  items: CVScreeningHistoryItem[]
  currentScreeningId?: string
}

export function CVScreeningHistory({ title, items, currentScreeningId }: CVScreeningHistoryProps) {
  return (
    <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Phase 2 history</p>
        <h2 className="text-2xl font-semibold text-[var(--color-brand-text-primary)]">{title}</h2>
      </div>

      {items.length ? (
        <div className="mt-6 space-y-3">
          {items.map((item) => {
            const isCurrent = item.screening_id === currentScreeningId
            return (
              <Link
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
                    {item.recommendation} · score {item.match_score}
                  </p>
                </div>
                <span className="text-xs text-[var(--color-brand-text-muted)]">
                  {isCurrent ? "Current" : new Date(item.created_at).toLocaleString()}
                </span>
              </Link>
            )
          })}
        </div>
      ) : (
        <p className="mt-6 rounded-[16px] border border-dashed border-[var(--color-brand-input-border)] px-4 py-6 text-sm text-[var(--color-brand-text-muted)]">
          No screenings yet.
        </p>
      )}
    </section>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}
