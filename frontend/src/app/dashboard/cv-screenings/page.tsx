import { getServerSession } from "next-auth"
import type { Route } from "next"
import { redirect } from "next/navigation"

import { AppLink } from "@/components/navigation/app-link"
import { authOptions } from "@/lib/auth-options"
import { formatVietnamDate } from "@/lib/datetime"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type ScreeningListItem = {
  screening_id: string
  jd_id: string
  candidate_id: string
  file_name: string
  created_at: string
  recommendation: "advance" | "review" | "reject"
  match_score: number
}

const RECOMMENDATION_STYLES: Record<string, string> = {
  advance:
    "bg-emerald-50 text-emerald-700",
  review:
    "bg-amber-50 text-amber-700",
  reject:
    "bg-rose-50 text-rose-700",
}

export default async function CVScreeningsPage() {
  const session = await getServerSession(authOptions)

  if (!session?.accessToken || !backendBaseUrl) {
    redirect("/login")
  }

  const response = await fetch(`${backendBaseUrl}/api/v1/cv/screenings`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
    },
    cache: "no-store",
  })

  if (!response.ok) {
    redirect("/login")
  }

  const { items } = (await response.json()) as { items: ScreeningListItem[] }

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)]">
        <div>
          <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Lịch sử</p>
          <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
            Sàng lọc CV
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
            Rà soát tất cả kết quả sàng lọc CV của ứng viên trên mọi JD.
          </p>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4">
          {items.length ? (
            items.map((item) => (
              <AppLink
                className="group rounded-[14px] border border-[var(--color-brand-input-border)] p-3 transition duration-200 hover:-translate-y-0.5 hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                href={buildScreeningRoute(item.screening_id)}
                key={item.screening_id}
              >
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={[
                      "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                      RECOMMENDATION_STYLES[item.recommendation] ?? "bg-gray-50 text-gray-700",
                    ].join(" ")}
                  >
                    {formatRecommendation(item.recommendation)}
                  </span>
                  <span className="text-[10px] tabular-nums text-[var(--color-brand-text-muted)]">
                    {Math.round(item.match_score * 100)}%
                  </span>
                </div>
                <p className="mt-2 truncate text-sm font-semibold text-[var(--color-brand-text-primary)]">
                  {item.file_name}
                </p>
                <p className="mt-1 text-[10px] text-[var(--color-brand-text-muted)]">
                  {formatVietnamDate(item.created_at)}
                </p>
              </AppLink>
            ))
          ) : (
            <p className="col-span-full rounded-[14px] border border-dashed border-[var(--color-brand-input-border)] p-3 text-sm text-[var(--color-brand-text-muted)]">
              Chưa có lượt sàng lọc CV nào. Hãy tải một CV từ trang chi tiết JD để tạo danh sách này.
            </p>
          )}
        </div>
      </section>
    </main>
  )
}

function buildScreeningRoute(screeningId: string): Route {
  return `/dashboard/cv-screenings/${screeningId}` as Route
}

function formatRecommendation(recommendation: ScreeningListItem["recommendation"]) {
  if (recommendation === "advance") {
    return "Nên mời vào vòng tiếp theo"
  }
  if (recommendation === "review") {
    return "Cần xem xét thêm"
  }
  return "Không phù hợp để đi tiếp"
}
