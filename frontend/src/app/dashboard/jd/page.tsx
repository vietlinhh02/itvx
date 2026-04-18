import { getServerSession } from "next-auth"
import type { Route } from "next"
import { redirect } from "next/navigation"

import { DashboardSystemErrorState } from "@/components/dashboard/dashboard-system-error-state"
import { JDUploadPanel } from "@/components/jd/jd-upload-panel"
import { AppLink } from "@/components/navigation/app-link"
import { authOptions } from "@/lib/auth-options"
import { fetchDashboardJson } from "@/lib/dashboard-server"
import { formatVietnamDateTime } from "@/lib/datetime"

const backendBaseUrl = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL

type JDRecentItem = {
  jd_id: string
  file_name: string
  status: string
  created_at: string
  job_title: string | null
}

export default async function JDDashboardPage() {
  const session = await getServerSession(authOptions)

  if (!session?.accessToken) {
    redirect("/login")
  }

  if (!backendBaseUrl) {
    return (
      <DashboardSystemErrorState
        title="Không thể tải danh sách JD"
        description="Ứng dụng chưa được cấu hình địa chỉ backend. Hãy kiểm tra API_URL hoặc NEXT_PUBLIC_API_URL."
      />
    )
  }

  const recentResult = await fetchDashboardJson<JDRecentItem[]>({
    accessToken: session.accessToken,
    resourceLabel: "recent JD uploads",
    url: `${backendBaseUrl}/api/v1/jd`,
  })

  if (recentResult.kind === "auth") {
    redirect("/login")
  }

  if (recentResult.kind !== "success") {
    return (
      <DashboardSystemErrorState
        title="Không thể tải danh sách JD"
        description="Backend đang lỗi hoặc không phản hồi khi tải danh sách JD gần đây."
        status={recentResult.status}
      />
    )
  }

  const recentUploads = recentResult.kind === "success" ? recentResult.data : []

  return (
    <main className="flex w-full flex-col gap-6 py-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.8fr)_minmax(360px,0.9fr)]">
        <JDUploadPanel accessToken={session.accessToken} backendBaseUrl={backendBaseUrl} />

        <section className="rounded-[24px] bg-white p-6 shadow-[0px_10px_30px_0px_rgba(15,79,87,0.06)] xl:max-h-[calc(100vh-14rem)] xl:overflow-y-auto xl:scrollbar-hidden">
          <div>
            <p className="text-sm font-medium text-[var(--color-brand-text-muted)]">Điều hướng</p>
            <h2 className="mt-2 text-2xl font-semibold text-[var(--color-brand-text-primary)]">
              Các JD tải lên gần đây
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--color-brand-text-body)]">
              Mở nhanh bất kỳ bản phân tích JD gần đây nào từ mã đã được lưu.
            </p>
          </div>

          <div className="mt-5 flex flex-col gap-3">
            {recentUploads.length ? (
              recentUploads.map((item: JDRecentItem) => (
                <AppLink
                  className="rounded-[18px] border border-[var(--color-brand-input-border)] p-4 transition duration-200 hover:-translate-y-0.5 hover:border-[var(--color-brand-primary)] hover:bg-[var(--color-primary-50)]"
                  href={buildJDRoute(item.jd_id)}
                  key={item.jd_id}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-base font-semibold text-[var(--color-brand-text-primary)]">
                        {item.job_title ?? item.file_name}
                      </p>
                      <p className="mt-1 text-sm text-[var(--color-brand-text-muted)]">{item.file_name}</p>
                    </div>
                    <span className="rounded-full bg-[var(--color-primary-50)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]">
                      {item.status}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-[var(--color-brand-text-muted)]">
                    {formatVietnamDateTime(item.created_at)}
                  </p>
                </AppLink>
              ))
            ) : (
              <p className="rounded-[18px] border border-dashed border-[var(--color-brand-input-border)] p-4 text-sm text-[var(--color-brand-text-muted)]">
                Chưa có JD nào được tải lên. Hãy tải tài liệu đầu tiên để tạo danh sách này.
              </p>
            )}
          </div>
        </section>
      </div>
    </main>
  )
}

function buildJDRoute(jdId: string): Route {
  return `/dashboard/jd/${jdId}` as Route
}
